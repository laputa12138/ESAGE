
import sys
import os
import unittest
from typing import Dict, Any, List

# Ensure we can import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.graph_refiner import GraphRefiner
from core.llm_service import LLMService

class MockLLMService(LLMService):
    def __init__(self):
        pass
    def chat(self, query, system_prompt=None):
        return "{}"

class TestGraphRefinerDuplication(unittest.TestCase):
    
    def setUp(self):
        self.mock_llm = MockLLMService()
        self.refiner = GraphRefiner(self.mock_llm)

    def test_cross_category_merge_existing_target(self):
        """
        Scenario: Merge 'NodeA' (Upstream) into 'NodeB' (Midstream).
        Expected: 'NodeB' remains in Midstream, 'NodeA' is removed from Upstream. 
                  'NodeB' should NOT appear in Upstream.
        """
        graph = {
            'structure': {
                'upstream': ['NodeA', 'OtherUp'],
                'midstream': ['NodeB', 'OtherMid'],
                'downstream': ['NodeC']
            },
            'node_details': {
                'NodeA': {'entity_name': 'NodeA', 'input_elements': ['ShouldMove']},
                'NodeB': {'entity_name': 'NodeB', 'input_elements': ['Existing']},
                'NodeC': {'entity_name': 'NodeC'}
            }
        }
        
        suggestions = [
            {
                'target_node': 'NodeB',
                'source_nodes': ['NodeA'],
                'reason': 'Merge Upstream to Midstream'
            }
        ]
        
        refined_graph = self.refiner._apply_merges(graph, suggestions)
        
        up = refined_graph['structure']['upstream']
        mid = refined_graph['structure']['midstream']
        
        print(f"Upstream: {up}")
        print(f"Midstream: {mid}")
        
        # Checks
        self.assertNotIn('NodeA', up, "NodeA should be removed from upstream")
        self.assertNotIn('NodeB', up, "NodeB should NOT be added to upstream") # Key check for the bug
        self.assertIn('NodeB', mid, "NodeB should remain in midstream")
        self.assertIn('ShouldMove', refined_graph['node_details']['NodeB']['input_elements'], "Details should merge")

    def test_merge_to_new_node(self):
        """
        Scenario: Merge 'NodeA' (Upstream) and 'NodeB' (Midstream) into 'NodeNew'.
        Expected: 'NodeNew' should appear in ONLY ONE category (Project logic: source priority).
                  Current logic: First source found determines category. If NodeA found first -> Upstream.
        """
        graph = {
            'structure': {
                'upstream': ['NodeA'],
                'midstream': ['NodeB'],
                'downstream': []
            },
            'node_details': {
                'NodeA': {'entity_name': 'NodeA'},
                'NodeB': {'entity_name': 'NodeB'}
            }
        }
        
        suggestions = [
            {
                'target_node': 'NodeNew',
                'source_nodes': ['NodeA', 'NodeB'],
                'reason': 'Merge to new node'
            }
        ]
        
        refined_graph = self.refiner._apply_merges(graph, suggestions)
        
        up = refined_graph['structure']['upstream']
        mid = refined_graph['structure']['midstream']
        down = refined_graph['structure']['downstream']
        
        print(f"Upstream (New): {up}")
        print(f"Midstream (New): {mid}")
        
        # Check NodeNew appears exactly once
        count = 0
        if 'NodeNew' in up: count += 1
        if 'NodeNew' in mid: count += 1
        if 'NodeNew' in down: count += 1
        
        self.assertEqual(count, 1, "NodeNew should appear in exactly one category")
        self.assertNotIn('NodeA', up)
        self.assertNotIn('NodeB', mid)

if __name__ == '__main__':
    unittest.main()
