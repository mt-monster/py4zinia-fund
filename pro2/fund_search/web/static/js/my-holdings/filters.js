/**
 * 筛选模块 - 处理筛选逻辑
 */
const FundFilters = {
    /**
     * 当前筛选条件
     */
    currentFilters: {},

    /**
     * 打开筛选模态框
     */
    openModal() {
        document.getElementById('filter-modal').classList.add('active');
        this.loadFilterValues();
    },

    /**
     * 关闭筛选模态框
     */
    closeModal() {
        document.getElementById('filter-modal').classList.remove('active');
    },

    /**
     * 加载当前筛选值到表单
     */
    loadFilterValues() {
        const filters = this.currentFilters;
        
        // 基本信息
        document.getElementById('filter-code').value = filters.code || '';
        document.getElementById('filter-name').value = filters.name || '';
        document.getElementById('filter-date-start').value = filters.dateStart || '';
        document.getElementById('filter-date-end').value = filters.dateEnd || '';
        
        // 业绩指标
        document.getElementById('filter-today-min').value = filters.todayMin || '';
        document.getElementById('filter-today-max').value = filters.todayMax || '';
        document.getElementById('filter-annual-min').value = filters.annualMin || '';
        document.getElementById('filter-annual-max').value = filters.annualMax || '';
        document.getElementById('filter-amount-min').value = filters.amountMin || '';
        document.getElementById('filter-amount-max').value = filters.amountMax || '';
        
        // 风险指标
        document.getElementById('filter-drawdown-min').value = filters.drawdownMin || '';
        document.getElementById('filter-drawdown-max').value = filters.drawdownMax || '';
        document.getElementById('filter-sharpe-min').value = filters.sharpeMin || '';
        document.getElementById('filter-sharpe-max').value = filters.sharpeMax || '';
        
        // 基金类型
        document.getElementById('filter-odii').checked = filters.types?.includes('odii') || false;
        document.getElementById('filter-etf').checked = filters.types?.includes('etf') || false;
        document.getElementById('filter-index').checked = filters.types?.includes('index') || false;
        document.getElementById('filter-active').checked = filters.types?.includes('active') || false;
    },

    /**
     * 应用筛选
     */
    apply() {
        // 收集表单值
        const types = [];
        if (document.getElementById('filter-odii').checked) types.push('odii');
        if (document.getElementById('filter-etf').checked) types.push('etf');
        if (document.getElementById('filter-index').checked) types.push('index');
        if (document.getElementById('filter-active').checked) types.push('active');
        
        this.currentFilters = {
            // 基本信息
            code: document.getElementById('filter-code').value.trim(),
            name: document.getElementById('filter-name').value.trim(),
            dateStart: document.getElementById('filter-date-start').value,
            dateEnd: document.getElementById('filter-date-end').value,
            
            // 业绩指标
            todayMin: document.getElementById('filter-today-min').value,
            todayMax: document.getElementById('filter-today-max').value,
            annualMin: document.getElementById('filter-annual-min').value,
            annualMax: document.getElementById('filter-annual-max').value,
            amountMin: document.getElementById('filter-amount-min').value,
            amountMax: document.getElementById('filter-amount-max').value,
            
            // 风险指标
            drawdownMin: document.getElementById('filter-drawdown-min').value,
            drawdownMax: document.getElementById('filter-drawdown-max').value,
            sharpeMin: document.getElementById('filter-sharpe-min').value,
            sharpeMax: document.getElementById('filter-sharpe-max').value,
            
            // 基金类型
            types: types
        };
        
        this.executeFilter();
        this.renderFilterTags();
        this.closeModal();
    },

    /**
     * 执行筛选逻辑
     */
    executeFilter() {
        const filters = this.currentFilters;
        
        FundState.filteredFunds = FundState.funds.filter(fund => {
            // 基金代码筛选
            if (filters.code && !fund.fund_code?.includes(filters.code)) {
                return false;
            }
            
            // 基金名称筛选
            if (filters.name && !fund.fund_name?.includes(filters.name)) {
                return false;
            }
            
            // 今日收益范围
            if (filters.todayMin !== '' && fund.today_return < parseFloat(filters.todayMin)) {
                return false;
            }
            if (filters.todayMax !== '' && fund.today_return > parseFloat(filters.todayMax)) {
                return false;
            }
            
            // 年化收益范围
            if (filters.annualMin !== '' && fund.annual_return < parseFloat(filters.annualMin)) {
                return false;
            }
            if (filters.annualMax !== '' && fund.annual_return > parseFloat(filters.annualMax)) {
                return false;
            }
            
            // 持有金额范围
            if (filters.amountMin !== '' && fund.holding_amount < parseFloat(filters.amountMin)) {
                return false;
            }
            if (filters.amountMax !== '' && fund.holding_amount > parseFloat(filters.amountMax)) {
                return false;
            }
            
            // 最大回撤范围
            if (filters.drawdownMin !== '' && fund.max_drawdown < parseFloat(filters.drawdownMin)) {
                return false;
            }
            if (filters.drawdownMax !== '' && fund.max_drawdown > parseFloat(filters.drawdownMax)) {
                return false;
            }
            
            // 夏普比率范围
            if (filters.sharpeMin !== '' && fund.sharpe_ratio < parseFloat(filters.sharpeMin)) {
                return false;
            }
            if (filters.sharpeMax !== '' && fund.sharpe_ratio > parseFloat(filters.sharpeMax)) {
                return false;
            }
            
            // 基金类型筛选
            if (filters.types?.length > 0) {
                const fundType = this.getFundType(fund);
                if (!filters.types.includes(fundType)) {
                    return false;
                }
            }
            
            return true;
        });
        
        FundState.currentPage = 1;
        FundTable.renderData();
        this.updateCount();
    },

    /**
     * 获取基金类型
     */
    getFundType(fund) {
        const name = fund.fund_name || '';
        if (name.includes('QDII') || name.includes('qdii')) return 'odii';
        if (name.includes('ETF') || name.includes('etf')) return 'etf';
        if (name.includes('指数')) return 'index';
        return 'active';
    },

    /**
     * 重置筛选
     */
    reset() {
        this.currentFilters = {};
        
        // 清空表单
        document.querySelectorAll('#filter-modal .form-control').forEach(input => {
            input.value = '';
        });
        document.querySelectorAll('#filter-modal .form-check-input').forEach(checkbox => {
            checkbox.checked = false;
        });
    },

    /**
     * 清除所有筛选
     */
    clearAll() {
        this.reset();
        FundState.filteredFunds = [...FundState.funds];
        FundTable.renderData();
        this.renderFilterTags();
        this.updateCount();
    },

    /**
     * 渲染筛选标签
     */
    renderFilterTags() {
        const container = document.getElementById('active-filters');
        const tags = [];
        const filters = this.currentFilters;
        
        if (filters.code) tags.push({ key: 'code', label: `代码: ${filters.code}` });
        if (filters.name) tags.push({ key: 'name', label: `名称: ${filters.name}` });
        if (filters.todayMin || filters.todayMax) {
            tags.push({ key: 'today', label: `日收益: ${filters.todayMin || '-'} ~ ${filters.todayMax || '-'}` });
        }
        if (filters.annualMin || filters.annualMax) {
            tags.push({ key: 'annual', label: `年化: ${filters.annualMin || '-'} ~ ${filters.annualMax || '-'}` });
        }
        if (filters.types?.length > 0) {
            const typeLabels = { odii: 'QDII', etf: 'ETF', index: '指数', active: '主动' };
            tags.push({ key: 'types', label: `类型: ${filters.types.map(t => typeLabels[t]).join(', ')}` });
        }
        
        if (tags.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.innerHTML = tags.map(tag => `
            <span class="filter-tag">
                ${tag.label}
                <i class="bi bi-x remove" onclick="FundFilters.removeFilter('${tag.key}')"></i>
            </span>
        `).join('') + `
            <button class="btn btn-sm btn-ghost" onclick="FundFilters.clearAll()">
                <i class="bi bi-x-circle"></i> 清除全部
            </button>
        `;
        
        container.style.display = 'flex';
    },

    /**
     * 移除单个筛选条件
     */
    removeFilter(key) {
        delete this.currentFilters[key];
        this.executeFilter();
        this.renderFilterTags();
    },

    /**
     * 更新基金数量显示
     */
    updateCount() {
        document.getElementById('total-count').textContent = FundState.filteredFunds.length;
    },

    /**
     * 切换标签页
     */
    switchTab(tabName) {
        // 更新按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        
        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });
    },

    /**
     * 搜索处理
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
        this.updateCount();
    }
};
