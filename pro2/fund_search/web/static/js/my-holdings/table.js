/**
 * 表格模块 - 处理表格渲染、排序、选择
 */
const FundTable = {
    /**
     * 初始化表格
     */
    init() {
        this.loadColumnConfig();
        this.renderHeader();
        this.bindEvents();
    },

    /**
     * 加载列配置
     */
    loadColumnConfig() {
        const saved = FundUtils.getStorage(FundConfig.storage.columns);
        if (saved) {
            FundState.columnConfig = saved;
        } else {
            FundState.columnConfig = FundUtils.deepClone(FundConfig.defaultColumns);
        }
    },

    /**
     * 保存列配置
     */
    saveColumnConfig() {
        FundUtils.setStorage(FundConfig.storage.columns, FundState.columnConfig);
    },

    /**
     * 渲染表头
     */
    renderHeader() {
        const headerRow = document.getElementById('table-header');
        const checkboxCell = headerRow.querySelector('.checkbox-cell');
        
        // 清空现有表头（保留复选框）
        headerRow.innerHTML = '';
        headerRow.appendChild(checkboxCell);
        
        // 添加可见列
        FundState.columnConfig
            .filter(col => col.visible)
            .forEach(col => {
                const th = document.createElement('th');
                th.dataset.column = col.key;
                
                if (col.sortable) {
                    th.className = 'sortable';
                    if (FundState.sortColumn === col.key) {
                        th.classList.add(FundState.sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
                    }
                    th.onclick = () => this.handleSort(col.key);
                }
                
                th.innerHTML = `
                    ${col.label}
                    ${col.sortable ? '<span class="sort-indicator">↕</span>' : ''}
                `;
                
                headerRow.appendChild(th);
            });
        
        // 添加操作列
        const actionTh = document.createElement('th');
        actionTh.textContent = '操作';
        headerRow.appendChild(actionTh);
    },

    /**
     * 渲染表格数据
     */
    renderData(funds = FundState.filteredFunds) {
        const tbody = document.getElementById('table-body');
        
        if (funds.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${this.getVisibleColumnCount() + 2}" class="empty-state">
                        <i class="bi bi-inbox"></i>
                        <p>暂无数据</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = funds.map(fund => this.renderRow(fund)).join('');
        this.updateSelectAllCheckbox();
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
     * 渲染单行
     */
    renderRow(fund) {
        const isSelected = FundState.selectedFunds.has(fund.fund_code);
        // 使用后端返回的基金类型信息（证监会标准分类）
        const typeInfo = this.getFundTypeInfo(fund);
        const visibleColumns = FundState.columnConfig.filter(col => col.visible);
        
        let cells = visibleColumns.map(col => {
            const value = fund[col.key];
            let displayValue;
            let cellClass = '';
            let titleAttr = '';
            
            // Fund code becomes a clickable link
            if (col.key === 'fund_code') {
                displayValue = `<a href="javascript:void(0)" 
                    class="fund-code-link" 
                    onclick="FundTable.openDetailPanel('${fund.fund_code}')"
                    title="点击查看详情">${value}</a>`;
            } else if (col.key === 'fund_name') {
                // 基金名称列添加类型标签（使用后端返回的证监会标准分类）
                displayValue = `<span class="fund-name-text">${value}</span><span class="fund-type-tag ${typeInfo.className}">${typeInfo.label}</span>`;
            } else if (col.key === 'prev_day_return') {
                // 昨日盈亏率列添加数据时效性标记
                const isStale = fund.yesterday_return_is_stale;
                const daysDiff = fund.yesterday_return_days_diff;
                const dateStr = fund.yesterday_return_date;
                
                displayValue = FundUtils.formatPercent(value);
                cellClass = FundUtils.getCellClass(value, 'percent');
                
                if (isStale && daysDiff > 1) {
                    // 延迟数据标记
                    cellClass += ' stale-data';
                    const tLabel = `T-${daysDiff}`;
                    displayValue = `<span class="stale-value">${displayValue}</span><span class="stale-badge" title="数据日期: ${dateStr || '未知'}，延迟 ${daysDiff} 天">(${tLabel})</span>`;
                    titleAttr = `昨日盈亏率数据来自 ${dateStr || '未知'}，比最新净值延迟 ${daysDiff} 天`;
                } else if (dateStr) {
                    titleAttr = `数据日期: ${dateStr}`;
                }
            } else {
                switch (col.type) {
                    case 'percent':
                        displayValue = FundUtils.formatPercent(value);
                        cellClass = FundUtils.getCellClass(value, 'percent');
                        break;
                    case 'currency':
                        displayValue = FundUtils.formatCurrency(value);
                        cellClass = FundUtils.getCellClass(value, 'currency');
                        break;
                    case 'nav':
                        displayValue = (value != null && !isNaN(value)) ? parseFloat(value).toFixed(4) : '--';
                        break;
                    case 'number':
                        displayValue = FundUtils.formatNumber(value);
                        break;
                    default:
                        displayValue = value || '--';
                }
            }
            
            return `<td class="${cellClass}"${titleAttr ? ` title="${titleAttr}"` : ''}>${displayValue}</td>`;
        }).join('');
        
        return `
            <tr data-fund-code="${fund.fund_code}" class="${isSelected ? 'selected' : ''}">
                <td class="checkbox-cell">
                    <input type="checkbox" 
                           ${isSelected ? 'checked' : ''} 
                           onchange="FundTable.toggleSelect('${fund.fund_code}')">
                </td>
                ${cells}
                <td class="action-cell">
                    <button class="btn btn-sm btn-ghost action-btn edit-btn" 
                            onclick="FundTable.editFund('${fund.fund_code}')"
                            title="编辑基金"
                            aria-label="编辑基金 ${fund.fund_code}">
                        <i class="bi bi-pencil-square"></i>
                    </button>
                    <button class="btn btn-sm btn-ghost action-btn delete-btn" 
                            onclick="FundTable.deleteFund('${fund.fund_code}')"
                            title="删除基金"
                            aria-label="删除基金 ${fund.fund_code}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    },

    /**
     * 获取可见列数
     */
    getVisibleColumnCount() {
        return FundState.columnConfig.filter(col => col.visible).length;
    },

    /**
     * 处理排序
     */
    handleSort(column) {
        if (FundState.sortColumn === column) {
            FundState.sortDirection = FundState.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            FundState.sortColumn = column;
            FundState.sortDirection = 'asc';
        }
        
        this.sortData();
        this.renderHeader();
        this.renderData();
    },

    /**
     * 排序数据
     */
    sortData() {
        if (!FundState.sortColumn) return;
        
        const col = FundState.columnConfig.find(c => c.key === FundState.sortColumn);
        if (!col) return;
        
        FundState.filteredFunds.sort((a, b) => {
            let aVal = a[FundState.sortColumn];
            let bVal = b[FundState.sortColumn];
            
            // 处理 null/undefined
            if (aVal === null || aVal === undefined) aVal = col.type === 'number' || col.type === 'percent' ? -Infinity : '';
            if (bVal === null || bVal === undefined) bVal = col.type === 'number' || col.type === 'percent' ? -Infinity : '';
            
            // 数值比较
            if (col.type === 'number' || col.type === 'percent' || col.type === 'currency') {
                aVal = parseFloat(aVal) || 0;
                bVal = parseFloat(bVal) || 0;
            } else if (FundState.sortColumn === 'fund_name') {
                // 基金名称按拼音排序
                const strA = String(aVal);
                const strB = String(bVal);
                
                if (typeof pinyinPro !== 'undefined') {
                    // 使用 pinyin-pro 库
                    const pinyinA = pinyinPro.pinyin(strA, { toneType: 'none', type: 'string' });
                    const pinyinB = pinyinPro.pinyin(strB, { toneType: 'none', type: 'string' });
                    if (pinyinA < pinyinB) return FundState.sortDirection === 'asc' ? -1 : 1;
                    if (pinyinA > pinyinB) return FundState.sortDirection === 'asc' ? 1 : -1;
                    return 0;
                } else {
                    // 降级到普通字符串比较
                    aVal = strA.toLowerCase();
                    bVal = strB.toLowerCase();
                }
            } else {
                aVal = String(aVal).toLowerCase();
                bVal = String(bVal).toLowerCase();
            }
            
            if (aVal < bVal) return FundState.sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return FundState.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    },

    /**
     * 切换选择
     */
    toggleSelect(fundCode) {
        if (FundState.selectedFunds.has(fundCode)) {
            FundState.selectedFunds.delete(fundCode);
        } else {
            FundState.selectedFunds.add(fundCode);
        }
        
        const row = document.querySelector(`tr[data-fund-code="${fundCode}"]`);
        if (row) {
            row.classList.toggle('selected', FundState.selectedFunds.has(fundCode));
        }
        
        this.updateSelectAllCheckbox();
        this.updateAnalysisButton();
    },

    /**
     * 全选/取消全选
     */
    toggleSelectAll() {
        const checkbox = document.getElementById('select-all');
        const isChecked = checkbox.checked;
        
        if (isChecked) {
            FundState.filteredFunds.forEach(fund => {
                FundState.selectedFunds.add(fund.fund_code);
            });
        } else {
            FundState.selectedFunds.clear();
        }
        
        this.renderData();
        this.updateAnalysisButton();
    },

    /**
     * 更新全选复选框状态
     */
    updateSelectAllCheckbox() {
        const checkbox = document.getElementById('select-all');
        const visibleFunds = FundState.filteredFunds.length;
        const selectedVisible = FundState.filteredFunds.filter(
            f => FundState.selectedFunds.has(f.fund_code)
        ).length;
        
        checkbox.checked = visibleFunds > 0 && selectedVisible === visibleFunds;
        checkbox.indeterminate = selectedVisible > 0 && selectedVisible < visibleFunds;
    },

    /**
     * 更新分析按钮状态
     */
    updateAnalysisButton() {
        const btn = document.getElementById('analysis-btn');
        const count = FundState.selectedFunds.size;
        btn.disabled = count < 2;
        btn.innerHTML = `<i class="bi bi-chart-line"></i> 相关性分析 (${count})`;
        
        // 同时更新投资建议按钮
        const adviceBtn = document.getElementById('investment-advice-btn');
        if (adviceBtn) {
            adviceBtn.disabled = count === 0;
            adviceBtn.innerHTML = `<i class="bi bi-lightbulb"></i> 投资建议 (${count})`;
        }
    },

    /**
     * 获取选中的基金代码列表
     */
    getSelectedFundCodes() {
        return Array.from(FundState.selectedFunds);
    },

    /**
     * 编辑基金 - 打开编辑模态框
     */
    editFund(fundCode) {
        const fund = FundState.funds.find(f => f.fund_code === fundCode);
        if (!fund) {
            FundUtils.showNotification('未找到基金信息', 'error');
            return;
        }
        
        // 打开编辑面板
        FundEdit.openModal(fund);
    },

    /**
     * 打开详情侧边面板
     */
    openDetailPanel(fundCode) {
        const fund = FundState.funds.find(f => f.fund_code === fundCode);
        if (!fund) {
            FundUtils.showNotification('未找到基金信息', 'error');
            return;
        }
        
        // 打开详情面板
        FundDetail.openPanel(fund);
    },

    /**
     * 删除基金
     */
    async deleteFund(fundCode) {
        if (!confirm(`确定要删除基金 ${fundCode} 吗？`)) return;
        
        try {
            const response = await fetch(`/api/holdings/${fundCode}?user_id=default_user`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                FundState.funds = FundState.funds.filter(f => f.fund_code !== fundCode);
                FundState.filteredFunds = FundState.filteredFunds.filter(f => f.fund_code !== fundCode);
                FundState.selectedFunds.delete(fundCode);

                this.renderData();
                FundApp.updateTotalCount();
                FundUtils.showNotification('删除成功', 'success');
            } else {
                FundUtils.showNotification('删除失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('删除基金失败:', error);
            FundUtils.showNotification('删除失败: 网络错误', 'error');
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 表格行点击事件委托
        const tbody = document.getElementById('table-body');
        tbody.addEventListener('click', (e) => {
            const row = e.target.closest('tr[data-fund-code]');
            if (row && !e.target.closest('input[type="checkbox"]') && !e.target.closest('button') && !e.target.closest('a')) {
                const fundCode = row.dataset.fundCode;
                const checkbox = row.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                this.toggleSelect(fundCode);
            }
        });
    }
};
