/**
 * 图表性能优化模块
 * 提供DOM操作优化和图表控制功能
 */

// 图表容器优化
const ChartContainerOptimizer = {
    // 智能清空容器 - 只在需要时才清空
    smartClear: function(container) {
        if (!container) return;
        
        // 检查是否已有图表
        const existingCharts = container.querySelectorAll('canvas');
        if (existingCharts.length > 0) {
            console.log('🔄 检测到已有图表，先销毁旧图表...');
            // 销毁所有已存在的图表实例
            if (typeof correlationCharts !== 'undefined') {
                Object.values(correlationCharts).forEach(chart => {
                    if (chart && typeof chart.destroy === 'function') {
                        try {
                            chart.destroy();
                        } catch (e) {
                            console.warn('销毁图表失败:', e);
                        }
                    }
                });
            }
        }
        
        // 清空容器
        container.innerHTML = '';
    },
    
    // 检查容器是否需要刷新
    needsRefresh: function(container, newData) {
        if (!container || !container.innerHTML) return true;
        if (container.innerHTML.trim() === '') return true;
        return false;
    }
};

// 图表控制按钮管理器
const ChartControlButtons = {
    // 为图表添加控制按钮
    addControlButtons: function(canvasId, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const wrapper = canvas.closest('.chart-wrapper');
        if (!wrapper) return;
        
        // 检查是否已有控制按钮（包括chart-toolbar）
        if (wrapper.querySelector('.chart-zoom-controls') || wrapper.querySelector('.chart-toolbar')) {
            console.log('控制按钮已存在，跳过');
            return;
        }
        
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'chart-zoom-controls';
        controlsDiv.style.cssText = 'position: absolute; top: 10px; right: 10px; display: flex; gap: 5px; z-index: 10;';
        
        let buttonsHtml = `
            <button class="btn btn-sm btn-outline-secondary" onclick="ChartControlButtons.toggleFullscreen('${canvasId}')" title="全屏">
                <i class="bi bi-fullscreen"></i>
            </button>
        `;
        
        // 根据选项添加缩放按钮
        if (options.zoom !== false) {
            buttonsHtml += `
                <button class="btn btn-sm btn-outline-primary" onclick="ChartControlButtons.zoomIn('${canvasId}')" title="放大">+</button>
                <button class="btn btn-sm btn-outline-primary" onclick="ChartControlButtons.zoomOut('${canvasId}')" title="缩小">-</button>
                <button class="btn btn-sm btn-outline-secondary" onclick="ChartControlButtons.resetZoom('${canvasId}')" title="重置">⟲</button>
            `;
        }
        
        controlsDiv.innerHTML = buttonsHtml;
        wrapper.style.position = 'relative';
        wrapper.appendChild(controlsDiv);
    },
    
    // 放大
    zoomIn: function(canvasId) {
        const chart = this.getChartInstance(canvasId);
        if (chart && chart.zoom) {
            chart.zoom(1.2);
        }
    },
    
    // 缩小
    zoomOut: function(canvasId) {
        const chart = this.getChartInstance(canvasId);
        if (chart && chart.zoom) {
            chart.zoom(0.8);
        }
    },
    
    // 重置缩放
    resetZoom: function(canvasId) {
        const chart = this.getChartInstance(canvasId);
        if (chart && chart.resetZoom) {
            chart.resetZoom();
        }
    },
    
    // 全屏切换
    toggleFullscreen: function(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const wrapper = canvas.closest('.chart-wrapper');
        if (!wrapper) return;
        
        if (!document.fullscreenElement) {
            if (wrapper.requestFullscreen) {
                wrapper.requestFullscreen();
            } else if (wrapper.webkitRequestFullscreen) {
                wrapper.webkitRequestFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
        }
    },
    
    // 获取图表实例
    getChartInstance: function(canvasId) {
        // 尝试从correlationCharts获取
        if (typeof correlationCharts !== 'undefined') {
            const chartMap = {
                'scatter-correlation-chart': 'scatter',
                'nav-comparison-chart': 'line',
                'distribution-chart': 'distribution'
            };
            const key = chartMap[canvasId];
            if (key && correlationCharts[key]) {
                return correlationCharts[key];
            }
        }
        
        // 尝试从Chart.js获取
        const canvas = document.getElementById(canvasId);
        if (canvas && canvas.chart) {
            return canvas.chart;
        }
        
        return null;
    }
};

// 导出到全局
window.ChartContainerOptimizer = ChartContainerOptimizer;
window.ChartControlButtons = ChartControlButtons;

console.log('✅ chart-performance.js 模块加载完成');
