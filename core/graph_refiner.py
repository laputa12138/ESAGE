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
        
        details = graph.get('node_details', {})
        structure = graph.get('structure', {})
        # 使用副本进行更新
        structure_updates = {k: list(structure.get(k, [])) for k in ['upstream', 'midstream', 'downstream']}
        
        for suggestion in suggestions:
            target = suggestion.get('target_node')
            sources = suggestion.get('source_nodes', [])
            
            if not target or not sources:
                continue
            
            # Clean sources: remove target from sources if present
            sources = [s for s in sources if s != target]
            if not sources:
                continue
                
            logger.info(f"[GraphRefiner] Merging {sources} -> {target} ({suggestion.get('reason')})")
            
            # --- A. Update Details Mapping ---
            target_detail = details.get(target, {})
            if not target_detail: 
                # 如果目标节点不存在，尝试从源节点中找一个最丰富的作为基础
                for s in sources:
                    if s in details:
                        target_detail = details[s].copy()
                        target_detail['entity_name'] = target
                        details[target] = target_detail
                        break
            
            # 合并源节点的信息到目标节点
            for s in sources:
                if s in details:
                    source_detail = details[s]
                    self._merge_node_content(target_detail, source_detail)
                    del details[s]
            
            # --- B. Update Structure Lists (Fixing Duplication Issue) ---
            # 1. Determine the final category for the target node.
            #    Priority: 
            #    1. Already exists in a category -> Keep it there.
            #    2. Doesn't exist -> Use the category of the first source node found.
            #    3. Fallback -> 'upstream' (or maybe handle as error/warning)
            
            target_category = None
            
            # Check if target already exists in any category
            for cat in ['upstream', 'midstream', 'downstream']:
                if target in structure_updates[cat]:
                    target_category = cat
                    break
            
            # If not found, find category from sources
            if not target_category:
                for s in sources:
                    for cat in ['upstream', 'midstream', 'downstream']:
                        if s in structure_updates[cat]:
                            target_category = cat
                            break
                    if target_category:
                        break
            
            # Default fallback
            if not target_category:
                target_category = 'upstream' 
            
            # 2. Rebuild lists: Remove sources from ALL categories, Add target ONLY to target_category
            for cat in ['upstream', 'midstream', 'downstream']:
                current_list = structure_updates[cat]
                new_list = []
                
                for item in current_list:
                    # Remove sources
                    if item in sources:
                        continue
                    # Remove target if it's in the wrong category (e.g. moved via merge logic somehow, or duplicate cleanup)
                    if item == target and cat != target_category:
                        continue
                    # Keep other items
                    if item == target and cat == target_category:
                         # We will handle adding target explicitly to ensure it's there
                         pass 
                    else:
                        new_list.append(item)
                
                # If this is the target category, ensure target is added (once)
                if cat == target_category:
                     if target not in new_list:
                         new_list.append(target)
                
                structure_updates[cat] = new_list

        # Apply updates
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
