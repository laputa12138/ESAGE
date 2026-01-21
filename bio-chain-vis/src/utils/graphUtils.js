export const processGraphData = (data) => {
  const elements = [];
  const { structure, node_details } = data;

  // 1. Identify valid nodes and their types explicitly from structure
  const validNodes = new Map(); // id -> type
  
  structure.upstream?.forEach(id => validNodes.set(id, 'upstream'));
  structure.midstream?.forEach(id => validNodes.set(id, 'midstream'));
  structure.downstream?.forEach(id => validNodes.set(id, 'downstream'));

  // 2. Calculate positions for 3-column layout
  const COLUMN_WIDTH = 500;
  const ROW_HEIGHT = 100;
  
  const columns = {
    upstream: { x: 0, count: 0 },
    midstream: { x: COLUMN_WIDTH, count: 0 },
    downstream: { x: COLUMN_WIDTH * 2, count: 0 }
  };

  // 3. Add Nodes with Preset Positions
  // We sort them to ensure consistent ordering, maybe by name
  const sortedNodeIds = Array.from(validNodes.keys()).sort();

  sortedNodeIds.forEach(id => {
    const type = validNodes.get(id);
    const col = columns[type];
    
    // Safety check if type is somehow undefined (though map ensures it shouldn't be)
    if (!col) return;

    elements.push({
      data: { id, label: id, type },
      classes: type,
      position: { x: col.x, y: col.count * ROW_HEIGHT }
    });
    
    col.count++;
  });

  // Center vertical alignment
  const maxRows = Math.max(columns.upstream.count, columns.midstream.count, columns.downstream.count);
  const maxHeight = maxRows * ROW_HEIGHT;

  elements.forEach(el => {
    if (el.position) {
        const type = el.data.type;
        const colHeight = columns[type].count * ROW_HEIGHT;
        const offset = (maxHeight - colHeight) / 2;
        el.position.y += offset;
    }
  });


  // 4. Add Edges (STRICT FILTERING)
  // Only add edge if source AND target are in validNodes
  Object.entries(node_details).forEach(([nodeId, details]) => {
    if (!validNodes.has(nodeId)) return;

    // Inputs: Input (Source) -> Node (Target)
    if (details.input_elements) {
      details.input_elements.forEach(sourceId => {
        if (validNodes.has(sourceId)) {
           elements.push({
            data: { source: sourceId, target: nodeId, id: `${sourceId}-${nodeId}` }
          });
        }
      });
    }

    // Outputs: Node (Source) -> Output (Target)
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
