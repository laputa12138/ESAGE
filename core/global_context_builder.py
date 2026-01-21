import logging
from typing import Optional
from core.llm_service import LLMService
from core.retrieval_service import RetrievalService
from config import settings

logger = logging.getLogger(__name__)

class GlobalContextBuilder:
    """
    负责构建“全局产业上下文”（即知识索引）。
    在抽取任务开始前，先扫描一部分文档，让 LLM 对当前数据库的内容、粒度有一个整体的认知。
    """

    def __init__(self, llm_service: LLMService, retrieval_service: RetrievalService):
        self.llm_service = llm_service
        self.retrieval_service = retrieval_service
        self.prompt_template = settings.GLOBAL_CONTEXT_PROMPT

    def build_context(self, user_topic: str) -> str:
        """
        检索宽泛的文档，生成全局上下文摘要。
        """
        logger.info(f"[GlobalContextBuilder] 正在为主题 '{user_topic}' 构建全局上下文...")

        # 1. Broad Retrieval
        # 使用泛化的查询（如主题本身）检索一批文档
        # 我们假设 retrieval_service.retrieve 支持简单的字符串列表
        queries = [
            f"{user_topic} 产业链结构",
            f"{user_topic} 关键环节",
            f"{user_topic} 上游原材料 中游制造 下游应用",
            f"{user_topic} 行业概览"
        ]
        
        # 检索较多文档以覆盖全貌 (e.g., 20 docs)
        # Note: We use empty bm25_queries list as we focus on semantic overview mainly, 
        # but retrieval_service.retrieve expects lists.
        try:
            retrieved_docs = self.retrieval_service.retrieve(
                query_texts=queries,
                bm25_query_texts=[user_topic], # 简单的关键词匹配
                final_top_n=20 # 检索较多文档
            )
        except Exception as e:
            logger.error(f"[GlobalContextBuilder] 检索失败: {e}")
            return "无法获取全局上下文 (检索失败)。"

        if not retrieved_docs:
            logger.warning("[GlobalContextBuilder] 未检索到文档，无法构建上下文。")
            return "数据库中未找到相关文档。"

        # 2. Format Context
        context_text = ""
        for i, doc in enumerate(retrieved_docs):
            content = doc.get("parent_text") or doc.get("document", "")
            source = doc.get("source_document_name", "Unknown")
            # 截断过长文档以节省 token
            context_text += f"\n[Document {i+1}] (Source: {source})\n{content[:800]}...\n"

        # 3. Call LLM to summarize
        prompt = self.prompt_template.format(
            user_topic=user_topic,
            retrieved_content=context_text
        )

        try:
            logger.info(f"[GlobalContextBuilder] 调用 LLM 生成上下文摘要...")
            global_context = self.llm_service.chat(
                query=prompt,
                system_prompt="你是一个资深的产业分析师，擅长快速总结行业数据概貌。"
            )
            logger.info(f"[GlobalContextBuilder] 上下文构建完成 (长度: {len(global_context)})。")
            logger.debug(f"[GlobalContextBuilder] Context: {global_context}")
            return global_context
        except Exception as e:
            logger.error(f"[GlobalContextBuilder] LLM 生成失败: {e}")
            return "无法生成全局上下文 (LLM 错误)。"
