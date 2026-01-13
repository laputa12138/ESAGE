import logging
import json
from typing import Dict, Any, Optional

from core.workflow_state import WorkflowState, TASK_TYPE_PLAN_STRUCTURE, TASK_TYPE_EXTRACT_NODE
from agents.structure_planner_agent import StructurePlannerAgent
from agents.node_extractor_agent import NodeExtractorAgent

logger = logging.getLogger(__name__)

class OrchestratorError(Exception):
    """Custom exception for Orchestrator errors."""
    pass

class Orchestrator:
    """
    Drives the industry extraction workflow by managing tasks from WorkflowState
    and dispatching them to appropriate agents.
    """
    def __init__(self,
                 workflow_state: WorkflowState,
                 structure_planner: StructurePlannerAgent,
                 node_extractor: NodeExtractorAgent,
                 max_workflow_iterations: int = 100,
                ):
        self.workflow_state = workflow_state
        self.agents = {
            TASK_TYPE_PLAN_STRUCTURE: structure_planner,
            TASK_TYPE_EXTRACT_NODE: node_extractor
        }
        self.max_workflow_iterations = max_workflow_iterations
        logger.info("编排器初始化完成，已加载结构规划与节点抽取智能体。")

    def _execute_task_type(self, task: Dict[str, Any]):
        """Executes a specific task by calling the appropriate agent."""
        task_type = task['type']
        task_id = task['id']
        payload = task.get('payload', {})

        agent = self.agents.get(task_type)

        if agent:
            try:
                task_name_cn = "结构规划" if task_type == TASK_TYPE_PLAN_STRUCTURE else "节点抽取"
                self.workflow_state.log_event(f"编排器正在分发任务 '{task_name_cn}' 给智能体 '{agent.agent_name}'。",
                                             {"task_id": task_id, "payload": payload})
                agent.execute_task(self.workflow_state, payload)
                # Agents are responsible for calling workflow_state.complete_task for their own tasks.
            except Exception as e:
                logger.error(f"执行任务 {task_type} ({task_id}) 时发生错误: {e}", exc_info=True)
                self.workflow_state.log_event(f"任务 {task_type} ({task_id}) 智能体执行出错",
                                             {"error": str(e), "agent": getattr(agent, 'agent_name', 'UnknownAgent')})
                self.workflow_state.complete_task(task_id, f"智能体执行失败: {e}", status='failed')
        else:
            logger.warning(f"未找到处理任务类型 {task_type} (task_id: {task_id}) 的智能体。")
            self.workflow_state.complete_task(task_id, f"未知任务类型 {task_type}", status='failed')

    def coordinate_workflow(self) -> None:
        """
        Main loop to coordinate the workflow.
        """
        self.workflow_state.log_event("编排器开始协调工作流。")
        iteration_count = 0
        stall_patience_counter = 0
        STALL_PATIENCE_THRESHOLD = 5

        while not self.workflow_state.get_flag('extraction_complete', False):
            if iteration_count >= self.max_workflow_iterations:
                self.workflow_state.log_event("达到最大工作流迭代次数。停止执行。", {"level": "ERROR"})
                break

            task = self.workflow_state.get_next_task()

            if not task:
                stall_patience_counter += 1
                
                # Check completion condition
                if self.workflow_state.are_all_nodes_extracted():
                    self.workflow_state.set_flag('extraction_complete', True)
                    self.workflow_state.log_event("所有节点抽取完成。工作流结束。")
                    break
                
                if stall_patience_counter >= STALL_PATIENCE_THRESHOLD:
                    logger.warning("编排器: 检测到停滞（任务队列长期为空）。停止执行。")
                    self.workflow_state.log_event("检测到停滞：任务队列为空且未完成所有节点抽取。")
                    break
            else:
                stall_patience_counter = 0
                self._execute_task_type(task)

            iteration_count += 1
            
            # Periodic logging
            if iteration_count % 5 == 0:
                 self.workflow_state.log_event(f"工作流迭代次数: {iteration_count}。")

        self.workflow_state.log_event("编排器工作流协调结束。")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Orchestrator Main Block (Update needed for test)")
