/**
 * 重仓股数据展示模块
 * 提供实时数据获取、缓存管理和错误处理功能
 */

class HeavyweightStocksDisplay {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.fundCode = options.fundCode || '';
        this.cacheDuration = options.cacheDuration || 5 * 60 * 1000; // 默认5分钟缓存
        this.autoRefresh = options.autoRefresh || false;
        this.refreshInterval = options.refreshInterval || 5 * 60 * 1000; // 5分钟自动刷新
        this.autoRefreshTimer = null;
        
        // 状态管理
        this.state = {
            loading: false,
            error: null,
            data: null,
            lastUpdated: null,
            source: null
        };
        
        // 缓存键
        this.cacheKey = `heavyweight_stocks_${this.fundCode}`;
        
        this.init();
    }
    
    /**
     * 初始化组件
     */
    init() {
        if (!this.container) {
            console.error(`Container #${this.containerId} not found`);
            return;
        }
        
        this.renderSkeleton();
        
        // 尝试从缓存加载数据
        if (this.loadFromCache()) {
            this.render();
        } else {
            // 没有缓存，立即获取数据
            this.fetchData();
        }
        
        // 设置自动刷新
        if (this.autoRefresh) {
            this.startAutoRefresh();
        }
    }
    
    /**
     * 渲染骨架屏（加载状态）
     */
    renderSkeleton() {
        const skeletonHTML = `
            <div class="heavyweight-stocks-container">
                <div class="stocks-header">
                    <h3>重仓股 TOP10</h3>
                    <div class="stocks-actions">
                        <span class="last-updated">--</span>
                        <button class="refresh-btn" onclick="heavyweightStocksDisplay.refreshData()">
                            <i class="refresh-icon">↻</i> 刷新
                        </button>
                    </div>
                </div>
                <div class="stocks-loading" id="${this.containerId}-loading">
                    <div class="loading-spinner"></div>
                    <p>正在加载重仓股数据...</p>
                </div>
                <div class="stocks-error" id="${this.containerId}-error" style="display: none;">
                    <div class="error-icon">⚠️</div>
                    <p class="error-message"></p>
                    <button class="retry-btn" onclick="heavyweightStocksDisplay.retry()">重试</button>
                </div>
                <div class="stocks-content" id="${this.containerId}-content" style="display: none;">
                    <div style="overflow-x: auto;">
                        <table class="stocks-table">
                            <thead>
                                <tr>
                                    <th>股票名称</th>
                                    <th>代码</th>
                                    <th style="text-align: right;">持仓占比</th>
                                    <th style="text-align: right;">市值(万)</th>
                                    <th style="text-align: right;">涨跌幅</th>
                                </tr>
                            </thead>
                            <tbody id="${this.containerId}-tbody">
                            </tbody>
                        </table>
                    </div>
                    <div class="data-source">
                        数据来源: <span class="source-name">--</span>
                    </div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = skeletonHTML;
        
        // 绑定刷新按钮事件
        const refreshBtn = this.container.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }
    }
    
    /**
     * 从缓存加载数据
     */
    loadFromCache() {
        try {
            const cached = localStorage.getItem(this.cacheKey);
            if (!cached) return false;
            
            const { data, timestamp, source } = JSON.parse(cached);
            const age = Date.now() - timestamp;
            
            // 检查缓存是否过期
            if (age > this.cacheDuration) {
                localStorage.removeItem(this.cacheKey);
                return false;
            }
            
            this.state.data = data;
            this.state.lastUpdated = new Date(timestamp);
            this.state.source = source;
            
            console.log(`[HeavyweightStocks] Loaded from cache for ${this.fundCode}`);
            return true;
        } catch (e) {
            console.error('[HeavyweightStocks] Cache load error:', e);
            return false;
        }
    }
    
    /**
     * 保存数据到缓存
     */
    saveToCache() {
        try {
            const cacheData = {
                data: this.state.data,
                timestamp: Date.now(),
                source: this.state.source
            };
            localStorage.setItem(this.cacheKey, JSON.stringify(cacheData));
        } catch (e) {
            console.error('[HeavyweightStocks] Cache save error:', e);
        }
    }
    
    /**
     * 清除缓存
     */
    clearCache() {
        localStorage.removeItem(this.cacheKey);
        console.log(`[HeavyweightStocks] Cache cleared for ${this.fundCode}`);
    }
    
    /**
     * 获取数据（主方法）
     */
    async fetchData(forceRefresh = false) {
        if (this.state.loading) return;
        
        this.state.loading = true;
        this.state.error = null;
        this.updateLoadingState(true);
        
        try {
            const url = `/api/fund/${this.fundCode}/heavyweight-stocks${forceRefresh ? '?refresh=true' : ''}`;
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || '获取数据失败');
            }
            
            // 更新状态
            this.state.data = result.data;
            this.state.source = result.source;
            this.state.lastUpdated = new Date(result.timestamp);
            
            // 保存到缓存
            this.saveToCache();
            
            // 渲染数据
            this.render();
            
            console.log(`[HeavyweightStocks] Data fetched successfully from ${result.source}`);
            
        } catch (error) {
            console.error('[HeavyweightStocks] Fetch error:', error);
            this.state.error = error.message;
            this.renderError();
        } finally {
            this.state.loading = false;
            this.updateLoadingState(false);
        }
    }
    
    /**
     * 刷新数据
     */
    refreshData() {
        this.clearCache();
        this.fetchData(true);
    }
    
    /**
     * 重试
     */
    retry() {
        this.fetchData();
    }
    
    /**
     * 更新加载状态UI
     */
    updateLoadingState(loading) {
        const loadingEl = document.getElementById(`${this.containerId}-loading`);
        const contentEl = document.getElementById(`${this.containerId}-content`);
        const errorEl = document.getElementById(`${this.containerId}-error`);
        
        if (loadingEl) loadingEl.style.display = loading ? 'block' : 'none';
        if (contentEl) contentEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
    }
    
    /**
     * 渲染数据
     */
    render() {
        const loadingEl = document.getElementById(`${this.containerId}-loading`);
        const contentEl = document.getElementById(`${this.containerId}-content`);
        const errorEl = document.getElementById(`${this.containerId}-error`);
        const tbodyEl = document.getElementById(`${this.containerId}-tbody`);
        
        if (loadingEl) loadingEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        if (contentEl) contentEl.style.display = 'block';
        
        // 更新时间
        const lastUpdatedEl = this.container.querySelector('.last-updated');
        if (lastUpdatedEl && this.state.lastUpdated) {
            const timeStr = this.formatTime(this.state.lastUpdated);
            lastUpdatedEl.textContent = `更新于: ${timeStr}`;
        }
        
        // 更新数据源
        const sourceEl = this.container.querySelector('.source-name');
        if (sourceEl && this.state.source) {
            const sourceNames = {
                'akshare': 'akshare',
                'eastmoney': '东方财富',
                'sina': '新浪财经',
                'cache': '本地缓存'
            };
            sourceEl.textContent = sourceNames[this.state.source] || this.state.source;
        }
        
        // 渲染表格
        if (tbodyEl && this.state.data) {
            if (this.state.data.length === 0) {
                tbodyEl.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 20px; color: #999;">
                            暂无重仓股数据
                        </td>
                    </tr>
                `;
            } else {
                tbodyEl.innerHTML = this.state.data.map(stock => `
                    <tr>
                        <td>${this.escapeHtml(stock.name)}</td>
                        <td style="font-family: monospace;">${this.escapeHtml(stock.code)}</td>
                        <td style="text-align: right;">${stock.holding_ratio}</td>
                        <td style="text-align: right;">${stock.market_value}</td>
                        <td style="text-align: right;" class="${this.getChangeClass(stock.change_percent)}">
                            ${stock.change_percent}
                        </td>
                    </tr>
                `).join('');
            }
        }
    }
    
    /**
     * 渲染错误状态
     */
    renderError() {
        const loadingEl = document.getElementById(`${this.containerId}-loading`);
        const contentEl = document.getElementById(`${this.containerId}-content`);
        const errorEl = document.getElementById(`${this.containerId}-error`);
        const errorMessageEl = errorEl?.querySelector('.error-message');
        
        if (loadingEl) loadingEl.style.display = 'none';
        if (contentEl) contentEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'block';
        
        if (errorMessageEl && this.state.error) {
            errorMessageEl.textContent = this.state.error;
        }
    }
    
    /**
     * 获取涨跌幅样式类
     */
    getChangeClass(changePercent) {
        if (!changePercent || changePercent === '--') return '';
        const value = parseFloat(changePercent.replace('%', ''));
        if (value > 0) return 'positive-change';
        if (value < 0) return 'negative-change';
        return '';
    }
    
    /**
     * 格式化时间
     */
    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        
        // 小于1分钟
        if (diff < 60000) {
            return '刚刚';
        }
        // 小于1小时
        if (diff < 3600000) {
            return `${Math.floor(diff / 60000)}分钟前`;
        }
        // 小于24小时
        if (diff < 86400000) {
            return `${Math.floor(diff / 3600000)}小时前`;
        }
        
        return date.toLocaleString('zh-CN');
    }
    
    /**
     * HTML转义
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 启动自动刷新
     */
    startAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
        }
        
        this.autoRefreshTimer = setInterval(() => {
            console.log('[HeavyweightStocks] Auto refreshing...');
            this.fetchData();
        }, this.refreshInterval);
    }
    
    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
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
    }
}

// 全局实例管理
const heavyweightStocksInstances = new Map();

/**
 * 初始化重仓股显示
 */
function initHeavyweightStocks(containerId, fundCode, options = {}) {
    // 如果已存在实例，先销毁
    if (heavyweightStocksInstances.has(containerId)) {
        heavyweightStocksInstances.get(containerId).destroy();
    }
    
    // 创建新实例
    const instance = new HeavyweightStocksDisplay(containerId, {
        fundCode,
        ...options
    });
    
    heavyweightStocksInstances.set(containerId, instance);
    return instance;
}

/**
 * 获取实例
 */
function getHeavyweightStocksInstance(containerId) {
    return heavyweightStocksInstances.get(containerId);
}

/**
 * 清除所有缓存
 */
function clearAllCache() {
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('heavyweight_stocks_')) {
            localStorage.removeItem(key);
        }
    });
    console.log('[HeavyweightStocks] All cache cleared');
}

/**
 * 格式化日期时间
 */
function formatDateTime(date) {
    if (!date) return '--';
    const d = new Date(date);
    return d.toLocaleString('zh-CN');
}

/**
 * 格式化数字
 */
function formatNumber(num, decimals = 2) {
    if (num === undefined || num === null) return '--';
    return parseFloat(num).toFixed(decimals);
}

/**
 * 格式化百分比
 */
function formatPercentage(num) {
    if (num === undefined || num === null) return '--';
    const val = parseFloat(num);
    const sign = val > 0 ? '+' : '';
    return `${sign}${val.toFixed(2)}%`;
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HeavyweightStocksDisplay, initHeavyweightStocks, clearAllCache, formatDateTime, formatNumber, formatPercentage };
}

// 浏览器环境：挂载到 window 对象
if (typeof window !== 'undefined') {
    window.HeavyweightStocksDisplay = HeavyweightStocksDisplay;
    window.initHeavyweightStocks = initHeavyweightStocks;
    window.clearAllCache = clearAllCache;
    window.formatDateTime = formatDateTime;
    window.formatNumber = formatNumber;
    window.formatPercentage = formatPercentage;
    window.heavyweightStocksDisplay = {
        HeavyweightStocksDisplay,
        initHeavyweightStocks,
        utils: {
            clearAllCache,
            formatDateTime,
            formatNumber,
            formatPercentage
        }
    };
}
