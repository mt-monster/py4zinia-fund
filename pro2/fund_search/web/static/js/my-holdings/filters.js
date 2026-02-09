/**
 * 高级筛选模块 - 参考主流金融平台设计
 * 支持多条件组合筛选、实时筛选、条件标签化展示
 */
window.FundFilters = {
    /**
     * 当前筛选条件
     */
    currentFilters: {},
    
    /**
     * 筛选条件定义
     */
    filterDefinitions: {
        // 基金类型 - 多选
        fundType: {
            label: '基金类型',
            type: 'multiSelect',
            options: [
                { value: 'stock', label: '股票型', color: '#28a745' },
                { value: 'bond', label: '债券型', color: '#17a2b8' },
                { value: 'hybrid', label: '混合型', color: '#ffc107' },
                { value: 'money', label: '货币型', color: '#6c757d' },
                { value: 'index', label: '指数型', color: '#007bff' },
                { value: 'qdii', label: 'QDII', color: '#9b59b6' },
                { value: 'etf', label: 'ETF', color: '#e74c3c' },
                { value: 'fof', label: 'FOF', color: '#fd7e14' }
            ]
        },
        // 风险等级 - 多选
        riskLevel: {
            label: '风险等级',
            type: 'multiSelect',
            options: [
                { value: 'low', label: '低风险', desc: 'R1' },
                { value: 'low-mid', label: '中低风险', desc: 'R2' },
                { value: 'mid', label: '中风险', desc: 'R3' },
                { value: 'mid-high', label: '中高风险', desc: 'R4' },
                { value: 'high', label: '高风险', desc: 'R5' }
            ]
        },
        // 成立时间 - 单选
        establishDate: {
            label: '成立时间',
            type: 'singleSelect',
            options: [
                { value: 'all', label: '不限' },
                { value: '1y', label: '1年以内' },
                { value: '1y-3y', label: '1-3年' },
                { value: '3y-5y', label: '3-5年' },
                { value: '5y+', label: '5年以上' }
            ]
        },
        // 基金规模 - 单选
        fundScale: {
            label: '基金规模',
            type: 'singleSelect',
            options: [
                { value: 'all', label: '不限' },
                { value: '0-1', label: '1亿以下' },
                { value: '1-10', label: '1-10亿' },
                { value: '10-50', label: '10-50亿' },
                { value: '50-100', label: '50-100亿' },
                { value: '100+', label: '100亿以上' }
            ]
        },
        // 收益率区间 - 多时间段
        returnRate: {
            label: '收益率',
            type: 'rangeGroup',
            periods: [
                { key: 'today', label: '今日' },
                { key: 'week', label: '近1周' },
                { key: 'month', label: '近1月' },
                { key: '3month', label: '近3月' },
                { key: '6month', label: '近6月' },
                { key: 'year', label: '近1年' },
                { key: 'ytd', label: '今年来' },
                { key: 'all', label: '成立以来' }
            ]
        },
        // 夏普比率 - 范围
        sharpeRatio: {
            label: '夏普比率',
            type: 'range',
            min: -5,
            max: 5,
            step: 0.1
        },
        // 最大回撤 - 范围
        maxDrawdown: {
            label: '最大回撤',
            type: 'range',
            min: -100,
            max: 0,
            step: 1,
            unit: '%'
        },
        // 波动率 - 范围
        volatility: {
            label: '波动率',
            type: 'range',
            min: 0,
            max: 100,
            step: 1,
            unit: '%'
        },
        // 净值 - 范围
        nav: {
            label: '单位净值',
            type: 'range',
            min: 0,
            max: 100,
            step: 0.01
        },
        // 持仓金额 - 范围
        holdingAmount: {
            label: '持仓金额',
            type: 'range',
            min: 0,
            max: 10000000,
            step: 1000
        },
        // 相关性筛选
        correlation: {
            label: '相关性',
            type: 'singleSelect',
            options: [
                { value: 'all', label: '不限' },
                { value: 'high', label: '高度相关 (>0.8)' },
                { value: 'mid', label: '中度相关 (0.5-0.8)' },
                { value: 'low', label: '低相关 (0.2-0.5)' },
                { value: 'none', label: '无相关 (<0.2)' }
            ]
        }
    },

    /**
     * 预设筛选条件
     */
    presetFilters: [
        { name: '全部基金', filters: {} },
        { name: '高收益基金', filters: { returnRate: { year: { min: 20 } } } },
        { name: '稳健基金', filters: { maxDrawdown: { max: -10 }, sharpeRatio: { min: 1 } } },
        { name: '指数基金', filters: { fundType: ['index', 'etf'] } },
        { name: '海外配置', filters: { fundType: ['qdii'] } },
        { name: '债券基金', filters: { fundType: ['bond'] } }
    ],

    /**
     * 防抖定时器
     */
    debounceTimer: null,

    /**
     * 初始化筛选模块
     */
    init() {
        this.bindEvents();
        this.renderFilterPanel();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 筛选按钮点击
        const filterBtn = document.getElementById('filter-toggle-btn');
        if (filterBtn) {
            filterBtn.addEventListener('click', () => {
                this.togglePanel();
            });
        }

        // 点击遮罩关闭
        const overlay = document.getElementById('filter-panel-overlay');
        if (overlay) {
            overlay.addEventListener('click', () => {
                this.closePanel();
            });
        }

        // 键盘ESC关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closePanel();
        });
    },

    /**
     * 渲染筛选面板
     */
    renderFilterPanel() {
        const panel = document.getElementById('filter-panel-content');
        if (!panel) return;

        let html = `
            <!-- 预设条件 -->
            <div class="filter-section">
                <div class="filter-section-title">快速筛选</div>
                <div class="preset-filters">
                    ${this.presetFilters.map((preset, index) => `
                        <button class="preset-tag ${index === 0 ? 'active' : ''}" 
                                onclick="FundFilters.applyPreset(${index})"
                                data-preset="${index}">
                            ${preset.name}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;

        // 渲染各筛选条件
        Object.entries(this.filterDefinitions).forEach(([key, config]) => {
            html += this.renderFilterItem(key, config);
        });

        panel.innerHTML = html;
    },

    /**
     * 渲染单个筛选条件
     */
    renderFilterItem(key, config) {
        const value = this.currentFilters[key];
        const hasValue = value !== undefined && value !== null && value !== '';

        let content = '';
        switch (config.type) {
            case 'multiSelect':
                content = this.renderMultiSelect(key, config, value);
                break;
            case 'singleSelect':
                content = this.renderSingleSelect(key, config, value);
                break;
            case 'range':
                content = this.renderRange(key, config, value);
                break;
            case 'rangeGroup':
                content = this.renderRangeGroup(key, config, value);
                break;
        }

        return `
            <div class="filter-section ${hasValue ? 'has-value' : ''}" data-filter="${key}">
                <div class="filter-section-header">
                    <span class="filter-section-title">${config.label}</span>
                    ${hasValue ? `<button class="clear-section-btn" onclick="FundFilters.clearSection('${key}')">
                        <i class="bi bi-x-circle"></i>
                    </button>` : ''}
                </div>
                <div class="filter-section-content">
                    ${content}
                </div>
            </div>
        `;
    },

    /**
     * 渲染多选
     */
    renderMultiSelect(key, config, value) {
        const selectedValues = Array.isArray(value) ? value : [];
        return `
            <div class="filter-options multi-select">
                ${config.options.map(opt => `
                    <label class="filter-option ${selectedValues.includes(opt.value) ? 'selected' : ''}"
                           style="${opt.color ? `--option-color: ${opt.color}` : ''}">
                        <input type="checkbox" 
                               value="${opt.value}"
                               ${selectedValues.includes(opt.value) ? 'checked' : ''}
                               onchange="FundFilters.handleMultiSelect('${key}', '${opt.value}', this.checked)">
                        <span class="option-label">${opt.label}</span>
                        ${opt.desc ? `<span class="option-desc">${opt.desc}</span>` : ''}
                    </label>
                `).join('')}
            </div>
        `;
    },

    /**
     * 渲染单选
     */
    renderSingleSelect(key, config, value) {
        const selectedValue = value || 'all';
        return `
            <div class="filter-options single-select">
                ${config.options.map(opt => `
                    <label class="filter-option ${selectedValue === opt.value ? 'selected' : ''}">
                        <input type="radio" 
                               name="${key}"
                               value="${opt.value}"
                               ${selectedValue === opt.value ? 'checked' : ''}
                               onchange="FundFilters.handleSingleSelect('${key}', '${opt.value}')">
                        <span class="option-label">${opt.label}</span>
                    </label>
                `).join('')}
            </div>
        `;
    },

    /**
     * 渲染范围选择
     */
    renderRange(key, config, value) {
        const min = value?.min ?? '';
        const max = value?.max ?? '';
        const unit = config.unit || '';
        
        return `
            <div class="filter-range">
                <div class="range-inputs">
                    <div class="range-input-group">
                        <input type="number" 
                               class="form-control range-input" 
                               placeholder="最小值"
                               value="${min}"
                               step="${config.step}"
                               onchange="FundFilters.handleRange('${key}', 'min', this.value)">
                        <span class="range-unit">${unit}</span>
                    </div>
                    <span class="range-separator">-</span>
                    <div class="range-input-group">
                        <input type="number" 
                               class="form-control range-input" 
                               placeholder="最大值"
                               value="${max}"
                               step="${config.step}"
                               onchange="FundFilters.handleRange('${key}', 'max', this.value)">
                        <span class="range-unit">${unit}</span>
                    </div>
                </div>
                ${config.min !== undefined && config.max !== undefined ? `
                    <div class="range-slider" data-key="${key}" data-min="${config.min}" data-max="${config.max}">
                        <div class="range-slider-track"></div>
                        <div class="range-slider-fill"></div>
                        <div class="range-slider-thumb min" draggable="true"></div>
                        <div class="range-slider-thumb max" draggable="true"></div>
                    </div>
                ` : ''}
            </div>
        `;
    },

    /**
     * 渲染分组范围选择（收益率多时间段）
     */
    renderRangeGroup(key, config, value) {
        const currentPeriod = value?.period || 'year';
        const periodValue = value?.[currentPeriod] || {};
        
        return `
            <div class="filter-range-group">
                <div class="period-tabs">
                    ${config.periods.map(p => `
                        <button class="period-tab ${currentPeriod === p.key ? 'active' : ''}"
                                onclick="FundFilters.switchPeriod('${key}', '${p.key}')">
                            ${p.label}
                        </button>
                    `).join('')}
                </div>
                <div class="range-quick-options">
                    <button class="range-quick-btn" onclick="FundFilters.setReturnRange('${currentPeriod}', -10, 0)">亏损</button>
                    <button class="range-quick-btn" onclick="FundFilters.setReturnRange('${currentPeriod}', 0, 10)">0-10%</button>
                    <button class="range-quick-btn" onclick="FundFilters.setReturnRange('${currentPeriod}', 10, 20)">10-20%</button>
                    <button class="range-quick-btn" onclick="FundFilters.setReturnRange('${currentPeriod}', 20, 50)">20%+</button>
                </div>
                <div class="range-inputs">
                    <div class="range-input-group">
                        <input type="number" 
                               class="form-control range-input" 
                               placeholder="最小值"
                               value="${periodValue.min ?? ''}"
                               step="0.01"
                               onchange="FundFilters.handleRangeGroup('${key}', '${currentPeriod}', 'min', this.value)">
                        <span class="range-unit">%</span>
                    </div>
                    <span class="range-separator">-</span>
                    <div class="range-input-group">
                        <input type="number" 
                               class="form-control range-input" 
                               placeholder="最大值"
                               value="${periodValue.max ?? ''}"
                               step="0.01"
                               onchange="FundFilters.handleRangeGroup('${key}', '${currentPeriod}', 'max', this.value)">
                        <span class="range-unit">%</span>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 处理多选变化
     */
    handleMultiSelect(key, value, checked) {
        let current = this.currentFilters[key] || [];
        
        if (checked) {
            if (!current.includes(value)) {
                current = [...current, value];
            }
        } else {
            current = current.filter(v => v !== value);
        }
        
        this.currentFilters[key] = current.length > 0 ? current : undefined;
        this.debounceExecute();
        this.updateFilterUI(key);
    },

    /**
     * 处理单选变化
     */
    handleSingleSelect(key, value) {
        this.currentFilters[key] = value === 'all' ? undefined : value;
        this.debounceExecute();
        this.updateFilterUI(key);
    },

    /**
     * 处理范围变化
     */
    handleRange(key, type, value) {
        const numValue = value === '' ? undefined : parseFloat(value);
        
        if (!this.currentFilters[key]) {
            this.currentFilters[key] = {};
        }
        
        this.currentFilters[key][type] = numValue;
        
        // 如果都为空则删除
        if (this.currentFilters[key].min === undefined && this.currentFilters[key].max === undefined) {
            delete this.currentFilters[key];
        }
        
        this.debounceExecute();
        this.updateFilterUI(key);
    },

    /**
     * 处理分组范围变化
     */
    handleRangeGroup(key, period, type, value) {
        const numValue = value === '' ? undefined : parseFloat(value);
        
        if (!this.currentFilters[key]) {
            this.currentFilters[key] = { period };
        }
        
        if (!this.currentFilters[key][period]) {
            this.currentFilters[key][period] = {};
        }
        
        this.currentFilters[key][period][type] = numValue;
        this.debounceExecute();
        this.updateFilterUI(key);
    },

    /**
     * 切换时间段
     */
    switchPeriod(key, period) {
        if (!this.currentFilters[key]) {
            this.currentFilters[key] = {};
        }
        this.currentFilters[key].period = period;
        this.renderFilterPanel();
    },

    /**
     * 设置收益率范围快捷选项
     */
    setReturnRange(period, min, max) {
        if (!this.currentFilters.returnRate) {
            this.currentFilters.returnRate = { period };
        }
        this.currentFilters.returnRate[period] = { min, max };
        this.renderFilterPanel();
        this.debounceExecute();
    },

    /**
     * 防抖执行筛选
     */
    debounceExecute() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.executeFilter();
        }, 300);
    },

    /**
     * 更新筛选UI
     */
    updateFilterUI(key) {
        const section = document.querySelector(`[data-filter="${key}"]`);
        if (section) {
            const hasValue = this.currentFilters[key] !== undefined;
            section.classList.toggle('has-value', hasValue);
            this.renderFilterPanel();
        }
        this.renderFilterTags();
        this.updateResultCount();
    },

    /**
     * 执行筛选
     */
    executeFilter() {
        const filters = this.currentFilters;
        const startTime = performance.now();
        
        FundState.filteredFunds = FundState.funds.filter(fund => {
            // 基金类型筛选
            if (filters.fundType?.length > 0) {
                const fundType = fund.fund_type || 'unknown';
                if (!filters.fundType.includes(fundType)) {
                    return false;
                }
            }

            // 风险等级筛选（根据最大回撤和波动率估算）
            if (filters.riskLevel?.length > 0) {
                const risk = this.calculateRiskLevel(fund);
                if (!filters.riskLevel.includes(risk)) {
                    return false;
                }
            }

            // 成立时间筛选
            if (filters.establishDate && filters.establishDate !== 'all') {
                if (!this.checkEstablishDate(fund, filters.establishDate)) {
                    return false;
                }
            }

            // 基金规模筛选
            if (filters.fundScale && filters.fundScale !== 'all') {
                if (!this.checkFundScale(fund, filters.fundScale)) {
                    return false;
                }
            }

            // 收益率筛选
            if (filters.returnRate) {
                const period = filters.returnRate.period || 'year';
                const range = filters.returnRate[period];
                if (range && !this.checkReturnRate(fund, period, range)) {
                    return false;
                }
            }

            // 夏普比率筛选
            if (filters.sharpeRatio) {
                const sharpe = fund.sharpe_ratio;
                if (sharpe === null || sharpe === undefined) return false;
                if (filters.sharpeRatio.min !== undefined && sharpe < filters.sharpeRatio.min) return false;
                if (filters.sharpeRatio.max !== undefined && sharpe > filters.sharpeRatio.max) return false;
            }

            // 最大回撤筛选
            if (filters.maxDrawdown) {
                const drawdown = fund.max_drawdown;
                if (drawdown === null || drawdown === undefined) return false;
                if (filters.maxDrawdown.min !== undefined && drawdown < filters.maxDrawdown.min) return false;
                if (filters.maxDrawdown.max !== undefined && drawdown > filters.maxDrawdown.max) return false;
            }

            // 波动率筛选
            if (filters.volatility) {
                const vol = fund.volatility;
                if (vol === null || vol === undefined) return false;
                if (filters.volatility.min !== undefined && vol < filters.volatility.min) return false;
                if (filters.volatility.max !== undefined && vol > filters.volatility.max) return false;
            }

            // 净值筛选
            if (filters.nav) {
                const nav = fund.current_nav || fund.nav;
                if (nav === null || nav === undefined) return false;
                if (filters.nav.min !== undefined && nav < filters.nav.min) return false;
                if (filters.nav.max !== undefined && nav > filters.nav.max) return false;
            }

            // 持仓金额筛选
            if (filters.holdingAmount) {
                const amount = fund.holding_amount;
                if (amount === null || amount === undefined) return false;
                if (filters.holdingAmount.min !== undefined && amount < filters.holdingAmount.min) return false;
                if (filters.holdingAmount.max !== undefined && amount > filters.holdingAmount.max) return false;
            }

            return true;
        });

        const endTime = performance.now();
        console.log(`筛选完成: ${FundState.filteredFunds.length} 条结果, 耗时 ${(endTime - startTime).toFixed(2)}ms`);

        FundState.currentPage = 1;
        FundTable.renderData();
    },

    /**
     * 计算风险等级
     */
    calculateRiskLevel(fund) {
        const maxDrawdown = Math.abs(fund.max_drawdown || 0);
        const volatility = fund.volatility || 0;
        
        // 综合最大回撤和波动率判断
        const riskScore = maxDrawdown * 0.6 + volatility * 0.4;
        
        if (riskScore < 5) return 'low';
        if (riskScore < 15) return 'low-mid';
        if (riskScore < 25) return 'mid';
        if (riskScore < 35) return 'mid-high';
        return 'high';
    },

    /**
     * 检查成立时间
     */
    checkEstablishDate(fund, range) {
        // 从buy_date推算或使用基金的establish_date
        const buyDate = new Date(fund.buy_date);
        const now = new Date();
        const years = (now - buyDate) / (365 * 24 * 60 * 60 * 1000);
        
        switch (range) {
            case '1y': return years < 1;
            case '1y-3y': return years >= 1 && years < 3;
            case '3y-5y': return years >= 3 && years < 5;
            case '5y+': return years >= 5;
            default: return true;
        }
    },

    /**
     * 检查基金规模
     */
    checkFundScale(fund, range) {
        // 使用holding_value作为规模的代理
        const scale = fund.holding_value || fund.current_value || 0;
        const scaleInYi = scale / 100000000; // 转换为亿
        
        switch (range) {
            case '0-1': return scaleInYi < 1;
            case '1-10': return scaleInYi >= 1 && scaleInYi < 10;
            case '10-50': return scaleInYi >= 10 && scaleInYi < 50;
            case '50-100': return scaleInYi >= 50 && scaleInYi < 100;
            case '100+': return scaleInYi >= 100;
            default: return true;
        }
    },

    /**
     * 检查收益率
     */
    checkReturnRate(fund, period, range) {
        let returnValue;
        
        switch (period) {
            case 'today': returnValue = fund.today_return; break;
            case 'week': returnValue = fund.week_return || fund.today_return * 5; break;
            case 'month': returnValue = fund.month_return || fund.annualized_return / 12; break;
            case '3month': returnValue = fund.return_3m || fund.annualized_return / 4; break;
            case '6month': returnValue = fund.return_6m || fund.annualized_return / 2; break;
            case 'year': returnValue = fund.annualized_return; break;
            case 'ytd': returnValue = fund.ytd_return || fund.annualized_return * 0.8; break;
            case 'all': returnValue = fund.total_return; break;
            default: returnValue = fund.annualized_return;
        }
        
        if (returnValue === null || returnValue === undefined) return false;
        
        if (range.min !== undefined && returnValue < range.min) return false;
        if (range.max !== undefined && returnValue > range.max) return false;
        
        return true;
    },

    /**
     * 应用预设筛选
     */
    applyPreset(index) {
        const preset = this.presetFilters[index];
        if (preset) {
            this.currentFilters = JSON.parse(JSON.stringify(preset.filters));
            this.renderFilterPanel();
            this.executeFilter();
            this.renderFilterTags();
            
            // 更新预设按钮状态
            document.querySelectorAll('.preset-tag').forEach((btn, i) => {
                btn.classList.toggle('active', i === index);
            });
        }
    },

    /**
     * 渲染筛选标签
     */
    renderFilterTags() {
        const container = document.getElementById('active-filter-tags');
        if (!container) return;

        const tags = [];
        const filters = this.currentFilters;

        // 基金类型
        if (filters.fundType?.length > 0) {
            const typeDef = this.filterDefinitions.fundType;
            const typeLabels = filters.fundType.map(v => 
                typeDef.options.find(o => o.value === v)?.label || v
            );
            tags.push({ key: 'fundType', label: `类型: ${typeLabels.join(', ')}` });
        }

        // 风险等级
        if (filters.riskLevel?.length > 0) {
            const riskDef = this.filterDefinitions.riskLevel;
            const riskLabels = filters.riskLevel.map(v => 
                riskDef.options.find(o => o.value === v)?.label || v
            );
            tags.push({ key: 'riskLevel', label: `风险: ${riskLabels.join(', ')}` });
        }

        // 收益率
        if (filters.returnRate) {
            const period = filters.returnRate.period || 'year';
            const range = filters.returnRate[period];
            if (range && (range.min !== undefined || range.max !== undefined)) {
                const periodLabel = this.filterDefinitions.returnRate.periods.find(p => p.key === period)?.label;
                tags.push({ key: 'returnRate', label: `${periodLabel}: ${range.min ?? '-'}%~${range.max ?? '-'}%` });
            }
        }

        // 其他范围筛选
        ['sharpeRatio', 'maxDrawdown', 'volatility', 'nav', 'holdingAmount'].forEach(key => {
            if (filters[key]) {
                const def = this.filterDefinitions[key];
                const min = filters[key].min;
                const max = filters[key].max;
                if (min !== undefined || max !== undefined) {
                    tags.push({ 
                        key, 
                        label: `${def.label}: ${min ?? '-'}${def.unit || ''}~${max ?? '-'}${def.unit || ''}` 
                    });
                }
            }
        });

        if (tags.length === 0) {
            container.innerHTML = '';
            container.style.display = 'none';
            return;
        }

        container.innerHTML = `
            <div class="filter-tags-container">
                <span class="filter-tags-label">筛选条件:</span>
                ${tags.map(tag => `
                    <span class="filter-tag">
                        ${tag.label}
                        <i class="bi bi-x-circle-fill" onclick="FundFilters.removeFilter('${tag.key}')"></i>
                    </span>
                `).join('')}
                <button class="clear-all-btn" onclick="FundFilters.clearAll()">
                    <i class="bi bi-trash"></i> 清除全部
                </button>
            </div>
        `;
        container.style.display = 'block';
    },

    /**
     * 移除单个筛选条件
     */
    removeFilter(key) {
        delete this.currentFilters[key];
        this.renderFilterPanel();
        this.executeFilter();
        this.renderFilterTags();
    },

    /**
     * 清除某一部分的筛选条件
     */
    clearSection(key) {
        delete this.currentFilters[key];
        this.renderFilterPanel();
        this.executeFilter();
        this.renderFilterTags();
    },

    /**
     * 清除所有筛选
     */
    clearAll() {
        this.currentFilters = {};
        this.renderFilterPanel();
        FundState.filteredFunds = [...FundState.funds];
        FundTable.renderData();
        this.renderFilterTags();
        this.updateResultCount();
        
        // 重置预设按钮
        document.querySelectorAll('.preset-tag').forEach((btn, i) => {
            btn.classList.toggle('active', i === 0);
        });
    },

    /**
     * 更新结果计数
     */
    updateResultCount() {
        const count = FundState.filteredFunds.length;
        const total = FundState.funds.length;
        
        const countEl = document.getElementById('filter-result-count');
        if (countEl) {
            countEl.innerHTML = `显示 <strong>${count}</strong> / ${total} 只基金`;
        }
    },

    /**
     * 切换筛选面板
     */
    togglePanel() {
        const panel = document.getElementById('filter-panel');
        const overlay = document.getElementById('filter-panel-overlay');
        
        if (panel?.classList.contains('open')) {
            this.closePanel();
        } else {
            panel?.classList.add('open');
            overlay?.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    },

    /**
     * 关闭筛选面板
     */
    closePanel() {
        const panel = document.getElementById('filter-panel');
        const overlay = document.getElementById('filter-panel-overlay');
        
        panel?.classList.remove('open');
        overlay?.classList.remove('active');
        document.body.style.overflow = '';
    },

    /**
     * 搜索处理（保留原功能）
     */
    handleSearch(keyword) {
        if (!keyword.trim()) {
            FundState.filteredFunds = [...FundState.funds];
        } else {
            const lowerKeyword = keyword.toLowerCase();
            FundState.filteredFunds = FundState.funds.filter(fund => 
                fund.fund_code?.toLowerCase().includes(lowerKeyword) ||
                fund.fund_name?.toLowerCase().includes(lowerKeyword)
            );
        }
        
        FundState.currentPage = 1;
        FundTable.renderData();
        this.updateResultCount();
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    FundFilters.init();
});
/* 文件内容已在上方完整写入 */

// 兼容性函数 - 保持与旧代码的兼容
function openFilterModal() { FundFilters.togglePanel(); }
function closeFilterModal() { FundFilters.closePanel(); }
function applyFilters() { FundFilters.apply(); }
function resetFilters() { FundFilters.reset(); }
function clearAllFilters() { FundFilters.clearAll(); }
function handleModalBackdrop(event) {
    if (event.target.classList.contains('modal-overlay')) {
        event.target.classList.remove('active');
    }
}
function handleSearchKeyup(event) {
    if (event.key === 'Enter') {
        FundFilters.handleSearch(event.target.value);
    }
}
