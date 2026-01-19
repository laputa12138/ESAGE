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

    def verify_claim(self, claim_text: str, retrieved_docs: List[Dict[str, Any]], focus_entity: Optional[str] = None) -> Dict[str, Any]:
        """
        验证单个陈述 (claim_text) 是否被 retrieved_docs 中的某篇文档支持。
        优化逻辑：
        1. 仅使用 Top-K 文档进行验证。
        2. 使用 LLM 直接在文档级别进行验证并提取原始证据句，替代之前的逐句匹配。
        
        Args:
            claim_text (str): 待验证的生成内容。
            retrieved_docs (List[Dict]): 检索到的文档列表。
            focus_entity (Optional[str]): 待验证的核心实体词 (如 "石英砂", "比亚迪")。

        Returns:
            Dict: 验证结果对象。
        """
        if not claim_text or not claim_text.strip():
            return {"verified": False, "score": 0.0, "reason": "Claim is empty"}
            
        if not retrieved_docs:
            return {"verified": False, "score": 0.0, "reason": "No retrieved docs provided"}

        # 1. Limit scope to Top-K docs (Performance Optimization)
        top_k = getattr(settings, "POSTERIOR_VERIFICATION_TOP_K", 3)
        candidate_docs = retrieved_docs[:top_k]
        
        best_result = {
            "verified": False,
            "score": -1.0,
            "score_breakdown": {"lexical": 0.0, "nli": 0.0, "final": 0.0, "reason": "No candidate docs"},
            "evidence_ref": None,
            "reason": "No relevant documents found in candidates."
        }

        # Optimization: Pass entities to skip pre-filter logic if exact match exists
        target_entity = focus_entity

        processed_count = 0
        
        for doc in candidate_docs:
            doc_text = doc.get("parent_text") or doc.get("document") or ""
            if not doc_text:
                continue
            
            processed_count += 1
                
            # 2. Quick Pre-filter using Lexical Overlap (Whole Doc)
            doc_lex_score = self._calculate_lexical_overlap(claim_text, doc_text)
            has_exact_entity = (target_entity and target_entity in doc_text)
            
            # --- CRITICAL FIX: Relax Pre-filter ---
            # If target entity is found, SKIP lexical check completely to prevent false negatives.
            # Only apply threshold if entity is NOT found.
            pre_filter_threshold = 0.05 
            
            if not has_exact_entity and doc_lex_score < pre_filter_threshold:
                # Even if skipped, we might want to track it if it's the only doc, but for now just skip
                logger.debug(f"[Verifier] Skipped doc '{doc.get('source_document_name')}' due to low lexical overlap ({doc_lex_score:.2f})")
                continue

            # 3. LLM verification & Evidence Extraction
            llm_result = self._verify_and_extract_evidence_llm(doc_text, claim_text)
            nli_score = llm_result["score"]
            extracted_sentence = llm_result["evidence_sentence"]
            
            # Recalculate lexical score on the *extracted sentence* for the final CSS score
            final_lex_score = doc_lex_score
            if extracted_sentence:
                final_lex_score = self._calculate_lexical_overlap(claim_text, extracted_sentence)
            
            css_score = self._compute_css_score(final_lex_score, nli_score)

            # Apply Exact Match Boosting
            boosted = False
            if has_exact_entity:
                 css_score = min(css_score + 0.25, 1.0)
                 boosted = True

            current_breakdown = {
                "lexical": float(f"{final_lex_score:.2f}"),
                "nli": float(f"{nli_score:.2f}"),
                "final": float(f"{css_score:.2f}"),
                "boosted": boosted
            }

            # Construct evidence ref (Always construct it so we can return it even if failed)
            current_evidence_ref = {
                "source_id": doc.get("source_document_name", "unknown"),
                "father_chunk_id": doc.get("parent_id", "unknown"),
                "child_chunk_id": doc.get("id", None),
                "father_text": doc_text, # Ensure father_text is included
                "key_evidence": extracted_sentence
            }
            
            # Update best valid result or just best result
            if css_score > best_result["score"]:
                best_result = {
                    "verified": (css_score >= self.threshold),
                    "score": css_score,
                    "score_breakdown": current_breakdown,
                    "evidence_ref": current_evidence_ref,
                    "reason": f"CSS({css_score:.2f}) >= Threshold" if css_score >= self.threshold else f"Best Score {css_score:.2f} < {self.threshold}"
                }
                
                # If we found a verified one, we can stop? Or continue to find BETTER one?
                # Optimization: stop if score is very high (e.g. > 0.9)
                if best_result["verified"] and best_result["score"] > 0.95:
                    break

        # If after checking all top-k docs, we still have -1.0 (all skipped by pre-filter), 
        # and we processed at least one doc, we should try to verify the best candidate 
        # (Top-1) without pre-filter to get a reason.
        if best_result["score"] == -1.0 and candidate_docs:
             # Force verify first doc to give user some feedback/evidence
             fallback_doc = candidate_docs[0]
             fallback_text = fallback_doc.get("parent_text") or fallback_doc.get("document") or ""
             if fallback_text:
                llm_res = self._verify_and_extract_evidence_llm(fallback_text, claim_text)
                
                # ... same calculation logic simplified ...
                f_lex = self._calculate_lexical_overlap(claim_text, llm_res["evidence_sentence"] or fallback_text)
                f_css = self._compute_css_score(f_lex, llm_res["score"])
                
                best_result = {
                    "verified": (f_css >= self.threshold),
                    "score": f_css,
                    "score_breakdown": {"lexical": f_lex, "nli": llm_res["score"], "final": f_css, "fallback": True},
                    "evidence_ref": {
                        "source_id": fallback_doc.get("source_document_name", "unknown"),
                        "father_text": fallback_text,
                        "key_evidence": llm_res["evidence_sentence"]
                    },
                    "reason": f"Fallback Verify: Score {f_css:.2f}"
                }

        return best_result

    def _verify_and_extract_evidence_llm(self, document_text: str, claim_text: str) -> Dict[str, Any]:
        """
        使用 LLM 验证 Claim 是否被 Document 支持，并未经修改地提取支撑证据句。
        增加 Regex Fallback 以增强鲁棒性。
        """
        prompt = f"""
你是一个严格的事实核查助手。你的任务是验证“待验证陈述”是否被“参考文档”所支持。

待验证陈述 (Claim): "{claim_text}"

参考文档 (Document):
---
{document_text}
---

任务要求：
1. 判断：参考文档是否在语义上支持待验证陈述？
2. 提取：如果支持，请从参考文档中提取**一句**最能证明该陈述的原始句子。
   - **必须**直接从文档中复制，**严禁**修改、改写或删减任何字符。
   - 如果文档中没有明确支持的句子，证据句请留空。

请返回严格的 JSON 格式（不要使用 Markdown 代码块）：
{{
  "score": <0.0 到 1.0 之间的置信度分数，1.0表示完全支持>,
  "evidence_sentence": "<提取的原始证据句，如果不支持则为空字符串>"
}}
"""
        try:
            # Disable thinking for speed, simpler task
            # response_format param removed as it is not supported by LLMService.chat
            response = self.llm_service.chat(prompt, max_tokens=200, temperature=0.0, enable_thinking=False)
            
            import json
            from core.json_utils import clean_and_parse_json
            
            try:
                result = clean_and_parse_json(response)
                if not isinstance(result, dict):
                    raise ValueError("Parsed result is not a dictionary")
            except Exception:
                # --- Regex Fallback ---
                logger.warning(f"[PosteriorVerifier] JSON parse failed, trying Regex. Response: {response[:100]}...")
                score_match = re.search(r'"score":\s*([\d\.]+)', response)
                evi_match = re.search(r'"evidence_sentence":\s*"(.*?)"', response)
                
                score = float(score_match.group(1)) if score_match else 0.0
                evidence = evi_match.group(1) if evi_match else ""
                result = {"score": score, "evidence_sentence": evidence}
            
            score = float(result.get("score", 0.0))
            evidence = result.get("evidence_sentence", "").strip()
            
            return {"score": score, "evidence_sentence": evidence}
            
        except Exception as e:
            logger.error(f"[PosteriorVerifier] LLM verification failed: {e}")
            return {"score": 0.0, "evidence_sentence": ""}

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

    def _compute_css_score(self, lexical_score: float, nli_score: float) -> float:
        """
        计算混合分数。
        """
        return (self.alpha * lexical_score) + (self.beta * nli_score)

    def _clean_text(self, text: str) -> str:
        """移除标点符号和空格"""
        return re.sub(r'[^\w\u4e00-\u9fff]', '', text)

