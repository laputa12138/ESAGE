import sys
import os

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from core.workflow_state import WorkflowState

class TestWorkflowPruning(unittest.TestCase):
    def setUp(self):
        self.state = WorkflowState("Test Topic")
        # Initialize some structure
        self.state.initialize_industry_graph({
            'upstream': ['NodeA', 'NodeB', 'NodeC'],
            'midstream': [],
            'downstream': []
        })

    def test_prune_empty_but_with_description(self):
        """Test that nodes with description but NO structural components are pruned."""
        # NodeA: Has description, but empty components -> Should be REMOVED
        self.state.update_node_details('NodeA', {
            'entity_name': 'NodeA',
            'description': 'This is a description.',
            'input_elements': [],
            'output_products': [],
            'key_technologies': [],
            'representative_companies': [],
            'evidence_snippet': 'Some evidence'
        })

        # NodeB: Has description and one component -> Should remain
        self.state.update_node_details('NodeB', {
            'entity_name': 'NodeB',
            'description': 'Valid node',
            'input_elements': ['Something'],
            'output_products': [],
            'key_technologies': [],
            'representative_companies': []
        })
        
        # NodeC: Empty dictionary -> Should be REMOVED
        self.state.update_node_details('NodeC', {})

        self.state.prune_industry_graph()

        # Check NodeA
        self.assertNotIn('NodeA', self.state.industry_graph['node_details'])
        self.assertNotIn('NodeA', self.state.industry_graph['structure']['upstream'])
        
        # Check NodeB
        self.assertIn('NodeB', self.state.industry_graph['node_details'])
        
        # Check NodeC
        self.assertNotIn('NodeC', self.state.industry_graph['node_details'])

if __name__ == '__main__':
    unittest.main()
