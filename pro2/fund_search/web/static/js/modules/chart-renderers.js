/**
 * 图表渲染器模块
 * 封装各类图表的渲染逻辑
 */

const ChartRenderers = (function() {
    'use strict';

    const { CONFIG, getLTTBIndices, generateColors, formatPercent } = CorrelationCore;

    /**
     * 渲染净值对比图
     */
    function renderLineChart(ctx, data, options = {}) {
        const colors = generateColors(data.datasets?.length || 2);
        
        // 数据采样处理
        const dates = data.dates || [];
        let labels = dates;
        let sampledDatasets = [];
        
        if (dates.length > CONFIG.sampling.threshold) {
            const sampleIndices = getLTTBIndices(dates.map((_, i) => i), CONFIG.sampling.lineChart);
            labels = sampleIndices.map(idx => dates[idx]);
            
            sampledDatasets = data.datasets.map(ds => ({
                ...ds,
                data: sampleIndices.map(idx => ds.data[idx])
            }));
        } else {
            sampledDatasets = data.datasets;
        }

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: sampledDatasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.data,
                    borderColor: colors[i],
                    backgroundColor: colors[i].replace('0.8', '0.1'),
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: !!options.title,
                        text: options.title
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + 
                                       (context.parsed.y?.toFixed(4) || '-');
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '累计收益率'
                        }
                    }
                }
            }
        });
    }

    /**
     * 渲染散点图
     */
    function renderScatterChart(ctx, data, options = {}) {
        const { fund1Returns, fund2Returns, correlation, fund1Name, fund2Name } = data;
        
        const scatterData = fund1Returns.map((x, i) => ({
            x: x,
            y: fund2Returns[i]
        }));

        // 计算回归线
        const n = fund1Returns.length;
        const sumX = fund1Returns.reduce((a, b) => a + b, 0);
        const sumY = fund2Returns.reduce((a, b) => a + b, 0);
        const sumXY = fund1Returns.reduce((sum, x, i) => sum + x * fund2Returns[i], 0);
        const sumX2 = fund1Returns.reduce((sum, x) => sum + x * x, 0);
        
        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        const intercept = (sumY - slope * sumX) / n;
        
        const minX = Math.min(...fund1Returns);
        const maxX = Math.max(...fund1Returns);

        return new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: '日收益率分布',
                    data: scatterData,
                    backgroundColor: correlation > 0 
                        ? CONFIG.chart.colors.positive 
                        : CONFIG.chart.colors.negative,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }, {
                    label: '趋势线',
                    data: [
                        { x: minX, y: slope * minX + intercept },
                        { x: maxX, y: slope * maxX + intercept }
                    ],
                    type: 'line',
                    borderColor: 'rgba(0, 0, 0, 0.5)',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '日收益率散点图 (相关系数: ' + (correlation?.toFixed(4) || '-') + ')'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.dataset.type === 'line') return '趋势线';
                                return '(' + context.parsed.x?.toFixed(4) + ', ' + context.parsed.y?.toFixed(4) + ')';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: fund1Name
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: fund2Name
                        }
                    }
                }
            }
        });
    }

    /**
     * 渲染分布图
     */
    function renderDistributionChart(ctx, data, options = {}) {
        const { bins, fund1Counts, fund2Counts, fund1Name, fund2Name } = data;
        
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: bins.map(b => b.toFixed(2)),
                datasets: [
                    {
                        label: fund1Name,
                        data: fund1Counts,
                        backgroundColor: CONFIG.chart.colors.primary,
                        borderColor: CONFIG.chart.colors.primary,
                        borderWidth: 1
                    },
                    {
                        label: fund2Name,
                        data: fund2Counts,
                        backgroundColor: CONFIG.chart.colors.secondary,
                        borderColor: CONFIG.chart.colors.secondary,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '收益率分布对比'
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '收益率区间'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '频次'
                        }
                    }
                }
            }
        });
    }

    // 公开API
    return {
        renderLineChart,
        renderScatterChart,
        renderDistributionChart
    };
})();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartRenderers;
}
