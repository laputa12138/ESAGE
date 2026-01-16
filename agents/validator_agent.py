import logging
import json
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent
from core.llm_service import LLMService
from core.workflow_state import WorkflowState
from core.json_utils import clean_and_parse_json

logger = logging.getLogger(__name__)

class ValidatorAgentError(Exception):
    pass

class ValidatorAgent(BaseAgent):
    """
    负责清洗和优化产业链图谱的智能体。
    功能：
    1. 识别并合并同义词节点（如“光伏玻璃”与“太阳能光伏玻璃”）。
    2. 过滤非物理产业链环节的无关节点（如“政策支持”、“市场分析”）。
    """
    
    def __init__(self, llm_service: LLMService):
        super().__init__(agent_name="ValidatorAgent", llm_service=llm_service)
        
        self.merge_prompt_template = """
你是一位产业链图谱数据治理专家。你的任务是分析给定的“节点列表”，找出其中含义完全相同的同义词，以及不属于产业链物理环节的无效词。

【背景】
用户正在抽取“{user_topic}”行业的产业链图谱。
节点列表包含了从文档中自动抽取的候选项，可能存在同义词重复（如“A”和“A的别名”）或噪音（如“行业政策”、“市场规模”等非环节词）。

【节点列表】
{node_list}

【任务要求】
请输出一个 JSON 对象，包含以下两个字段：
1. `merge_pairs`: 同义词合并对的列表。每对包含 `keep`（保留的标准名）和 `drop`（被合并的别名）。
   - 保留名称更短、更通用、更符合行业惯例的那个。
   - 只有在非常确定它们指代同一物理环节时才合并。
2. `invalid_nodes`: 需要删除的无效节点列表。
   - 删除抽象概念（“...技术”、“...趋势”、“...政策”）、泛指（“上游”、“下游”）、形容词（“高效的...”）或与产业链物理实体无关的词。

【输出格式】
```json
{{
    "merge_pairs": [
        {{"keep": "光伏玻璃", "drop": "太阳能光伏玻璃"}},
        {{"keep": "EVA胶膜", "drop": "乙烯-醋酸乙烯共聚物胶膜"}}
    ],
    "invalid_nodes": ["行业政策", "市场前景", "上游环节", "相关企业"]
}}
```
如果列表为空，请返回空数组。
"""

    def execute_task(self, workflow_state: WorkflowState, task_payload: Dict) -> None:
        """
        执行验证任务。通常在抽取工作流的末尾调用。
        """
        task_id = workflow_state.current_processing_task_id
        logger.info(f"[{self.agent_name}] 开始执行图谱验证与清洗...")
        
        try:
            # 1. 获取当前所有节点
            all_nodes = list(workflow_state.industry_graph['node_details'].keys())
            if not all_nodes:
                logger.warning(f"[{self.agent_name}] 图谱为空，无需验证。")
                if task_id: workflow_state.complete_task(task_id, "图谱为空，跳过验证。", status='success')
                return

            # 如果节点太多，可能需要分批处理？目前假设 LLM 上下文足够（几百个词应该没问题）
            # 转为字符串列表
            node_list_str = json.dumps(all_nodes, ensure_ascii=False)
            
            # 2. 调用 LLM
            prompt = self.merge_prompt_template.format(
                user_topic=workflow_state.user_topic,
                node_list=node_list_str
            )
            
            logger.info(f"[{self.agent_name}] 正在调用 LLM 分析 {len(all_nodes)} 个节点...")
            response = self.llm_service.chat(prompt, system_prompt="你是一位严谨的数据治理专家。")
            
            # 3. 解析结果
            result = clean_and_parse_json(response)
            if not result:
                logger.warning(f"[{self.agent_name}] 无法解析 LLM 响应，跳过验证。")
                if task_id: workflow_state.complete_task(task_id, "验证失败（解析错误）", status='failed')
                return
                
            merge_pairs = result.get('merge_pairs', [])
            invalid_nodes = result.get('invalid_nodes', [])
            
            stats = {"merged": 0, "removed": 0}

            # 4. 执行合并
            for pair in merge_pairs:
                keep = pair.get('keep')
                drop = pair.get('drop')
                if keep and drop and keep != drop:
                    if workflow_state.merge_nodes(keep, drop):
                        stats['merged'] += 1
                        logger.info(f"[{self.agent_name}] 合并: {drop} -> {keep}")

            # 5. 执行删除
            for node in invalid_nodes:
                if workflow_state.remove_node(node):
                    stats['removed'] += 1
                    logger.info(f"[{self.agent_name}] 删除无效节点: {node}")

            success_msg = f"验证完成。合并了 {stats['merged']} 对节点，删除了 {stats['removed']} 个无效节点。"
            logger.info(f"[{self.agent_name}] {success_msg}")
            
            if task_id: workflow_state.complete_task(task_id, success_msg, status='success')

        except Exception as e:
            err_msg = f"验证过程出错: {e}"
            logger.error(f"[{self.agent_name}] {err_msg}", exc_info=True)
            if task_id: workflow_state.complete_task(task_id, err_msg, status='failed')
            raise ValidatorAgentError(err_msg) from e
