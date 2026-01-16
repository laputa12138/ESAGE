import unittest
import logging
from unittest.mock import MagicMock, patch
import json

from core.workflow_state import WorkflowState, TASK_TYPE_EXTRACT_NODE
from agents.node_extractor_agent import NodeExtractorAgent
from core.llm_service import LLMService
from core.retrieval_service import RetrievalService
from core.posterior_verifier import PosteriorVerifier

logging.basicConfig(level=logging.DEBUG)

class TestPosteriorVerification(unittest.TestCase):
    def setUp(self):
        self.mock_llm_service = MagicMock(spec=LLMService)
        self.mock_retrieval_service = MagicMock(spec=RetrievalService)
        self.workflow_state = WorkflowState("Solar Panel Industry")
        
        # Initialize Agent
        self.agent = NodeExtractorAgent(
            llm_service=self.mock_llm_service,
            retrieval_service=self.mock_retrieval_service
        )
        
        # Mock QueryBuilder output
        self.agent.query_builder.generate_queries = MagicMock(return_value={
            "vector_queries": ["Solar Panel Process"],
            "bm25_queries": ["PV Module"]
        })

    def test_evidence_injection(self):
        # 1. Mock Retrieval Docs
        mock_docs = [
            {
                "parent_text": "The main input element for Solar Panels is High Purity Silicon. Another input is Eva Film.",
                "source_document_name": "Doc A",
                "parent_id": "P1",
                "child_id": "C1"
            },
            {
                "parent_text": "Solar Panels result in clean energy.",
                "source_document_name": "Doc B",
                "parent_id": "P2"
            }
        ]
        self.mock_retrieval_service.retrieve.return_value = mock_docs

        # 2. Mock LLM Extraction Result
        extraction_json = {
            "entity_name": "Solar Panel",
            "input_elements": ["High Purity Silicon", "Unobtanium"],
            "output_products": ["Electricity"]
        }
        
        def llm_side_effect(*args, **kwargs):
            # args[0] or kwargs['query'] is the prompt
            prompt = kwargs.get('query', args[0] if args else "")
            # print(f"DEBUG: Mock received prompt: {prompt[:50]}...")
            
            # Robust Dispatch using Keywords
            if "逻辑关系" in prompt or "Premise" in prompt:
                # NLI Call
                # Negative cases first!
                if "Unobtanium" in prompt:
                    return "0.05"
                
                if "High Purity Silicon" in prompt: 
                    return "0.9"
                if "Electricity" in prompt:
                    return "0.9"
                return "0.1" # Default low
            
            # Otherwise assume extraction
            return json.dumps(extraction_json)

        self.mock_llm_service.chat.side_effect = llm_side_effect

        # 3. Execute Task
        task_id = self.workflow_state.add_task(TASK_TYPE_EXTRACT_NODE, payload={
            'node_name': "Solar Panel",
            'category': "midstream"
        })
        task = self.workflow_state.get_next_task()
        
        self.agent.execute_task(self.workflow_state, task)

        # 4. Assertions
        node_details = self.workflow_state.industry_graph['node_details']['Solar Panel']
        
        # Check that 'High Purity Silicon' is kept and 'Unobtanium' is filtered (or noted)
        inputs = node_details.get('input_elements', [])
        
        self.assertIn("High Purity Silicon", inputs)
        # Depending on logic, Unobtanium might be filtered out or kept but without evidence
        # Current logic: filtered out if verification fails
        self.assertNotIn("Unobtanium", inputs) 

        # Check Evidence Details map
        evidence_map = node_details.get('evidence_details', {})
        self.assertIn('input_elements', evidence_map)
        silicon_evidence = evidence_map['input_elements'].get('High Purity Silicon')
        
        self.assertIsNotNone(silicon_evidence)
        self.assertEqual(silicon_evidence['source_id'], "Doc A")
        self.assertEqual(silicon_evidence['key_evidence'], "The main input element for Solar Panels is High Purity Silicon.") 
        # Note: best sentence might vary depending on split logic, but should be from Doc A

        # Check usage of focus_entity in verify_claim
        # We can mock the verifier method to check call args, 
        # but since we want integration test, we can trust the logic or spy on it.
        # Here we just assume it works if the result is correct.
        
        # Enhanced check: Ensure 'Unobtanium' is NOT in the final inputs
        self.assertNotIn("Unobtanium", inputs)
        
        # Verify that 'Electricity' is processed (even if verified or not)
        # In this mock setup, we didn't add doc for Electricity so it might be missing or filtered.
        
        print("Test Posterior Verification Passed!")

if __name__ == '__main__':
    unittest.main()
