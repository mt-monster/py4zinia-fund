/**
 * 基金相关性分析交互式图表模块
 * 使用Chart.js库创建散点图、净值走势对比图、滚动相关性变化图和收益率分布对比图
 */

// 图表实例存储
const correlationCharts = {
    scatter: null,
    line: null,
    rolling: null,
    distribution: null
};

/**
 * 初始化相关性图表
 * @param {HTMLElement} container - 图表容器元素
 * @param {Object} chartData - 图表数据对象
 */
function initCorrelationCharts(container, chartData) {
    console.log('📊 初始化相关性图表模块');
    console.log('容器:', container);
    console.log('图表数据:', chartData);
    
    // 清空容器
    container.innerHTML = '';
    
    // 动态注入样式
    injectChartStyles();
    
    // 创建四个图表容器 - 适配后端实际返回的数据结构
    const scatterData = chartData.scatter_data;
    const lineData = chartData.nav_comparison_data || chartData.line_data;  // 后端返回nav_comparison_data
    const rollingData = chartData.rolling_correlation_data || chartData.rolling_data;  // 后端返回rolling_correlation_data
    const distributionData = chartData.distribution_data;
    
    console.log('数据检查:', {
        scatterData: !!scatterData,
        lineData: !!lineData,
        rollingData: !!rollingData,
        distributionData: !!distributionData,
        distributionKeys: distributionData ? Object.keys(distributionData) : null
    });
    
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
    
    if (rollingData) {
        const rollingWrapper = createChartWrapper('rolling-correlation-chart', '滚动相关性变化图');
        container.appendChild(rollingWrapper);
        initRollingChart(rollingData);
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
 * 创建图表包装器
 */
function createChartWrapper(canvasId, title) {
    const wrapper = document.createElement('div');
    wrapper.className = 'chart-wrapper';
    wrapper.innerHTML = `
        <canvas id="${canvasId}" class="chart-canvas"></canvas>
    `;
    return wrapper;
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
            gap: 35px;
            margin: 30px 0;
            padding: 30px;
            background: linear-gradient(145deg, #ffffff, #f8fafc);
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            width: 100%;
        }
        
        .chart-wrapper {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border: 1px solid #e2e8f0;
            position: relative;
            overflow: hidden;
            min-height: 500px;
            width: 100%;
        }
        
        .chart-wrapper:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }
        
        .chart-wrapper > * {
            max-width: 100%;
        }
        
        .chart-wrapper canvas {
            width: 100% !important;
            height: 500px !important;
        }
        
        /* 响应式设计 */
        @media (max-width: 992px) {
            .interactive-charts-container {
                gap: 30px;
                padding: 25px;
            }
            
            .chart-wrapper {
                padding: 25px;
                min-height: 450px;
            }
            
            .chart-wrapper canvas {
                height: 400px !important;
            }
        }
        
        @media (max-width: 768px) {
            .interactive-charts-container {
                gap: 25px;
                padding: 20px;
            }
            
            .chart-wrapper {
                padding: 20px;
                min-height: 400px;
            }
            
            .chart-wrapper canvas {
                height: 350px !important;
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
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 80,
                    right: 40,
                    top: 50,
                    bottom: 80
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `日收益率散点图 (相关系数: ${scatterData.correlation.toFixed(4)})`,
                    font: {
                        size: 18,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 25
                    }
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
                            return `基金1: ${(context.parsed.x * 100).toFixed(2)}%, 基金2: ${(context.parsed.y * 100).toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: scatterData.fund1_name + ' 日收益率 (%)',
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
                        text: scatterData.fund2_name + ' 日收益率 (%)',
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
 * 初始化净值走势对比图
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
    
    correlationCharts.line = new Chart(ctx, {
        type: 'line',
        data: {
            labels: lineData.dates,
            datasets: [
                {
                    label: lineData.fund1_name,
                    data: lineData.fund1_values,
                    borderColor: 'rgba(59, 130, 246, 0.8)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.1
                },
                {
                    label: lineData.fund2_name,
                    data: lineData.fund2_values,
                    borderColor: 'rgba(16, 185, 129, 0.8)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 80,
                    right: 40,
                    top: 50,
                    bottom: 80
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: '净值走势对比图',
                    font: {
                        size: 18,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 25
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 14
                        },
                        padding: 15,
                        usePointStyle: true
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
 * 初始化滚动相关性图
 */
function initRollingChart(rollingData) {
    const canvas = document.getElementById('rolling-correlation-chart');
    if (!canvas) {
        console.error('滚动相关性图Canvas元素未找到');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // 销毁旧图表
    if (correlationCharts.rolling) {
        correlationCharts.rolling.destroy();
    }
    
    correlationCharts.rolling = new Chart(ctx, {
        type: 'line',
        data: {
            labels: rollingData.dates,
            datasets: [{
                label: '滚动相关系数',
                data: rollingData.correlations,
                borderColor: 'rgba(147, 51, 234, 0.8)',
                backgroundColor: 'rgba(147, 51, 234, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    left: 80,
                    right: 40,
                    top: 50,
                    bottom: 80
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `滚动相关性变化图 (窗口: ${rollingData.window}天)`,
                    font: {
                        size: 18,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 25
                    }
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
                            return `相关系数: ${context.parsed.y.toFixed(4)}`;
                        }
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
                        text: '相关系数',
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
                    },
                    min: -1,
                    max: 1
                }
            }
        }
    });
}

/**
 * 初始化收益率分布对比图
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
    
    // 检查后端实际使用的字段名
    const bins = distributionData.bins || distributionData.labels;
    const fund1_counts = distributionData.fund1_counts || distributionData.fund1_data;
    const fund2_counts = distributionData.fund2_counts || distributionData.fund2_data;
    
    if (!bins || !fund1_counts || !fund2_counts) {
        console.error('❌ 收益率分布数据字段不完整:', {
            has_bins: !!bins,
            has_fund1_counts: !!fund1_counts,
            has_fund2_counts: !!fund2_counts,
            actual_keys: Object.keys(distributionData)
        });
        return;
    }
    
    console.log('📊 数据验证通过:');
    console.log('- bins/labels长度:', bins.length);
    console.log('- fund1_counts长度:', fund1_counts.length);
    console.log('- fund2_counts长度:', fund2_counts.length);
    console.log('- 实际数据样本:', {
        bins_sample: bins.slice(0, 3),
        fund1_sample: fund1_counts.slice(0, 3),
        fund2_sample: fund2_counts.slice(0, 3)
    });
    
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
                labels: bins,
                datasets: [
                    {
                        label: distributionData.fund1_name || '基金1',
                        data: fund1_counts,
                        backgroundColor: 'rgba(59, 130, 246, 0.6)',
                        borderColor: 'rgba(59, 130, 246, 0.8)',
                        borderWidth: 1
                    },
                    {
                        label: distributionData.fund2_name || '基金2',
                        data: fund2_counts,
                        backgroundColor: 'rgba(16, 185, 129, 0.6)',
                        borderColor: 'rgba(16, 185, 129, 0.8)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 80,
                        right: 40,
                        top: 50,
                        bottom: 80
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: '收益率分布对比图',
                        font: {
                            size: 18,
                            weight: 'bold'
                        },
                        padding: {
                            top: 10,
                            bottom: 25
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 14
                            },
                            padding: 15,
                            usePointStyle: true
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
        console.log('- 总数据点数:', fund1_counts.reduce((a,b) => a+b, 0) + fund2_counts.reduce((a,b) => a+b, 0));
        console.log('- 基金1总计数:', fund1_counts.reduce((a,b) => a+b, 0));
        console.log('- 基金2总计数:', fund2_counts.reduce((a,b) => a+b, 0));
        
    } catch (error) {
        console.error('❌ 收益率分布图创建失败:', error);
        console.error('错误详情:', error.stack);
    }
}

// 导出全局函数
window.initCorrelationCharts = initCorrelationCharts;

console.log('✅ fund-correlation-charts.js 模块加载完成');
