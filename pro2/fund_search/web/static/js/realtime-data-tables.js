/**
 * 实时数据表格展示模块
 * 统一处理资产配置、行业分布、重仓股等表格的实时数据展示
 */

class RealtimeDataTable {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.title = options.title || '数据表格';
        this.dataType = options.dataType || 'generic'; // 'asset', 'industry', 'heavyweight'
        this.fundCodes = options.fundCodes || [];
        this.cacheDuration = options.cacheDuration || 5 * 60 * 1000;
        this.autoRefresh = options.autoRefresh || false;
        this.refreshInterval = options.refreshInterval || 5 * 60 * 1000;
        this.autoRefreshTimer = null;
        this.columns = options.columns || [];
        this.fetchUrl = options.fetchUrl || null;
        this.fetchMethod = options.fetchMethod || 'GET';
        this.fetchBody = options.fetchBody || null;
        
        // 状态管理
        this.state = {
            loading: false,
            error: null,
            data: null,
            lastUpdated: null,
            source: null
        };
        
        // 排序状态
        this.sortState = {
            column: null,
            direction: 'asc' // 'asc' 或 'desc'
        };
        
        // 缓存键
        this.cacheKey = `realtime_table_${this.dataType}_${this.fundCodes.join('_')}`;
        
        this.init();
    }
    
    /**
     * 初始化组件
     */
    init() {
        if (!this.container) {
            console.error(`[RealtimeDataTable] Container #${this.containerId} not found`);
            return;
        }
        
        this.renderSkeleton();
        
        // 尝试从缓存加载数据
        if (this.loadFromCache()) {
            this.render();
        } else {
            this.fetchData();
        }
        
        // 设置自动刷新
        if (this.autoRefresh) {
            this.startAutoRefresh();
        }
    }
    
    /**
     * 渲染骨架屏
     */
    renderSkeleton() {
        const skeletonHTML = `
            <div class="realtime-table-container" data-type="${this.dataType}">
                <div class="realtime-table-header">
                    <h3 class="realtime-table-title">
                        <span class="title-icon">${this.getTitleIcon()}</span>
                        ${this.title}
                    </h3>
                    <div class="realtime-table-actions">
                        <span class="last-updated">--</span>
                        <button class="refresh-btn" onclick="${this.containerId}_table.refresh()" title="刷新数据">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="realtime-table-content">
                    <div class="loading-state">
                        <div class="loading-spinner"></div>
                        <p>正在加载${this.title}数据...</p>
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = skeletonHTML;
        
        // 将实例挂载到全局，供刷新按钮使用
        window[`${this.containerId}_table`] = this;
    }
    
    /**
     * 获取标题图标
     */
    getTitleIcon() {
        const icons = {
            'asset': '💰',
            'industry': '🏭',
            'heavyweight': '📈',
            'generic': '📊'
        };
        return icons[this.dataType] || icons['generic'];
    }
    
    /**
     * 从缓存加载数据
     */
    loadFromCache() {
        try {
            const cached = localStorage.getItem(this.cacheKey);
            if (cached) {
                const { data, timestamp, source } = JSON.parse(cached);
                const age = Date.now() - timestamp;
                
                if (age < this.cacheDuration) {
                    this.state.data = data;
                    this.state.lastUpdated = new Date(timestamp);
                    this.state.source = source;
                    console.log(`[RealtimeDataTable] ${this.title} loaded from cache`);
                    return true;
                }
            }
        } catch (e) {
            console.warn(`[RealtimeDataTable] Cache load failed:`, e);
        }
        return false;
    }
    
    /**
     * 保存数据到缓存
     */
    saveToCache(data, source) {
        try {
            const cacheData = {
                data,
                timestamp: Date.now(),
                source
            };
            localStorage.setItem(this.cacheKey, JSON.stringify(cacheData));
        } catch (e) {
            console.warn(`[RealtimeDataTable] Cache save failed:`, e);
        }
    }
    
    /**
     * 获取数据
     */
    async fetchData() {
        if (this.state.loading) return;
        
        this.state.loading = true;
        this.state.error = null;
        this.renderLoading();
        
        try {
            let data;
            let source;
            
            if (this.fetchUrl) {
                // 从API获取数据
                const response = await fetch(this.fetchUrl, {
                    method: this.fetchMethod,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: this.fetchBody ? JSON.stringify(this.fetchBody) : null
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                if (!result.success) {
                    throw new Error(result.error || '数据获取失败');
                }
                
                data = result.data;
                source = result.source || 'api';
            } else {
                // 使用静态数据（用于资产配置和行业分布）
                data = this.state.data;
                source = 'static';
            }
            
            this.state.data = data;
            this.state.lastUpdated = new Date();
            this.state.source = source;
            
            // 保存到缓存
            this.saveToCache(data, source);
            
            this.render();
            
        } catch (error) {
            console.error(`[RealtimeDataTable] ${this.title} fetch failed:`, error);
            this.state.error = error.message;
            this.renderError();
        } finally {
            this.state.loading = false;
        }
    }
    
    /**
     * 渲染加载状态
     */
    renderLoading() {
        const contentDiv = this.container.querySelector('.realtime-table-content');
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="loading-state">
                    <div class="loading-spinner"></div>
                    <p>正在加载${this.title}数据...</p>
                </div>
            `;
        }
    }
    
    /**
     * 渲染错误状态
     */
    renderError() {
        const contentDiv = this.container.querySelector('.realtime-table-content');
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">⚠️</div>
                    <p>加载失败: ${this.state.error}</p>
                    <button class="retry-btn" onclick="${this.containerId}_table.refresh()">重试</button>
                </div>
            `;
        }
    }
    
    /**
     * 渲染数据表格
     */
    render() {
        const contentDiv = this.container.querySelector('.realtime-table-content');
        const lastUpdatedSpan = this.container.querySelector('.last-updated');
        
        if (!this.state.data) {
            contentDiv.innerHTML = `
                <div class="empty-state">
                    <p>暂无数据</p>
                </div>
            `;
            return;
        }
        
        // 更新时间
        if (lastUpdatedSpan && this.state.lastUpdated) {
            lastUpdatedSpan.textContent = this.formatTime(this.state.lastUpdated);
            lastUpdatedSpan.title = `数据来源: ${this.state.source} | 更新时间: ${this.state.lastUpdated.toLocaleString()}`;
        }
        
        // 根据数据类型渲染不同的表格
        let tableHTML = '';
        
        if (Array.isArray(this.state.data)) {
            // 数组数据（重仓股格式）
            tableHTML = this.renderArrayTable(this.state.data);
        } else if (typeof this.state.data === 'object') {
            // 对象数据（资产配置/行业分布格式）
            tableHTML = this.renderObjectTable(this.state.data);
        }
        
        contentDiv.innerHTML = tableHTML;
    }
    
    /**
     * 渲染数组表格（重仓股格式）
     */
    renderArrayTable(data) {
        if (!this.columns || this.columns.length === 0) {
            return '<div class="empty-state"><p>未配置表格列</p></div>';
        }
        
        let html = `
            <div class="table-responsive">
                <table class="realtime-data-table">
                    <thead>
                        <tr>
                            ${this.columns.map(col => `
                                <th class="${col.class || ''}" style="${col.style || ''}">${col.title}</th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach((row, index) => {
            html += `<tr class="${index % 2 === 0 ? 'even' : 'odd'}">`;
            this.columns.forEach(col => {
                // 特殊处理 index 字段，使用数组索引
                let value;
                if (col.field === 'index') {
                    value = index;
                } else {
                    value = this.getNestedValue(row, col.field);
                }
                const formattedValue = col.formatter ? col.formatter(value, row, index) : value;
                html += `<td class="${col.class || ''}" style="${col.style || ''}">${formattedValue !== undefined ? formattedValue : '-'}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        return html;
    }
    
    /**
     * 渲染对象表格（资产配置/行业分布格式）
     */
    renderObjectTable(data) {
        let entries = Object.entries(data);
        
        if (entries.length === 0) {
            return '<div class="empty-state"><p>暂无数据</p></div>';
        }
        
        // 应用排序
        if (this.sortState.column === 'proportion') {
            entries.sort((a, b) => {
                const valA = parseFloat(a[1]) || 0;
                const valB = parseFloat(b[1]) || 0;
                return this.sortState.direction === 'asc' ? valA - valB : valB - valA;
            });
        } else if (this.sortState.column === 'name') {
            entries.sort((a, b) => {
                return this.sortState.direction === 'asc' 
                    ? a[0].localeCompare(b[0], 'zh-CN') 
                    : b[0].localeCompare(a[0], 'zh-CN');
            });
        }
        
        // 获取排序指示器
        const getSortIcon = (column) => {
            if (this.sortState.column !== column) {
                return '<span class="sort-icon">⇅</span>';
            }
            return this.sortState.direction === 'asc' 
                ? '<span class="sort-icon active">↑</span>' 
                : '<span class="sort-icon active">↓</span>';
        };
        
        // 使用方括号语法访问全局变量（避免连字符问题）
        const tableRef = `window['${this.containerId}_table']`;
        
        let html = `
            <div class="table-responsive">
                <table class="realtime-data-table">
                    <thead>
                        <tr>
                            <th class="sortable" onclick="${tableRef}.handleSort('name')">
                                类别 ${getSortIcon('name')}
                            </th>
                            <th class="sortable" style="text-align: right;" onclick="${tableRef}.handleSort('proportion')">
                                占比 ${getSortIcon('proportion')}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        entries.forEach(([key, value], index) => {
            const percentage = typeof value === 'number' ? value.toFixed(1) : value;
            html += `
                <tr class="${index % 2 === 0 ? 'even' : 'odd'}">
                    <td>${key}</td>
                    <td style="text-align: right;">
                        <div class="percentage-cell">
                            <span class="percentage-value">${percentage}%</span>
                            <div class="percentage-bar">
                                <div class="percentage-fill" style="width: ${Math.min(percentage, 100)}%"></div>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        return html;
    }
    
    /**
     * 处理排序点击
     */
    handleSort(column) {
        if (this.sortState.column === column) {
            // 切换排序方向
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            // 新列，默认降序（占比高的在前）
            this.sortState.column = column;
            this.sortState.direction = column === 'proportion' ? 'desc' : 'asc';
        }
        
        console.log(`[RealtimeDataTable] Sort by ${column} ${this.sortState.direction}`);
        
        // 重新渲染
        this.render();
    }
    
    /**
     * 获取嵌套对象值
     */
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }
    
    /**
     * 格式化时间
     */
    formatTime(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        
        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
        return date.toLocaleDateString();
    }
    
    /**
     * 刷新数据
     */
    refresh() {
        this.fetchData();
    }
    
    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }
        
        this.autoRefreshTimer = setInterval(() => {
            this.fetchData();
        }, this.refreshInterval);
        
        console.log(`[RealtimeDataTable] ${this.title} auto-refresh started (${this.refreshInterval / 1000}s)`);
    }
    
    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
            console.log(`[RealtimeDataTable] ${this.title} auto-refresh stopped`);
        }
    }
    
    /**
     * 清除缓存
     */
    clearCache() {
        try {
            localStorage.removeItem(this.cacheKey);
            console.log(`[RealtimeDataTable] ${this.title} cache cleared`);
        } catch (e) {
            console.warn(`[RealtimeDataTable] Cache clear failed:`, e);
        }
    }
    
    /**
     * 销毁组件
     */
    destroy() {
        this.stopAutoRefresh();
        if (this.container) {
            this.container.innerHTML = '';
        }
        delete window[`${this.containerId}_table`];
    }
}

/**
 * 初始化资产配置表格
 */
function initAssetAllocationTable(containerId, data, options = {}) {
    return new RealtimeDataTable(containerId, {
        title: '资产配置',
        dataType: 'asset',
        ...options,
        autoRefresh: false // 资产配置通常不需要自动刷新
    });
}

/**
 * 初始化行业分布表格
 */
function initIndustryDistributionTable(containerId, data, options = {}) {
    return new RealtimeDataTable(containerId, {
        title: '行业分布',
        dataType: 'industry',
        ...options,
        autoRefresh: false // 行业分布通常不需要自动刷新
    });
}

/**
 * 初始化重仓股表格
 */
function initHeavyweightStocksTable(containerId, fundCodes, options = {}) {
    const table = new RealtimeDataTable(containerId, {
        title: '重仓股 TOP10',
        dataType: 'heavyweight',
        fundCodes: Array.isArray(fundCodes) ? fundCodes : [fundCodes],
        columns: [
            { title: '排名', field: 'rank', class: 'text-center', style: 'width: 60px;' },
            { title: '股票名称', field: 'name', class: 'stock-name' },
            { title: '股票代码', field: 'code', class: 'stock-code text-center' },
            { title: '持仓占比', field: 'ratio', class: 'text-right', formatter: (v) => `${v}%` },
            { title: '持仓市值', field: 'marketValue', class: 'text-right', formatter: (v) => `${v}万` },
            { title: '较上期变化', field: 'change', class: 'text-right', formatter: (v) => {
                const change = parseFloat(v);
                const className = change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
                const sign = change > 0 ? '+' : '';
                return `<span class="${className}">${sign}${v}%</span>`;
            }}
        ],
        fetchUrl: `/api/fund/${Array.isArray(fundCodes) ? fundCodes[0] : fundCodes}/heavyweight-stocks`,
        ...options
    });
    
    // 手动设置数据（因为API返回格式可能不同）
    if (options.initialData) {
        table.state.data = options.initialData;
        table.render();
    }
    
    return table;
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        RealtimeDataTable, 
        initAssetAllocationTable, 
        initIndustryDistributionTable,
        initHeavyweightStocksTable 
    };
}

// 浏览器环境：挂载到 window 对象
if (typeof window !== 'undefined') {
    window.RealtimeDataTable = RealtimeDataTable;
    window.initAssetAllocationTable = initAssetAllocationTable;
    window.initIndustryDistributionTable = initIndustryDistributionTable;
    window.initHeavyweightStocksTable = initHeavyweightStocksTable;
}
