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
     * 渲染单行
     */
    renderRow(fund) {
        const isSelected = FundState.selectedFunds.has(fund.fund_code);
        const visibleColumns = FundState.columnConfig.filter(col => col.visible);
        
        let cells = visibleColumns.map(col => {
            const value = fund[col.key];
            let displayValue;
            let cellClass = '';
            
            // Fund code becomes a clickable link
            if (col.key === 'fund_code') {
                displayValue = `<a href="javascript:void(0)" 
                    class="fund-code-link" 
                    onclick="FundTable.openDetailPanel('${fund.fund_code}')"
                    title="点击查看详情">${value}</a>`;
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
                    case 'number':
                        displayValue = FundUtils.formatNumber(value);
                        break;
                    default:
                        displayValue = value || '--';
                }
            }
            
            return `<td class="${cellClass}">${displayValue}</td>`;
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
