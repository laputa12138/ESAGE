/**
 * 数据服务模块
 * 用于动态加载和管理JSON数据文件
 */

/**
 * 从服务器获取可用的数据文件列表
 * @returns {Promise<Array>} 数据文件列表
 */
export const fetchDataFileList = async () => {
    try {
        const response = await fetch('/api/data-list');
        if (!response.ok) {
            throw new Error(`无法获取数据列表 (HTTP ${response.status})`);
        }
        return await response.json();
    } catch (error) {
        console.error('获取数据文件列表失败:', error);
        return [];
    }
};

/**
 * 从public/data目录加载指定的数据文件
 * @param {string} filename - 文件名
 * @returns {Promise<Object>} 加载的JSON数据
 */
export const loadDataFile = async (filename) => {
    try {
        // 从public/data目录加载数据（Vite会将public目录作为静态资源根目录）
        const response = await fetch(`/data/${filename}`);
        if (!response.ok) {
            throw new Error(`无法加载文件: ${filename} (HTTP ${response.status})`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('加载数据文件失败:', error);
        throw error;
    }
};

/**
 * 获取默认数据文件名
 * 优先从URL参数获取，否则返回列表中的第一个文件
 * @param {Array} availableFiles - 可用的文件列表
 * @returns {string|null} 默认数据文件名
 */
export const getDefaultDataFile = (availableFiles = []) => {
    // 从URL参数获取数据文件名
    const urlParams = new URLSearchParams(window.location.search);
    const dataFile = urlParams.get('data');

    if (dataFile && availableFiles.some(f => f.name === dataFile)) {
        return dataFile;
    }

    // 返回默认值：列表中的第一个文件
    if (availableFiles.length > 0) {
        return availableFiles[0].name;
    }

    return null;
};
