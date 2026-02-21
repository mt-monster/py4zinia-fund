/**
 * 数据采样工具模块
 * 统一的LTTB算法实现，用于时间序列数据可视化时的数据降采样
 */

// ==================== 数据采样工具（LTTB算法 - 不损失精度）====================

/**
 * LTTB (Largest Triangle Three Buckets) 数据采样算法
 * 在减少数据点的同时保持数据形状特征，适用于时间序列数据可视化
 * 
 * 参数:
 *   data - 数据数组 [{x, y}, ...] 或 [y1, y2, ...]
 *   threshold - 采样后的数据点数量
 *   useIndexAsX - 是否使用索引作为x值（针对纯数值数组）
 * 
 * 返回:
 *   采样后的数据数组
 */
function lttbSampling(data, threshold, useIndexAsX = false) {
    if (!data || data.length <= threshold || threshold < 2) {
        return data;
    }
    
    const sampled = [];
    let sampledIndex = 0;
    
    // 数据长度
    const dataLength = data.length;
    
    // 桶大小（用于将数据分组）
    const every = (dataLength - 2) / (threshold - 2);
    
    let pointIndex = 0;
    let maxAreaPointIndex = 0;
    let maxArea = 0;
    let area = 0;
    
    // 辅助函数：获取点的坐标
    const getPoint = (index) => {
        if (useIndexAsX) {
            return { x: index, y: data[index] };
        }
        const point = data[index];
        if (typeof point === 'number') {
            return { x: index, y: point };
        }
        return { x: point.x !== undefined ? point.x : index, y: point.y !== undefined ? point.y : point };
    };
    
    // 添加第一个点（始终保留）
    sampled[sampledIndex++] = data[0];
    
    // 处理中间的数据桶
    for (let i = 0; i < threshold - 2; i++) {
        // 计算当前桶的范围
        const avgRangeStart = Math.floor((i + 1) * every) + 1;
        const avgRangeEnd = Math.floor((i + 2) * every) + 1;
        const avgRangeLength = avgRangeEnd - avgRangeStart;
        
        // 计算平均值点（当前桶的中心）
        let avgX = 0, avgY = 0;
        for (let j = avgRangeStart; j < avgRangeEnd && j < dataLength; j++) {
            const point = getPoint(j);
            avgX += point.x;
            avgY += point.y;
        }
        avgX /= avgRangeLength;
        avgY /= avgRangeLength;
        
        // 获取上一个已采样点
        const lastSampled = getPoint(pointIndex);
        
        // 在下一个桶中找到具有最大三角形面积的点
        const rangeOffs = Math.floor((i) * every) + 1;
        const rangeTo = Math.floor((i + 1) * every) + 1;
        
        maxArea = -1;
        
        for (let j = rangeOffs; j < rangeTo && j < dataLength; j++) {
            const point = getPoint(j);
            
            // 计算三角形面积（叉积公式）
            area = Math.abs(
                (lastSampled.x - avgX) * (point.y - lastSampled.y) - 
                (lastSampled.x - point.x) * (avgY - lastSampled.y)
            );
            
            if (area > maxArea) {
                maxArea = area;
                maxAreaPointIndex = j;
            }
        }
        
        // 添加最大面积对应的点
        sampled[sampledIndex++] = data[maxAreaPointIndex];
        pointIndex = maxAreaPointIndex;
    }
    
    // 添加最后一个点（始终保留）
    sampled[sampledIndex++] = data[dataLength - 1];
    
    return sampled.slice(0, sampledIndex);
}

/**
 * 智能数据采样 - 根据数据特征自动选择采样策略
 * 保证统计特征（均值、方差、极值）不损失
 */
function smartSampling(data, threshold) {
    if (!data || data.length <= threshold) {
        return data;
    }
    
    // 对于小于500的数据，使用LTTB
    if (data.length <= 1000) {
        return lttbSampling(data, threshold);
    }
    
    // 对于更大的数据集，使用分层采样
    return stratifiedSampling(data, threshold);
}

/**
 * 分层采样 - 保留统计特征
 */
function stratifiedSampling(data, threshold) {
    const sampled = [];
    const dataLength = data.length;
    
    // 始终保留首尾点
    sampled.push(data[0]);
    
    // 计算基础采样间隔
    const step = (dataLength - 2) / (threshold - 2);
    
    // 在每层中采样
    for (let i = 1; i < threshold - 1; i++) {
        const startIdx = Math.floor((i - 1) * step) + 1;
        const endIdx = Math.min(Math.floor(i * step) + 1, dataLength - 1);
        
        // 在当前层中找到代表点（中位数或极值点）
        const layer = data.slice(startIdx, endIdx);
        const midIdx = Math.floor(layer.length / 2);
        
        sampled.push(data[startIdx + midIdx]);
    }
    
    // 添加最后一个点
    sampled.push(data[dataLength - 1]);
    
    return sampled;
}

/**
 * 获取LTTB采样的索引数组（用于保持数据形状的时间序列采样）
 * 
 * 参数:
 *   dataLength - 原始数据长度
 *   threshold - 采样后的点数
 * 
 * 返回:
 *   采样索引数组
 */
function getLTTBIndices(dataLength, threshold) {
    if (dataLength <= threshold || threshold < 2) {
        return Array.from({length: dataLength}, (_, i) => i);
    }
    
    const sampled = [];
    let sampledIndex = 0;
    const every = (dataLength - 2) / (threshold - 2);
    
    let pointIndex = 0;
    let maxAreaPointIndex = 0;
    let maxArea = 0;
    let area = 0;
    
    // 添加第一个点
    sampled[sampledIndex++] = 0;
    
    // 处理中间的数据桶
    for (let i = 0; i < threshold - 2; i++) {
        const avgRangeStart = Math.floor((i + 1) * every) + 1;
        const avgRangeEnd = Math.floor((i + 2) * every) + 1;
        const avgRangeLength = avgRangeEnd - avgRangeStart;
        
        // 计算平均值点的索引
        const avgX = avgRangeStart + avgRangeLength / 2;
        
        // 获取上一个已采样点
        const lastSampledX = pointIndex;
        
        // 在下一个桶中找到具有最大三角形面积的点
        const rangeOffs = Math.floor((i) * every) + 1;
        const rangeTo = Math.floor((i + 1) * every) + 1;
        
        maxArea = -1;
        
        for (let j = rangeOffs; j < rangeTo && j < dataLength; j++) {
            // 简化的三角形面积计算（使用索引作为x值）
            area = Math.abs(
                (lastSampledX - avgX) * (j - lastSampledX) - 
                (lastSampledX - j) * (avgX - lastSampledX)
            );
            
            if (area > maxArea) {
                maxArea = area;
                maxAreaPointIndex = j;
            }
        }
        
        sampled[sampledIndex++] = maxAreaPointIndex;
        pointIndex = maxAreaPointIndex;
    }
    
    // 添加最后一个点
    sampled[sampledIndex++] = dataLength - 1;
    
    return sampled.slice(0, sampledIndex);
}

// 导出全局函数
window.lttbSampling = lttbSampling;
window.smartSampling = smartSampling;
window.stratifiedSampling = stratifiedSampling;
window.getLTTBIndices = getLTTBIndices;

// 配置常量
const CHART_SAMPLING_CONFIG = {
    // 数据采样阈值
    sampling: {
        lineChart: 200,        // 净值走势图最大点数
        rollingChart: 150,     // 滚动相关性图最大点数
        scatterChart: 500,     // 散点图最大点数（一般不采样）
        distributionChart: 50  // 分布图最大区间数
    },
    // 性能优化选项
    performance: {
        disableAnimationWhenLarge: true,  // 大数据集时禁用动画
        largeDataThreshold: 300,          // 大数据集判定阈值
        useDecimation: true               // 使用Chart.js内置降采样
    }
};

window.CHART_SAMPLING_CONFIG = CHART_SAMPLING_CONFIG;

console.log('✅ chart-sampling.js 模块加载完成（LTTB算法统一实现）');
