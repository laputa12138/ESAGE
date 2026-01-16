import logging
import json
import json_repair
from typing import Dict, Optional, List, Any
import uuid

from agents.base_agent import BaseAgent
from core.llm_service import LLMService, LLMServiceError
from core.retrieval_service import RetrievalService, RetrievalServiceError
from core.workflow_state import WorkflowState, TASK_TYPE_EXTRACT_NODE
from config import settings as app_settings
from core.json_utils import clean_and_parse_json

logger = logging.getLogger(__name__)

class StructurePlannerAgentError(Exception):
    """Custom exception for StructurePlannerAgent errors."""
    pass

class StructurePlannerAgent(BaseAgent):
    """
    负责分析产业/主题并规划图谱结构（上游、中游、下游）及识别节点的智能体。
    更新 WorkflowState 中的产业图谱并创建抽取任务。
    """

    def __init__(self,
                 llm_service: LLMService,
                 retrieval_service: RetrievalService,
                 prompt_template: Optional[str] = None,
                 system_prompt: Optional[str] = None):
        super().__init__(agent_name="StructurePlannerAgent", llm_service=llm_service)
        self.retrieval_service = retrieval_service
        self.prompt_template = prompt_template or app_settings.INDUSTRY_STRUCTURE_PLANNER_PROMPT
        self.system_prompt = system_prompt or "你是一位专注于产业链图谱规划的产业分析专家。" # Localized System Prompt
        
        if not self.llm_service:
            raise StructurePlannerAgentError("需要 LLMService。")
        if not self.retrieval_service:
            raise StructurePlannerAgentError("需要 RetrievalService。")
        if not self.prompt_template:
            raise StructurePlannerAgentError("需要 Prompt 模板。")

    def _execute_global_retrieval(self, user_topic: str) -> List[Dict[str, Any]]:
        """
        执行检索过程以收集关于该行业的广泛背景信息。
        """
        logger.info(f"[{self.agent_name}] 正在为主题检索全局上下文: {user_topic}")
        try:
            # 使用中文查询扩展
            queries = [user_topic, f"{user_topic} 产业链", f"{user_topic} 上游 中游 下游"]
            
            retrieved_docs = self.retrieval_service.retrieve(
                query_texts=queries,
                final_top_n=10 
            )
            logger.info(f"[{self.agent_name}] 检索到 {len(retrieved_docs)} 篇相关文档。")
            return retrieved_docs
        except RetrievalServiceError as e:
            logger.error(f"[{self.agent_name}] 检索失败: {e}")
            raise StructurePlannerAgentError(f"检索失败: {e}") from e

    def execute_task(self, workflow_state: WorkflowState, task: Dict) -> None:
        task_id = workflow_state.current_processing_task_id
        task_payload = task.get('payload', {})
        user_topic = task_payload.get('user_topic')
        
        logger.info(f"[{self.agent_name}] 开始规划产业结构: {user_topic}")
        
        if not user_topic:
            err_msg = "任务载荷中未找到用户主题 (user_topic)。"
            logger.error(err_msg)
            if task_id: workflow_state.complete_task(task_id, err_msg, status='failed')
            raise StructurePlannerAgentError(err_msg)

        try:
            # 1. 检索全局上下文
            retrieved_docs = self._execute_global_retrieval(user_topic)
            
            # 准备上下文摘要
            context_summary = "\n".join([f"- {d.get('document', '')[:500]}..." for d in retrieved_docs])
            
            # 2. 构建 Prompt
            # 手动拼接上下文摘要到 prompt 中
            full_prompt = self.prompt_template.format(user_topic=user_topic)
            full_prompt += f"\n\n基于以下参考文档摘要进行分析：\n{context_summary}"

            # 3. 调用 LLM
            logger.info(f"[{self.agent_name}] 正在调用 LLM 进行结构规划...")
            raw_response = self.llm_service.chat(
                query=full_prompt, 
                system_prompt=self.system_prompt
            )

            # 4. 解析 JSON
            logger.info(f"[{self.agent_name}] 正在解析 LLM 响应...")
            parsed_structure = clean_and_parse_json(raw_response)
            
            if not parsed_structure:
                 raise StructurePlannerAgentError("无法从 LLM 响应中解析出产业结构 JSON数据。")

            # 验证结构
            required_keys = ['upstream', 'midstream', 'downstream']
            if not all(k in parsed_structure for k in required_keys):
                raise StructurePlannerAgentError(f"结构规划结果缺失必要的键: {required_keys}")

            # 5. 更新工作流状态
            workflow_state.initialize_industry_graph(parsed_structure)

            # 6. 创建节点抽取任务
            total_tasks_added = 0
            for category in required_keys:
                nodes = parsed_structure.get(category, [])
                for node in nodes:
                    workflow_state.add_task(
                        task_type=TASK_TYPE_EXTRACT_NODE,
                        payload={
                            'node_name': node, 
                            'category': category,
                            'depth': 0, # Initial planned nodes are depth 0
                            'max_depth': task_payload.get('max_recursion_depth', 2)
                        },
                        priority=1
                    )
                    total_tasks_added += 1

            success_msg = f"结构规划完成。已添加 {total_tasks_added} 个节点抽取任务。"
            logger.info(f"[{self.agent_name}] {success_msg}")
            if task_id: workflow_state.complete_task(task_id, success_msg, status='success')

        except Exception as e:
            err_msg = f"结构规划失败: {e}"
            logger.error(f"[{self.agent_name}] {err_msg}", exc_info=True)
            if task_id: workflow_state.complete_task(task_id, err_msg, status='failed')
            raise StructurePlannerAgentError(err_msg) from e
