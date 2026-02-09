/**
 * 基金详情模块 - 侧边面板（重新设计版）
 */
const FundDetail = {
    currentFund: null,
    currentTab: 'performance',  // 当前主Tab: performance, nav, profit
    currentSubTab: 'stage',     // 当前子Tab: stage, holdings, history, trades
    currentPeriod: '1y',        // 当前图表周期

    /**
     * 打开详情面板
     */
    openPanel(fund) {
        this.currentFund = fund;
        this.currentTab = 'performance';
        this.currentSubTab = 'stage';
        this.currentPeriod = '1y';
        this.renderPanel();
        
        const panel = document.getElementById('detail-panel');
        if (panel) {
            panel.classList.add('open');
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
     * 格式化涨跌值（带符号和颜色类）
     */
    formatChange(value, isPercent = false) {
        if (value == null || isNaN(value)) return { text: '--', class: 'neutral' };
        const num = parseFloat(value);
        const sign = num > 0 ? '+' : '';
        const text = isPercent ? `${sign}${num.toFixed(2)}%` : `${sign}${num.toFixed(2)}`;
        const colorClass = num > 0 ? 'positive' : (num < 0 ? 'negative' : 'neutral');
        return { text, class: colorClass };
    },

    /**
     * 获取基金类型信息
     * 使用后端返回的基金类型数据（证监会标准分类）
     * 类型代码: stock(股票型), bond(债券型), hybrid(混合型), money(货币型), 
     *          index(指数型), qdii(QDII), etf(ETF), fof(FOF), unknown(未知)
     */
    getFundTypeInfo(fund) {
        // 优先使用后端返回的基金类型数据
        const typeCode = fund.fund_type || 'unknown';
        const typeCn = fund.fund_type_cn || this.getFundTypeDisplayName(typeCode);
        const typeClass = fund.fund_type_class || this.getFundTypeClass(typeCode);
        
        return {
            code: typeCode,
            label: typeCn,
            className: typeClass
        };
    },

    /**
     * 获取基金类型的CSS类名（备用，当后端未返回时）
     */
    getFundTypeClass(fundType) {
        const classMap = {
            'stock': 'fund-type-stock',
            'bond': 'fund-type-bond',
            'hybrid': 'fund-type-hybrid',
            'money': 'fund-type-money',
            'index': 'fund-type-index',
            'qdii': 'fund-type-qdii',
            'etf': 'fund-type-etf',
            'fof': 'fund-type-fof',
            'unknown': 'fund-type-unknown',
            'other': 'fund-type-unknown'
        };
        return classMap[fundType] || 'fund-type-unknown';
    },

    /**
     * 获取基金类型的显示名称（备用，当后端未返回时）
     */
    getFundTypeDisplayName(fundType) {
        const nameMap = {
            'stock': '股票型',
            'bond': '债券型',
            'hybrid': '混合型',
            'money': '货币型',
            'index': '指数型',
            'qdii': 'QDII',
            'etf': 'ETF',
            'fof': 'FOF',
            'unknown': '其他',
            'other': '其他'
        };
        return nameMap[fundType] || '其他';
    },

    /**
     * 渲染详情面板
     */
    renderPanel() {
        const panelBody = document.getElementById('detail-panel-body');
        const panelTitle = document.querySelector('.detail-panel-title');
        const panelHeader = document.querySelector('.detail-panel-header');
        if (!panelBody || !this.currentFund) return;

        const fund = this.currentFund;
        // 使用后端返回的基金类型信息（证监会标准分类）
        const typeInfo = this.getFundTypeInfo(fund);
        
        // 更新标题为基金名称，添加基金类型标识（使用证监会标准分类）
        if (panelTitle) {
            panelTitle.innerHTML = `
                <span class="fund-title-name">${fund.fund_name || '基金详情'}</span>
                <span class="fund-title-code">${fund.fund_code}</span>
                <span class="fund-type-tag ${typeInfo.className}">${typeInfo.label}</span>
            `;
        }
        
        // 为详情面板头部添加基金类型样式
        if (panelHeader) {
            // 移除所有基金类型类
            panelHeader.classList.remove('fund-type-stock', 'fund-type-bond', 'fund-type-hybrid', 
                                         'fund-type-money', 'fund-type-index', 'fund-type-qdii', 
                                         'fund-type-etf', 'fund-type-fof', 'fund-type-unknown');
            // 添加当前基金类型类
            panelHeader.classList.add(typeInfo.className);
        }

        // 格式化各项数据
        const todayReturn = this.formatChange(fund.today_return, true);
        const yearReturn = this.formatChange(fund.annualized_return, true);
        const todayProfit = this.formatChange(fund.today_profit);
        const todayProfitRate = this.formatChange(fund.today_profit_rate, true);
        const holdingProfit = this.formatChange(fund.holding_profit);
        const holdingProfitRate = this.formatChange(fund.holding_profit_rate, true);

        panelBody.innerHTML = `
            <!-- 核心指标区域 -->
            <div class="detail-metrics-card">
                <div class="metrics-main">
                    <div class="metric-primary">
                        <span class="metric-label">当日涨幅</span>
                        <span class="metric-value ${todayReturn.class}">${todayReturn.text}</span>
                    </div>
                    <div class="metric-secondary">
                        <div class="metric-item">
                            <span class="metric-label">近一年</span>
                            <span class="metric-value ${yearReturn.class}">${yearReturn.text}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">最新净值 (${this.getDateStr()})</span>
                            <span class="metric-value">${fund.nav || fund.current_nav || '1.0000'}</span>
                        </div>
                    </div>
                </div>
                <div class="metrics-detail">
                    <div class="metrics-row">
                        <div class="metric-cell">
                            <span class="metric-label">当日盈亏</span>
                            <span class="metric-value ${todayProfit.class}">${todayProfit.text}</span>
                        </div>
                        <div class="metric-cell">
                            <span class="metric-label">当日盈亏率</span>
                            <span class="metric-value ${todayProfitRate.class}">${todayProfitRate.text}</span>
                        </div>
                    </div>
                    <div class="metrics-row">
                        <div class="metric-cell">
                            <span class="metric-label">持有盈亏</span>
                            <span class="metric-value ${holdingProfit.class}">${holdingProfit.text}</span>
                        </div>
                        <div class="metric-cell">
                            <span class="metric-label">持有盈亏率</span>
                            <span class="metric-value ${holdingProfitRate.class}">${holdingProfitRate.text}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 主Tab导航 -->
            <div class="detail-main-tabs">
                <button class="main-tab-btn ${this.currentTab === 'performance' ? 'active' : ''}" 
                        onclick="FundDetail.switchMainTab('performance')">
                    <span class="tab-indicator"></span>业绩走势
                </button>
                <button class="main-tab-btn ${this.currentTab === 'nav' ? 'active' : ''}" 
                        onclick="FundDetail.switchMainTab('nav')">单位净值</button>
                <button class="main-tab-btn ${this.currentTab === 'profit' ? 'active' : ''}" 
                        onclick="FundDetail.switchMainTab('profit')">累计盈亏</button>
            </div>

            <!-- 图表区域 -->
            <div class="detail-chart-section">
                <div class="chart-legend">
                    <span class="legend-label">区间涨幅</span>
                    <span class="legend-item fund-legend">
                        <span class="legend-dot fund"></span>本基金 <span class="${this.formatChange(fund.annualized_return, true).class}">${this.formatChange(fund.annualized_return, true).text}</span>
                    </span>
                    <span class="legend-item benchmark-legend">
                        <span class="legend-dot benchmark"></span>沪深300 <span class="positive">+22.65%</span>
                    </span>
                </div>
                <div class="chart-container" id="detail-chart">
                    <canvas id="performance-chart"></canvas>
                </div>
                <div class="chart-period-selector">
                    <button class="period-btn ${this.currentPeriod === '1d' ? 'active' : ''}" 
                            onclick="FundDetail.switchPeriod('1d')">当日</button>
                    <button class="period-btn ${this.currentPeriod === '1m' ? 'active' : ''}" 
                            onclick="FundDetail.switchPeriod('1m')">近一月</button>
                    <button class="period-btn ${this.currentPeriod === '6m' ? 'active' : ''}" 
                            onclick="FundDetail.switchPeriod('6m')">近半年</button>
                    <button class="period-btn ${this.currentPeriod === '1y' ? 'active' : ''}" 
                            onclick="FundDetail.switchPeriod('1y')">近一年</button>
                    <button class="period-btn ${this.currentPeriod === 'ytd' ? 'active' : ''}" 
                            onclick="FundDetail.switchPeriod('ytd')">今年来</button>
                </div>
            </div>

            <!-- 子Tab导航 -->
            <div class="detail-sub-tabs">
                <button class="sub-tab-btn ${this.currentSubTab === 'stage' ? 'active' : ''}" 
                        onclick="FundDetail.switchSubTab('stage')">
                    <span class="tab-indicator"></span>阶段涨幅
                </button>
                <button class="sub-tab-btn ${this.currentSubTab === 'holdings' ? 'active' : ''}" 
                        onclick="FundDetail.switchSubTab('holdings')">基金持仓</button>
                <button class="sub-tab-btn ${this.currentSubTab === 'history' ? 'active' : ''}" 
                        onclick="FundDetail.switchSubTab('history')">历史净值</button>
                <button class="sub-tab-btn ${this.currentSubTab === 'trades' ? 'active' : ''}" 
                        onclick="FundDetail.switchSubTab('trades')">交易记录</button>
            </div>

            <!-- 阶段涨幅表格 -->
            <div class="detail-table-section" id="sub-tab-content">
                ${this.renderSubTabContent()}
            </div>

            <!-- 底部操作按钮 -->
            <div class="detail-footer-actions">
                <button class="btn btn-outline" onclick="FundDetail.addToWatchlist()">
                    <i class="bi bi-plus-circle"></i> 加自选
                </button>
                <button class="btn btn-primary" onclick="FundTable.editFund('${fund.fund_code}'); FundDetail.closePanel();">
                    <i class="bi bi-pencil-square"></i> 编辑
                </button>
            </div>
        `;

        // 延迟渲染图表
        setTimeout(() => this.renderChart(), 100);
    },

    /**
     * 获取日期字符串
     */
    getDateStr() {
        const now = new Date();
        return `${now.getMonth() + 1}-${String(now.getDate()).padStart(2, '0')}`;
    },

    /**
     * 切换主Tab
     */
    switchMainTab(tab) {
        this.currentTab = tab;
        // 更新Tab按钮状态
        document.querySelectorAll('.main-tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.closest('.main-tab-btn').classList.add('active');
        // 重新渲染图表
        this.renderChart();
    },

    /**
     * 切换子Tab
     */
    switchSubTab(tab) {
        this.currentSubTab = tab;
        // 更新Tab按钮状态
        document.querySelectorAll('.sub-tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.closest('.sub-tab-btn').classList.add('active');
        // 更新内容
        const content = document.getElementById('sub-tab-content');
        if (content) {
            content.innerHTML = this.renderSubTabContent();
        }
    },

    /**
     * 切换图表周期
     */
    switchPeriod(period) {
        this.currentPeriod = period;
        // 更新按钮状态
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
        // 重新渲染图表
        this.renderChart();
    },

    /**
     * 渲染子Tab内容
     */
    renderSubTabContent() {
        switch (this.currentSubTab) {
            case 'stage':
                return this.renderStageTable();
            case 'holdings':
                return this.renderHoldingsTable();
            case 'history':
                return this.renderHistoryTable();
            case 'trades':
                return this.renderTradesTable();
            default:
                return '';
        }
    },

    /**
     * 渲染阶段涨幅表格
     */
    renderStageTable() {
        const fund = this.currentFund;
        // 模拟阶段数据（实际应从API获取）
        const stages = [
            { period: '近一周', fundReturn: '+1.38%', benchmark: '-2.06%' },
            { period: '近一月', fundReturn: '-3.93%', benchmark: '-1.31%' },
            { period: '近三月', fundReturn: '-5.90%', benchmark: '+0.62%' },
            { period: '近六月', fundReturn: '-9.22%', benchmark: '+13.47%' },
            { period: '近一年', fundReturn: '+5.82%', benchmark: '+22.69%' },
            { period: '近三年', fundReturn: '+42.62%', benchmark: '+12.42%' }
        ];

        return `
            <table class="stage-table">
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>涨跌幅</th>
                        <th>沪深300</th>
                    </tr>
                </thead>
                <tbody>
                    ${stages.map(s => `
                        <tr>
                            <td class="period-cell">${s.period}</td>
                            <td class="${this.getChangeClass(s.fundReturn)}">${s.fundReturn}</td>
                            <td class="${this.getChangeClass(s.benchmark)}">${s.benchmark}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    /**
     * 渲染基金持仓表格
     */
    renderHoldingsTable() {
        return `
            <div class="empty-content">
                <i class="bi bi-pie-chart"></i>
                <p>暂无持仓数据</p>
            </div>
        `;
    },

    /**
     * 渲染历史净值表格
     */
    renderHistoryTable() {
        const fund = this.currentFund;
        if (!fund) {
            return `
                <div class="empty-content">
                    <i class="bi bi-clock-history"></i>
                    <p>暂无历史净值数据</p>
                </div>
            `;
        }

        // 先显示加载状态，然后异步加载数据
        setTimeout(() => this.loadHistoryData(), 100);
        
        return `
            <div class="history-table-container" id="history-table-container">
                <div class="loading-content">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p>正在加载历史净值数据...</p>
                </div>
            </div>
        `;
    },

    /**
     * 异步加载历史净值数据
     */
    async loadHistoryData() {
        const container = document.getElementById('history-table-container');
        if (!container || !this.currentFund) return;

        const fund = this.currentFund;
        
        try {
            // 调用后端API获取历史净值数据（最近30天）
            const response = await fetch(`/api/fund/${fund.fund_code}/history?days=30`);
            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || '获取数据失败');
            }

            const data = result.data || [];
            
            if (data.length === 0) {
                container.innerHTML = `
                    <div class="empty-content">
                        <i class="bi bi-clock-history"></i>
                        <p>暂无历史净值数据</p>
                    </div>
                `;
                return;
            }

            // 按日期降序排列（最新的在前面）
            data.sort((a, b) => new Date(b.date) - new Date(a.date));

            // 计算涨跌幅（如果API没有返回，手动计算）
            const processedData = data.map((item, index) => {
                let changePercent = item.today_return || item.change_percent;
                
                // 如果没有涨跌幅，尝试计算
                if (changePercent == null && index < data.length - 1) {
                    const prevNav = data[index + 1].nav;
                    if (prevNav && prevNav > 0) {
                        changePercent = ((item.nav - prevNav) / prevNav * 100).toFixed(2);
                    }
                }
                
                return {
                    date: item.date,
                    nav: item.nav,
                    changePercent: changePercent
                };
            });

            // 渲染表格
            container.innerHTML = `
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>单位净值</th>
                            <th>日涨跌</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${processedData.map(item => {
                            const changeClass = this.getChangeClass(item.changePercent);
                            const changeText = this.formatChangePercent(item.changePercent);
                            return `
                                <tr>
                                    <td class="date-cell">${this.formatDate(item.date)}</td>
                                    <td class="nav-cell">${item.nav != null ? parseFloat(item.nav).toFixed(4) : '--'}</td>
                                    <td class="${changeClass}">${changeText}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            `;

        } catch (error) {
            console.error('加载历史净值数据失败:', error);
            container.innerHTML = `
                <div class="empty-content error-content">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p>加载失败: ${error.message}</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="FundDetail.retryLoadHistory()">
                        <i class="bi bi-arrow-clockwise"></i> 重试
                    </button>
                </div>
            `;
        }
    },

    /**
     * 重试加载历史数据
     */
    retryLoadHistory() {
        const container = document.getElementById('history-table-container');
        if (container) {
            container.innerHTML = `
                <div class="loading-content">
                    <div class="spinner-border spinner-border-sm text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                    <p>正在加载历史净值数据...</p>
                </div>
            `;
        }
        this.loadHistoryData();
    },

    /**
     * 格式化日期显示
     */
    formatDate(dateStr) {
        if (!dateStr) return '--';
        try {
            const date = new Date(dateStr);
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${month}-${day}`;
        } catch (e) {
            return dateStr;
        }
    },

    /**
     * 格式化涨跌幅百分比
     */
    formatChangePercent(value) {
        if (value == null || isNaN(value)) return '--';
        const num = parseFloat(value);
        const sign = num > 0 ? '+' : '';
        return `${sign}${num.toFixed(2)}%`;
    },

    /**
     * 渲染交易记录表格
     */
    renderTradesTable() {
        return `
            <div class="empty-content">
                <i class="bi bi-receipt"></i>
                <p>暂无交易记录</p>
            </div>
        `;
    },

    /**
     * 获取涨跌颜色类名
     */
    getChangeClass(value) {
        if (value == null || value === '--' || value === '') return '';
        let num;
        if (typeof value === 'string') {
            num = parseFloat(value.replace('%', '').replace('+', ''));
        } else {
            num = parseFloat(value);
        }
        if (isNaN(num)) return '';
        if (num > 0) return 'positive';
        if (num < 0) return 'negative';
        return '';
    },

    /**
     * 渲染走势图表
     */
    renderChart() {
        const canvas = document.getElementById('performance-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const container = canvas.parentElement;
        
        // 设置画布尺寸
        const dpr = window.devicePixelRatio || 1;
        const rect = container.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = 180 * dpr;
        canvas.style.width = rect.width + 'px';
        canvas.style.height = '180px';
        ctx.scale(dpr, dpr);

        // 清空画布
        ctx.clearRect(0, 0, rect.width, 180);

        // 生成模拟数据
        const points = 50;
        const fundData = [];
        const benchmarkData = [];
        let fundValue = 0;
        let benchmarkValue = 0;

        for (let i = 0; i < points; i++) {
            fundValue += (Math.random() - 0.48) * 3;
            benchmarkValue += (Math.random() - 0.45) * 2.5;
            fundData.push(fundValue);
            benchmarkData.push(benchmarkValue);
        }

        // 绘制参数
        const padding = { top: 20, right: 10, bottom: 30, left: 40 };
        const chartWidth = rect.width - padding.left - padding.right;
        const chartHeight = 180 - padding.top - padding.bottom;

        // 计算Y轴范围
        const allValues = [...fundData, ...benchmarkData];
        const minY = Math.min(...allValues) - 2;
        const maxY = Math.max(...allValues) + 2;

        // 绘制网格线
        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = padding.top + (chartHeight / 4) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(rect.width - padding.right, y);
            ctx.stroke();

            // Y轴标签
            const value = maxY - ((maxY - minY) / 4) * i;
            ctx.fillStyle = '#999';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(value.toFixed(1) + '%', padding.left - 5, y + 3);
        }

        // 绘制曲线函数
        const drawLine = (data, color) => {
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            data.forEach((value, index) => {
                const x = padding.left + (chartWidth / (points - 1)) * index;
                const y = padding.top + chartHeight - ((value - minY) / (maxY - minY)) * chartHeight;
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            ctx.stroke();
        };

        // 绘制基金曲线（红色）
        drawLine(fundData, '#e74c3c');
        // 绘制基准曲线（黄色）
        drawLine(benchmarkData, '#f39c12');

        // X轴标签
        ctx.fillStyle = '#999';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        const xLabels = ['2025-02-05', '2025-08-06', '2026-02-05'];
        xLabels.forEach((label, i) => {
            const x = padding.left + (chartWidth / 2) * i;
            ctx.fillText(label, x, 180 - 10);
        });
    },

    /**
     * 加入自选
     */
    addToWatchlist() {
        if (!this.currentFund) return;
        // 实际应调用API
        alert(`已将 ${this.currentFund.fund_name} 加入自选`);
    }
};
