import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Set
import math

from core.llm_service import LLMService
from config import settings

logger = logging.getLogger(__name__)

class PosteriorVerifier:
    """
    后验验证器 (Posterior Verifier)。
    
    核心职责：
    1. 不依赖 LLM 自行生成的引用 ID，而是使用算法强制将生成内容与原始文档绑定。
    2. 计算混合支撑分数 (CSS - Composite Support Score)。
       公式: CSS = Alpha * LexicalOverlap + Beta * NLI_Probability
    3. 提取核心证据句。
    """

    def __init__(self, llm_service: LLMService):
        """
        初始化验证器。
        Args:
            llm_service: 用于计算 NLI (自然语言推理) 分数的 LLM 服务。
        """
        self.llm_service = llm_service
        self.alpha = settings.POSTERIOR_VERIFIER_ALPHA
        self.beta = settings.POSTERIOR_VERIFIER_BETA
        self.threshold = settings.POSTERIOR_VERIFIER_THRESHOLD
        self.epsilon = settings.POSTERIOR_VERIFIER_EPSILON
        
        logger.info(f"PosteriorVerifier Initialized. Alpha={self.alpha}, Beta={self.beta}, Threshold={self.threshold}")

    def verify_claim(self, claim_text: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证单个陈述 (claim_text) 是否被 retrieved_docs 中的某篇文档支持。
        
        Args:
            claim_text (str): 待验证的生成内容 (如 "光伏玻璃的主要成分是二氧化硅")。
            retrieved_docs (List[Dict]): 检索到的文档列表。每个文档应包含 'parent_text' 或 'document'。

        Returns:
            Dict: 验证结果对象。
            {
                "verified": bool, # 是否通过验证
                "score": float,   # CSS 分数
                "evidence_ref": { # 最佳证据引用 (如果 verified=True)
                    "source_id": str,
                    "father_chunk_id": str,
                    "child_chunk_id": str (Optional),
                    "father_text": str,
                    "key_evidence": str # 核心证据句
                },
                "reason": str # 验证失败的原因或通过的日志
            }
        """
        if not claim_text or not claim_text.strip():
            return {"verified": False, "score": 0.0, "reason": "Claim is empty"}
            
        if not retrieved_docs:
            return {"verified": False, "score": 0.0, "reason": "No retrieved docs provided"}

        best_score = -1.0
        best_doc = None
        best_sentence = None
        
        # 遍历所有文档寻找最佳支撑
        # 优化：为了性能，可以只对 Top-N 文档进行 NLI 计算，或者先用 Lexical 筛选
        for doc in retrieved_docs:
            # 获取文档文本 (兼容不同命名习惯)
            doc_text = doc.get("parent_text") or doc.get("document") or ""
            if not doc_text:
                continue
                
            # 1. 定位核心句 (Heuristic: 寻找与 claim 字面重叠度最高的句子)
            # 这可以是粗略的，为了给 NLI 提供更聚焦的“前提 (Premise)”
            sentences = self._split_sentences(doc_text)
            best_local_sent = ""
            best_local_lex_score = -1.0
            
            for sent in sentences:
                lex_score = self._calculate_lexical_overlap(claim_text, sent)
                if lex_score > best_local_lex_score:
                    best_local_lex_score = lex_score
                    best_local_sent = sent
            
            # 如果整段都没什么重叠，可能根本不相关，跳过昂贵的 NLI
            # 粗筛阈值可以设低一点，比如 0.1
            if best_local_lex_score < 0.1:
                continue

            # 2. 计算 CSS 分数 (针对最佳句子)
            # NLI 计算: Premise=best_local_sent, Hypothesis=claim_text
            nli_score = self._calculate_nli_score(premise=best_local_sent, hypothesis=claim_text)
            
            css_score = self._compute_css_score(best_local_lex_score, nli_score)
            
            # 更新全局最佳
            if css_score > best_score:
                best_score = css_score
                best_doc = doc
                best_sentence = best_local_sent
        
        # 3. 最终判定
        if best_score >= self.threshold:
            return {
                "verified": True,
                "score": best_score,
                "evidence_ref": {
                    "source_id": best_doc.get("source_document_name", "unknown"),
                    "father_chunk_id": best_doc.get("parent_id", "unknown"),
                    "child_chunk_id": best_doc.get("id", None), # 可能是子块
                    "father_text": best_doc.get("parent_text") or best_doc.get("document", ""),
                    "key_evidence": best_sentence
                },
                "reason": f"CSS({best_score:.2f}) >= Threshold({self.threshold})"
            }
        else:
            return {
                "verified": False,
                "score": best_score,
                "evidence_ref": None,
                "reason": f"Best score ({best_score:.2f}) below threshold ({self.threshold})"
            }

    def _calculate_lexical_overlap(self, str1: str, str2: str) -> float:
        """
        计算字面刚性约束分数 (Lexical Overlap)。
        公式: Intersection(Tokens) / (Len(Tokens1) + epsilon)
        这里简单使用字符级或分词级重叠。为了通用性，暂用字符级 n-gram 或 jieba (如果可用)。
        为减少依赖，这里使用简单的字符集重叠 (针对中文这种表意文字效果尚可，或简单的按字切分)。
        对于专有名词，这种方法能有效防止篡改。
        """
        # 简单预处理：去标点，转小写
        s1 = self._clean_text(str1)
        s2 = self._clean_text(str2)
        
        if not s1: return 0.0
        
        # 使用 Set[Char] 计算重叠 (Jaccard-like containment)
        # 或者更严格：计算 s1 中的字符有多少出现在 s2 中
        # Overlap = count(chars in s1 that are in s2) / len(s1)
        # 这是一种非对称的“覆盖率”：生成的 claim (s1) 必须被 source (s2) 覆盖。
        
        count_covered = 0
        for char in s1:
            if char in s2:
                count_covered += 1
        
        overlap_score = count_covered / (len(s1) + self.epsilon)
        return min(overlap_score, 1.0) # Cap at 1.0

    def _calculate_nli_score(self, premise: str, hypothesis: str) -> float:
        """
        计算语义柔性约束分数 (NLI Probability)。
        调用 LLM 判断：前提 (Premise) 是否蕴含 (Entails) 假设 (Hypothesis)。
        """
        prompt = f"""
请判断以下两句话的逻辑关系。
前提 (Premise): "{premise}"
假设 (Hypothesis): "{hypothesis}"

基于“前提”的内容，“假设”是否被语义支撑或蕴含？
请只输出一个 0.0 到 1.0 之间的分数值用来表示置信度。
- 1.0: 完全支持/蕴含。
- 0.0: 完全无关或矛盾。
- 0.5: 部分相关或不确定。

请只输出数字，不要输出其他文字。
"""
        try:
            # 使用较快的模型或默认模型
            response = self.llm_service.chat(prompt, max_tokens=10, temperature=0.1) # 低温确保确定性
            
            # 提取数字
            match = re.search(r"(\d+(\.\d+)?)", response)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0) # Clip 0-1
            else:
                logger.warning(f"[PosteriorVerifier] NLI response not a number: {response}")
                return 0.5 # Default fallback
        except Exception as e:
            logger.error(f"[PosteriorVerifier] NLI check failed: {e}")
            return 0.5

    def _compute_css_score(self, lexical_score: float, nli_score: float) -> float:
        """
        计算混合分数。
        """
        return (self.alpha * lexical_score) + (self.beta * nli_score)

    def _split_sentences(self, text: str) -> List[str]:
        """
        简单的中文分句 (兼容英文句号).
        保留标点符号。
        """
        # regex: split by punctuation, capturing the delimiter
        # [。！？；!?;] or \.
        # Note: We need to be careful not to split decimal numbers (e.g. 3.14).
        # A simple lookbehind (?<!\d)\.(?!\d) is good, or just accept simple splitting for now.
        # Given this is for text verification, simple splitting is usually fine.
        
        sentences = re.split(r'([。！？；!?;]|\.(?=\s|$))', text) 
        # \.(?=\s|$) means dot followed by space or end of string, avoiding 3.14
        
        return self._reconstruct_sentences(sentences)

    def _reconstruct_sentences(self, tokens: List[str]) -> List[str]:
        result = []
        current_sent = ""
        for token in tokens:
            current_sent += token
            # If token is a delimiter, flush
            if re.match(r'^[。！？；!?;.]+$', token.strip()): 
               result.append(current_sent.strip())
               current_sent = ""
        
        if current_sent.strip():
            result.append(current_sent.strip())
            
        return result

    def _clean_text(self, text: str) -> str:
        """移除标点符号和空格"""
        return re.sub(r'[^\w\u4e00-\u9fff]', '', text)
