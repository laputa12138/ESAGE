
import pytest
from unittest.mock import MagicMock
from core.posterior_verifier import PosteriorVerifier

class MockReranker:
    def rerank(self, query, documents, top_n=1):
        # 简单模拟：如果文档包含 query 中的某些字，就给高分
        # 注意：这里 query 和 doc 都是 unicode 字符串
        results = []
        for i, doc in enumerate(documents):
            score = 0.0
            # 严格匹配
            if query in doc:
                score = 0.99
            # 部分匹配 (只要有一个字在里面)
            elif any(char in doc for char in query):
                score = 0.5 # 注意：之前是 0.6，如果 threshold 是 0.3，这里会通过
            else:
                score = 0.1
            
            # 针对 failure case 的特殊处理 (模拟语义不匹配但字面可能无重叠)
            if query == "量子计算机" and "光刻机" in doc:
                score = 0.1 # 强制低分

            results.append({
                'original_index': i,
                'relevance_score': score,
                'document': doc
            })
        
        # Sort by score desc
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:top_n]

@pytest.fixture
def verifier():
    mock_reranker = MockReranker()
    v = PosteriorVerifier(reranker_service=mock_reranker)
    # 强制设置阈值，确保测试确定性
    v.verification_threshold = 0.4 # 提高阈值，或者降低 Mock 的部分匹配分数
    return v

def test_verify_item_success(verifier):
    query = "光刻机"
    docs = [
        {"parent_text": "半导体制造中，光刻机是核心设备。", "source_document_name": "source1"},
        {"parent_text": "农业发展需要拖拉机。", "source_document_name": "source2"}
    ]
    
    result = verifier.verify_item(query, docs)
    
    assert result['verified'] is True, f"Failed match reason: {result.get('reason')}"
    assert "source1" in result['evidence_refs'][0]['source_id']
    assert result['evidence_refs'][0]['father_chunk_content'] == "半导体制造中，光刻机是核心设备。"

def test_verify_item_failure_low_score(verifier):
    query = "量子计算机"
    docs = [
         {"parent_text": "半导体制造中，光刻机是核心设备。", "source_document_name": "source1"}
    ]
    
    # Mock Reranker should return score 0.1
    # Threshold is 0.4
    # So verified should be False
    result = verifier.verify_item(query, docs)
    
    assert result['verified'] is False, f"Should have failed but got verified=True"
    # New logic doesn't explicitly put score in the final fail message if filtered out
    assert "precise span" in result.get('reason', '').lower() or "no results" in result.get('reason', '').lower()

def test_verify_item_empty(verifier):
    assert verifier.verify_item("", [])['verified'] is False
