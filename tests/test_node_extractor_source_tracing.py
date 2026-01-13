
import unittest
from unittest.mock import MagicMock
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.node_extractor_agent import NodeExtractorAgent
# Assuming strict import paths or mocking classes directly

class TestNodeExtractorSourceTracing(unittest.TestCase):
    def setUp(self):
        # Setup Logger
        logging.basicConfig(level=logging.ERROR)
        
        # Mock Services
        self.mock_llm_service = MagicMock()
        self.mock_retrieval_service = MagicMock()
        self.mock_reranker_service = MagicMock()
        
        # Attach reranker to retrieval service
        self.mock_retrieval_service.reranker_service = self.mock_reranker_service
        
        # Initialize Agent
        self.agent = NodeExtractorAgent(
            llm_service=self.mock_llm_service,
            retrieval_service=self.mock_retrieval_service,
            prompt_template="Test {node_name} {retrieved_content}"
        )

    def test_match_evidence_success(self):
        """Test that _match_evidence correctly maps details to documents using reranker."""
        
        # 1. Setup Input Data
        extracted_data = {
            "input_elements": ["High-grade Steel", "Plastic"],
            "output_products": ["Cars"],
            "key_technologies": [],
            "representative_companies": []
        }
        
        # 2. Setup Retrieved Docs
        retrieved_docs = [
            {"source_document_name": "Doc_Steel.txt", "document": "We use High-grade Steel to build frames."},
            {"source_document_name": "Doc_Fruit.txt", "document": "Apples are delicious fruits."},
            {"source_document_name": "Doc_Auto.txt",  "document": "Cars are the main output product."}
        ]
        
        # 3. Mock Reranker Behavior
        # rerank signature: rerank(query, documents, top_n, ...)
        # return list of dicts with 'original_index', 'relevance_score'
        
        def mock_rerank_side_effect(query, documents, top_n, **kwargs):
            results = []
            if "Steel" in query:
                # Expect match with Doc_Steel (index 0)
                results.append({"original_index": 0, "relevance_score": 0.9})
            elif "Cars" in query:
                # Expect match with Doc_Auto (index 2)
                results.append({"original_index": 2, "relevance_score": 0.95})
            elif "Plastic" in query:
                 # Assume low score or random match, let's say it matches Doc_Fruit poorly (index 1)
                 results.append({"original_index": 1, "relevance_score": 0.1})
            return results

        self.mock_reranker_service.rerank.side_effect = mock_rerank_side_effect
        
        # 4. Execute Method
        result = self.agent._match_evidence(extracted_data, retrieved_docs)
        
        # 5. Assertions
        # Check Sources presence
        self.assertIn("sources", result)
        self.assertIn("evidence_snippets", result)
        
        # Check Specific Matches
        # High-grade Steel -> Doc_Steel.txt
        self.assertEqual(result["sources"].get("High-grade Steel"), "Doc_Steel.txt")
        self.assertEqual(result["evidence_snippets"].get("High-grade Steel"), "We use High-grade Steel to build frames.")
        
        # Cars -> Doc_Auto.txt
        self.assertEqual(result["sources"].get("Cars"), "Doc_Auto.txt")
        self.assertEqual(result["evidence_snippets"].get("Cars"), "Cars are the main output product.")
        
        # Plastic -> Doc_Fruit.txt (as mocked)
        self.assertEqual(result["sources"].get("Plastic"), "Doc_Fruit.txt")

    def test_match_evidence_no_reranker(self):
        """Test behavior when reranker is missing."""
        # Unset reranker
        self.mock_retrieval_service.reranker_service = None
        
        extracted_data = {"input_elements": ["Steel"]}
        retrieved_docs = [{"document": "Steel doc"}]
        
        result = self.agent._match_evidence(extracted_data, retrieved_docs)
        
        # Should return original data unmodified (no new keys if completely skipped, or empty dictionaries?)
        # Implementation returns extracted_data immediately if no reranker in early check
        # But wait, the method initializes sources={}, evidence_snippets={}, then checks returns extracted_data.
        # So 'sources' key will NOT be present if it returns early on 'if not reranker'.
        
        # Let's check implementation again:
        # if not reranker: return extracted_data (so no modification)
        self.assertNotIn("sources", result)

if __name__ == '__main__':
    unittest.main()
