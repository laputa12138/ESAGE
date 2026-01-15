
import logging
from typing import List, Dict, Any, Optional, Tuple
import re

from core.reranker_service import RerankerService
from config import settings

logger = logging.getLogger(__name__)

class PosteriorVerifier:
    """
    负责对抽取出的信息进行后验式溯源 (Posterior Traceability)。
    通过 Reranker 和文本匹配，确保每一个抽取项都能在原文中找到精确的证据片段 (Span)。
    """

    def __init__(self, reranker_service: RerankerService):
        self.reranker_service = reranker_service
        # 设置相似度阈值，低于此值认为证据不足
        self.verification_threshold = getattr(settings, 'VERIFICATION_THRESHOLD', 0.5)

    def verify_item(self, query_item: str, evidence_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证单个条目在证据文档中的存在性。

        Args:
            query_item: 需要验证的信息项 (如 "晶圆制造", "光刻机" 等)。
            evidence_docs: 检索回来的相关文档上下文列表 (通常是 RAG 的 retrieved results)。

        Returns:
            Dict: {
                "verified": bool,           # 是否验证通过
                "evidence_ref": Dict,       # 证据引用 {source_id, father_chunk_id, span_text, score}
                "reason": str              # 验证结果说明
            }
        """
        if not query_item or not query_item.strip():
             return {"verified": False, "reason": "Query item is empty."}
        
        if not evidence_docs:
            return {"verified": False, "reason": "No context documents provided."}

        # 1. 准备文档内容供 Reranker 使用
        # 假设 evidence_docs 结构包含 'parent_text' 或 'document'
        doc_texts = [doc.get('parent_text', doc.get('document', '')) for doc in evidence_docs]
        
        if not any(doc_texts):
             return {"verified": False, "reason": "Context documents have no text."}

        try:
            # 2. 从父块级别找到最相关的文档 (Top 3 Parent Chunks)
            # 使用 query_item 直接去匹配父块
            rerank_results = self.reranker_service.rerank(
                query=query_item,
                documents=doc_texts,
                top_n=3
            )
            
            if not rerank_results:
                return {"verified": False, "reason": "Reranker returned no results.", "evidence_refs": []}

            collected_evidences = []

            for match in rerank_results:
                match_score = match['relevance_score']
                match_idx = match['original_index']
                parent_doc_full = evidence_docs[match_idx]
                parent_doc_text = doc_texts[match_idx]

                # 初步过滤：如果父块相关性低于阈值，则跳过
                if match_score < self.verification_threshold:
                    continue

                # 3. 片段级定位 (Span-Level Localization)
                best_span, span_score = self._find_best_span(query_item, parent_doc_text)
                
                # 如果找到有效片段，加入证据列表
                if best_span:
                    collected_evidences.append({
                        "source_id": parent_doc_full.get('source_document_name', 'Unknown'),
                        "father_chunk_id": parent_doc_full.get('parent_id', parent_doc_full.get('child_id', 'Unknown')),
                        "father_chunk_content": parent_doc_text,
                        "span_text": best_span,
                        "score": span_score 
                    })

            if collected_evidences:
                return {
                    "verified": True,
                    "evidence_refs": collected_evidences,
                    "reason": f"Found {len(collected_evidences)} supporting evidence(s)."
                }
            else:
                 return {
                    "verified": False,
                    "reason": "Could not locate precise span in any relevant parent chunk.",
                    "evidence_refs": []
                 }

        except Exception as e:
            logger.error(f"Error verifies item '{query_item}': {e}", exc_info=True)
            return {"verified": False, "reason": str(e)}

    def _find_best_span(self, query: str, full_text: str) -> Tuple[Optional[str], float]:
        """
        在长文本中找到与 query 最相关的句子或片段。
        """
        # 简单策略：按标点分句
        sentences = re.split(r'[。！？；\n]', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return None, 0.0
        
        # 如果 query 直接包含在某个句子中，优先返回该句
        for s in sentences:
            if query in s:
                return s, 1.0
        
        # 否则再次调用 Reranker 对句子进行排序 (High Cost but Accurate)
        # 或者使用简单的字面重叠率
        try:
             span_results = self.reranker_service.rerank(
                query=query,
                documents=sentences,
                top_n=1
             )
             if span_results:
                 best = span_results[0]
                 return best['document'], best['relevance_score']
        except Exception:
            pass # Fallback to simple logic

        return None, 0.0
