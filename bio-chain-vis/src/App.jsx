import React, { useState, useMemo } from 'react';
import { GraphComponent } from './components/GraphComponent';
import { DetailSidebar } from './components/DetailSidebar';
import { processGraphData } from './utils/graphUtils';
import graphData from './data/graphData.json';
import { Layers } from 'lucide-react';

function App() {
  const [selectedNode, setSelectedNode] = useState(null);
  const elements = useMemo(() => processGraphData(graphData), []);

  return (
    <div className="w-full h-screen bg-emerald-50 relative overflow-hidden flex">
      {/* Background Gradient decoration */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-400/20 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-orange-400/20 rounded-full blur-[100px] pointer-events-none" />

      {/* Main Content Area */}
      <div className="flex-1 relative flex flex-col h-full z-10">
        {/* Navbar / Header */}
        <header className="h-16 px-8 flex items-center justify-between bg-white/30 backdrop-blur-sm border-b border-white/20">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-primary to-blue-600 p-2 rounded-lg text-white shadow-lg shadow-blue-500/30">
              <Layers size={20} />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-600">
              BioChainVis <span className="opacity-50 font-medium text-sm ml-2"> | {graphData.root_topic} Dashboard</span>
            </h1>
          </div>
          <div className="text-sm font-medium text-slate-500">
            {elements.length} Nodes Loaded
          </div>
        </header>

        {/* Graph Area */}
        <div className="flex-1 relative p-4 bg-slate-50/50">
          <GraphComponent
            elements={elements}
            onNodeClick={setSelectedNode}
          />

          {/* Legend / Overlay Controls (Simple) */}
          <div className="absolute bottom-8 left-8 bg-white/80 backdrop-blur rounded-lg p-4 shadow-sm border border-white/50 text-xs text-slate-600 space-y-2">
            <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-blue-500 mr-2" /> Upstream</div>
            <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-orange-500 mr-2" /> Midstream (Focus)</div>
            <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-emerald-500 mr-2" /> Downstream</div>
          </div>
        </div>
      </div>

      {/* Sidebar (Overlay) */}
      <DetailSidebar
        nodeId={selectedNode}
        data={graphData}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
}

export default App;
