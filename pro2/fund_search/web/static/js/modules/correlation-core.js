/**
 * 相关性分析核心模块
 * 包含数据采样、日期处理、格式化等公共函数
 */

const CorrelationCore = (function() {
    'use strict';

    // 图表配置常量
    const CONFIG = {
        sampling: {
            lineChart: 200,
            scatterChart: 500,
            threshold: 500
        },
        chart: {
            animationDuration: 300,
            colors: {
                primary: 'rgba(54, 162, 235, 0.8)',
                secondary: 'rgba(255, 99, 132, 0.8)',
                positive: 'rgba(16, 185, 129, 0.6)',
                negative: 'rgba(239, 68, 68, 0.6)'
            }
        }
    };

    /**
     * 数据采样算法（LTTB）
     * @param {Array} data - 原始数据
     * @param {number} threshold - 采样后数据点数量
     */
    function lttbSampling(data, threshold) {
        if (!data || data.length <= threshold) return data;
        
        const sampled = [];
        let sampledIndex = 0;
        const every = (data.length - 2) / (threshold - 2);
        
        let a = 0;
        let maxAreaPoint;
        let maxArea;
        let area;
        let nextA;
        
        sampled[sampledIndex++] = data[0];
        
        for (let i = 0; i < threshold - 2; i++) {
            let avgX = 0;
            let avgY = 0;
            let avgRangeStart = Math.floor((i + 1) * every) + 1;
            let avgRangeEnd = Math.floor((i + 2) * every) + 1;
            avgRangeEnd = avgRangeEnd < data.length ? avgRangeEnd : data.length;
            
            const avgRangeLength = avgRangeEnd - avgRangeStart;
            
            for (; avgRangeStart < avgRangeEnd; avgRangeStart++) {
                avgX += avgRangeStart;
                avgY += data[avgRangeStart];
            }
            
            avgX /= avgRangeLength;
            avgY /= avgRangeLength;
            
            let rangeOffs = Math.floor((i) * every) + 1;
            let rangeTo = Math.floor((i + 1) * every) + 1;
            
            const pointAX = a;
            const pointAY = data[a];
            
            maxArea = area = -1;
            
            for (; rangeOffs < rangeTo; rangeOffs++) {
                area = Math.abs((pointAX - avgX) * (data[rangeOffs] - pointAY) -
                               (pointAX - rangeOffs) * (avgY - pointAY));
                
                if (area > maxArea) {
                    maxArea = area;
                    maxAreaPoint = data[rangeOffs];
                    nextA = rangeOffs;
                }
            }
            
            sampled[sampledIndex++] = maxAreaPoint;
            a = nextA;
        }
        
        sampled[sampledIndex++] = data[data.length - 1];
        return sampled;
    }

    /**
     * 获取LTTB采样索引
     */
    function getLTTBIndices(data, threshold) {
        if (data.length <= threshold) {
            return data.map((_, i) => i);
        }
        
        const indices = [];
        let sampledIndex = 0;
        const every = (data.length - 2) / (threshold - 2);
        
        indices[sampledIndex++] = 0;
        
        for (let i = 0; i < threshold - 2; i++) {
            let avgX = 0;
            let avgY = 0;
            let avgRangeStart = Math.floor((i + 1) * every) + 1;
            let avgRangeEnd = Math.floor((i + 2) * every) + 1;
            avgRangeEnd = avgRangeEnd < data.length ? avgRangeEnd : data.length;
            
            const avgRangeLength = avgRangeEnd - avgRangeStart;
            
            for (; avgRangeStart < avgRangeEnd; avgRangeStart++) {
                avgX += avgRangeStart;
                avgY += data[avgRangeStart];
            }
            
            avgX /= avgRangeLength;
            avgY /= avgRangeLength;
            
            let rangeOffs = Math.floor((i) * every) + 1;
            let rangeTo = Math.floor((i + 1) * every) + 1;
            
            maxArea = -1;
            let maxAreaIdx = rangeOffs;
            
            for (; rangeOffs < rangeTo; rangeOffs++) {
                const area = Math.abs((indices[indices.length - 1] - avgX) * (data[rangeOffs] - data[indices[indices.length - 1]]) -
                                    (indices[indices.length - 1] - rangeOffs) * (avgY - data[indices[indices.length - 1]]));
                
                if (area > maxArea) {
                    maxArea = area;
                    maxAreaIdx = rangeOffs;
                }
            }
            
            indices[sampledIndex++] = maxAreaIdx;
        }
        
        indices[sampledIndex++] = data.length - 1;
        return indices;
    }

    /**
     * 格式化日期
     */
    function formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    }

    /**
     * 格式化百分比
     */
    function formatPercent(value, decimals = 2) {
        if (value === null || value === undefined) return '-';
        return (value * 100).toFixed(decimals) + '%';
    }

    /**
     * 防抖函数
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * 合并两个日期数组，取交集
     */
    function alignDates(dates1, dates2) {
        const set1 = new Set(dates1);
        return dates2.filter(d => set1.has(d));
    }

    /**
     * 生成随机颜色
     */
    function generateColors(count) {
        const colors = [
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 99, 132, 0.8)',
            'rgba(75, 192, 192, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(153, 102, 255, 0.8)',
            'rgba(255, 159, 64, 0.8)',
            'rgba(199, 199, 199, 0.8)',
            'rgba(83, 102, 255, 0.8)'
        ];
        
        const result = [];
        for (let i = 0; i < count; i++) {
            result.push(colors[i % colors.length]);
        }
        return result;
    }

    // 公开API
    return {
        CONFIG,
        lttbSampling,
        getLTTBIndices,
        formatDate,
        formatPercent,
        debounce,
        alignDates,
        generateColors
    };
})();

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CorrelationCore;
}
