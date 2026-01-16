import logging
import json
from typing import Dict, List, Any, Optional

from agents.base_agent import BaseAgent
from core.llm_service import LLMService
from core.json_utils import clean_and_parse_json
from config import settings

logger = logging.getLogger(__name__)

class QueryBuilderAgentError(Exception):
    """QueryBuilderAgent 专用异常类"""
    pass

class QueryBuilderAgent(BaseAgent):
    """
    负责生成混合检索查询的智能体。
    旨在为给定的产业链环节生成：
    1. 语义向量查询 (Vector Queries)：捕捉隐含语义。
    2. 关键词查询 (BM25 Queries)：捕捉精准术语。
    """

    def __init__(self, llm_service: LLMService):
        """
        初始化 QueryBuilderAgent。
        Args:
            llm_service: LLM 服务实例，用于生成查询。
        """
        super().__init__(agent_name="QueryBuilderAgent", llm_service=llm_service)
        self.prompt_template = settings.DEFAULT_QUERY_BUILDER_PROMPT

    def generate_queries(self, node_name: str, user_topic: str) -> Dict[str, List[str]]:
        """
        为指定节点生成检索查询。

        Args:
            node_name (str): 节点名称 (如 "光伏玻璃")。
            user_topic (str): 行业主题 (如 "光伏产业")。

        Returns:
            Dict[str, List[str]]: 包含 'vector_queries' 和 'bm25_queries' 的字典。
            例如:
            {
                "vector_queries": ["光伏玻璃生产工艺", ...],
                "bm25_queries": ["光伏玻璃", "超白玻璃"]
            }
        """
        logger.info(f"[{self.agent_name}] 正在为节点 '{node_name}' (主题: {user_topic}) 生成检索查询...")

        try:
            # 1. 格式化 Prompt
            prompt = self.prompt_template.format(
                node_name=node_name,
                user_topic=user_topic
            )

            # 2. 调用 LLM
            # 使用较低的 temperature 确保生成精准的关键词
            raw_response = self.llm_service.chat(
                query=prompt,
                system_prompt="你是一个精准的搜索专家。"
            )

            # 3. 解析 JSON
            parsed_result = clean_and_parse_json(raw_response)
            
            if not parsed_result:
                logger.warning(f"[{self.agent_name}] JSON 解析失败，将使用默认查询策略。")
                return self._fallback_queries(node_name, user_topic)

            vector_queries = parsed_result.get("vector_queries", [])
            bm25_queries = parsed_result.get("bm25_queries", [])

            # 简单的验证
            if not vector_queries:
                vector_queries = [f"{user_topic} {node_name} 详细信息"]
            if not bm25_queries:
                bm25_queries = [node_name]

            logger.info(f"[{self.agent_name}] 生成完成。Vector: {len(vector_queries)}, BM25: {len(bm25_queries)}")
            return {
                "vector_queries": vector_queries,
                "bm25_queries": bm25_queries
            }

        except Exception as e:
            logger.error(f"[{self.agent_name}] 查询生成过程出错: {e}", exc_info=True)
            return self._fallback_queries(node_name, user_topic)

        """
        当 LLM 生成失败时的回退策略。
        Optimization: Explicitly add company-related terms.
        """
        logger.info(f"[{self.agent_name}] 使用回退查询策略。")
        return {
            "vector_queries": [
                f"{user_topic} {node_name} 定义与描述", 
                f"{node_name} 的上下游关系",
                f"{node_name} 行业代表性企业及龙头公司"
            ],
            "bm25_queries": [
                node_name, 
                f"{node_name}企业", 
                f"{node_name}上市公司"
            ]
        }
