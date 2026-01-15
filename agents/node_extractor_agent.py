import logging
import json
import json_repair
from typing import Dict, Optional, List, Any

from agents.base_agent import BaseAgent
from core.llm_service import LLMService, LLMServiceError
from core.retrieval_service import RetrievalService, RetrievalServiceError
from core.workflow_state import WorkflowState, TASK_TYPE_EXTRACT_NODE
from config import settings as app_settings
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
        self.posterior_verifier = None
        if hasattr(self.retrieval_service, 'reranker_service') and self.retrieval_service.reranker_service:
            self.posterior_verifier = PosteriorVerifier(self.retrieval_service.reranker_service)
        else:
            logger.warning(f"[{self.agent_name}] RerankerService missing, PosteriorVerifier disabled.")
        self.prompt_template = prompt_template or app_settings.NODE_EXTRACTOR_PROMPT
        
        if not self.llm_service:
            raise NodeExtractorAgentError("需要 LLMService。")
        if not self.retrieval_service:
            raise NodeExtractorAgentError("需要 RetrievalService。")
        if not self.prompt_template:
            raise NodeExtractorAgentError("需要 Prompt 模板。")

    def execute_task(self, workflow_state: WorkflowState, task_payload: Dict) -> None:
        task_id = workflow_state.current_processing_task_id
        node_name = task_payload.get('node_name')
        category = task_payload.get('category', 'unknown')
        
        logger.info(f"[{self.agent_name}] 开始抽取节点信息: {node_name} (分类: {category})")
        
        if not node_name:
            err_msg = "任务载荷中未找到节点名称 (node_name)。"
            logger.error(err_msg)
            if task_id: workflow_state.complete_task(task_id, err_msg, status='failed')
            raise NodeExtractorAgentError(err_msg)

        try:
            # 1. 检索上下文
            user_topic = workflow_state.user_topic
            query = f"{user_topic} {node_name} 详细信息" # Localized query
            
            logger.info(f"[{self.agent_name}] 正在为节点 '{node_name}' 检索相关文档...")
            retrieved_docs = self.retrieval_service.retrieve(
                query_texts=[query, node_name],
                final_top_n=5 
            )
            
            if not retrieved_docs:
                logger.warning(f"[{self.agent_name}] 未找到关于 {node_name} 的相关文档。跳过抽取。")
                # Directly return None/Empty to indicate valid failure to find data
                # WorkflowState should verify and prune these later.
                workflow_state.update_node_details(node_name, None) 
                
                msg = f"未找到节点 '{node_name}' 的参考文档，已跳过。"
                if task_id: workflow_state.complete_task(task_id, msg, status='success') # Success in processing, but result is empty
                return
            else:
                context_summary = "\n".join([f"--- Source: {d.get('source_document_name', 'Unknown')} ---\n{d.get('document', '')}" for d in retrieved_docs])
                logger.info(f"[{self.agent_name}] 检索到 {len(retrieved_docs)} 篇相关文档。")

            # 2. 构建 Prompt
            prompt_formatted = self.prompt_template.format(
                node_name=node_name,
                retrieved_content=context_summary
            )

            # 3. 调用 LLM
            logger.info(f"[{self.agent_name}] 正在调用 LLM 进行信息抽取...")
            raw_response = self.llm_service.chat(
                query=prompt_formatted,
                system_prompt="你是一个精准的数据抽取助手。" # Localized System Prompt
            )

            # 4. 解析 JSON
            extracted_data = clean_and_parse_json(raw_response, context=f"extraction_{node_name}")
            
            # Handling edge case where LLM returns a list instead of a dict
            if isinstance(extracted_data, list):
                if extracted_data and isinstance(extracted_data[0], dict):
                    logger.warning(f"[{self.agent_name}] Parsed JSON is a list, taking the first item for {node_name}.")
                    extracted_data = extracted_data[0]
                else:
                    logger.warning(f"[{self.agent_name}] Parsed JSON is a list but empty or invalid content for {node_name}. Treating as failure.")
                    extracted_data = None

            if not extracted_data or not isinstance(extracted_data, dict):
                logger.warning(f"[{self.agent_name}] 无法为 {node_name} 解析 JSON 或格式不正确。保存空记录。")
                extracted_data = {
                    "entity_name": node_name,
                    "description": "抽取失败或无数据。",
                    "error": "JSON parse error or invalid format"
                }
            else:
                # 4.1 溯源匹配 (Source Tracing & Evidence Matching)
                # 只有成功解析且非空时才进行匹配
                try:
                    logger.info(f"[{self.agent_name}] 正在为节点 '{node_name}' 进行溯源匹配...")
                    extracted_data = self._match_evidence(extracted_data, retrieved_docs)
                except Exception as e:
                    logger.error(f"[{self.agent_name}] 溯源匹配过程中发生错误: {e}", exc_info=True)
                    # 即使匹配失败，也保留原始提取数据，避免任务完全失败
                    extracted_data['source_tracing_error'] = str(e)

            # 5. Expand Graph (Recursive Extraction)
            current_depth = task_payload.get('depth', 0)
            max_depth = task_payload.get('max_depth', 2) # Default limit to prevent infinite loops

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

    def _match_evidence(self, extracted_data: Dict[str, Any], retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        使用 PosteriorVerifier 对提取出的每个细节进行严格溯源。
        验证失败的条目将被标记或移除。
        """
        if not retrieved_docs or not self.posterior_verifier:
            logger.warning(f"[{self.agent_name}] 无法进行后验溯源 (Docs={len(retrieved_docs)}, Verifier={self.posterior_verifier is not None})")
            return extracted_data

        fields_to_trace = [
            "input_elements", 
            "output_products", 
            "key_technologies", 
            "representative_companies"
        ]
        
        evidence_refs_map = {}
        filtered_items_map = {}
        
        for field in fields_to_trace:
            items = extracted_data.get(field)
            if not items or not isinstance(items, list):
                continue
            
            verified_items = []
            filtered_field_items = []
            
            for item in items:
                if not isinstance(item, str) or not item.strip():
                    continue
                    
                # 调用 PosteriorVerifier 进行验证
                verify_result = self.posterior_verifier.verify_item(item, retrieved_docs)
                
                if verify_result['verified']:
                    verified_items.append(item)
                    evidence_refs_map[item] = verify_result['evidence_refs']
                    logger.debug(f"[{self.agent_name}] Item verified: '{item}' -> {len(verify_result['evidence_refs'])} evidence(s)")
                else:
                    reason = verify_result.get('reason', 'Unknown rejection reason')
                    logger.info(f"[{self.agent_name}] Item REJECTED: '{item}' Reason: {reason}")
                    filtered_field_items.append({
                        "value": item,
                        "reason": reason
                    })
            
            # Update the list with only verified items
            extracted_data[field] = verified_items
            if filtered_field_items:
                filtered_items_map[field] = filtered_field_items

        extracted_data['evidence_refs'] = evidence_refs_map
        extracted_data['filtered_items'] = filtered_items_map
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

