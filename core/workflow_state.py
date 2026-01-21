import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import json

logger = logging.getLogger(__name__)

# Define task type constants
TASK_TYPE_PLAN_STRUCTURE = "plan_structure"
TASK_TYPE_EXTRACT_NODE = "extract_node"
TASK_TYPE_VALIDATE_GRAPH = "validate_graph"

# 定义节点状态常量 (如果需要，虽然简单的 None 检查即可)
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"

class WorkflowState:
    """
    管理产业链抽取工作流的动态状态。
    作为智能体和流水线的“工作记忆”或“中枢神经系统”。
    """
    def __init__(self, user_topic: str, report_title: Optional[str] = None): # report_title 保留兼容性
        self.workflow_id: str = str(uuid.uuid4())
        self.start_time: datetime = datetime.now()

        self.user_topic: str = user_topic
        
        # 产业链图谱数据
        # 替代旧的 'parsed_outline' 和 'chapter_data'
        self.industry_graph: Dict[str, Any] = {
            "root_topic": user_topic,
            "structure": {
                "upstream": [],
                "midstream": [],
                "downstream": []
            },
            "node_details": {} # Key: node_name, Value: extracted_data (dict) or None
        }

        # 任务队列
        self.pending_tasks: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []
        self.workflow_log: List[Tuple[datetime, str, Dict[str, Any]]] = []
        
        self.global_flags: Dict[str, Any] = {
            'structure_planned': False,
            'extraction_complete': False,
        }
        self.global_context: str = "" # Added Global Context
        self.error_count: int = 0
        self.current_processing_task_id: Optional[str] = None

        self.log_event("WorkflowState initialized.", {"user_topic": user_topic, "workflow_id": self.workflow_id})

    def set_global_context(self, context: str):
        self.global_context = context
        self.log_event("Global context set.")

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
        根据规划智能体的输出初始化产业结构。
        structure_data 期望的键: 'upstream', 'midstream', 'downstream' (字符串列表)
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
        动态将新节点添加到产业结构中。
        如果节点已添加（不存在），则返回 True，否则返回 False。
        """
        if category not in ['upstream', 'midstream', 'downstream']:
            logger.warning(f"Invalid category '{category}' for node '{node_name}'. Defaulting to 'upstream' for safety.")
            # Default fallback logic or strict reject? Let's be flexible but warn.
            # Actually, let's keep it strict or existing categories.
            if category not in self.industry_graph['structure']:
                 self.industry_graph['structure'][category] = [] # Initialize if new category somehow

        # 检查是否已存在于任何类别中，以避免图谱中重复
        # (虽然技术上一个节点可能既是 A 的下游又是 B 的上游，
        # 为了简化树状视图，目前保持唯一性)
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
        抽取后更新特定节点的详细信息。
        """
        if node_name not in self.industry_graph['node_details']:
             self.log_event(f"Warning: Updating details for unknown node '{node_name}'. Adding it.", level="WARNING")
        
        self.industry_graph['node_details'][node_name] = extracted_data
        self.log_event(f"Node details updated: {node_name}")

    def prune_industry_graph(self):
        """
        移除没有抽取细节或标记为无证据的节点。
        """
        logger.info("开始进行产业链图谱剪枝...")
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

            # 模式检查：空组件列表
            # 修改：严格检查。如果所有结构化组件为空，则移除该节点。
            # 即使有描述，如果是没有图谱结构价值的“僵尸节点”也移除。
            is_empty_components = (
                not details.get('input_elements') and 
                not details.get('output_products') and 
                not details.get('key_technologies') and 
                not details.get('representative_companies')
            )
            
            # Removed dependence on "negative evidence" strings.
            if is_empty_components:
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
        检查结构中的所有节点是否已完成抽取（即 node_details 中有数据）。
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

    def remove_node(self, node_name: str) -> bool:
        """
        从结构（图谱）和 node_details 中移除节点。
        成功返回 True，未找到返回 False。
        """
        removed = False
        
        # 1. Remove from structure lists
        for category in ['upstream', 'midstream', 'downstream']:
            if node_name in self.industry_graph['structure'].get(category, []):
                self.industry_graph['structure'][category].remove(node_name)
                removed = True
        
        # 2. Remove from node_details
        if node_name in self.industry_graph['node_details']:
            del self.industry_graph['node_details'][node_name]
            removed = True

        if removed:
            self.log_event(f"Node removed: {node_name}")
            return True
        return False

    def merge_nodes(self, keep_name: str, drop_name: str) -> bool:
        """
        将 'drop_name' 合并到 'keep_name' 中。
        - 将 drop_name 的任何唯一抽取细节移动到 keep_name（简单策略）。
        - 从结构中移除 drop_name。
        - 更新引用（如果有链接逻辑，虽然目前图谱是隐式的）。
        """
        if drop_name not in self.industry_graph['node_details']:
            return False
            
        # Ensure keep_name exists (if not, maybe rename? assuming keep_name exists for now)
        if keep_name not in self.industry_graph['node_details']:
             self.log_event(f"Merge target '{keep_name}' does not exist. Initializing it.")
             # Try to find category of drop_name to assign to keep_name
             found_cat = 'upstream' # default
             for cat in ['upstream', 'midstream', 'downstream']:
                 if drop_name in self.industry_graph['structure'].get(cat, []):
                     found_cat = cat
                     break
             self.add_node_to_structure(keep_name, found_cat)

        # 合并细节逻辑
        # 策略：首选 keep_name 的细节。如果 keep_name 的细节为空/None，则取 drop_name 的。
        # 如果两者都有细节，可能合并列表（例如 input_elements）？
        # V1版本：简单的“为空则填充” + “合并证据”
        
        keep_data = self.industry_graph['node_details'].get(keep_name)
        drop_data = self.industry_graph['node_details'].get(drop_name)

        if not keep_data and drop_data:
            # Full copy if target is empty
            self.industry_graph['node_details'][keep_name] = drop_data
            # Update entity_name in the data
            if isinstance(drop_data, dict):
                self.industry_graph['node_details'][keep_name]['entity_name'] = keep_name
        
        elif keep_data and drop_data and isinstance(keep_data, dict) and isinstance(drop_data, dict):
            # Intelligent Merge for lists
            for list_key in ['input_elements', 'output_products', 'key_technologies', 'representative_companies']:
                if list_key in drop_data and isinstance(drop_data[list_key], list):
                    existing = set(keep_data.get(list_key, []))
                    for item in drop_data[list_key]:
                        if item not in existing:
                            keep_data.setdefault(list_key, []).append(item)
            
            # Merge Evidence (Simple append)
            if 'evidence_refs' in drop_data:
                keep_data.setdefault('evidence_refs', {}).update(drop_data['evidence_refs'])
        
        self.log_event(f"Merged node '{drop_name}' into '{keep_name}'.")
        
        # Remove the dropped node
        self.remove_node(drop_name)
        return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print("WorkflowState Refactored Test Start")
    state = WorkflowState("Semiconductor Industry")
    # Test passed...
