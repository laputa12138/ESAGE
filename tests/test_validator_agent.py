import unittest
import logging
from unittest.mock import MagicMock, patch

from core.workflow_state import WorkflowState, TASK_TYPE_VALIDATE_GRAPH
from agents.validator_agent import ValidatorAgent
from core.llm_service import LLMService

logging.basicConfig(level=logging.DEBUG)

class TestValidatorAgent(unittest.TestCase):
    def setUp(self):
        self.mock_llm_service = MagicMock(spec=LLMService)
        self.agent = ValidatorAgent(llm_service=self.mock_llm_service)
        self.workflow_state = WorkflowState("Test Topic")

    def test_validation_logic(self):
        # 1. Setup Mock State: "A", "A_Alias", "Invalid"
        self.workflow_state.industry_graph['structure']['upstream'] = ["Node A", "Node A (Alias)", "Invalid Node"]
        self.workflow_state.industry_graph['node_details'] = {
            "Node A": {"entity_name": "Node A", "input_elements": ["input1"]},
            "Node A (Alias)": {"entity_name": "Node A (Alias)", "input_elements": ["input2"]}, # Should be merged
            "Invalid Node": {"entity_name": "Invalid Node"}
        }

        # 2. Mock LLM Response
        mock_response = """
        {
            "merge_pairs": [
                {"keep": "Node A", "drop": "Node A (Alias)"}
            ],
            "invalid_nodes": ["Invalid Node"]
        }
        """
        self.mock_llm_service.chat.return_value = mock_response

        # 3. Execute Task
        task_id = self.workflow_state.add_task(TASK_TYPE_VALIDATE_GRAPH)
        self.workflow_state.get_next_task() # Move to in_progress
        
        self.agent.execute_task(self.workflow_state, {})

        # 4. Assertions
        structure = self.workflow_state.industry_graph['structure']['upstream']
        details = self.workflow_state.industry_graph['node_details']

        # Check Merger
        self.assertIn("Node A", structure)
        self.assertNotIn("Node A (Alias)", structure)
        self.assertIn("Node A", details)
        self.assertNotIn("Node A (Alias)", details)
        
        # Check that details were merged (simple list append logic)
        node_a_inputs = details["Node A"].get("input_elements", [])
        self.assertIn("input1", node_a_inputs)
        self.assertIn("input2", node_a_inputs) # Merged from Alias

        # Check Deletion
        self.assertNotIn("Invalid Node", structure)
        self.assertNotIn("Invalid Node", details)

        print("Test Validator Logic Passed!")

if __name__ == '__main__':
    unittest.main()
