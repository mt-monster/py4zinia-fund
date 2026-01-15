// ==================== DataSorter 类 ====================
// 负责执行数据排序逻辑
class DataSorter {
    // 判断是否为空值
    isNullValue(value) {
        return value === null || value === undefined || value === '' || value === '--' || 
               (typeof value === 'number' && isNaN(value));
    }

    // 处理空值，返回用于比较的值
    handleNullValue(value) {
        if (this.isNullValue(value)) {
            return null;
        }
        return value;
    }

    // 比较数字
    compareNumbers(a, b, order) {
        const aVal = this.handleNullValue(a);
        const bVal = this.handleNullValue(b);
        
        // 空值处理：升序时空值排最后，降序时空值排最前
        if (aVal === null && bVal === null) return 0;
        if (aVal === null) return order === 'asc' ? 1 : -1;
        if (bVal === null) return order === 'asc' ? -1 : 1;
        
        const numA = parseFloat(aVal);
        const numB = parseFloat(bVal);
        
        if (isNaN(numA) && isNaN(numB)) return 0;
        if (isNaN(numA)) return order === 'asc' ? 1 : -1;
        if (isNaN(numB)) return order === 'asc' ? -1 : 1;
        
        return order === 'asc' ? numA - numB : numB - numA;
    }

    // 比较字符串（支持中文）
    compareStrings(a, b, order) {
        const aVal = this.handleNullValue(a);
        const bVal = this.handleNullValue(b);
        
        // 空值处理
        if (aVal === null && bVal === null) return 0;
        if (aVal === null) return order === 'asc' ? 1 : -1;
        if (bVal === null) return order === 'asc' ? -1 : 1;
        
        const strA = String(aVal);
        const strB = String(bVal);
        
        const result = strA.localeCompare(strB, 'zh-CN');
        return order === 'asc' ? result : -result;
    }

    // 按列排序数据
    sortByColumn(data, columnName, order, columnType) {
        if (!data || data.length === 0) return data;
        if (order === 'none') return data;
        
        const sortedData = [...data];
        
        sortedData.sort((a, b) => {
            const aValue = a[columnName];
            const bValue = b[columnName];
            
            if (columnType === 'number') {
                return this.compareNumbers(aValue, bValue, order);
            } else {
                return this.compareStrings(aValue, bValue, order);
            }
        });
        
        return sortedData;
    }
}

// ==================== SortController 类 ====================
// 负责管理排序状态和处理用户交互
class SortController {
    constructor(columnConfig) {
        this.columnConfig = columnConfig || this.getDefaultColumnConfig();
        this.currentColumn = 'composite_score';  // 默认按综合评分排序
        this.currentOrder = 'desc';  // 默认降序
        this.previousColumn = null;
    }

    // 获取默认列配置
    getDefaultColumnConfig() {
        return {
            'fund_code': { type: 'text', sortable: true, label: '代码' },
            'fund_name': { type: 'text', sortable: true, label: '名称' },
            'today_return': { type: 'number', sortable: true, label: '日涨跌幅' },
            'yesterday_return': { type: 'number', sortable: true, label: '昨日盈亏率' },
            'holding_amount': { type: 'number', sortable: true, label: '持有金额' },
            'today_profit': { type: 'number', sortable: true, label: '当日盈亏' },
            'today_profit_rate': { type: 'number', sortable: true, label: '当日盈亏率' },
            'holding_profit': { type: 'number', sortable: true, label: '持有盈亏' },
            'holding_profit_rate': { type: 'number', sortable: true, label: '持有盈亏率' },
            'total_profit': { type: 'number', sortable: true, label: '累计盈亏' },
            'total_profit_rate': { type: 'number', sortable: true, label: '累计盈亏率' },
            'sharpe_ratio': { type: 'number', sortable: true, label: '夏普比率' },
            'max_drawdown': { type: 'number', sortable: true, label: '最大回撤' },
            'composite_score': { type: 'number', sortable: true, label: '综合评分' },
            'checkbox': { type: 'none', sortable: false, label: '' }
        };
    }

    // 处理列标题点击
    handleColumnClick(columnName) {
        if (!this.isColumnSortable(columnName)) {
            return null; // 不可排序的列，忽略点击
        }

        const nextOrder = this.calculateNextSortOrder(columnName);
        this.updateSortState(columnName, nextOrder);
        
        return {
            column: this.currentColumn,
            order: this.currentOrder,
            type: this.getColumnType(columnName)
        };
    }

    // 计算下一个排序状态
    calculateNextSortOrder(columnName) {
        // 如果点击的是不同的列，重置为升序
        if (columnName !== this.currentColumn) {
            return 'asc';
        }

        // 同一列的状态循环：asc -> desc -> none -> asc
        switch (this.currentOrder) {
            case 'asc':
                return 'desc';
            case 'desc':
                return 'none';
            case 'none':
            default:
                return 'asc';
        }
    }

    // 更新排序状态
    updateSortState(columnName, order) {
        this.previousColumn = this.currentColumn;
        this.currentColumn = columnName;
        this.currentOrder = order;
    }

    // 检查列是否可排序
    isColumnSortable(columnName) {
        const config = this.columnConfig[columnName];
        return config && config.sortable === true;
    }

    // 获取列数据类型
    getColumnType(columnName) {
        const config = this.columnConfig[columnName];
        return config ? config.type : 'text';
    }

    // 获取当前排序状态
    getSortState() {
        return {
            column: this.currentColumn,
            order: this.currentOrder,
            previousColumn: this.previousColumn
        };
    }

    // 设置排序状态（用于外部设置默认状态）
    setSortState(columnName, order) {
        if (this.isColumnSortable(columnName)) {
            this.updateSortState(columnName, order);
        }
    }
}

// Export for Node.js (testing)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DataSorter, SortController };
}
