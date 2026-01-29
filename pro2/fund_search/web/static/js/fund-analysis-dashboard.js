/**
 * 基金综合分析仪表盘模块
 * 参考京东金融盈亏分析设计风格
 */

class FundAnalysisDashboard {
    constructor(containerId, data) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.data = data;
        
        // 颜色系统
        this.colors = [
            '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9a825', 
            '#9b59b6', '#2ecc71', '#ff7979', '#1abc9c',
            '#e74c3c', '#3498db', '#f39c12', '#2c3e50'
        ];
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error(`[FundAnalysisDashboard] Container #${this.containerId} not found`);
            return;
        }
        
        this.render();
    }
    
    render() {
        const html = `
            <div class="fund-dashboard">
                ${this.renderAssetAllocation()}
                ${this.renderIndustryDistribution()}
                ${this.renderTopStocks()}
                ${this.renderSummary()}
            </div>
        `;
        
        this.container.innerHTML = html;
        
        // 渲染图表
        this.renderCharts();
    }
    
    /**
     * 渲染资产配置
     */
    renderAssetAllocation() {
        if (!this.data.asset_allocation) return '';
        
        // 资产配置显示所有类型（包括0%的），按占比降序排列
        const entries = Object.entries(this.data.asset_allocation)
            .sort((a, b) => b[1] - a[1]);
        
        if (entries.length === 0) return '';
        
        // 只统计有值的资产类型
        const activeCount = entries.filter(([key, value]) => value > 0).length;
        
        // 计算总占比（股票+债券+现金+其他）
        const totalProportion = entries.reduce((sum, [, value]) => sum + value, 0);
        
        return `
            <div class="fund-dashboard-section">
                <div class="section-header">
                    <h3 class="section-title asset">资产配置</h3>
                    <span class="section-more">${activeCount}种资产</span>
                </div>
                <div class="chart-container">
                    <div class="chart-wrapper">
                        <canvas id="asset-chart" width="140" height="140"></canvas>
                        <div class="chart-center-text">
                            <div class="chart-center-number">${totalProportion.toFixed(1)}%</div>
                            <div class="chart-center-label">总占比</div>
                        </div>
                    </div>
                    <div class="legend-list">
                        ${entries.map(([name, value], index) => `
                            <div class="legend-item">
                                <div class="legend-left">
                                    <span class="legend-dot" style="background: ${this.colors[index % this.colors.length]}"></span>
                                    <span class="legend-name">${name}</span>
                                </div>
                                <div class="legend-right">
                                    <span class="legend-value">${value.toFixed(2)}%</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染行业分布
     */
    renderIndustryDistribution() {
        if (!this.data.industry_distribution) return '';
        
        const entries = Object.entries(this.data.industry_distribution)
            .sort((a, b) => b[1] - a[1]);
        
        if (entries.length === 0) return '';
        
        const totalCount = entries.length;
        
        // 计算行业总占比
        const totalProportion = entries.reduce((sum, [, value]) => sum + value, 0);
        
        return `
            <div class="fund-dashboard-section">
                <div class="section-header">
                    <h3 class="section-title industry">行业分布</h3>
                    <span class="section-more">${totalCount}个行业</span>
                </div>
                <div class="chart-container">
                    <div class="chart-wrapper">
                        <canvas id="industry-chart" width="140" height="140"></canvas>
                        <div class="chart-center-text">
                            <div class="chart-center-number">${totalProportion.toFixed(1)}%</div>
                            <div class="chart-center-label">总占比</div>
                        </div>
                    </div>
                    <div class="legend-list">
                        ${entries.slice(0, 6).map(([name, value], index) => `
                            <div class="legend-item">
                                <div class="legend-left">
                                    <span class="legend-dot" style="background: ${this.colors[index % this.colors.length]}"></span>
                                    <span class="legend-name">${name}</span>
                                </div>
                                <div class="legend-right">
                                    <span class="legend-value">${value.toFixed(2)}%</span>
                                </div>
                            </div>
                        `).join('')}
                        ${entries.length > 6 ? `
                            <div class="legend-item">
                                <div class="legend-left">
                                    <span class="legend-dot" style="background: #ddd"></span>
                                    <span class="legend-name">其他</span>
                                </div>
                                <div class="legend-right">
                                    <span class="legend-value">${entries.slice(6).reduce((sum, [, val]) => sum + val, 0).toFixed(2)}%</span>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染重仓股
     */
    renderTopStocks() {
        if (!this.data.top_stocks || this.data.top_stocks.length === 0) return '';
        
        const stocks = this.data.top_stocks.slice(0, 10);
        
        return `
            <div class="fund-dashboard-section">
                <div class="section-header">
                    <h3 class="section-title stocks">账户重仓股</h3>
                    <span class="section-more">TOP10</span>
                </div>
                <div class="stocks-list">
                    ${stocks.map((stock, index) => `
                        <div class="stock-item">
                            <div class="stock-info">
                                <div class="stock-name">${stock.stock_name || stock.name}</div>
                                <div class="stock-code">${stock.stock_code || stock.code}</div>
                            </div>
                            <div class="stock-metrics">
                                <div class="stock-ratio">${(stock.proportion || stock.ratio || 0).toFixed(2)}%</div>
                                <div class="stock-change ${this.getChangeClass(stock.change_percent || stock.change)}">
                                    ${this.formatChange(stock.change_percent || stock.change)}
                                </div>
                                <div class="stock-fund-count">${stock.fund_count || 1}只</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染分析摘要
     */
    renderSummary() {
        if (!this.data.summary) return '';
        
        const summary = this.data.summary;
        
        return `
            <div class="fund-dashboard-section">
                <div class="section-header">
                    <h3 class="section-title">分析摘要</h3>
                </div>
                <div class="summary-cards">
                    <div class="summary-card">
                        <div class="summary-label">总股票占比</div>
                        <div class="summary-value">${(summary.total_stock_proportion || 0).toFixed(2)}%</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-label">行业集中度(前3)</div>
                        <div class="summary-value">${(summary.top_industry_concentration || 0).toFixed(2)}%</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-label">重仓股集中度(前5)</div>
                        <div class="summary-value">${(summary.top_stock_concentration || 0).toFixed(2)}%</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-label">分析日期</div>
                        <div class="summary-value">${summary.analysis_date || '--'}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染图表
     */
    renderCharts() {
        // 资产配置环形图
        if (this.data.asset_allocation) {
            const assetCanvas = document.getElementById('asset-chart');
            if (assetCanvas) {
                this.renderDonutChart(assetCanvas, this.data.asset_allocation);
            }
        }
        
        // 行业分布环形图
        if (this.data.industry_distribution) {
            const industryCanvas = document.getElementById('industry-chart');
            if (industryCanvas) {
                this.renderDonutChart(industryCanvas, this.data.industry_distribution);
            }
        }
    }
    
    /**
     * 渲染环形图
     */
    renderDonutChart(canvas, data) {
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        
        // 设置画布实际尺寸（考虑设备像素比）
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
        
        // 清除画布
        ctx.clearRect(0, 0, rect.width, rect.height);
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const radius = Math.min(centerX, centerY) - 8;
        const innerRadius = radius * 0.6;
        
        const entries = Object.entries(data).filter(([key, value]) => value > 0);
        const total = entries.reduce((sum, [, value]) => sum + value, 0);
        
        if (total === 0) return;
        
        // 当只有一个数据项时，绘制不完整的环形（留一个缺口）
        const isSingleEntry = entries.length === 1;
        
        let currentAngle = -Math.PI / 2;
        
        entries.forEach(([name, value], index) => {
            let sliceAngle = (value / total) * 2 * Math.PI;
            
            // 如果是单一数据，留一个小的缺口（10度）
            if (isSingleEntry) {
                sliceAngle = 2 * Math.PI - (10 * Math.PI / 180);
            }
            
            // 绘制扇形
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.arc(centerX, centerY, innerRadius, currentAngle + sliceAngle, currentAngle, true);
            ctx.closePath();
            ctx.fillStyle = this.colors[index % this.colors.length];
            ctx.fill();
            
            currentAngle += sliceAngle;
        });
        
        // 绘制中心白色圆形背景，确保文字清晰
        ctx.beginPath();
        ctx.arc(centerX, centerY, innerRadius - 2, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
    }
    
    /**
     * 获取涨跌幅样式类
     */
    getChangeClass(change) {
        if (!change || change === '--') return '';
        const val = parseFloat(change);
        if (isNaN(val)) return '';
        return val >= 0 ? 'positive' : 'negative';
    }
    
    /**
     * 格式化涨跌幅
     */
    formatChange(change) {
        if (!change || change === '--') return '--';
        const val = parseFloat(change);
        if (isNaN(val)) return '--';
        const sign = val >= 0 ? '+' : '';
        return `${sign}${val.toFixed(2)}%`;
    }
}

/**
 * 初始化基金分析仪表盘
 */
function initFundAnalysisDashboard(containerId, data) {
    return new FundAnalysisDashboard(containerId, data);
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FundAnalysisDashboard, initFundAnalysisDashboard };
}

// 浏览器环境：挂载到 window 对象
if (typeof window !== 'undefined') {
    window.FundAnalysisDashboard = FundAnalysisDashboard;
    window.initFundAnalysisDashboard = initFundAnalysisDashboard;
}
