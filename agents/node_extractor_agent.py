import logging
import json
import json_repair
from typing import Dict, Optional, List, Any

from agents.base_agent import BaseAgent
from agents.query_builder_agent import QueryBuilderAgent
import concurrent.futures
from core.llm_service import LLMService, LLMServiceError
from core.retrieval_service import RetrievalService, RetrievalServiceError
from core.workflow_state import WorkflowState, TASK_TYPE_EXTRACT_NODE
from config import settings
from core.json_utils import clean_and_parse_json

from core.posterior_verifier import PosteriorVerifier

logger = logging.getLogger(__name__)

class NodeExtractorAgentError(Exception):
    """Custom exception for NodeExtractorAgent errors."""
    pass

class NodeExtractorAgent(BaseAgent):
    """
    负责从特定产业节点抽取详细结构化信息的智能体。
    更新 WorkflowState 中的抽取数据。
    """

    def __init__(self,
                 llm_service: LLMService,
                 retrieval_service: RetrievalService,
                 prompt_template: Optional[str] = None):
        super().__init__(agent_name="NodeExtractorAgent", llm_service=llm_service)
        self.retrieval_service = retrieval_service
        
        # Initialize PosteriorVerifier if reranker is available
        # This part is now handled by the new self.verifier, but keeping for potential future use or if reranker is used elsewhere.
        self.posterior_verifier = None
        if hasattr(self.retrieval_service, 'reranker_service') and self.retrieval_service.reranker_service:
            self.posterior_verifier = PosteriorVerifier(self.retrieval_service.reranker_service)
        else:
            logger.warning(f"[{self.agent_name}] RerankerService missing, PosteriorVerifier disabled.")
        self.prompt_template = prompt_template or settings.NODE_EXTRACTOR_PROMPT
        
        # Phase 2 Components
        self.query_builder = QueryBuilderAgent(llm_service)
        self.verifier = PosteriorVerifier(llm_service) # Logic now in verifier
        
        if not self.llm_service:
            raise NodeExtractorAgentError("需要 LLMService。")
        if not self.retrieval_service:
            raise NodeExtractorAgentError("需要 RetrievalService。")
        if not self.prompt_template:
            raise NodeExtractorAgentError("需要 Prompt 模板。")

    def execute_task(self, workflow_state: WorkflowState, task: Dict) -> None:
        task_id = workflow_state.current_processing_task_id
        payload = task.get('payload', {})
        node_name = payload.get('node_name')
        category = payload.get('category', 'unknown')
        current_depth = payload.get('depth', 0)
        max_depth = payload.get('max_depth', 2) # Default limit to prevent infinite loops
        
        logger.info(f"[{self.agent_name}] 开始抽取节点信息: {node_name} (分类: {category})")
        
        if not node_name:
            err_msg = "任务载荷中未找到节点名称 (node_name)。"
            logger.error(err_msg)
            if task_id: workflow_state.complete_task(task_id, err_msg, status='failed')
            raise NodeExtractorAgentError(err_msg)

        try:
            user_topic = workflow_state.user_topic

            # --- Step 1: Query Generation (Query Builder) ---
            # 使用 QueryBuilder 生成专用的 Vector 和 BM25 查询
            queries = self.query_builder.generate_queries(node_name, user_topic)
            vector_queries = queries.get('vector_queries', [])
            bm25_queries = queries.get('bm25_queries', [])

            # --- Step 2: Hybrid Retrieval (Retrieval Service) ---
            # 使用分离的查询列表进行检索
            retrieved_docs = self.retrieval_service.retrieve(
                query_texts=vector_queries,
                bm25_query_texts=bm25_queries,
                final_top_n=settings.DEFAULT_RETRIEVAL_FINAL_TOP_N
            )
            
            # Format context for LLM extraction
            context_text = ""
            for i, doc in enumerate(retrieved_docs):
                # doc包含 'parent_text' (上下文) 和 'child_text_preview'
                content = doc.get("parent_text") or doc.get("document", "")
                source = doc.get("source_document_name", "Unknown")
                context_text += f"\n[Document {i+1}] (Source: {source})\n{content}\n"

            logger.info(f"[{self.agent_name}] Retrieved {len(retrieved_docs)} docs for extraction.")

            # --- Step 3: Candidate Extraction (LLM) ---
            prompt = self.prompt_template.format(
                node_name=node_name,
                retrieved_content=context_text
            )

            # 调用 LLM (Log simplified)
            logger.info(f"[{self.agent_name}] 正在调用 LLM 进行信息抽取 (Docs: {len(retrieved_docs)})...")
            logger.debug(f"Extraction Prompt for {node_name}: {prompt[:200]}...") # Log full prompt only in DEBUG

            raw_response = self.llm_service.chat(
                query=prompt,
                system_prompt="你是一个精准的数据抽取助手。"
            )

            # 解析 JSON
            extracted_data = clean_and_parse_json(raw_response, context=f"extraction_{node_name}")
            
            # Handling edge case where LLM returns a list
            if isinstance(extracted_data, list):
                if extracted_data and isinstance(extracted_data[0], dict):
                    extracted_data = extracted_data[0]
                else:
                    extracted_data = None

            # JSON Parsing Failure Handling
            if not extracted_data or not isinstance(extracted_data, dict):
                logger.error(f"[{self.agent_name}] 无法为 {node_name} 解析 JSON。保存原始输出以供调试。")
                extracted_data = {
                    "entity_name": node_name,
                    "description": "JSON 解析失败",
                    "_raw_llm_output": raw_response, # User requirement: Keep raw output
                    "error": "JSON parse error"
                }
            else:
                # 4.1 Check for Empty Node (All fields empty)
                # If only entity_name is present, treat as empty
                meaningful_keys = ['input_elements', 'output_products', 'key_technologies', 'representative_companies', 'description']
                has_content = any(extracted_data.get(k) and str(extracted_data.get(k)).strip() for k in meaningful_keys)
                
                if not has_content:
                    logger.warning(f"[{self.agent_name}] 节点 '{node_name}' 抽取结果为空 (无实质信息)。跳过保存。")
                    if task_id: workflow_state.complete_task(task_id, f"节点 '{node_name}' 无有效信息，已忽略。", status='success')
                    return # Skip saving and recursion

                # 4.2 溯源匹配 (Source Tracing & Evidence Matching)
                try:
                    logger.info(f"[{self.agent_name}] 正在为节点 '{node_name}' 进行溯源匹配...")
                    extracted_data = self._match_evidence(node_name, extracted_data, retrieved_docs)
                except Exception as e:
                    logger.error(f"[{self.agent_name}] 溯源匹配错误: {e}", exc_info=True)
                    extracted_data['source_tracing_error'] = str(e)


            # 5. Expand Graph (Recursive Extraction)
            if current_depth < max_depth:
                self._expand_nodes(extracted_data, workflow_state, current_depth, max_depth)

            # 6. 更新工作流状态
            workflow_state.update_node_details(node_name, extracted_data)

            success_msg = f"节点 '{node_name}' 数据抽取完成。"
            logger.info(f"[{self.agent_name}] {success_msg}")
            if task_id: workflow_state.complete_task(task_id, success_msg, status='success')

        except Exception as e:
            err_msg = f"节点 '{node_name}' 抽取失败: {e}"
            logger.error(err_msg, exc_info=True)
            if task_id: workflow_state.complete_task(task_id, err_msg, status='failed')
            raise NodeExtractorAgentError(err_msg) from e

    def _match_evidence(self, node_name: str, extracted_data: Dict[str, Any], retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        使用 PosteriorVerifier 对提取出的每个细节进行严格溯源。
        验证失败的条目将被标记或移除。
        """
        if not retrieved_docs or not self.verifier:
            logger.warning(f"[{self.agent_name}] 无法进行后验溯源 (Docs={len(retrieved_docs)}, Verifier={self.verifier is not None})")
            return extracted_data

        fields_to_trace = [
            "input_elements", 
            "output_products", 
            "key_technologies", 
            "representative_companies"
        ]
        
        evidence_details_map = {} # Parallel map for detailed evidence
        filtered_items_map = {}
        
        for field in fields_to_trace:
            items = extracted_data.get(field)
            if not items or not isinstance(items, list):
                continue
            
            verified_items = []
            filtered_field_items = []

            # Clean items for verification
            items_cleaned = [item for item in items if isinstance(item, str) and item.strip()]
            if not items_cleaned:
                extracted_data[field] = []
                continue

            # 4.3.2 验证 (Posterior Verification) - Parallelized
            # Optimization (Phase 5): Use ThreadPoolExecutor for parallel verification
            
            # Define helper function for parallel execution
            def verify_single_item(item):
                if field == 'representative_companies':
                    claim = f"{item}是{node_name}环节的代表性企业。"
                else:
                    claim = f"{node_name}的{field}包括{item}。" # Generic claim
                
                # verify_claim Returns {verified, score, evidence_ref, reason}
                v_res = self.verifier.verify_claim(claim, retrieved_docs, focus_entity=item)
                return item, v_res

            # Select items to verify
            items_to_verify = list(items_cleaned)
            
            # Execute in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all tasks
                future_to_item = {executor.submit(verify_single_item, item): item for item in items_to_verify}
                
                for future in concurrent.futures.as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        _, verify_result = future.result()
                        
                        if verify_result['verified']:
                            verified_items.append(item)
                            
                            # Inject Evidence
                            if verify_result['evidence_ref']:
                                # Initialize detail map if first time
                                if field not in evidence_details_map:
                                    evidence_details_map[field] = {}
                                
                                evidence_details_map[field][item] = {
                                    "source_id": verify_result['evidence_ref']['source_id'],
                                    "key_evidence": verify_result['evidence_ref']['key_evidence'],
                                    "score": verify_result['score']
                                }
                            logger.debug(f"[{self.agent_name}] Item verified: '{item}' (Score: {verify_result['score']:.2f})")
                        else:
                            reason = verify_result.get('reason', 'Unknown reason')
                            filtered_field_items.append({
                                "value": item,
                                "reason": reason,
                                "score": verify_result.get('score', 0.0)
                            })
                            logger.debug(f"[Verifier] Rejected '{item}' (Score: {verify_result['score']:.2f})")

                    except Exception as exc:
                        logger.error(f"[Verifier] Exception checking item '{item}': {exc}")
            
            # Update the list with only verified items
            extracted_data[field] = verified_items
            if filtered_field_items:
                filtered_items_map[field] = filtered_field_items

        extracted_data['evidence_details'] = evidence_details_map
        extracted_data['filtered_items'] = filtered_items_map
        
        # Verify Description separately
        desc = extracted_data.get("description", "")
        if desc:
             desc_ver = self.verifier.verify_claim(f"{node_name}的描述: {desc}", retrieved_docs)
             if desc_ver['verified']:
                 if 'description' not in evidence_details_map:
                      evidence_details_map['description'] = {}
                 # Description is single value, but map expects key. Use 'self' or similar?
                 # Or just put it directly under description key if consistent
                 evidence_details_map['description'] = desc_ver['evidence_ref']

        return extracted_data

    def _expand_nodes(self, extracted_data: Dict[str, Any], workflow_state: WorkflowState, current_depth: int, max_depth: int):
        """
        Analyzes the extracted data to find new candidate nodes and adds them to the workflow.
        Structure mapping:
          - input_elements -> upstream
          - output_products -> downstream
        """
        if not extracted_data:
            return

        expansion_rules = [
            ('input_elements', 'upstream'),
            ('output_products', 'downstream')
        ]

        logger.info(f"[{self.agent_name}] Checking for node expansion (Depth: {current_depth}/{max_depth})...")

        new_nodes_count = 0
        for field, category in expansion_rules:
            items = extracted_data.get(field, [])
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, str) or not item.strip():
                    continue
                
                # Check if it's a valid candidate (simple heuristic for now: length check)
                if len(item) > 20: # Skip very long descriptions masquerading as entities
                    continue

                # Add to workflow
                # add_node_to_structure returns True if it's a NEW node
                if workflow_state.add_node_to_structure(item, category):
                    workflow_state.add_task(
                        task_type=TASK_TYPE_EXTRACT_NODE,
                        payload={
                            'node_name': item, 
                            'category': category,
                            'depth': current_depth + 1,
                            'max_depth': max_depth
                        },
                        priority=1 # High priority to explore deeper
                    )
                    new_nodes_count += 1
        
        if new_nodes_count > 0:
            logger.info(f"[{self.agent_name}] Expanded graph with {new_nodes_count} new nodes.")

