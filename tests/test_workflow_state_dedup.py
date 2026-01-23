
import sys
import os
import unittest
from typing import Dict, Any, List

# Ensure we can import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.workflow_state import WorkflowState

class TestWorkflowStateDedup(unittest.TestCase):
    
    def test_initialize_deduplication(self):
        """
        Scenario: Planner returns duplicate nodes in different categories.
        Inputs:
            Upstream: ['A', 'B']
            Midstream: ['B', 'C']
            Downstream: ['C', 'A']
        
        Priority Rule: Midstream > Downstream > Upstream
        
        Expected:
            Midstream: ['B', 'C'] (Keeps both)
            Downstream: ['A']      (C removed because in Midstream)
            Upstream: []           (A removed because in Downstream, B removed because in Midstream)
            
            Wait, let's trace:
            1. Priority Order = Mid, Down, Up
            2. Process Mid: ['B', 'C']. Seen={'B', 'C'}
            3. Process Down: ['C', 'A']. 
               - 'C' in Seen? Yes -> Remove
               - 'A' in Seen? No -> Keep, Add to Seen. Seen={'B', 'C', 'A'}
               -> Downstream Final: ['A']
            4. Process Up: ['A', 'B'].
               - 'A' in Seen? Yes -> Remove
               - 'B' in Seen? Yes -> Remove
               -> Upstream Final: []
               
        Result:
            Mid: ['B', 'C']
            Down: ['A']
            Up: []
        """
        state = WorkflowState("Test Topic")
        
        init_data = {
            'upstream': ['A', 'B'],
            'midstream': ['B', 'C'],
            'downstream': ['C', 'A']
        }
        
        state.initialize_industry_graph(init_data)
        
        structure = state.industry_graph['structure']
        
        print(f"Final Structure: {structure}")
        
        self.assertIn('B', structure['midstream'])
        self.assertIn('C', structure['midstream'])
        self.assertNotIn('C', structure['downstream'])
        self.assertIn('A', structure['downstream'])
        self.assertNotIn('A', structure['upstream'])
        self.assertNotIn('B', structure['upstream'])
        
        # Check totals
        total_nodes = len(structure['upstream']) + len(structure['midstream']) + len(structure['downstream'])
        self.assertEqual(total_nodes, 3) # A, B, C

if __name__ == '__main__':
    unittest.main()
