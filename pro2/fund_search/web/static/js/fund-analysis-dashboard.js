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
        
        // 存储股票数据用于弹窗
        this.stocksData = [];
        
        // 重仓股展开状态
        this.isStocksExpanded = false;
        
        // 卡片展开状态
        this.cardExpandState = {
            holdings: false,    // 持仓分布
            sector: false,      // 板块分布
            asset: false        // 资产配置
        };
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error(`[FundAnalysisDashboard] Container #${this.containerId} not found`);
            return;
        }
        
        this.render();
        this.bindEvents();
    }
    
    render() {
        const html = `
            <div class="fund-dashboard">
                <div class="dashboard-grid">
                    ${this.renderFundDistribution()}
                    ${this.renderSectorDistribution()}
                    ${this.renderAssetAllocation()}
                </div>
                ${this.renderTopStocksTable()}
                ${this.renderStrategyAnalysis()}
            </div>
            ${this.renderFundModal()}
        `;
        
        this.container.innerHTML = html;
        
        // 渲染图表
        this.renderCharts();
    }
    
    /**
     * 绑定事件处理器
     */
    bindEvents() {
        // 为关联基金单元格绑定点击事件
        const fundCells = this.container.querySelectorAll('.stock-fund-cell[data-stock-index]');
        fundCells.forEach(cell => {
            cell.addEventListener('click', (e) => this.handleFundCellClick(e));
        });
        
        // 为"更多"按钮绑定点击事件（重仓股表格）
        const stocksMore = this.container.querySelector('.stocks-more');
        if (stocksMore) {
            stocksMore.addEventListener('click', () => this.handleStocksMoreClick());
        }
        
        // 为卡片"更多"按钮绑定点击事件
        const cardMoreBtns = this.container.querySelectorAll('.card-more[data-card-type]');
        cardMoreBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.handleCardMoreClick(e));
        });
        
        // 模态框关闭事件
        const modal = this.container.querySelector('.fund-modal');
        if (modal) {
            // 点击遮罩层关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeFundModal();
                }
            });
            
            // 关闭按钮点击
            const closeBtn = modal.querySelector('.fund-modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeFundModal());
            }
        }
        
        // ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFundModal();
            }
        });
    }
    
    /**
     * 处理"更多"按钮点击 - 展开/收起重仓股列表
     */
    handleStocksMoreClick() {
        this.isStocksExpanded = !this.isStocksExpanded;
        this.updateStocksTable();
    }
    
    /**
     * 处理卡片"更多"按钮点击 - 展开/收起卡片内容
     */
    handleCardMoreClick(e) {
        const cardType = e.currentTarget.dataset.cardType;
        if (!cardType) return;
        
        // 切换展开状态
        this.cardExpandState[cardType] = !this.cardExpandState[cardType];
        
        // 更新对应卡片内容
        switch (cardType) {
            case 'holdings':
                this.updateHoldingsCard();
                break;
            case 'sector':
                this.updateSectorCard();
                break;
            case 'asset':
                this.updateAssetCard();
                break;
        }
        
        // 更新按钮状态
        const btn = e.currentTarget;
        const isExpanded = this.cardExpandState[cardType];
        btn.textContent = isExpanded ? '收起 ‹' : '更多 ›';
        btn.classList.toggle('expanded', isExpanded);
    }
    
    /**
     * 更新持仓分布卡片内容
     */
    updateHoldingsCard() {
        const card = this.container.querySelector('.dashboard-card[data-card="holdings"]');
        if (!card) return;
        
        const fundList = card.querySelector('.fund-list');
        if (!fundList) return;
        
        // 从strategy_analysis获取基金数据
        let data = [];
        if (this.data.strategy_analysis && this.data.strategy_analysis.funds) {
            data = this.data.strategy_analysis.funds.map(fund => ({
                fund_code: fund.fund_code,
                fund_name: fund.fund_name,
                ratio: fund.composite_score * 100,
                proportion: fund.composite_score * 100,
                today_return: fund.today_return,
                status_label: fund.status_label
            }));
        }
        
        const isExpanded = this.cardExpandState.holdings;
        const displayData = isExpanded ? data : data.slice(0, 6);
        
        fundList.innerHTML = displayData.length > 0 ? displayData.map((fund, index) => `
            <div class="fund-list-item ${index >= 6 ? 'card-item-expanded' : ''}">
                <span class="fund-list-name" style="color: ${this.colors[index % this.colors.length]}">${fund.fund_name || fund.fund_code}</span>
                <span class="fund-list-ratio">${(fund.ratio || fund.proportion || 0).toFixed(2)}%</span>
            </div>
        `).join('') : '<div class="empty-hint">暂无持仓数据</div>';
        
        // 更新"更多"按钮显示状态
        const moreBtn = card.querySelector('.card-more');
        if (moreBtn) {
            if (data.length <= 6) {
                moreBtn.style.display = 'none';
            } else {
                moreBtn.style.display = '';
            }
        }
    }
    
    /**
     * 更新板块分布卡片内容
     */
    updateSectorCard() {
        const card = this.container.querySelector('.dashboard-card[data-card="sector"]');
        if (!card) return;
        
        const legendList = card.querySelector('.chart-legend-list');
        if (!legendList) return;
        
        if (!this.data.industry_distribution) return;
        
        const entries = Object.entries(this.data.industry_distribution)
            .sort((a, b) => b[1] - a[1]);
        
        const isExpanded = this.cardExpandState.sector;
        const displayEntries = isExpanded ? entries : entries.slice(0, 6);
        
        legendList.innerHTML = displayEntries.map(([name, value], index) => `
            <div class="legend-row ${index >= 6 ? 'card-item-expanded' : ''}">
                <div class="legend-label">
                    <span class="legend-color" style="background: ${this.colors[index % this.colors.length]}"></span>
                    <span class="legend-text">${name}</span>
                </div>
                <div class="legend-data">
                    <span class="legend-amount">${this.formatAmount(value)}元</span>
                    <span class="legend-pct">${value.toFixed(2)}%</span>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * 更新资产配置卡片内容
     */
    updateAssetCard() {
        const card = this.container.querySelector('.dashboard-card[data-card="asset"]');
        if (!card) return;
        
        const legendList = card.querySelector('.chart-legend-list');
        if (!legendList) return;
        
        if (!this.data.asset_allocation) return;
        
        const entries = Object.entries(this.data.asset_allocation)
            .sort((a, b) => b[1] - a[1]);
        
        const isExpanded = this.cardExpandState.asset;
        const displayEntries = isExpanded ? entries : entries.slice(0, 6);
        
        legendList.innerHTML = displayEntries.map(([name, value], index) => `
            <div class="legend-row ${index >= 6 ? 'card-item-expanded' : ''}">
                <div class="legend-label">
                    <span class="legend-color" style="background: ${this.colors[index % this.colors.length]}"></span>
                    <span class="legend-text">${name}</span>
                </div>
                <div class="legend-data">
                    <span class="legend-amount">${this.formatAmount(value)}元</span>
                    <span class="legend-pct">${value.toFixed(2)}%</span>
                </div>
            </div>
        `).join('');
    }
    
    /**
     * 更新重仓股表格（展开/收起）
     */
    updateStocksTable() {
        const stocksSection = this.container.querySelector('.stocks-section');
        if (!stocksSection) return;
        
        const allStocks = this.data.top_stocks || [];
        const displayStocks = this.isStocksExpanded ? allStocks : allStocks.slice(0, 5);
        
        // 存储当前显示的股票数据
        this.stocksData = displayStocks;
        
        // 更新"更多"按钮文字
        const moreBtn = stocksSection.querySelector('.stocks-more');
        if (moreBtn) {
            if (allStocks.length <= 5) {
                moreBtn.style.display = 'none';
            } else {
                moreBtn.textContent = this.isStocksExpanded ? '收起 ‹' : '更多 ›';
                moreBtn.classList.toggle('expanded', this.isStocksExpanded);
            }
        }
        
        // 更新表格内容
        const tbody = stocksSection.querySelector('.stocks-table tbody');
        if (tbody) {
            tbody.innerHTML = displayStocks.map((stock, index) => `
                <tr class="${index >= 5 ? 'stock-row-expanded' : ''}">
                    <td class="stock-name-cell">${stock.stock_name || stock.name}</td>
                    <td class="stock-ratio-cell">${(stock.proportion || stock.ratio || 0).toFixed(2)}%</td>
                    <td class="stock-return-cell ${this.getChangeClass(stock.year_return || stock.change_percent || stock.change)}">
                        ${this.formatChange(stock.year_return || stock.change_percent || stock.change)}
                    </td>
                    <td class="stock-fund-cell clickable" data-stock-index="${index}" title="点击查看关联基金详情">
                        <span class="fund-count-text">${stock.fund_count || 1}只</span>
                        <i class="fund-expand-icon">›</i>
                    </td>
                </tr>
            `).join('');
            
            // 重新绑定点击事件
            const newFundCells = tbody.querySelectorAll('.stock-fund-cell[data-stock-index]');
            newFundCells.forEach(cell => {
                cell.addEventListener('click', (e) => this.handleFundCellClick(e));
            });
        }
        
        // 更新底部提示文字
        let footerHint = stocksSection.querySelector('.stocks-footer-hint');
        if (allStocks.length > 5) {
            if (this.isStocksExpanded) {
                // 展开状态：隐藏提示或显示收起提示
                if (footerHint) {
                    footerHint.textContent = `已显示全部 ${allStocks.length} 只重仓股`;
                }
            } else {
                // 收起状态：显示展开提示
                if (footerHint) {
                    footerHint.textContent = `共 ${allStocks.length} 只重仓股，点击"更多"查看全部`;
                }
            }
        }
    }
    
    /**
     * 处理关联基金单元格点击
     */
    handleFundCellClick(e) {
        const stockIndex = parseInt(e.currentTarget.dataset.stockIndex);
        const stock = this.stocksData[stockIndex];
        
        if (!stock) {
            console.warn('未找到股票数据');
            return;
        }
        
        this.showFundModal(stock);
    }
    
    /**
     * 显示基金详情模态框
     */
    showFundModal(stock) {
        const modal = this.container.querySelector('.fund-modal');
        const content = this.container.querySelector('.fund-modal-body');
        
        if (!modal || !content) return;
        
        // 更新模态框标题
        const title = modal.querySelector('.fund-modal-title');
        if (title) {
            title.textContent = `${stock.stock_name} 关联基金`;
        }
        
        // 渲染关联基金列表
        const relatedFunds = stock.related_funds || [];
        
        if (relatedFunds.length === 0) {
            content.innerHTML = `
                <div class="fund-modal-empty">
                    <i class="bi bi-inbox"></i>
                    <p>暂无关联基金数据</p>
                </div>
            `;
        } else {
            content.innerHTML = `
                <div class="fund-modal-stock-info">
                    <span class="fund-modal-stock-name">${stock.stock_name}</span>
                    <span class="fund-modal-stock-code">${stock.stock_code}</span>
                    <span class="fund-modal-stock-ratio">总持仓占比: ${stock.proportion}%</span>
                </div>
                <table class="fund-modal-table">
                    <thead>
                        <tr>
                            <th>基金代码</th>
                            <th>持仓占比</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${relatedFunds.map((fund, index) => `
                            <tr>
                                <td class="fund-code-cell">
                                    <span class="fund-color-dot" style="background: ${this.colors[index % this.colors.length]}"></span>
                                    ${fund.fund_code}
                                </td>
                                <td class="fund-proportion-cell">${fund.proportion}%</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div class="fund-modal-summary">
                    <span>共 <strong>${relatedFunds.length}</strong> 只基金持有该股票</span>
                </div>
            `;
        }
        
        // 显示模态框
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    
    /**
     * 关闭基金详情模态框
     */
    closeFundModal() {
        const modal = this.container.querySelector('.fund-modal');
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
    
    /**
     * 渲染基金详情模态框HTML结构
     */
    renderFundModal() {
        return `
            <div class="fund-modal">
                <div class="fund-modal-content">
                    <div class="fund-modal-header">
                        <h3 class="fund-modal-title">关联基金详情</h3>
                        <button class="fund-modal-close" type="button">&times;</button>
                    </div>
                    <div class="fund-modal-body">
                        <!-- 动态内容 -->
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染持仓分布（基金列表）
     */
    renderFundDistribution() {
        // 从fund_codes获取基金数量
        const fundCount = this.data.fund_codes ? this.data.fund_codes.length : 0;
        
        // 从strategy_analysis获取基金持仓信息（这是API实际返回的数据）
        let fundList = [];
        
        // 如果有strategy_analysis数据则使用
        if (this.data.strategy_analysis && this.data.strategy_analysis.funds) {
            fundList = this.data.strategy_analysis.funds.map(fund => ({
                fund_code: fund.fund_code,
                fund_name: fund.fund_name,
                ratio: fund.composite_score * 100, // 使用综合评分作为相对权重
                proportion: fund.composite_score * 100,
                today_return: fund.today_return,
                status_label: fund.status_label
            }));
        }
        
        return `
            <div class="dashboard-card" data-card="holdings">
                <div class="card-header">
                    <div class="card-title-group">
                        <div class="card-number">${fundCount}只</div>
                        <div class="card-subtitle">基金</div>
                    </div>
                    <span class="card-more" data-card-type="holdings">更多 ›</span>
                </div>
                <div class="fund-list" data-default-count="6">
                    ${fundList.length > 0 ? fundList.slice(0, 6).map((fund, index) => `
                        <div class="fund-list-item">
                            <span class="fund-list-name" style="color: ${this.colors[index % this.colors.length]}">${fund.fund_name || fund.fund_code}</span>
                            <span class="fund-list-ratio">${(fund.ratio || fund.proportion || 0).toFixed(2)}%</span>
                        </div>
                    `).join('') : `
                        <div class="empty-hint">暂无持仓数据</div>
                    `}
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染板块分布
     */
    renderSectorDistribution() {
        if (!this.data.industry_distribution) return '';
        
        const entries = Object.entries(this.data.industry_distribution)
            .sort((a, b) => b[1] - a[1]);
        
        if (entries.length === 0) return '';
        
        const totalCount = entries.length;
        const totalProportion = entries.reduce((sum, [, value]) => sum + value, 0);
        
        return `
            <div class="dashboard-card" data-card="sector">
                <div class="card-header">
                    <div class="card-title-group">
                        <div class="card-number">${totalCount}个</div>
                        <div class="card-subtitle">板块</div>
                    </div>
                    <span class="card-more" data-card-type="sector" ${entries.length <= 6 ? 'style="display:none"' : ''}>更多 ›</span>
                </div>
                <div class="chart-row">
                    <div class="donut-chart-wrapper">
                        <canvas id="sector-chart" width="100" height="100"></canvas>
                        <div class="donut-center">
                            <div class="donut-value">${totalProportion.toFixed(1)}%</div>
                        </div>
                    </div>
                    <div class="chart-legend-list" data-default-count="6" data-total-count="${entries.length}">
                        ${entries.slice(0, 6).map(([name, value], index) => `
                            <div class="legend-row">
                                <div class="legend-label">
                                    <span class="legend-color" style="background: ${this.colors[index % this.colors.length]}"></span>
                                    <span class="legend-text">${name}</span>
                                </div>
                                <div class="legend-data">
                                    <span class="legend-amount">${this.formatAmount(value)}元</span>
                                    <span class="legend-pct">${value.toFixed(2)}%</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染资产配置
     */
    renderAssetAllocation() {
        if (!this.data.asset_allocation) return '';
        
        const entries = Object.entries(this.data.asset_allocation)
            .sort((a, b) => b[1] - a[1]);
        
        if (entries.length === 0) return '';
        
        const activeCount = entries.filter(([key, value]) => value > 0).length;
        const totalProportion = entries.reduce((sum, [, value]) => sum + value, 0);
        
        return `
            <div class="dashboard-card" data-card="asset">
                <div class="card-header">
                    <div class="card-title-group">
                        <div class="card-number">${activeCount}种</div>
                        <div class="card-subtitle">资产</div>
                    </div>
                    <span class="card-more" data-card-type="asset" ${entries.length <= 6 ? 'style="display:none"' : ''}>更多 ›</span>
                </div>
                <div class="chart-row">
                    <div class="donut-chart-wrapper">
                        <canvas id="asset-chart" width="100" height="100"></canvas>
                        <div class="donut-center">
                            <div class="donut-value">${totalProportion.toFixed(1)}%</div>
                        </div>
                    </div>
                    <div class="chart-legend-list" data-default-count="6" data-total-count="${entries.length}">
                        ${entries.map(([name, value], index) => `
                            <div class="legend-row">
                                <div class="legend-label">
                                    <span class="legend-color" style="background: ${this.colors[index % this.colors.length]}"></span>
                                    <span class="legend-text">${name}</span>
                                </div>
                                <div class="legend-data">
                                    <span class="legend-pct">${value.toFixed(2)}%</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染账户重仓股表格
     */
    renderTopStocksTable() {
        if (!this.data.top_stocks || this.data.top_stocks.length === 0) return '';
        
        const allStocks = this.data.top_stocks;
        const stocks = allStocks.slice(0, 5);
        const hasMore = allStocks.length > 5;
        
        // 存储股票数据用于点击事件
        this.stocksData = stocks;
        
        return `
            <div class="stocks-section">
                <div class="stocks-header">
                    <h3 class="stocks-title">账户重仓股</h3>
                    <span class="stocks-more" ${!hasMore ? 'style="display:none"' : ''}>更多 ›</span>
                </div>
                <table class="stocks-table">
                    <thead>
                        <tr>
                            <th>股票名称</th>
                            <th>持仓占比</th>
                            <th>近1年收益</th>
                            <th>关联基金</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${stocks.map((stock, index) => `
                            <tr>
                                <td class="stock-name-cell">${stock.stock_name || stock.name}</td>
                                <td class="stock-ratio-cell">${(stock.proportion || stock.ratio || 0).toFixed(2)}%</td>
                                <td class="stock-return-cell ${this.getChangeClass(stock.year_return || stock.change_percent || stock.change)}">
                                    ${this.formatChange(stock.year_return || stock.change_percent || stock.change)}
                                </td>
                                <td class="stock-fund-cell clickable" data-stock-index="${index}" title="点击查看关联基金详情">
                                    <span class="fund-count-text">${stock.fund_count || 1}只</span>
                                    <i class="fund-expand-icon">›</i>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                ${hasMore ? `<div class="stocks-footer-hint">共 ${allStocks.length} 只重仓股，点击"更多"查看全部</div>` : ''}
            </div>
        `;
    }
    
    /**
     * 格式化金额显示
     */
    formatAmount(value) {
        if (value >= 10000) {
            return (value / 10000).toFixed(2) + '万';
        }
        return value.toFixed(2);
    }
    
    /**
     * 渲染图表
     */
    renderCharts() {
        // 板块分布环形图
        if (this.data.industry_distribution) {
            const sectorCanvas = document.getElementById('sector-chart');
            if (sectorCanvas) {
                this.renderDonutChart(sectorCanvas, this.data.industry_distribution);
            }
        }
        
        // 资产配置环形图
        if (this.data.asset_allocation) {
            const assetCanvas = document.getElementById('asset-chart');
            if (assetCanvas) {
                this.renderDonutChart(assetCanvas, this.data.asset_allocation);
            }
        }
    }
    
    /**
     * 渲染环形图
     */
    renderDonutChart(canvas, data) {
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.scale(dpr, dpr);
        
        ctx.clearRect(0, 0, rect.width, rect.height);
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const radius = Math.min(centerX, centerY) - 4;
        const innerRadius = radius * 0.65;
        
        const entries = Object.entries(data).filter(([key, value]) => value > 0);
        const total = entries.reduce((sum, [, value]) => sum + value, 0);
        
        if (total === 0) return;
        
        const isSingleEntry = entries.length === 1;
        let currentAngle = -Math.PI / 2;
        
        entries.forEach(([name, value], index) => {
            let sliceAngle = (value / total) * 2 * Math.PI;
            
            if (isSingleEntry) {
                sliceAngle = 2 * Math.PI - (10 * Math.PI / 180);
            }
            
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.arc(centerX, centerY, innerRadius, currentAngle + sliceAngle, currentAngle, true);
            ctx.closePath();
            ctx.fillStyle = this.colors[index % this.colors.length];
            ctx.fill();
            
            currentAngle += sliceAngle;
        });
        
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
    
    /**
     * 渲染策略分析表格
     */
    renderStrategyAnalysis() {
        const strategyData = this.data.strategy_analysis;
        if (!strategyData || !strategyData.funds || strategyData.funds.length === 0) {
            return '';
        }
        
        const summary = strategyData.summary || {};
        const funds = strategyData.funds || [];
        
        return `
            <div class="strategy-section">
                <div class="strategy-header">
                    <div class="strategy-title-group">
                        <h3 class="strategy-title">智能策略分析</h3>
                        <span class="strategy-subtitle">基于收益率变化的交易决策</span>
                    </div>
                    <div class="strategy-summary">
                        <span class="summary-item buy">
                            <i class="bi bi-arrow-up-circle-fill"></i> 买入 ${summary.buy_count || 0}
                        </span>
                        <span class="summary-item sell">
                            <i class="bi bi-arrow-down-circle-fill"></i> 卖出 ${summary.sell_count || 0}
                        </span>
                        <span class="summary-item hold">
                            <i class="bi bi-pause-circle-fill"></i> 持有 ${summary.hold_count || 0}
                        </span>
                    </div>
                </div>
                
                <div class="strategy-table-container">
                    <table class="strategy-table">
                        <thead>
                            <tr>
                                <th class="col-code">代码</th>
                                <th class="col-name">基金名称</th>
                                <th class="col-return">今日</th>
                                <th class="col-return">昨日</th>
                                <th class="col-status">趋势状态</th>
                                <th class="col-action">操作建议</th>
                                <th class="col-amount">执行金额</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${funds.map(fund => this.renderStrategyRow(fund)).join('')}
                        </tbody>
                    </table>
                </div>
                
                <div class="strategy-explanation-section">
                    <div class="explanation-header">
                        <i class="bi bi-lightbulb"></i>
                        <span>策略逻辑说明</span>
                    </div>
                    <div class="explanation-cards">
                        ${funds.map(fund => this.renderExplanationCard(fund)).join('')}
                    </div>
                </div>
                
                <div class="strategy-footer">
                    <span class="analysis-time">分析时间: ${summary.analysis_date || '--'}</span>
                    <span class="strategy-hint">提示: 以上策略建议基于量化模型，仅供参考，请结合市场情况谨慎决策</span>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染策略表格行
     */
    renderStrategyRow(fund) {
        const todayClass = fund.today_return >= 0 ? 'positive' : 'negative';
        const yesterdayClass = fund.yesterday_return >= 0 ? 'positive' : 'negative';
        const actionClass = this.getActionClass(fund.action);
        
        return `
            <tr class="strategy-row ${actionClass}">
                <td class="col-code">
                    <span class="fund-code">${fund.fund_code}</span>
                </td>
                <td class="col-name">
                    <span class="fund-name" title="${fund.fund_name}">${fund.fund_name}</span>
                </td>
                <td class="col-return">
                    <span class="return-value ${todayClass}">${this.formatReturn(fund.today_return)}</span>
                </td>
                <td class="col-return">
                    <span class="return-value ${yesterdayClass}">${this.formatReturn(fund.yesterday_return)}</span>
                </td>
                <td class="col-status">
                    <span class="status-label">${fund.status_label}</span>
                </td>
                <td class="col-action">
                    <span class="action-badge ${actionClass}">${fund.operation_suggestion}</span>
                </td>
                <td class="col-amount">
                    <span class="execution-amount ${actionClass}">${fund.execution_amount}</span>
                </td>
            </tr>
        `;
    }
    
    /**
     * 渲染策略解释卡片
     */
    renderExplanationCard(fund) {
        const actionClass = this.getActionClass(fund.action);
        
        return `
            <div class="explanation-card ${actionClass}">
                <div class="card-header-mini">
                    <span class="fund-badge">${fund.fund_code}</span>
                    <span class="fund-name-mini">${fund.fund_name}</span>
                </div>
                <div class="card-content">
                    <div class="return-comparison">
                        <span class="return-item">
                            <label>今日</label>
                            <value class="${fund.today_return >= 0 ? 'positive' : 'negative'}">${this.formatReturn(fund.today_return)}</value>
                        </span>
                        <span class="return-arrow">→</span>
                        <span class="return-item">
                            <label>昨日</label>
                            <value class="${fund.yesterday_return >= 0 ? 'positive' : 'negative'}">${this.formatReturn(fund.yesterday_return)}</value>
                        </span>
                        <span class="return-diff">
                            <label>差值</label>
                            <value class="${fund.return_diff >= 0 ? 'positive' : 'negative'}">${fund.return_diff >= 0 ? '+' : ''}${fund.return_diff}%</value>
                        </span>
                    </div>
                    <div class="strategy-logic">
                        <p>${fund.strategy_explanation || '暂无策略说明'}</p>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * 获取操作类型样式类
     */
    getActionClass(action) {
        if (!action) return 'hold';
        if (['buy', 'strong_buy', 'weak_buy'].includes(action)) return 'buy';
        if (['sell', 'redeem'].includes(action)) return 'sell';
        return 'hold';
    }
    
    /**
     * 格式化收益率
     */
    formatReturn(value) {
        if (value === null || value === undefined) return '--';
        const num = parseFloat(value);
        if (isNaN(num)) return '--';
        const sign = num >= 0 ? '+' : '';
        return `${sign}${num.toFixed(2)}%`;
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
