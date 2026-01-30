/**
 * 基金详情模块 - 侧边面板
 */
const FundDetail = {
    currentFund: null,

    /**
     * 打开详情面板
     */
    openPanel(fund) {
        this.currentFund = fund;
        this.renderPanel();
        
        const panel = document.getElementById('detail-panel');
        if (panel) {
            panel.classList.add('open');
            // 添加遮罩层
            this.createOverlay();
        }
    },

    /**
     * 关闭详情面板
     */
    closePanel() {
        const panel = document.getElementById('detail-panel');
        if (panel) {
            panel.classList.remove('open');
        }
        // 移除遮罩层
        this.removeOverlay();
        this.currentFund = null;
    },

    /**
     * 创建遮罩层
     */
    createOverlay() {
        let overlay = document.getElementById('detail-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'detail-overlay';
            overlay.className = 'detail-overlay';
            overlay.onclick = () => this.closePanel();
            document.body.appendChild(overlay);
        }
        // 强制重绘以确保过渡动画
        requestAnimationFrame(() => {
            overlay.classList.add('active');
        });
    },

    /**
     * 移除遮罩层
     */
    removeOverlay() {
        const overlay = document.getElementById('detail-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    },

    /**
     * 渲染详情面板
     */
    renderPanel() {
        const panelBody = document.getElementById('detail-panel-body');
        if (!panelBody || !this.currentFund) return;

        const fund = this.currentFund;
        
        panelBody.innerHTML = `
            <div class="detail-section">
                <h4 class="detail-section-title">基本信息</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">基金代码</span>
                        <span class="detail-value">${fund.fund_code}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">基金名称</span>
                        <span class="detail-value">${fund.fund_name || '--'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">买入日期</span>
                        <span class="detail-value">${fund.buy_date || '--'}</span>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <h4 class="detail-section-title">持仓信息</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">持有份额</span>
                        <span class="detail-value">${FundUtils.formatNumber(fund.holding_shares)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">成本价</span>
                        <span class="detail-value">${FundUtils.formatCurrency(fund.cost_price)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">持仓金额</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.holding_amount, 'currency')}">${FundUtils.formatCurrency(fund.holding_amount)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">当前市值</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.current_value, 'currency')}">${FundUtils.formatCurrency(fund.current_value)}</span>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <h4 class="detail-section-title">盈亏分析</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">持有收益</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.holding_profit, 'currency')}">${FundUtils.formatCurrency(fund.holding_profit)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">持有收益率</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.holding_profit_rate, 'percent')}">${FundUtils.formatPercent(fund.holding_profit_rate)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">当日收益</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.today_profit, 'currency')}">${FundUtils.formatCurrency(fund.today_profit)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">当日收益率</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.today_profit_rate, 'percent')}">${FundUtils.formatPercent(fund.today_profit_rate)}</span>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <h4 class="detail-section-title">绩效指标</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">年化收益</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.annualized_return, 'percent')}">${FundUtils.formatPercent(fund.annualized_return)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">夏普比率</span>
                        <span class="detail-value">${FundUtils.formatNumber(fund.sharpe_ratio)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">最大回撤</span>
                        <span class="detail-value ${FundUtils.getCellClass(fund.max_drawdown, 'percent')}">${FundUtils.formatPercent(fund.max_drawdown)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">波动率</span>
                        <span class="detail-value">${FundUtils.formatPercent(fund.volatility)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">综合评分</span>
                        <span class="detail-value">${FundUtils.formatNumber(fund.composite_score)}</span>
                    </div>
                </div>
            </div>

            ${fund.notes ? `
            <div class="detail-section">
                <h4 class="detail-section-title">备注</h4>
                <p class="detail-notes">${fund.notes}</p>
            </div>
            ` : ''}

            <div class="detail-actions">
                <button class="btn btn-primary" onclick="FundTable.editFund('${fund.fund_code}'); FundDetail.closePanel();">
                    <i class="bi bi-pencil-square"></i> 编辑
                </button>
                <button class="btn btn-secondary" onclick="FundDetail.closePanel();">
                    <i class="bi bi-x-lg"></i> 关闭
                </button>
            </div>
        `;
    }
};
