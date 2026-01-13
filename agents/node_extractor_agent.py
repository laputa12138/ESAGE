import logging
import json
import json_repair
from typing import Dict, Optional, List, Any

from agents.base_agent import BaseAgent
from core.llm_service import LLMService, LLMServiceError
from core.retrieval_service import RetrievalService, RetrievalServiceError
from core.workflow_state import WorkflowState
from config import settings as app_settings
from core.json_utils import clean_and_parse_json

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

            # 5. 更新工作流状态
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
        使用 Reranker 对提取出的每个细节进行溯源，找到最相关的来源文档和证据片段。
        
        Args:
            extracted_data: LLM 提取出的 JSON 数据。
            retrieved_docs: 检索回来的文档列表（即 RAG 上下文）。
            
        Returns:
            更新后的提取数据，包含 'sources' 和 'evidence_snippets' 字段。
        """
        if not retrieved_docs:
            return extracted_data

        # 需要进行溯源的字段列表
        fields_to_trace = [
            "input_elements", 
            "output_products", 
            "key_technologies", 
            "representative_companies"
        ]
        
        sources = {}
        evidence_snippets = {}
        
        # 准备文档内容列表供 Reranker 使用
        # 注意：这里我们使用 parent_text 作为完整的文档内容进行匹配
        doc_contents = [doc.get('document', '') for doc in retrieved_docs]
        doc_names = [doc.get('source_document_name', 'Unknown') for doc in retrieved_docs]
        
        reranker = getattr(self.retrieval_service, 'reranker_service', None)
        
        if not reranker:
            logger.warning(f"[{self.agent_name}] RerankerService 不可用，无法进行精确溯源匹配。跳过匹配步骤。")
            return extracted_data

        for field in fields_to_trace:
            items = extracted_data.get(field)
            if not items or not isinstance(items, list):
                continue
            
            for item in items:
                if not isinstance(item, str) or not item.strip():
                    continue
                    
                # 使用 item 作为 query，在 retrieved_docs 中寻找最相关的文档
                try:
                    # rerank 接受 query 和 documents 列表
                    # 返回按分数排序的结果 list
                    rerank_results = reranker.rerank(
                        query=item,
                        documents=doc_contents,
                        top_n=1
                    )
                    
                    if rerank_results:
                        best_match = rerank_results[0]
                        best_idx = best_match['original_index']
                        best_score = best_match['relevance_score']
                        
                        # 可以设置一个阈值，如果分数太低则认为没有来源 (Optional)
                        # if best_score > 0.3: 
                        source_name = doc_names[best_idx]
                        evidence_text = doc_contents[best_idx]
                        
                        sources[item] = source_name
                        evidence_snippets[item] = evidence_text
                        
                except Exception as e:
                    logger.warning(f"[{self.agent_name}] 为条目 '{item}' 进行 Rerank 匹配时失败: {e}")
                    continue

        extracted_data['sources'] = sources
        extracted_data['evidence_snippets'] = evidence_snippets
        
        return extracted_data
