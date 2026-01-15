import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import json

logger = logging.getLogger(__name__)

# Define task type constants
TASK_TYPE_PLAN_STRUCTURE = "plan_structure"
TASK_TYPE_EXTRACT_NODE = "extract_node"

# Define node status constants (if needed, though simple None check works)
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"

class WorkflowState:
    """
    Manages the dynamic state of the industry extraction workflow.
    Acts as a "working memory" or "central nervous system" for the agents and pipeline.
    """
    def __init__(self, user_topic: str, report_title: Optional[str] = None): # report_title kept for compat if needed, or ignore
        self.workflow_id: str = str(uuid.uuid4())
        self.start_time: datetime = datetime.now()

        self.user_topic: str = user_topic
        
        # Industry Graph Data
        # Replaces old 'parsed_outline' and 'chapter_data'
        self.industry_graph: Dict[str, Any] = {
            "root_topic": user_topic,
            "structure": {
                "upstream": [],
                "midstream": [],
                "downstream": []
            },
            "node_details": {} # Key: node_name, Value: extracted_data (dict) or None
        }

        # Task queue
        self.pending_tasks: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []
        self.workflow_log: List[Tuple[datetime, str, Dict[str, Any]]] = []
        
        self.global_flags: Dict[str, Any] = {
            'structure_planned': False,
            'extraction_complete': False,
        }
        self.error_count: int = 0
        self.current_processing_task_id: Optional[str] = None

        self.log_event("WorkflowState initialized.", {"user_topic": user_topic, "workflow_id": self.workflow_id})

    def log_event(self, message: str, details: Optional[Dict[str, Any]] = None, level: str = "INFO"):
        timestamp = datetime.now()
        log_details = details or {}
        if 'level' not in log_details:
            log_details['level_implicit'] = level.upper()

        log_entry = (timestamp, message, log_details)
        self.workflow_log.append(log_entry)

        # Print for visibility
        print(f"[WF_LOG] {message}")

        if level.upper() == "ERROR":
            logger.error(f"[WF Log] {message} {log_details if log_details else ''}")
        elif level.upper() == "WARNING":
            logger.warning(f"[WF Log] {message} {log_details if log_details else ''}")
        elif level.upper() == "DEBUG":
            logger.debug(f"[WF Log] {message} {log_details if log_details else ''}")
        else:
            logger.info(f"[WF Log] {message} {log_details if log_details else ''}")

    def add_task(self, task_type: str, payload: Optional[Dict[str, Any]] = None, priority: int = 0) -> str:
        task_id = str(uuid.uuid4())
        task = {
            'id': task_id,
            'type': task_type,
            'priority': priority,
            'payload': payload or {},
            'status': 'pending',
            'added_at': datetime.now()
        }
        self.pending_tasks.append(task)
        self.pending_tasks.sort(key=lambda t: (t['priority'], t['added_at']))
        self.log_event(f"Task added: {task_type}", {"task_id": task_id, "priority": priority, "payload": payload})
        return task_id

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        if not self.pending_tasks:
            return None
        task = self.pending_tasks.pop(0)
        task['status'] = 'in_progress'
        self.current_processing_task_id = task['id']
        self.log_event(f"Task started: {task['type']}", {"task_id": task['id'], "payload": task['payload']})
        return task

    def complete_task(self, task_id: str, result_summary: Optional[str] = None, status: str = 'success'):
        if self.current_processing_task_id == task_id:
            self.current_processing_task_id = None
        
        completed_task_info = {
            'id': task_id,
            'completed_at': datetime.now().isoformat(),
            'status': status,
            'message': result_summary or "N/A"
        }
        self.completed_tasks.append(completed_task_info)

        log_level = "INFO"
        if status == 'failed':
            self.increment_error_count()
            log_level = "ERROR"
        
        self.log_event(f"Task completed: {task_id}", {"status": status, "result_summary": result_summary}, level=log_level)

    def initialize_industry_graph(self, structure_data: Dict[str, List[str]]):
        """
        Initializes the industry structure from the planning agent's output.
        structure_data expected keys: 'upstream', 'midstream', 'downstream' (lists of strings)
        """
        self.industry_graph['structure'] = structure_data
        
        # Initialize empty details for all nodes
        total_nodes = 0
        for category in ['upstream', 'midstream', 'downstream']:
            nodes = structure_data.get(category, [])
            for node in nodes:
                # Initialize as None to indicate pending extraction
                self.industry_graph['node_details'][node] = None
                total_nodes += 1
        
        self.set_flag('structure_planned', True)
        self.log_event("Industry graph structure initialized.", {"total_nodes": total_nodes, "structure": structure_data})

    def add_node_to_structure(self, node_name: str, category: str) -> bool:
        """
        Dynamically adds a new node to the industry structure.
        Returns True if the node was added (didn't exist), False otherwise.
        """
        if category not in ['upstream', 'midstream', 'downstream']:
            logger.warning(f"Invalid category '{category}' for node '{node_name}'. Defaulting to 'upstream' for safety.")
            # Default fallback logic or strict reject? Let's be flexible but warn.
            # Actually, let's keep it strict or existing categories.
            if category not in self.industry_graph['structure']:
                 self.industry_graph['structure'][category] = [] # Initialize if new category somehow

        # Check if already exists in ANY category to avoid duplicates across the graph
        # (Though technically a node could be both downstream of A and upstream of B, 
        # for simplicity in this tree view, we might want unique nodes for now)
        for cat in self.industry_graph['structure']:
            if node_name in self.industry_graph['structure'][cat]:
                return False
        
        # Add to structure
        if category not in self.industry_graph['structure']:
             self.industry_graph['structure'][category] = []
        
        self.industry_graph['structure'][category].append(node_name)
        
        # Initialize details
        if node_name not in self.industry_graph['node_details']:
            self.industry_graph['node_details'][node_name] = None
            
        self.log_event(f"Dynamically added node: {node_name} (Category: {category})")
        return True

    def update_node_details(self, node_name: str, extracted_data: Dict[str, Any]):
        """
        Updates the details for a specific node after extraction.
        """
        if node_name not in self.industry_graph['node_details']:
             self.log_event(f"Warning: Updating details for unknown node '{node_name}'. Adding it.", level="WARNING")
        
        self.industry_graph['node_details'][node_name] = extracted_data
        self.log_event(f"Node details updated: {node_name}")

    def prune_industry_graph(self):
        """
        Removes nodes that have no extracted details or are marked as having no evidence.
        """
        logger.info("Starting industry graph pruning...")
        nodes_to_remove = []
        
        # Identify nodes to remove
        for node_name, details in self.industry_graph['node_details'].items():
            if not details: # None or empty dict
                nodes_to_remove.append(node_name)
                continue
            
            if not isinstance(details, dict):
                logger.warning(f"Node '{node_name}' details is not a dict (got {type(details)}). Marking for removal.")
                nodes_to_remove.append(node_name)
                continue

            # Check for "Not Found" patterns
            evidence = details.get('evidence_snippet', '') or ''
            desc = details.get('description', '') or ''
            
            # Pattern check: "未找到" in evidence or description AND empty component lists
            is_empty_components = (
                not details.get('input_elements') and 
                not details.get('output_products') and 
                not details.get('key_technologies') and 
                not details.get('representative_companies')
            )
            
            has_negative_evidence = "未找到" in str(evidence) or "No specific documents" in str(evidence) or "not found" in str(evidence).lower()
            
            if is_empty_components and has_negative_evidence:
                 nodes_to_remove.append(node_name)
        
        # Remove from structure and details
        removed_count = 0
        for node in nodes_to_remove:
            # Remove from node_details
            if node in self.industry_graph['node_details']:
                del self.industry_graph['node_details'][node]
            
            # Remove from structure lists
            for category in ['upstream', 'midstream', 'downstream']:
                if node in self.industry_graph['structure'].get(category, []):
                    self.industry_graph['structure'][category].remove(node)
            
            removed_count += 1
            
        logger.info(f"Pruned {removed_count} nodes due to lack of evidence/data.")
        self.log_event(f"Graph pruned. Removed {removed_count} nodes.", {"removed_nodes": nodes_to_remove})

    def are_all_nodes_extracted(self) -> bool:
        """
        Checks if all nodes in the structure have been extracted (i.e., have data in node_details).
        """
        if not self.get_flag('structure_planned', False):
            return False
        
        for category in ['upstream', 'midstream', 'downstream']:
            nodes = self.industry_graph['structure'].get(category, [])
            for node in nodes:
                if self.industry_graph['node_details'].get(node) is None:
                    return False
        return True

    def set_flag(self, flag_name: str, value: Any):
        self.global_flags[flag_name] = value
        self.log_event(f"Global flag '{flag_name}' set to: {value}")

    def get_flag(self, flag_name: str, default: Optional[Any] = None) -> Any:
        return self.global_flags.get(flag_name, default)

    def increment_error_count(self):
        self.error_count += 1
        self.log_event("Global error count incremented.", {"current_error_count": self.error_count})

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print("WorkflowState Refactored Test Start")
    state = WorkflowState("Semiconductor Industry")
    # Test passed...
