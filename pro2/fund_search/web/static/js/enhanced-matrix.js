/**
 * 相关性矩阵增强模块
 * 提供数字显示、悬停提示、排序功能
 */

class EnhancedMatrixManager {
    constructor() {
        this.matrixContainer = null;
        this.currentSort = { column: null, direction: 'desc' };
        this.fundData = [];
        this.correlationMatrix = [];
    }

    /**
     * 初始化增强矩阵
     */
    init(containerId, correlationData) {
        this.matrixContainer = document.getElementById(containerId);
        if (!this.matrixContainer) {
            console.error(`❌ 找不到矩阵容器: ${containerId}`);
            return;
        }

        this.fundData = correlationData.funds || [];
        this.correlationMatrix = correlationData.matrix || [];

        this.renderEnhancedMatrix();
        this.attachEvents();
    }

    /**
     * 渲染增强矩阵
     */
    renderEnhancedMatrix() {
        if (!this.fundData.length || !this.correlationMatrix.length) {
            this.matrixContainer.innerHTML = '<div class="empty-state">暂无数据</div>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'correlation-matrix enhanced';
        table.innerHTML = this.buildTableHTML();
        
        this.matrixContainer.innerHTML = '';
        this.matrixContainer.appendChild(table);
    }

    /**
     * 构建表格HTML
     */
    buildTableHTML() {
        const funds = this.fundData;
        const matrix = this.correlationMatrix;
        
        // 表头
        let html = '<thead><tr><th class="corner-header">基金</th>';
        funds.forEach((fund, index) => {
            const sortIcon = this.getSortIcon(index);
            html += `
                <th class="sortable-header" data-column="${index}" title="点击排序">
                    <div class="header-content">
                        <span class="fund-code">${fund.code}</span>
                        <span class="sort-icon">${sortIcon}</span>
                    </div>
                </th>
            `;
        });
        html += '</tr></thead>';

        // 表体
        html += '<tbody>';
        funds.forEach((rowFund, rowIndex) => {
            html += `<tr data-fund-code="${rowFund.code}">`;
            html += `<th class="row-header">
                <span class="fund-name" title="${rowFund.name}">${rowFund.name}</span>
                <span class="fund-code">${rowFund.code}</span>
            </th>`;
            
            funds.forEach((colFund, colIndex) => {
                const value = matrix[rowIndex]?.[colIndex] ?? null;
                const cellClass = this.getCellClass(value, rowIndex, colIndex);
                const displayValue = value !== null ? value.toFixed(3) : '-';
                const tooltip = this.buildTooltip(rowFund, colFund, value);
                
                html += `
                    <td class="${cellClass}" 
                        data-fund-code="${colFund.code}"
                        data-fund-name="${colFund.name}"
                        data-value="${value ?? ''}"
                        title="${tooltip}">
                        <span class="cell-value">${displayValue}</span>
                    </td>
                `;
            });
            html += '</tr>';
        });
        html += '</tbody>';

        return html;
    }

    /**
     * 获取单元格样式类
     */
    getCellClass(value, rowIndex, colIndex) {
        if (rowIndex === colIndex) return 'corr-cell diagonal';
        if (value === null) return 'corr-cell empty';
        
        let classes = ['corr-cell'];
        
        // 根据相关系数添加颜色类
        const absValue = Math.abs(value);
        if (absValue >= 0.8) classes.push(value > 0 ? 'high-positive' : 'high-negative');
        else if (absValue >= 0.5) classes.push(value > 0 ? 'medium-positive' : 'medium-negative');
        else classes.push('low-correlation');
        
        return classes.join(' ');
    }

    /**
     * 构建悬停提示内容
     */
    buildTooltip(fund1, fund2, correlation) {
        if (fund1.code === fund2.code) return fund1.name;
        
        const strength = this.getCorrelationStrength(correlation);
        return `${fund1.name} (${fund1.code})
${fund2.name} (${fund2.code})
相关系数: ${correlation?.toFixed(4) ?? 'N/A'}
相关程度: ${strength}

点击查看详情`;
    }

    /**
     * 获取相关强度描述
     */
    getCorrelationStrength(value) {
        if (value === null) return '未知';
        const absValue = Math.abs(value);
        if (absValue >= 0.8) return value > 0 ? '强正相关' : '强负相关';
        if (absValue >= 0.5) return value > 0 ? '中等正相关' : '中等负相关';
        if (absValue >= 0.3) return value > 0 ? '弱正相关' : '弱负相关';
        return '几乎不相关';
    }

    /**
     * 获取排序图标
     */
    getSortIcon(columnIndex) {
        if (this.currentSort.column !== columnIndex) return '⋮';
        return this.currentSort.direction === 'asc' ? '▲' : '▼';
    }

    /**
     * 按列排序
     */
    sortByColumn(columnIndex) {
        const direction = this.currentSort.column === columnIndex && 
                         this.currentSort.direction === 'desc' ? 'asc' : 'desc';
        
        this.currentSort = { column: columnIndex, direction };
        
        // 创建排序索引
        const indices = this.correlationMatrix.map((row, i) => ({
            index: i,
            value: row[columnIndex] ?? -999
        }));
        
        // 排序
        indices.sort((a, b) => {
            if (direction === 'asc') return a.value - b.value;
            return b.value - a.value;
        });
        
        // 重新排列数据
        const newMatrix = indices.map(item => this.correlationMatrix[item.index]);
        const newFunds = indices.map(item => this.fundData[item.index]);
        
        // 重新排列列（保持对称性）
        const finalMatrix = newMatrix.map(row => 
            indices.map(item => row[item.index])
        );
        
        this.fundData = newFunds;
        this.correlationMatrix = finalMatrix;
        
        // 重新渲染
        this.renderEnhancedMatrix();
        this.attachEvents();
    }

    /**
     * 附加事件监听
     */
    attachEvents() {
        // 表头点击排序
        const headers = this.matrixContainer.querySelectorAll('.sortable-header');
        headers.forEach(header => {
            header.addEventListener('click', () => {
                const column = parseInt(header.dataset.column);
                this.sortByColumn(column);
            });
        });

        // 单元格点击事件（委托）
        const table = this.matrixContainer.querySelector('table');
        if (table) {
            table.addEventListener('click', (e) => {
                const cell = e.target.closest('.corr-cell');
                if (cell) {
                    this.handleCellClick(cell);
                }
            });
        }
    }

    /**
     * 处理单元格点击
     */
    handleCellClick(cell) {
        if (cell.classList.contains('diagonal')) return;
        
        const row = cell.closest('tr');
        const fund1Code = row?.dataset.fundCode;
        const fund2Code = cell.dataset.fundCode;
        
        if (fund1Code && fund2Code && window.chartInteractionManager) {
            const fund1Name = this.fundData.find(f => f.code === fund1Code)?.name || fund1Code;
            const fund2Name = this.fundData.find(f => f.code === fund2Code)?.name || fund2Code;
            
            window.chartInteractionManager.highlightPair(
                fund1Code, fund2Code, fund1Name, fund2Name
            );
        }
    }
}

// 创建全局实例
const enhancedMatrixManager = new EnhancedMatrixManager();

// 添加样式
const style = document.createElement('style');
style.textContent = `
    .correlation-matrix.enhanced {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.75rem;
    }
    
    .correlation-matrix.enhanced th,
    .correlation-matrix.enhanced td {
        padding: 0.5rem;
        text-align: center;
        border: 1px solid #e5e7eb;
    }
    
    .correlation-matrix.enhanced .corner-header {
        background: #f9fafb;
        min-width: 120px;
    }
    
    .correlation-matrix.enhanced .sortable-header {
        cursor: pointer;
        background: #f3f4f6;
        transition: background 0.2s;
    }
    
    .correlation-matrix.enhanced .sortable-header:hover {
        background: #e5e7eb;
    }
    
    .correlation-matrix.enhanced .header-content {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.25rem;
    }
    
    .correlation-matrix.enhanced .row-header {
        background: #f9fafb;
        text-align: left;
    }
    
    .correlation-matrix.enhanced .fund-name {
        display: block;
        font-weight: 500;
        max-width: 150px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .correlation-matrix.enhanced .fund-code {
        font-size: 0.65rem;
        color: #6b7280;
    }
    
    .correlation-matrix.enhanced .corr-cell {
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
    }
    
    .correlation-matrix.enhanced .corr-cell:hover {
        transform: scale(1.1);
        z-index: 10;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    
    .correlation-matrix.enhanced .cell-value {
        font-weight: 600;
    }
    
    /* 颜色等级 */
    .correlation-matrix.enhanced .high-positive {
        background: #dcfce7;
        color: #166534;
    }
    
    .correlation-matrix.enhanced .high-negative {
        background: #fee2e2;
        color: #991b1b;
    }
    
    .correlation-matrix.enhanced .medium-positive {
        background: #ecfdf5;
        color: #065f46;
    }
    
    .correlation-matrix.enhanced .medium-negative {
        background: #fef2f2;
        color: #7f1d1d;
    }
    
    .correlation-matrix.enhanced .low-correlation {
        background: #f9fafb;
        color: #374151;
    }
    
    .correlation-matrix.enhanced .diagonal {
        background: #e5e7eb;
    }
`;
document.head.appendChild(style);

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedMatrixManager;
}
