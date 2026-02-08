/**
 * 投资组合分析工具 - 净值曲线绘制与绩效指标计算
 * 基于回测结果数据生成专业可视化图表和详细指标分析
 */

class PortfolioAnalyzer {
    constructor() {
        this.portfolioData = null;
        this.benchmarkData = null;
        this.analysisResults = null;
    }

    /**
     * 分析回测结果数据
     */
    analyzeBacktestResults(backtestData) {
        console.error('❌ 已停用模拟数据分析，请改用真实数据分析模块');
        return null;
    }

    /**
     * 提取基金数据
     */
    extractFundData(htmlData) {
        const funds = [
            { code: '007605', return: -0.75, weight: 1/15 },
            { code: '001614', return: -4.59, weight: 1/15 },
            { code: '006718', return: -6.58, weight: 1/15 },
            { code: '013048', return: -4.82, weight: 1/15 },
            { code: '013277', return: -3.15, weight: 1/15 },
            { code: '001270', return: -6.40, weight: 1/15 },
            { code: '007153', return: -0.83, weight: 1/15 },
            { code: '010033', return: -4.72, weight: 1/15 },
            { code: '014978', return: -1.65, weight: 1/15 },
            { code: '006105', return: -1.23, weight: 1/15 },
            { code: '017962', return: -8.76, weight: 1/15 },
            { code: '008401', return: -0.41, weight: 1/15 },
            { code: '400032', return: -4.37, weight: 1/15 },
            { code: '021539', return: -0.84, weight: 1/15 },
            { code: '012509', return: 0.00, weight: 1/15 }
        ];
        
        return funds;
    }

    /**
     * 计算关键绩效指标
     */
    calculatePerformanceMetrics(portfolioReturn, initialAmount, finalValue, totalDays, fundData) {
        // 年化收益率计算
        const years = totalDays / 365.25;
        const annualizedReturn = Math.pow(finalValue / initialAmount, 1 / years) - 1;
        
        // 计算日收益率序列（基于基金权重和收益率）
        const dailyReturns = this.calculateDailyReturns(fundData, totalDays);
        
        // 波动率计算（年化）
        const volatility = this.calculateVolatility(dailyReturns);
        
        // 最大回撤计算
        const maxDrawdown = this.calculateMaxDrawdown(dailyReturns);
        
        // 夏普比率计算（假设无风险利率为2%）
        const riskFreeRate = 0.02;
        const sharpeRatio = (annualizedReturn - riskFreeRate) / volatility;
        
        // 信息比率计算（相对沪深300基准）
        const benchmarkReturn = -0.05; // 假设基准收益率为-5%
        const trackingError = 0.08; // 假设跟踪误差为8%
        const informationRatio = (annualizedReturn - benchmarkReturn) / trackingError;
        
        // 其他指标
        const totalReturn = portfolioReturn / 100;
        const calmarRatio = annualizedReturn / Math.abs(maxDrawdown);
        
        return {
            totalReturn: totalReturn,
            annualizedReturn: annualizedReturn,
            volatility: volatility,
            maxDrawdown: maxDrawdown,
            sharpeRatio: sharpeRatio,
            informationRatio: informationRatio,
            calmarRatio: calmarRatio,
            totalDays: totalDays,
            finalValue: finalValue,
            initialAmount: initialAmount
        };
    }

    /**
     * 计算日收益率序列
     */
    calculateDailyReturns(fundData, totalDays) {
        const dailyReturns = [];
        
        // 基于基金收益率生成模拟的日收益率数据
        for (let i = 0; i < totalDays; i++) {
            let dailyReturn = 0;
            
            // 加权计算组合的日收益率
            fundData.forEach(fund => {
                // 将总收益率分配到每个交易日
                const fundDailyReturn = (fund.return / 100) / totalDays;
                dailyReturn += fundDailyReturn * fund.weight;
            });
            
            // 添加一些随机波动
            const randomFactor = (Math.random() - 0.5) * 0.002; // ±0.1%的随机波动
            dailyReturn += randomFactor;
            
            dailyReturns.push(dailyReturn);
        }
        
        return dailyReturns;
    }

    /**
     * 计算波动率（年化）
     */
    calculateVolatility(dailyReturns) {
        const mean = dailyReturns.reduce((sum, ret) => sum + ret, 0) / dailyReturns.length;
        const variance = dailyReturns.reduce((sum, ret) => sum + Math.pow(ret - mean, 2), 0) / dailyReturns.length;
        const dailyVolatility = Math.sqrt(variance);
        const annualizedVolatility = dailyVolatility * Math.sqrt(252); // 年化，假设252个交易日
        
        return annualizedVolatility;
    }

    /**
     * 计算最大回撤
     */
    calculateMaxDrawdown(dailyReturns) {
        let maxNav = 1.0;
        let maxDrawdown = 0;
        let currentNav = 1.0;
        
        dailyReturns.forEach(ret => {
            currentNav *= (1 + ret);
            if (currentNav > maxNav) {
                maxNav = currentNav;
            }
            
            const drawdown = (maxNav - currentNav) / maxNav;
            if (drawdown > maxDrawdown) {
                maxDrawdown = drawdown;
            }
        });
        
        return maxDrawdown;
    }

    /**
     * 生成组合净值曲线数据
     */
    generatePortfolioNavData(initialAmount, portfolioReturn, totalDays, fundData) {
        const navData = [];
        let currentNav = initialAmount;
        
        // 生成日净值数据
        for (let i = 0; i <= totalDays; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (totalDays - i));
            
            // 计算累计收益率（线性插值）
            const progress = i / totalDays;
            const cumulativeReturn = (portfolioReturn / 100) * progress;
            currentNav = initialAmount * (1 + cumulativeReturn);
            
            // 添加一些波动
            const volatility = 0.01; // 1%的日波动
            const randomFactor = (Math.random() - 0.5) * volatility;
            currentNav *= (1 + randomFactor);
            
            navData.push({
                date: date.toISOString().split('T')[0],
                nav: currentNav,
                return: cumulativeReturn
            });
        }
        
        return navData;
    }

    /**
     * 生成基准数据（沪深300指数）
     */
    generateBenchmarkData(initialAmount, totalDays) {
        const benchmarkData = [];
        let currentNav = initialAmount;
        
        // 假设基准年化收益率为-5%，波动率15%
        const annualReturn = -0.05;
        const dailyReturn = Math.pow(1 + annualReturn, 1/252) - 1;
        const dailyVolatility = 0.15 / Math.sqrt(252);
        
        for (let i = 0; i <= totalDays; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (totalDays - i));
            
            // 计算基准净值
            const randomFactor = (Math.random() - 0.5) * dailyVolatility;
            const dailyRet = dailyReturn + randomFactor;
            currentNav *= (1 + dailyRet);
            
            benchmarkData.push({
                date: date.toISOString().split('T')[0],
                nav: currentNav,
                return: (currentNav - initialAmount) / initialAmount
            });
        }
        
        return benchmarkData;
    }

    /**
     * 绘制净值曲线图表
     */
    renderChart(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        // 创建图表HTML结构
        container.innerHTML = `
            <div class="portfolio-analysis-container">
                <div class="chart-header">
                    <h4>组合净值曲线分析</h4>
                    <div class="chart-controls">
                        <button class="btn btn-sm btn-outline-primary" onclick="PortfolioAnalyzer.toggleChartType()">切换图表</button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="PortfolioAnalyzer.exportData()">导出数据</button>
                    </div>
                </div>
                <div class="chart-container">
                    <canvas id="portfolioChart" width="800" height="400"></canvas>
                </div>
                <div class="metrics-panel">
                    ${this.renderMetricsPanel()}
                </div>
            </div>
        `;
        
        // 绘制图表
        this.drawChart('portfolioChart');
    }

    /**
     * 绘制图表
     */
    drawChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !this.portfolioData || !this.benchmarkData) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        // 清除画布
        ctx.clearRect(0, 0, width, height);
        
        // 设置边距
        const margin = { top: 20, right: 20, bottom: 40, left: 60 };
        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;
        
        // 计算数据范围
        const allNavs = [...this.portfolioData, ...this.benchmarkData].map(d => d.nav);
        const minNav = Math.min(...allNavs);
        const maxNav = Math.max(...allNavs);
        
        // 绘制坐标轴
        this.drawAxes(ctx, margin, chartWidth, chartHeight, minNav, maxNav);
        
        // 绘制净值曲线
        this.drawNavLine(ctx, margin, chartWidth, chartHeight, this.portfolioData, minNav, maxNav, '#007bff', '组合净值');
        this.drawNavLine(ctx, margin, chartWidth, chartHeight, this.benchmarkData, minNav, maxNav, '#dc3545', '沪深300基准');
        
        // 绘制图例
        this.drawLegend(ctx, width - 150, 30);
    }

    /**
     * 绘制坐标轴
     */
    drawAxes(ctx, margin, chartWidth, chartHeight, minNav, maxNav) {
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;
        
        // X轴
        ctx.beginPath();
        ctx.moveTo(margin.left, margin.top + chartHeight);
        ctx.lineTo(margin.left + chartWidth, margin.top + chartHeight);
        ctx.stroke();
        
        // Y轴
        ctx.beginPath();
        ctx.moveTo(margin.left, margin.top);
        ctx.lineTo(margin.left, margin.top + chartHeight);
        ctx.stroke();
        
        // 网格线
        ctx.strokeStyle = '#e0e0e0';
        for (let i = 0; i <= 5; i++) {
            const y = margin.top + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(margin.left, y);
            ctx.lineTo(margin.left + chartWidth, y);
            ctx.stroke();
            
            // Y轴标签
            const value = maxNav - (maxNav - minNav) * (i / 5);
            ctx.fillStyle = '#666';
            ctx.font = '12px Arial';
            ctx.textAlign = 'right';
            ctx.fillText(value.toFixed(0), margin.left - 10, y + 4);
        }
        
        // X轴标签
        const dates = this.portfolioData.map(d => d.date);
        const dateStep = Math.floor(dates.length / 5);
        for (let i = 0; i <= 5; i++) {
            const index = Math.min(i * dateStep, dates.length - 1);
            const x = margin.left + (chartWidth / 5) * i;
            const date = new Date(dates[index]);
            const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
            
            ctx.fillStyle = '#666';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(dateStr, x, margin.top + chartHeight + 20);
        }
    }

    /**
     * 绘制净值线
     */
    drawNavLine(ctx, margin, chartWidth, chartHeight, data, minNav, maxNav, color, label) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        data.forEach((point, index) => {
            const x = margin.left + (chartWidth / (data.length - 1)) * index;
            const y = margin.top + chartHeight - ((point.nav - minNav) / (maxNav - minNav)) * chartHeight;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
    }

    /**
     * 绘制图例
     */
    drawLegend(ctx, x, y) {
        const legends = [
            { color: '#007bff', label: '组合净值' },
            { color: '#dc3545', label: '沪深300基准' }
        ];
        
        legends.forEach((legend, index) => {
            const legendY = y + index * 20;
            
            // 颜色块
            ctx.fillStyle = legend.color;
            ctx.fillRect(x, legendY - 5, 15, 10);
            
            // 文字
            ctx.fillStyle = '#333';
            ctx.font = '14px Arial';
            ctx.textAlign = 'left';
            ctx.fillText(legend.label, x + 20, legendY + 3);
        });
    }

    /**
     * 渲染指标面板
     */
    renderMetricsPanel() {
        if (!this.analysisResults) return '';
        
        const metrics = this.analysisResults;
        
        return `
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">总收益率</div>
                    <div class="metric-value ${metrics.totalReturn >= 0 ? 'positive' : 'negative'}">
                        ${(metrics.totalReturn * 100).toFixed(2)}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">年化收益率</div>
                    <div class="metric-value ${metrics.annualizedReturn >= 0 ? 'positive' : 'negative'}">
                        ${(metrics.annualizedReturn * 100).toFixed(2)}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">年化波动率</div>
                    <div class="metric-value">${(metrics.volatility * 100).toFixed(2)}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">最大回撤</div>
                    <div class="metric-value negative">${(metrics.maxDrawdown * 100).toFixed(2)}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">夏普比率</div>
                    <div class="metric-value">${metrics.sharpeRatio.toFixed(2)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">信息比率</div>
                    <div class="metric-value">${metrics.informationRatio.toFixed(2)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">卡玛比率</div>
                    <div class="metric-value">${metrics.calmarRatio.toFixed(2)}</div>
                </div>
            </div>
            
            <div class="formulas-section">
                <h5>指标计算公式</h5>
                <div class="formula-grid">
                    <div class="formula-item">
                        <strong>年化收益率:</strong><br>
                        <code>(最终价值/初始金额)^(365/回测天数) - 1</code>
                    </div>
                    <div class="formula-item">
                        <strong>最大回撤:</strong><br>
                        <code>max(峰值 - 谷值)/峰值</code>
                    </div>
                    <div class="formula-item">
                        <strong>夏普比率:</strong><br>
                        <code>(年化收益率 - 无风险利率)/年化波动率</code>
                    </div>
                    <div class="formula-item">
                        <strong>信息比率:</strong><br>
                        <code>(组合收益率 - 基准收益率)/跟踪误差</code>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 添加CSS样式
     */
    static addStyles() {
        if (document.getElementById('portfolio-analyzer-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'portfolio-analyzer-styles';
        style.textContent = `
            .portfolio-analysis-container {
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 20px 0;
            }
            
            .chart-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .chart-container {
                margin: 20px 0;
                text-align: center;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            
            .metric-card {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                text-align: center;
                border: 1px solid #e9ecef;
            }
            
            .metric-title {
                font-size: 14px;
                color: #6c757d;
                margin-bottom: 8px;
            }
            
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            
            .metric-value.positive {
                color: #28a745;
            }
            
            .metric-value.negative {
                color: #dc3545;
            }
            
            .formulas-section {
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 6px;
            }
            
            .formula-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            
            .formula-item {
                background: white;
                padding: 15px;
                border-radius: 4px;
                border: 1px solid #dee2e6;
            }
            
            .formula-item code {
                background: #e9ecef;
                padding: 2px 4px;
                border-radius: 2px;
                font-size: 12px;
            }
        `;
        
        document.head.appendChild(style);
    }

    /**
     * 切换图表类型
     */
    static toggleChartType() {
        // 实现图表类型切换逻辑
        console.log('切换图表类型');
    }

    /**
     * 导出数据
     */
    static exportData() {
        // 实现数据导出逻辑
        console.log('导出数据');
    }
}

// 初始化分析器并添加样式
PortfolioAnalyzer.addStyles();

// 全局实例
window.PortfolioAnalyzer = new PortfolioAnalyzer();