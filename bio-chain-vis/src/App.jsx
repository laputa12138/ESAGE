import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { GraphComponent } from './components/GraphComponent';
import { DetailSidebar } from './components/DetailSidebar';
import { DataSelector } from './components/DataSelector';
import { processGraphData } from './utils/graphUtils';
import { loadDataFile, getDefaultDataFile, fetchDataFileList } from './utils/dataService';
import { Layers, AlertCircle } from 'lucide-react';

function App() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [availableFiles, setAvailableFiles] = useState([]);
  const [currentDataFile, setCurrentDataFile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // 加载数据文件
  const loadData = useCallback(async (filename) => {
    if (!filename) return;

    setIsLoading(true);
    setError(null);
    setSelectedNode(null);

    try {
      const data = await loadDataFile(filename);
      setGraphData(data);
      setCurrentDataFile(filename);

      // 更新URL参数，方便分享和书签
      const url = new URL(window.location);
      url.searchParams.set('data', filename);
      window.history.replaceState({}, '', url);
    } catch (err) {
      setError(`加载数据失败: ${err.message}`);
      console.error('加载数据失败:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 初始加载：获取文件列表并加载默认文件
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      try {
        const files = await fetchDataFileList();
        setAvailableFiles(files);

        const defaultFile = getDefaultDataFile(files);
        if (defaultFile) {
          loadData(defaultFile);
        } else {
          setIsLoading(false); // 没有找到文件
          if (files.length === 0) {
            setError('未找到数据文件，请在 public/data 目录下添加 JSON 文件');
          }
        }
      } catch (e) {
        console.error("Initialization error:", e);
        setIsLoading(false);
        setError('初始化失败');
      }
    };
    init();
  }, [loadData]);

  // 处理数据源切换
  const handleDataFileChange = useCallback((filename) => {
    loadData(filename);
  }, [loadData]);

  // 处理图形数据
  const elements = useMemo(() => {
    if (!graphData) return [];
    return processGraphData(graphData);
  }, [graphData]);

  // 错误状态显示
  if (error) {
    return (
      <div className="w-full h-screen bg-red-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-red-700 mb-2">加载失败</h2>
          <p className="text-slate-600 mb-4">{error}</p>
          <button
            onClick={() => loadData(currentDataFile)}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

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
              BioChainVis <span className="opacity-50 font-medium text-sm ml-2">| {graphData?.root_topic || '加载中...'} Dashboard</span>
            </h1>
          </div>
          <div className="flex items-center space-x-4">
            {/* 数据源选择器 */}
            {/* 数据源选择器 */}
            <DataSelector
              currentFile={currentDataFile}
              onFileChange={handleDataFileChange}
              isLoading={isLoading}
              dataFiles={availableFiles}
            />
            <div className="text-sm font-medium text-slate-500">
              {isLoading ? '加载中...' : `${elements.length} Nodes Loaded`}
            </div>
          </div>
        </header>

        {/* Graph Area */}
        <div className="flex-1 relative p-4 bg-slate-50/50">
          {isLoading ? (
            <div className="w-full h-full flex items-center justify-center">
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-slate-500">正在加载数据...</p>
              </div>
            </div>
          ) : (
            <GraphComponent
              elements={elements}
              onNodeClick={setSelectedNode}
            />
          )}

          {/* Legend / Overlay Controls (Simple) */}
          <div className="absolute bottom-8 left-8 bg-white/80 backdrop-blur rounded-lg p-4 shadow-sm border border-white/50 text-xs text-slate-600 space-y-2">
            <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-blue-500 mr-2" /> 上游 (Upstream)</div>
            <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-orange-500 mr-2" /> 中游 (Midstream)</div>
            <div className="flex items-center"><div className="w-3 h-3 rounded-full bg-emerald-500 mr-2" /> 下游 (Downstream)</div>
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
