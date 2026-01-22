"""
工作流日志器 (Workflow Logger)

专用于 E-SAGE 系统的清晰、简洁日志输出模块。
设计目标：
1. 清晰展示每个 Agent 的输入/输出
2. 显示生成的 Query 列表
3. 显示 Reranker 得分
4. 显示实体处理结果
5. 不显示详细 Prompt，仅记录到日志文件
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowLogger:
    """
    专用工作流日志器，提供清晰简洁的执行追踪。
    
    输出格式示例：
    ═══════════════════════════════════════════════════════════════
    [Agent: NodeExtractorAgent] 任务: 抽取节点 "细胞株"
    ───────────────────────────────────────────────────────────────
    输入:
      - 节点名称: 细胞株
      - 检索 Query: [vector: 3, bm25: 3]
    
    检索结果:
      - 召回文档: 15 篇
      - Reranker Top-5 得分: [0.92, 0.87, 0.75, 0.68, 0.55]
    
    抽取结果:
      - input_elements: 5 项 (验证通过: 3)
      - output_products: 4 项 (验证通过: 2)
      - representative_companies: 8 项 (验证通过: 5)
    ───────────────────────────────────────────────────────────────
    """
    
    # 分隔线样式
    SEPARATOR_THICK = "═" * 65
    SEPARATOR_THIN = "─" * 65
    
    def __init__(self, enable_console: bool = True, log_level: str = "INFO"):
        """
        初始化工作流日志器。
        
        Args:
            enable_console: 是否在控制台输出格式化日志
            log_level: 日志级别
        """
        self.enable_console = enable_console
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
    
    def log_agent_start(self, agent_name: str, task_description: str, inputs: Dict[str, Any]) -> None:
        """
        记录智能体任务开始。
        
        Args:
            agent_name: 智能体名称
            task_description: 任务描述
            inputs: 输入参数字典
        """
        lines = [
            "",
            self.SEPARATOR_THICK,
            f"[Agent: {agent_name}] 任务: {task_description}",
            self.SEPARATOR_THIN,
            "输入:",
        ]
        
        for key, value in inputs.items():
            if isinstance(value, list):
                lines.append(f"  - {key}: {len(value)} 项")
            elif isinstance(value, dict):
                lines.append(f"  - {key}: {len(value)} 个字段")
            else:
                # 截断过长的值
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                lines.append(f"  - {key}: {value_str}")
        
        self._output("\n".join(lines))
    
    def log_query_generation(self, vector_queries: List[str], bm25_queries: List[str]) -> None:
        """
        记录生成的检索查询。
        
        Args:
            vector_queries: 向量检索查询列表
            bm25_queries: BM25 关键词查询列表
        """
        lines = [
            "",
            "生成的检索 Query:",
            f"  - Vector Queries ({len(vector_queries)}):"
        ]
        for i, q in enumerate(vector_queries[:5], 1):  # 最多显示5个
            lines.append(f"      {i}. {q[:60]}{'...' if len(q) > 60 else ''}")
        
        lines.append(f"  - BM25 Queries ({len(bm25_queries)}):")
        for i, q in enumerate(bm25_queries[:5], 1):
            lines.append(f"      {i}. {q[:60]}{'...' if len(q) > 60 else ''}")
        
        self._output("\n".join(lines))
    
    def log_retrieval_results(self, 
                               doc_count: int, 
                               reranker_scores: Optional[List[float]] = None,
                               top_sources: Optional[List[str]] = None) -> None:
        """
        记录检索结果。
        
        Args:
            doc_count: 召回文档数量
            reranker_scores: Reranker 得分列表
            top_sources: 来源文档名列表
        """
        lines = [
            "",
            "检索结果:",
            f"  - 召回文档: {doc_count} 篇"
        ]
        
        if reranker_scores:
            top_5_scores = [f"{s:.2f}" for s in reranker_scores[:5]]
            lines.append(f"  - Reranker Top-5 得分: [{', '.join(top_5_scores)}]")
        
        if top_sources:
            lines.append(f"  - 主要来源:")
            for src in top_sources[:3]:
                # 仅显示文件名
                src_name = src.split("/")[-1].split("\\")[-1]
                if len(src_name) > 50:
                    src_name = src_name[:47] + "..."
                lines.append(f"      • {src_name}")
        
        self._output("\n".join(lines))
    
    def log_extraction_results(self, 
                                node_name: str,
                                extracted_fields: Dict[str, int],
                                verified_counts: Optional[Dict[str, int]] = None) -> None:
        """
        记录抽取结果。
        
        Args:
            node_name: 节点名称
            extracted_fields: 各字段抽取数量 {"input_elements": 5, ...}
            verified_counts: 各字段验证通过数量
        """
        lines = [
            "",
            f"抽取结果 [{node_name}]:"
        ]
        
        for field, count in extracted_fields.items():
            if verified_counts and field in verified_counts:
                verified = verified_counts[field]
                lines.append(f"  - {field}: {count} 项 (验证通过: {verified})")
            else:
                lines.append(f"  - {field}: {count} 项")
        
        self._output("\n".join(lines))
    
    def log_verification_detail(self, 
                                 entity: str, 
                                 verified: bool, 
                                 score: float,
                                 breakdown: Optional[Dict[str, float]] = None) -> None:
        """
        记录单个实体的验证详情 (仅在 DEBUG 模式)。
        
        Args:
            entity: 实体名称
            verified: 是否验证通过
            score: 最终得分
            breakdown: 得分分解 {"lexical": 0.5, "nli": 0.8}
        """
        status = "✓" if verified else "✗"
        detail = f"  {status} {entity}: {score:.2f}"
        
        if breakdown:
            detail += f" (Lex: {breakdown.get('lexical', 0):.2f}, NLI: {breakdown.get('nli', 0):.2f})"
        
        logger.debug(detail)
    
    def log_agent_end(self, agent_name: str, success: bool, summary: str = "") -> None:
        """
        记录智能体任务结束。
        
        Args:
            agent_name: 智能体名称
            success: 是否成功
            summary: 结果摘要
        """
        status = "成功" if success else "失败"
        lines = [
            "",
            f"[{agent_name}] 任务{status}{'：' + summary if summary else ''}",
            self.SEPARATOR_THIN,
            ""
        ]
        self._output("\n".join(lines))
    
    def log_workflow_progress(self, 
                               iteration: int, 
                               pending_tasks: int, 
                               completed_nodes: int,
                               total_nodes: int) -> None:
        """
        记录工作流进度。
        
        Args:
            iteration: 当前迭代次数
            pending_tasks: 待处理任务数
            completed_nodes: 已完成节点数
            total_nodes: 总节点数
        """
        progress = f"{completed_nodes}/{total_nodes}"
        line = f"[Workflow] 迭代 {iteration} | 待处理任务: {pending_tasks} | 节点进度: {progress}"
        self._output(line)
    
    def log_graph_stats(self, 
                        upstream_count: int,
                        midstream_count: int,
                        downstream_count: int,
                        pruned_count: int = 0) -> None:
        """
        记录图谱统计信息。
        
        Args:
            upstream_count: 上游节点数
            midstream_count: 中游节点数
            downstream_count: 下游节点数
            pruned_count: 剪枝移除的节点数
        """
        total = upstream_count + midstream_count + downstream_count
        lines = [
            "",
            self.SEPARATOR_THICK,
            "图谱统计:",
            f"  - 上游节点: {upstream_count}",
            f"  - 中游节点: {midstream_count}",
            f"  - 下游节点: {downstream_count}",
            f"  - 总计: {total} 个有效节点",
        ]
        
        if pruned_count > 0:
            lines.append(f"  - 剪枝移除: {pruned_count} 个空节点")
        
        lines.append(self.SEPARATOR_THICK)
        lines.append("")
        
        self._output("\n".join(lines))
    
    def _output(self, message: str) -> None:
        """
        输出日志消息。
        
        Args:
            message: 日志消息
        """
        if self.enable_console:
            print(message)
        logger.info(message)


# 全局单例
_workflow_logger: Optional[WorkflowLogger] = None


def get_workflow_logger() -> WorkflowLogger:
    """
    获取全局工作流日志器实例。
    
    Returns:
        WorkflowLogger 实例
    """
    global _workflow_logger
    if _workflow_logger is None:
        _workflow_logger = WorkflowLogger()
    return _workflow_logger


def init_workflow_logger(enable_console: bool = True, log_level: str = "INFO") -> WorkflowLogger:
    """
    初始化全局工作流日志器。
    
    Args:
        enable_console: 是否在控制台输出
        log_level: 日志级别
    
    Returns:
        初始化后的 WorkflowLogger 实例
    """
    global _workflow_logger
    _workflow_logger = WorkflowLogger(enable_console=enable_console, log_level=log_level)
    return _workflow_logger
