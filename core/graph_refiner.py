import logging
import json
from typing import Dict, Any, List
from core.llm_service import LLMService, LLMServiceError
from config import settings
from core.json_utils import clean_and_parse_json

logger = logging.getLogger(__name__)

class GraphRefiner:
    """
    负责对抽取完成的产业链图谱进行后处理和优化。
    主要功能：
    1. 识别并合并同义词节点（同名异义/同义异名）。
    2. 优化节点粒度。
    3. 简单的层级调整。
    """

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.prompt_template = settings.GRAPH_REFINEMENT_PROMPT

    def refine_graph(self, industry_graph: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行图谱优化流程。
        """
        logger.info("[GraphRefiner] 开始执行图谱优化...")
        
        # 1. Collect all nodes
        # 假设 industry_graph 结构中有 'upstream', 'midstream', 'downstream' 和 'details'
        # 我们主要关注 'details' 中的 keys，因为它们是实际提取了信息的实体。
        # 或者关注 upstream/midstream/downstream 列表中的 items。
        
        all_nodes = set()
        
        # 获取结构数据 (修复：正确的路径是 structure 子字典)
        structure = industry_graph.get('structure', {})
        
        # Collect from structure lists
        for category in ['upstream', 'midstream', 'downstream']:
            nodes = structure.get(category, [])
            if isinstance(nodes, list):
                all_nodes.update([n for n in nodes if isinstance(n, str)])
        
        # Collect from details keys (修复：键名是 node_details，不是 details)
        details = industry_graph.get('node_details', {})
        all_nodes.update(details.keys())
        
        nodes_list = sorted(list(all_nodes))
        
        if not nodes_list:
            logger.warning("[GraphRefiner] 图谱为空，跳过优化。")
            return industry_graph

        logger.info(f"[GraphRefiner] 识别到 {len(nodes_list)} 个节点，准备进行 LLM 审查...")

        # 2. Call LLM for suggestions
        # 如果节点太多，可能需要分批处理。这里暂时假设节点数量在 LLM 上下文范围内。
        # 简单策略：仅发送节点名称列表。
        
        prompt = self.prompt_template.format(nodes_list=json.dumps(nodes_list, ensure_ascii=False))
        
        try:
            response = self.llm_service.chat(
                query=prompt,
                system_prompt="你是一个数据治理专家。"
            )
            
            suggestions_data = clean_and_parse_json(response)
            
            if not suggestions_data or not isinstance(suggestions_data, dict):
                logger.warning("[GraphRefiner] LLM 返回格式错误，跳过优化。")
                return industry_graph
            
            merge_suggestions = suggestions_data.get('merge_suggestions', [])
            
            if not merge_suggestions:
                logger.info("[GraphRefiner] LLM 未提出合并建议。")
                return industry_graph
                
            # 3. Apply Suggestions
            refined_graph = self._apply_merges(industry_graph, merge_suggestions)
            return refined_graph

        except Exception as e:
            logger.error(f"[GraphRefiner] 优化过程出错: {e}", exc_info=True)
            return industry_graph

    def _apply_merges(self, graph: Dict[str, Any], suggestions: List[Dict]) -> Dict[str, Any]:
        """
        应用合并建议到图谱数据结构。
        """
        logger.info(f"[GraphRefiner] 正在应用 {len(suggestions)} 条合并建议...")
        
        # 修复：正确的键名是 node_details，且 structure 是嵌套的
        details = graph.get('node_details', {})
        structure = graph.get('structure', {})
        structure_updates = {k: list(structure.get(k, [])) for k in ['upstream', 'midstream', 'downstream']}
        
        for suggestion in suggestions:
            target = suggestion.get('target_node')
            sources = suggestion.get('source_nodes', [])
            
            if not target or not sources:
                continue
            
            # Clean sources: remove target from sources if present to avoid self-merge issues
            sources = [s for s in sources if s != target]
            
            if not sources:
                continue
                
            logger.info(f"[GraphRefiner] Merging {sources} -> {target} ({suggestion.get('reason')})")
            
            # A. Update Details Mapping
            # 目标节点的详细信息
            target_detail = details.get(target, {})
            if not target_detail: 
                # 如果目标节点不存在，尝试从源节点中找一个最丰富的作为基础，或者新建
                # 简单起见，从第一个存在的源节点复制
                for s in sources:
                    if s in details:
                        target_detail = details[s].copy()
                        target_detail['entity_name'] = target # 更新名称
                        details[target] = target_detail
                        break
            
            # 合并源节点的信息到目标节点 (简单合并列表字段)
            for s in sources:
                if s in details:
                    source_detail = details[s]
                    self._merge_node_content(target_detail, source_detail)
                    del details[s] # 删除源节点详情
            
            # B. Update Structure Lists
            for category in ['upstream', 'midstream', 'downstream']:
                current_list = structure_updates[category]
                new_list = []
                # Replace sources with target, avoid duplicates
                seen_target = False
                for item in current_list:
                    if item in sources:
                        if not seen_target and target not in current_list: # 如果target不在原列表中，则替换第一个source
                             new_list.append(target)
                             seen_target = True
                        elif target in current_list: # 如果target已在原列表中，直接移除source
                             pass
                    elif item == target:
                        new_list.append(item)
                        seen_target = True
                    else:
                        new_list.append(item)
                
                # Update list, removing duplicates just in case
                structure_updates[category] = sorted(list(set(new_list)))

        # Apply updates (修复：正确更新嵌套的 structure)
        graph['node_details'] = details
        graph['structure'].update(structure_updates)
        
        return graph

    def _merge_node_content(self, target: Dict, source: Dict):
        """
        Helper to merge lists from source to target.
        """
        fields = ['input_elements', 'output_products', 'key_technologies', 'representative_companies']
        for f in fields:
            t_list = target.get(f, [])
            s_list = source.get(f, [])
            if not isinstance(t_list, list): t_list = []
            if not isinstance(s_list, list): s_list = []
            
            # Merge and deduplicate
            merged = list(set(t_list + s_list))
            target[f] = merged
            
        # Append descriptions? Maybe just keep target's or longest.
        # Keeping target's for now to be simple.
