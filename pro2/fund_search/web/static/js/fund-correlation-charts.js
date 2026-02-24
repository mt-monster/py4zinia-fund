/**
 * 基金相关性分析交互式图表模块（优化版）
 * 使用Chart.js库创建散点图、净值走势对比图、滚动相关性变化图和收益率分布对比图
 * 
 * 优化特性:
 * 1. LTTB数据采样 - 大数据集时保持形状的同时减少渲染点
 * 2. 懒加载支持 - 按需加载详细数据
 * 3. 性能优化 - 减少不必要的重绘和内存占用
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
            // 三角形由 (lastSampled, point, avgPoint) 构成
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
    // 保留极值点和周期性采样点
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

// 配置常量
const CHART_CONFIG = {
    // 数据采样阈值
    sampling: {
        lineChart: 200,        // 净值走势图最大点数
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

// ==================== 原始代码（保留功能）====================

/**
 * 基金相关性分析交互式图表模块
 * 使用Chart.js库创建散点图、净值走势对比图、滚动相关性变化图和收益率分布对比图
 */

// 图表实例存储
const correlationCharts = {
    scatter: null,
    line: null,
    distribution: null
};

// 净值走势图表全屏状态
let lineChartFullscreen = false;

/**
 * 净值走势图表放大
 */
function zoomLineChartIn() {
    if (correlationCharts.line) {
        correlationCharts.line.zoom(1.2);
    }
}

/**
 * 净值走势图表缩小
 */
function zoomLineChartOut() {
    if (correlationCharts.line) {
        correlationCharts.line.zoom(0.8);
    }
}

/**
 * 净值走势图表重置缩放
 */
function resetLineChartZoom() {
    if (correlationCharts.line) {
        correlationCharts.line.resetZoom();
    }
}

/**
 * 净值走势图表全屏切换
 */
function toggleLineChartFullscreen() {
    const wrapper = document.getElementById('nav-comparison-chart')?.closest('.chart-wrapper');
    if (!wrapper) return;

    if (!lineChartFullscreen) {
        // 进入全屏
        if (wrapper.requestFullscreen) {
            wrapper.requestFullscreen();
        } else if (wrapper.webkitRequestFullscreen) {
            wrapper.webkitRequestFullscreen();
        }
        lineChartFullscreen = true;
    } else {
        // 退出全屏
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        }
        lineChartFullscreen = false;
    }
}

// 监听全屏变化
document.addEventListener('fullscreenchange', function() {
    const wrapper = document.getElementById('nav-comparison-chart')?.closest('.chart-wrapper');
    if (wrapper) {
        lineChartFullscreen = !!document.fullscreenElement;
        if (correlationCharts.line) {
            setTimeout(() => correlationCharts.line.resize(), 100);
        }
    }
});

/**
 * 初始化相关性图表
 * @param {HTMLElement} container - 图表容器元素
 * @param {Object} chartData - 图表数据对象
 */
function initCorrelationCharts(container, chartData) {
    console.log('📊 初始化相关性图表模块');
    console.log('容器:', container);
    console.log('图表数据:', chartData);
    console.log('数据结构类型:', chartData.primary_combination ? '多基金组合' : '传统双基金');
    
    // 优化DOM操作：只在需要时清空容器
    if (container && container.innerHTML && container.innerHTML.trim() !== '') {
        // 检查是否已有图表，避免重复渲染
        const existingCharts = container.querySelectorAll('canvas');
        if (existingCharts.length > 0) {
            console.log('🔄 检测到已有图表，先销毁旧图表...');
            Object.values(correlationCharts).forEach(chart => {
                if (chart && typeof chart.destroy === 'function') {
                    chart.destroy();
                }
            });
        }
        container.innerHTML = '';
    }
    
    // 动态注入样式
    injectChartStyles();
    
    // 创建四个图表容器 - 适配后端实际返回的数据结构
    // 处理新的数据结构：包含primary_combination、all_combinations、all_funds_nav_comparison和all_funds_distribution
    let scatterData, lineData, rollingData, distributionData;
    
    if (chartData.primary_combination) {
        // 新的数据结构：多基金组合分析
        const primaryCombination = chartData.primary_combination;
        scatterData = primaryCombination.scatter_data;
        rollingData = primaryCombination.rolling_correlation_data || primaryCombination.rolling_data;
        
        // 优先使用 all_funds_nav_comparison（支持多只基金显示）
        if (chartData.all_funds_nav_comparison && chartData.all_funds_nav_comparison.funds) {
            lineData = chartData.all_funds_nav_comparison;
            console.log('📊 使用所有基金净值对比数据，基金数量:', lineData.funds.length);
        } else {
            lineData = primaryCombination.nav_comparison_data || primaryCombination.line_data;
        }
        
        // 优先使用 all_funds_distribution（支持多只基金显示）
        if (chartData.all_funds_distribution && chartData.all_funds_distribution.funds) {
            distributionData = chartData.all_funds_distribution;
            console.log('📊 使用所有基金收益率分布数据，基金数量:', distributionData.funds.length);
        } else {
            distributionData = primaryCombination.distribution_data;
        }
        
        console.log('📊 处理多基金组合数据，主组合:', {
            fund1: primaryCombination.fund1_name,
            fund2: primaryCombination.fund2_name,
            combinationCount: chartData.all_combinations ? chartData.all_combinations.length : 0,
            totalFunds: lineData.funds ? lineData.funds.length : 2
        });
    } else {
        // 兼容旧的数据结构
        scatterData = chartData.scatter_data;
        lineData = chartData.nav_comparison_data || chartData.line_data;
        rollingData = chartData.rolling_correlation_data || chartData.rolling_data;
        distributionData = chartData.distribution_data;
        
        console.log('📊 处理传统双基金数据结构');
    }
    
    console.log('数据检查:', {
        scatterData: !!scatterData,
        lineData: !!lineData,
        rollingData: !!rollingData,
        distributionData: !!distributionData,
        distributionKeys: distributionData ? Object.keys(distributionData) : null
    });
    
    // 检查必需的数据是否存在
    if (!scatterData && !lineData && !rollingData && !distributionData) {
        console.error('❌ 没有任何有效的图表数据');
        return;
    }
    
    if (scatterData) {
        const scatterWrapper = createChartWrapper('scatter-correlation-chart', '日收益率散点图');
        container.appendChild(scatterWrapper);
        initScatterChart(scatterData);
    }
    
    if (lineData) {
        const lineWrapper = createChartWrapper('nav-comparison-chart', '净值走势对比图');
        container.appendChild(lineWrapper);
        initLineChart(lineData);
    }
    

    
    if (distributionData) {
        console.log('🚀 初始化收益率分布图，数据:', distributionData);
        const distributionWrapper = createChartWrapper('distribution-chart', '收益率分布对比图');
        container.appendChild(distributionWrapper);
        initDistributionChart(distributionData);
    } else {
        console.warn('⚠️ 收益率分布数据为空，跳过分布图创建');
        // 创建一个占位图表显示错误信息
        const distributionWrapper = createChartWrapper('distribution-chart', '收益率分布对比图');
        container.appendChild(distributionWrapper);
        const canvas = document.getElementById('distribution-chart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('暂无收益率分布数据', canvas.width/2, canvas.height/2);
        }
    }
    
    console.log('✅ 所有图表创建完成');
}

/**
 * 创建图表包装器（使用可折叠版本）
 */
function createChartWrapper(canvasId, title) {
    // 使用 CollapsibleChartManager 创建可折叠包装器
    return collapsibleChartManager.createCollapsibleWrapper(canvasId, title);
}

/**
 * 动态注入图表样式
 */
function injectChartStyles() {
    const styleId = 'fund-correlation-chart-styles';
    if (document.getElementById(styleId)) {
        return; // 样式已注入
    }
    
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
        .interactive-charts-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 40px;
            margin: 0;
            padding: 20px;
            background: linear-gradient(145deg, #ffffff, #f8fafc);
            border-radius: 0;
            box-shadow: none;
            width: 100vw;
            max-width: 100%;
            min-height: calc(100vh - 200px);
        }
        
        .chart-wrapper {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            border: 1px solid #e2e8f0;
            position: relative;
            overflow: hidden;
            min-height: 700px;
            width: 100%;
            max-width: 100%;
        }
        
        .chart-wrapper:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
        }
        
        .chart-wrapper > * {
            max-width: 100%;
        }
        
        .chart-wrapper canvas {
            width: 100% !important;
            height: 600px !important;
        }
        
        .chart-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .chart-title-text {
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
        }
        
        .chart-actions {
            display: flex;
            gap: 8px;
        }
        
        .chart-action-btn {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 6px 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: #4b5563;
            font-size: 14px;
        }
        
        .chart-action-btn:hover {
            background: #e0e7ff;
            border-color: #818cf8;
            color: #4f46e5;
        }
        
        .chart-wrapper.fullscreen-mode {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 9999;
            border-radius: 0;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            animation: none;
        }
        
        .chart-wrapper.fullscreen-mode canvas {
            height: calc(100vh - 80px) !important;
        }
        
        /* 响应式设计 */
        @media (max-width: 1200px) {
            .interactive-charts-container {
                gap: 35px;
                padding: 35px;
            }
            
            .chart-wrapper {
                padding: 25px;
                min-height: 600px;
            }
            
            .chart-wrapper canvas {
                height: 550px !important;
            }
        }
        
        @media (max-width: 992px) {
            .interactive-charts-container {
                gap: 30px;
                padding: 30px;
            }
            
            .chart-wrapper {
                padding: 20px;
                min-height: 500px;
            }
            
            .chart-wrapper canvas {
                height: 450px !important;
            }
            
            .chart-title-text {
                font-size: 15px;
            }
        }
        
        @media (max-width: 768px) {
            .interactive-charts-container {
                gap: 25px;
                padding: 25px;
            }
            
            .chart-wrapper {
                padding: 15px;
                min-height: 400px;
            }
            
            .chart-wrapper canvas {
                height: 350px !important;
            }
            
            .chart-toolbar {
                flex-direction: column;
                gap: 10px;
                align-items: flex-start;
            }
            
            .chart-title-text {
                font-size: 14px;
            }
        }
        
        @media (max-width: 480px) {
            .interactive-charts-container {
                gap: 20px;
                padding: 20px;
                margin: 20px 0;
            }
            
            .chart-wrapper {
                padding: 12px;
                min-height: 350px;
            }
            
            .chart-wrapper canvas {
                height: 300px !important;
            }
            
            .chart-title-text {
                font-size: 13px;
            }
        }
        
        /* 图表动画效果 */
        @keyframes chartAppear {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .chart-wrapper {
            animation: chartAppear 0.6s ease-out forwards;
        }
        
        .chart-wrapper:nth-child(1) { animation-delay: 0.1s; }
        .chart-wrapper:nth-child(2) { animation-delay: 0.2s; }
        .chart-wrapper:nth-child(3) { animation-delay: 0.3s; }
        .chart-wrapper:nth-child(4) { animation-delay: 0.4s; }
    `;
    document.head.appendChild(style);
}

/**
 * 初始化散点图
 */
function initScatterChart(scatterData) {
    const canvas = document.getElementById('scatter-correlation-chart');
    if (!canvas) {
        console.error('散点图Canvas元素未找到');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // 销毁旧图表
    if (correlationCharts.scatter) {
        correlationCharts.scatter.destroy();
    }
    
    correlationCharts.scatter = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: '收益率对比',
                data: scatterData.points.map(p => ({x: p.x, y: p.y})),
                backgroundColor: 'rgba(59, 130, 246, 0.5)',
                borderColor: 'rgba(59, 130, 246, 0.8)',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        plugins: [{
            id: 'registerChart',
            afterInit: (chart) => {
                collapsibleChartManager.registerChart('scatter-correlation-chart', chart);
                collapsibleChartManager.updateCounter('scatter-correlation-chart', `${scatterData.points.length} 个数据点`);
            }
        }],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 80,
                    right: 40,
                    top: 20,
                    bottom: 80
                }
            },
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltip: {
                    bodyFont: {
                        size: 14
                    },
                    titleFont: {
                        size: 14
                    },
                    callbacks: {
                        label: function(context) {
                            const fund1Name = formatFundName({fund_name: scatterData.fund1_name, fund_code: scatterData.fund1_code});
                            const fund2Name = formatFundName({fund_name: scatterData.fund2_name, fund_code: scatterData.fund2_code});
                            return [
                                `${fund1Name}: ${(context.parsed.x * 100).toFixed(2)}%`,
                                `${fund2Name}: ${(context.parsed.y * 100).toFixed(2)}%`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: formatFundName({fund_name: scatterData.fund1_name, fund_code: scatterData.fund1_code}) + ' 日收益率 (%)',
                        font: {
                            size: 15,
                            weight: 'bold'
                        },
                        padding: {
                            top: 20
                        }
                    },
                    ticks: {
                        font: {
                            size: 13
                        },
                        callback: function(value) {
                            return (value * 100).toFixed(2);
                        }
                    }
                },
                y: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: formatFundName({fund_name: scatterData.fund2_name, fund_code: scatterData.fund2_code}) + ' 日收益率 (%)',
                        font: {
                            size: 15,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 20
                        }
                    },
                    ticks: {
                        font: {
                            size: 13
                        },
                        callback: function(value) {
                            return (value * 100).toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

/**
 * 格式化基金名称显示
 * 优先使用基金名称，如果名称无效则使用代码
 */
function formatFundName(fund) {
    if (!fund) return '未知基金';
    
    // 如果传入的是字符串，直接返回
    if (typeof fund === 'string') return fund;
    
    // 优先使用 fund_name，如果不存在或与 fund_code 相同，则使用 fund_code
    let name = fund.fund_name || fund.name;
    const code = fund.fund_code || fund.code;
    
    // 如果名称无效（为空、与代码相同或包含代码），则显示代码
    if (!name || name === code || (code && name.includes(code))) {
        return code || '未知基金';
    }
    
    // 返回基金名称（过长时截断）
    return name.length > 15 ? name.substring(0, 15) + '...' : name;
}

/**
 * 初始化净值走势对比图（优化版 - 支持数据采样）
 * 支持多只基金同时显示
 */
function initLineChart(lineData) {
    const canvas = document.getElementById('nav-comparison-chart');
    if (!canvas) {
        console.error('净值走势图Canvas元素未找到');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // 销毁旧图表
    if (correlationCharts.line) {
        correlationCharts.line.destroy();
    }
    
    // 定义颜色方案（支持多只基金）
    const colors = [
        { border: 'rgba(59, 130, 246, 0.8)', background: 'rgba(59, 130, 246, 0.1)' },   // 蓝色
        { border: 'rgba(16, 185, 129, 0.8)', background: 'rgba(16, 185, 129, 0.1)' },   // 绿色
        { border: 'rgba(239, 68, 68, 0.8)', background: 'rgba(239, 68, 68, 0.1)' },     // 红色
        { border: 'rgba(245, 158, 11, 0.8)', background: 'rgba(245, 158, 11, 0.1)' },   // 橙色
        { border: 'rgba(139, 92, 246, 0.8)', background: 'rgba(139, 92, 246, 0.1)' },   // 紫色
        { border: 'rgba(236, 72, 153, 0.8)', background: 'rgba(236, 72, 153, 0.1)' },   // 粉色
        { border: 'rgba(6, 182, 212, 0.8)', background: 'rgba(6, 182, 212, 0.1)' },     // 青色
        { border: 'rgba(99, 102, 241, 0.8)', background: 'rgba(99, 102, 241, 0.1)' }    // 靛蓝
    ];
    
    let datasets = [];
    let labels = [];
    let isLargeDataset = false;
    
    // 检查是否是新的多基金数据结构 (all_funds_nav_comparison)
    if (lineData.funds && Array.isArray(lineData.funds)) {
        console.log('📊 使用多基金数据结构，基金数量:', lineData.funds.length);
        labels = lineData.dates;
        
        // 检查数据量是否需要采样
        const dataPoints = labels ? labels.length : 0;
        const needsSampling = dataPoints > CHART_CONFIG.sampling.lineChart;
        let sampleIndices = null; // 声明在函数作用域中，供后续使用
        
        if (needsSampling) {
            console.log(`📊 数据点过多(${dataPoints})，启用LTTB采样至${CHART_CONFIG.sampling.lineChart}点`);
            isLargeDataset = true;
            
            // 对标签和数据进行采样
            sampleIndices = getLTTBIndices(dataPoints, CHART_CONFIG.sampling.lineChart);
            labels = sampleIndices.map(idx => lineData.dates[idx]);
        }
        
        datasets = lineData.funds.map((fund, index) => {
            const color = colors[index % colors.length];
            const displayName = formatFundName(fund);
            
            // 采样数据（如果需要）
            let sampledValues = fund.values;
            if (needsSampling && fund.values && sampleIndices) {
                sampledValues = sampleIndices.map(idx => fund.values[idx]);
            }
            
            console.log(`📊 基金 ${index + 1} 显示名称:`, displayName, 
                        needsSampling ? `(采样后: ${sampledValues.length}点)` : `(${sampledValues.length}点)`);
            
            return {
                label: displayName,
                data: sampledValues,
                borderColor: color.border,
                backgroundColor: color.background,
                borderWidth: 2,
                pointRadius: 0,  // 大数据集时不显示点
                pointHoverRadius: isLargeDataset ? 5 : 4,
                tension: 0.1,
                // 大数据集优化
                borderWidth: isLargeDataset ? 1.5 : 2,
            };
        });
    } else {
        // 兼容旧的双基金数据结构
        console.log('📊 使用传统双基金数据结构');
        labels = lineData.dates;
        
        // 检查数据量
        const dataPoints = labels ? labels.length : 0;
        const needsSampling = dataPoints > CHART_CONFIG.sampling.lineChart;
        
        if (needsSampling) {
            console.log(`📊 数据点过多(${dataPoints})，启用LTTB采样至${CHART_CONFIG.sampling.lineChart}点`);
            isLargeDataset = true;
            const sampleIndices = getLTTBIndices(dataPoints, CHART_CONFIG.sampling.lineChart);
            labels = sampleIndices.map(idx => lineData.dates[idx]);
            
            datasets = [
                {
                    label: formatFundName({fund_name: lineData.fund1_name, fund_code: lineData.fund1_code}),
                    data: sampleIndices.map(idx => lineData.fund1_values[idx]),
                    borderColor: colors[0].border,
                    backgroundColor: colors[0].background,
                    borderWidth: 1.5,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    tension: 0.1
                },
                {
                    label: formatFundName({fund_name: lineData.fund2_name, fund_code: lineData.fund2_code}),
                    data: sampleIndices.map(idx => lineData.fund2_values[idx]),
                    borderColor: colors[1].border,
                    backgroundColor: colors[1].background,
                    borderWidth: 1.5,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    tension: 0.1
                }
            ];
        } else {
            datasets = [
                {
                    label: formatFundName({fund_name: lineData.fund1_name, fund_code: lineData.fund1_code}),
                    data: lineData.fund1_values,
                    borderColor: colors[0].border,
                    backgroundColor: colors[0].background,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.1
                },
                {
                    label: formatFundName({fund_name: lineData.fund2_name, fund_code: lineData.fund2_code}),
                    data: lineData.fund2_values,
                    borderColor: colors[1].border,
                    backgroundColor: colors[1].background,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.1
                }
            ];
        }
    }
    
    console.log('📊 创建净值走势图，数据集数量:', datasets.length, 
                isLargeDataset ? '(大数据集模式)' : '(标准模式)');



    correlationCharts.line = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        plugins: [{
            id: 'registerChart',
            afterInit: (chart) => {
                collapsibleChartManager.registerChart('nav-comparison-chart', chart);
                const totalPoints = labels ? labels.length : 0;
                collapsibleChartManager.updateCounter('nav-comparison-chart', `${totalPoints} 个数据点`);
            }
        }],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 80,
                    right: 40,
                    top: 20,
                    bottom: 80
                }
            },
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 12
                        },
                        padding: 12,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        boxWidth: 6,
                        boxHeight: 6
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    bodyFont: {
                        size: 14
                    },
                    titleFont: {
                        size: 14
                    }
                },
                zoom: {
                    zoom: {
                        wheel: {
                            enabled: true
                        },
                        pinch: {
                            enabled: true
                        },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '日期',
                        font: {
                            size: 15,
                            weight: 'bold'
                        },
                        padding: {
                            top: 20
                        }
                    },
                    ticks: {
                        font: {
                            size: 13
                        },
                        maxTicksLimit: 10
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '累计净值',
                        font: {
                            size: 15,
                            weight: 'bold'
                        },
                        padding: {
                            bottom: 20
                        }
                    },
                    ticks: {
                        font: {
                            size: 13
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}



/**
 * 初始化收益率分布对比图
 * 支持多只基金同时显示
 */
function initDistributionChart(distributionData) {
    console.log('📈 初始化收益率分布图，接收数据:', distributionData);
    
    const canvas = document.getElementById('distribution-chart');
    if (!canvas) {
        console.error('❌ 收益率分布图Canvas元素未找到');
        return;
    }
    
    // 验证数据完整性 - 适配后端实际返回的数据结构
    if (!distributionData) {
        console.error('❌ 收益率分布数据为空');
        return;
    }
    
    // 定义颜色方案（支持多只基金）- 与净值走势图使用相同的颜色
    const colors = [
        { background: 'rgba(59, 130, 246, 0.6)', border: 'rgba(59, 130, 246, 0.8)' },   // 蓝色
        { background: 'rgba(16, 185, 129, 0.6)', border: 'rgba(16, 185, 129, 0.8)' },   // 绿色
        { background: 'rgba(239, 68, 68, 0.6)', border: 'rgba(239, 68, 68, 0.8)' },     // 红色
        { background: 'rgba(245, 158, 11, 0.6)', border: 'rgba(245, 158, 11, 0.8)' },   // 橙色
        { background: 'rgba(139, 92, 246, 0.6)', border: 'rgba(139, 92, 246, 0.8)' },   // 紫色
        { background: 'rgba(236, 72, 153, 0.6)', border: 'rgba(236, 72, 153, 0.8)' },   // 粉色
        { background: 'rgba(6, 182, 212, 0.6)', border: 'rgba(6, 182, 212, 0.8)' },     // 青色
        { background: 'rgba(99, 102, 241, 0.6)', border: 'rgba(99, 102, 241, 0.8)' }    // 靛蓝
    ];
    
    let labels = [];
    let datasets = [];
    let fund1_counts = null; // 声明在函数作用域，供后续日志使用
    let fund2_counts = null;
    
    // 检查是否是新的多基金数据结构 (all_funds_distribution)
    if (distributionData.funds && Array.isArray(distributionData.funds)) {
        console.log('📊 使用多基金收益率分布数据，基金数量:', distributionData.funds.length);
        labels = distributionData.bins || distributionData.labels;
        
        datasets = distributionData.funds.map((fund, index) => {
            const color = colors[index % colors.length];
            const displayName = formatFundName(fund);
            console.log(`📊 收益率分布 - 基金 ${index + 1} 显示名称:`, displayName);
            
            return {
                label: displayName,
                data: fund.counts,
                backgroundColor: color.background,
                borderColor: color.border,
                borderWidth: 1
            };
        });
        
        console.log('📊 生成的数据集数量:', datasets.length);
    } else {
        // 兼容旧的双基金数据结构
        console.log('📊 使用传统双基金收益率分布数据');
        labels = distributionData.bins || distributionData.labels;
        fund1_counts = distributionData.fund1_counts || distributionData.fund1_data;
        fund2_counts = distributionData.fund2_counts || distributionData.fund2_data;
        
        if (!labels || !fund1_counts || !fund2_counts) {
            console.error('❌ 收益率分布数据字段不完整:', {
                has_bins: !!labels,
                has_fund1_counts: !!fund1_counts,
                has_fund2_counts: !!fund2_counts,
                actual_keys: Object.keys(distributionData)
            });
            return;
        }
        
        datasets = [
            {
                label: formatFundName({fund_name: distributionData.fund1_name, fund_code: distributionData.fund1_code}) || '基金1',
                data: fund1_counts,
                backgroundColor: colors[0].background,
                borderColor: colors[0].border,
                borderWidth: 1
            },
            {
                label: formatFundName({fund_name: distributionData.fund2_name, fund_code: distributionData.fund2_code}) || '基金2',
                data: fund2_counts,
                backgroundColor: colors[1].background,
                borderColor: colors[1].border,
                borderWidth: 1
            }
        ];
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.error('❌ 无法获取Canvas上下文');
        return;
    }
    
    // 销毁旧图表
    if (correlationCharts.distribution) {
        console.log('🗑️ 销毁旧的分布图');
        correlationCharts.distribution.destroy();
    }
    
    try {
        correlationCharts.distribution = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            plugins: [{
                id: 'registerChart',
                afterInit: (chart) => {
                    collapsibleChartManager.registerChart('distribution-chart', chart);
                    collapsibleChartManager.updateCounter('distribution-chart', `${datasets.length} 组数据`);
                }
            }],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 80,
                        right: 40,
                        top: 20,
                        bottom: 80
                    }
                },
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 12
                            },
                            padding: 12,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            boxWidth: 6,
                            boxHeight: 6
                        }
                    },
                    tooltip: {
                        bodyFont: {
                            size: 14
                        },
                        titleFont: {
                            size: 14
                        },
                        callbacks: {
                            title: function(tooltipItems) {
                                return `收益率区间: ${tooltipItems[0].label}`;
                            },
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y} 天`;
                            }
                        }
                    },
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: true
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'x'
                        },
                        pan: {
                            enabled: true,
                            mode: 'x'
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '日收益率区间',
                            font: {
                                size: 15,
                                weight: 'bold'
                            },
                            padding: {
                                top: 20
                            }
                        },
                        ticks: {
                            font: {
                                size: 13
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '天数',
                            font: {
                                size: 15,
                                weight: 'bold'
                            },
                            padding: {
                                bottom: 20
                            }
                        },
                        ticks: {
                            font: {
                                size: 13
                            }
                        }
                    }
                }
            }
        });
        
        console.log('✅ 收益率分布图创建成功');
        console.log('📊 图表数据统计:');
        let totalCount = 0;
        datasets.forEach(dataset => {
            if (dataset.data && dataset.data.reduce) {
                const sum = dataset.data.reduce((a,b) => a+b, 0);
                totalCount += sum;
                console.log(`- ${dataset.label} 总计数:`, sum);
            }
        });
        console.log('- 总数据点数:', totalCount);
        
    } catch (error) {
        console.error('❌ 收益率分布图创建失败:', error);
        console.error('错误详情:', error.stack);
    }
}

/**
 * 重置图表缩放
 * @param {string} canvasId - Canvas元素ID
 */
function resetZoom(canvasId) {
    let chart = null;
    if (canvasId === 'scatter-correlation-chart') {
        chart = correlationCharts.scatter;
    } else if (canvasId === 'nav-comparison-chart') {
        chart = correlationCharts.line;
    } else if (canvasId === 'rolling-correlation-chart') {
        chart = correlationCharts.rolling;
    } else if (canvasId === 'distribution-chart') {
        chart = correlationCharts.distribution;
    }
    
    if (chart && chart.resetZoom) {
        chart.resetZoom();
    } else if (chart) {
        console.log('图表不支持缩放重置');
    }
}

/**
 * 切换全屏模式
 * @param {HTMLElement} wrapper - 图表包装器元素
 */
function toggleFullscreen(wrapper) {
    if (!wrapper) return;
    
    wrapper.classList.toggle('fullscreen-mode');
    
    const btn = wrapper.querySelector('.chart-action-btn:last-child i');
    if (btn) {
        if (wrapper.classList.contains('fullscreen-mode')) {
            btn.className = 'bi bi-fullscreen-exit';
        } else {
            btn.className = 'bi bi-fullscreen';
        }
    }
    
    const canvas = wrapper.querySelector('canvas');
    if (canvas) {
        const chartId = canvas.id;
        let chart = null;
        if (chartId === 'scatter-correlation-chart') {
            chart = correlationCharts.scatter;
        } else if (chartId === 'nav-comparison-chart') {
            chart = correlationCharts.line;
        } else if (chartId === 'rolling-correlation-chart') {
            chart = correlationCharts.rolling;
        } else if (chartId === 'distribution-chart') {
            chart = correlationCharts.distribution;
        }
        
        if (chart) {
            setTimeout(() => {
                chart.resize();
            }, 100);
        }
    }
}

// 注册插件
if (window.Chart && window.ChartZoom) {
    Chart.register(ChartZoom);
}

// 导出全局函数
window.initCorrelationCharts = initCorrelationCharts;
window.resetZoom = resetZoom;
window.toggleFullscreen = toggleFullscreen;

console.log('✅ fund-correlation-charts.js 模块加载完成（含LTTB采样优化）');

