import React from 'react';
import { Database, ChevronDown } from 'lucide-react';

/**
 * 数据源选择器组件
 * 提供下拉菜单用于切换不同的JSON数据文件
 */
export const DataSelector = ({ currentFile, onFileChange, isLoading, dataFiles = [] }) => {
    const currentLabel = dataFiles.find(f => f.name === currentFile)?.label || currentFile;

    return (
        <div className="relative inline-flex items-center">
            <div className="flex items-center space-x-2 bg-white/80 backdrop-blur rounded-lg px-3 py-2 shadow-sm border border-white/50">
                <Database size={16} className="text-slate-500" />
                <select
                    value={currentFile}
                    onChange={(e) => onFileChange(e.target.value)}
                    disabled={isLoading}
                    className="bg-transparent text-sm font-medium text-slate-700 border-none outline-none cursor-pointer pr-6 appearance-none"
                    style={{ minWidth: '200px' }}
                >
                    {dataFiles.map((file) => (
                        <option key={file.name} value={file.name}>
                            {file.label}
                        </option>
                    ))}
                </select>
                <ChevronDown size={14} className="text-slate-400 absolute right-3 pointer-events-none" />
            </div>
            {isLoading && (
                <div className="ml-2 w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            )}
        </div>
    );
};

export default DataSelector;
