/**
 * 处理图数据并生成Cytoscape元素
 * 采用优化的网格布局：每个区域（上游/中游/下游）内部采用多行多列排列
 */
export const processGraphData = (data) => {
  const elements = [];
  const { structure, node_details } = data;

  // 1. 识别有效节点及其类型
  const validNodes = new Map(); // id -> type

  structure.upstream?.forEach(id => validNodes.set(id, 'upstream'));
  structure.midstream?.forEach(id => validNodes.set(id, 'midstream'));
  structure.downstream?.forEach(id => validNodes.set(id, 'downstream'));

  // 2. 布局配置参数
  const CONFIG = {
    // 网格单元格尺寸
    cellWidth: 200,      // 每个节点的水平间距
    cellHeight: 120,     // 每个节点的垂直间距
    // 区域之间的间距
    sectionGap: 350,     // 上中下游区域之间的水平间距
    // 每个区域内的最大列数（用于控制宽度）
    maxColsPerSection: 4,
    // 垂直偏移（顶部留白）
    topPadding: 100,
  };

  // 3. 按类型分组节点
  const nodesByType = {
    upstream: [],
    midstream: [],
    downstream: [],
  };

  // 排序节点以确保一致的顺序
  const sortedNodeIds = Array.from(validNodes.keys()).sort();
  sortedNodeIds.forEach(id => {
    const type = validNodes.get(id);
    if (nodesByType[type]) {
      nodesByType[type].push(id);
    }
  });

  // 4. 计算每个区域的布局信息
  const calculateSectionLayout = (nodes, maxCols) => {
    const count = nodes.length;
    if (count === 0) return { cols: 0, rows: 0, width: 0, height: 0 };

    // 根据节点数量动态计算列数，但不超过maxCols
    const cols = Math.min(maxCols, Math.ceil(Math.sqrt(count)));
    const rows = Math.ceil(count / cols);

    return {
      cols,
      rows,
      width: cols * CONFIG.cellWidth,
      height: rows * CONFIG.cellHeight,
    };
  };

  const layouts = {
    upstream: calculateSectionLayout(nodesByType.upstream, CONFIG.maxColsPerSection),
    midstream: calculateSectionLayout(nodesByType.midstream, CONFIG.maxColsPerSection),
    downstream: calculateSectionLayout(nodesByType.downstream, CONFIG.maxColsPerSection),
  };

  // 5. 计算每个区域的起始X坐标
  const sectionStartX = {
    upstream: 0,
    midstream: layouts.upstream.width + CONFIG.sectionGap,
    downstream: layouts.upstream.width + CONFIG.sectionGap + layouts.midstream.width + CONFIG.sectionGap,
  };

  // 6. 计算全局最大高度用于垂直居中
  const maxHeight = Math.max(layouts.upstream.height, layouts.midstream.height, layouts.downstream.height);

  // 7. 为每个节点计算位置
  const addNodesWithGridLayout = (nodes, type) => {
    const layout = layouts[type];
    const startX = sectionStartX[type];
    // 垂直居中偏移
    const verticalOffset = (maxHeight - layout.height) / 2 + CONFIG.topPadding;

    nodes.forEach((id, index) => {
      const col = index % layout.cols;
      const row = Math.floor(index / layout.cols);

      const x = startX + col * CONFIG.cellWidth + CONFIG.cellWidth / 2;
      const y = verticalOffset + row * CONFIG.cellHeight + CONFIG.cellHeight / 2;

      elements.push({
        data: { id, label: id, type },
        classes: type,
        position: { x, y }
      });
    });
  };

  addNodesWithGridLayout(nodesByType.upstream, 'upstream');
  addNodesWithGridLayout(nodesByType.midstream, 'midstream');
  addNodesWithGridLayout(nodesByType.downstream, 'downstream');

  // 8. 添加边（仅当源节点和目标节点都有效时）
  Object.entries(node_details).forEach(([nodeId, details]) => {
    if (!validNodes.has(nodeId)) return;

    // 输入边: 输入 (Source) -> 节点 (Target)
    if (details.input_elements) {
      details.input_elements.forEach(sourceId => {
        if (validNodes.has(sourceId)) {
          elements.push({
            data: { source: sourceId, target: nodeId, id: `${sourceId}-${nodeId}` }
          });
        }
      });
    }

    // 输出边: 节点 (Source) -> 输出 (Target)
    if (details.output_products) {
      details.output_products.forEach(targetId => {
        if (validNodes.has(targetId)) {
          elements.push({
            data: { source: nodeId, target: targetId, id: `${nodeId}-${targetId}` }
          });
        }
      });
    }
  });

  return elements;
};
