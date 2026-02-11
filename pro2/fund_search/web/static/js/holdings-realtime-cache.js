/**
 * 持仓页面实时数据缓存管理器
 * 
 * 数据分级策略：
 * 1. 实时数据（日涨跌幅）：每30秒刷新一次
 * 2. 准实时数据（昨日盈亏）：页面加载时获取，不主动刷新
 * 3. 低频指标（年化收益、夏普等）：页面加载时获取，缓存
 */

class HoldingsCacheManager {
    constructor(options = {}) {
        this.options = {
            realtimeRefreshInterval: 30000,  // 实时数据刷新间隔：30秒
            apiBaseUrl: '/api',
            userId: 'default_user',
            ...options
        };
        
        this.data = {
            holdings: [],           // 完整持仓数据
            realtime: new Map(),    // 实时数据缓存 (fundCode -> data)
            lastFullUpdate: null    // 上次完整更新时间
        };
        
        this.timers = {
            realtimeRefresh: null
        };
        
        this.listeners = new Map();  // 事件监听器
        this.isLoading = false;
    }
    
    /**
     * 初始化并加载完整数据
     */
    async init() {
        console.log('[HoldingsCache] 初始化缓存管理器');
        await this.loadFullData();
        this.startRealtimeRefresh();
    }
    
    /**
     * 加载完整持仓数据（包含所有级别的数据）
     */
    async loadFullData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.emit('loading', { type: 'full' });
        
        try {
            const response = await fetch(
                `${this.options.apiBaseUrl}/my-holdings/combined?user_id=${this.options.userId}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.data.holdings = result.data;
                this.data.lastFullUpdate = new Date();
                
                // 更新实时数据缓存
                result.data.forEach(holding => {
                    this.data.realtime.set(holding.fund_code, {
                        today_return: holding.today_return,
                        current_nav: holding.current_nav,
                        current_market_value: holding.current_market_value,
                        today_profit: holding.today_profit,
                        timestamp: Date.now()
                    });
                });
                
                this.emit('dataUpdated', { 
                    type: 'full', 
                    data: result.data,
                    meta: result.meta 
                });
                
                console.log('[HoldingsCache] 完整数据加载完成', result.meta);
            } else {
                throw new Error(result.error || '加载数据失败');
            }
        } catch (error) {
            console.error('[HoldingsCache] 加载完整数据失败:', error);
            this.emit('error', { type: 'full', error });
        } finally {
            this.isLoading = false;
        }
    }
    
    /**
     * 启动实时数据定时刷新
     */
    startRealtimeRefresh() {
        // 清除已有的定时器
        this.stopRealtimeRefresh();
        
        console.log('[HoldingsCache] 启动实时数据刷新');
        
        // 立即执行一次
        this.refreshRealtimeData();
        
        // 设置定时器
        this.timers.realtimeRefresh = setInterval(() => {
            this.refreshRealtimeData();
        }, this.options.realtimeRefreshInterval);
    }
    
    /**
     * 停止实时数据刷新
     */
    stopRealtimeRefresh() {
        if (this.timers.realtimeRefresh) {
            clearInterval(this.timers.realtimeRefresh);
            this.timers.realtimeRefresh = null;
            console.log('[HoldingsCache] 停止实时数据刷新');
        }
    }
    
    /**
     * 刷新实时数据（只获取日涨跌幅等实时字段）
     */
    async refreshRealtimeData() {
        if (this.data.holdings.length === 0) return;
        
        try {
            const fundCodes = this.data.holdings.map(h => h.fund_code).join(',');
            
            const response = await fetch(
                `${this.options.apiBaseUrl}/my-holdings/realtime?user_id=${this.options.userId}&codes=${fundCodes}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success && result.data) {
                // 更新实时数据缓存
                result.data.forEach(rt => {
                    this.data.realtime.set(rt.fund_code, {
                        ...rt,
                        timestamp: Date.now()
                    });
                    
                    // 更新完整数据中的对应字段
                    const holding = this.data.holdings.find(h => h.fund_code === rt.fund_code);
                    if (holding) {
                        holding.today_return = rt.today_return;
                        holding.current_nav = rt.current_nav;
                        holding.current_market_value = rt.current_market_value;
                        holding.today_profit = rt.today_profit;
                    }
                });
                
                this.emit('dataUpdated', { 
                    type: 'realtime', 
                    data: result.data,
                    timestamp: result.timestamp 
                });
                
                console.log('[HoldingsCache] 实时数据刷新完成', result.timestamp);
            }
        } catch (error) {
            console.error('[HoldingsCache] 刷新实时数据失败:', error);
            // 不触发error事件，避免频繁报错
        }
    }
    
    /**
     * 获取当前持仓数据
     */
    getHoldings() {
        return [...this.data.holdings];
    }
    
    /**
     * 获取单只基金的实时数据
     */
    getRealtimeData(fundCode) {
        return this.data.realtime.get(fundCode);
    }
    
    /**
     * 手动刷新（供用户点击刷新按钮使用）
     */
    async manualRefresh() {
        console.log('[HoldingsCache] 手动刷新数据');
        this.stopRealtimeRefresh();
        await this.loadFullData();
        this.startRealtimeRefresh();
    }
    
    /**
     * 事件监听
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }
    
    /**
     * 取消事件监听
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }
    
    /**
     * 触发事件
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[HoldingsCache] 事件处理错误:`, error);
                }
            });
        }
    }
    
    /**
     * 销毁管理器
     */
    destroy() {
        this.stopRealtimeRefresh();
        this.listeners.clear();
        this.data.holdings = [];
        this.data.realtime.clear();
    }
}

// 导出全局实例
window.HoldingsCacheManager = HoldingsCacheManager;

/**
 * 持仓表格渲染器
 * 与HoldingsCacheManager配合，实现数据与UI分离
 */
class HoldingsTableRenderer {
    constructor(containerId, cacheManager) {
        this.container = document.getElementById(containerId);
        this.cache = cacheManager;
        
        // 绑定事件
        this.cache.on('dataUpdated', (event) => {
            if (event.type === 'full') {
                this.renderFullTable(event.data);
            } else if (event.type === 'realtime') {
                this.updateRealtimeCells(event.data);
            }
        });
        
        this.cache.on('loading', (event) => {
            if (event.type === 'full') {
                this.showLoading();
            }
        });
    }
    
    /**
     * 显示加载状态
     */
    showLoading() {
        if (this.container) {
            this.container.innerHTML = '<tr><td colspan="12" class="text-center py-4">加载中...</td></tr>';
        }
    }
    
    /**
     * 渲染完整表格
     */
    renderFullTable(holdings) {
        if (!this.container || !holdings || holdings.length === 0) return;
        
        const html = holdings.map(holding => this.renderRow(holding)).join('');
        this.container.innerHTML = html;
    }
    
    /**
     * 渲染单行
     */
    renderRow(holding) {
        const todayReturnClass = this.getReturnClass(holding.today_return);
        const holdingProfitClass = this.getReturnClass(holding.holding_profit_rate);
        
        return `
            <tr data-fund-code="${holding.fund_code}">
                <td>${holding.fund_code}</td>
                <td>${holding.fund_name}</td>
                <td class="realtime-cell today-return ${todayReturnClass}" data-field="today_return">
                    ${this.formatPercent(holding.today_return)}
                </td>
                <td>${this.formatPercent(holding.yesterday_return)}</td>
                <td>${holding.holding_amount?.toFixed(2) || '-'}</td>
                <td class="realtime-cell current-market-value" data-field="current_market_value">
                    ${holding.current_market_value?.toFixed(2) || '-'}
                </td>
                <td class="realtime-cell today-profit ${todayReturnClass}" data-field="today_profit">
                    ${holding.today_profit?.toFixed(2) || '-'}
                </td>
                <td class="${holdingProfitClass}">
                    ${this.formatPercent(holding.holding_profit_rate)}
                </td>
                <td>${this.formatPercent(holding.annualized_return)}</td>
                <td>${this.formatPercent(holding.max_drawdown)}</td>
                <td>${holding.sharpe_ratio?.toFixed(4) || '-'}</td>
                <td>${holding.composite_score?.toFixed(4) || '-'}</td>
            </tr>
        `;
    }
    
    /**
     * 更新实时数据单元格（局部更新）
     */
    updateRealtimeCells(realtimeData) {
        if (!this.container) return;
        
        realtimeData.forEach(rt => {
            const row = this.container.querySelector(`tr[data-fund-code="${rt.fund_code}"]`);
            if (!row) return;
            
            // 更新日涨跌幅
            const todayReturnCell = row.querySelector('[data-field="today_return"]');
            if (todayReturnCell) {
                todayReturnCell.textContent = this.formatPercent(rt.today_return);
                todayReturnCell.className = `realtime-cell today-return ${this.getReturnClass(rt.today_return)}`;
            }
            
            // 更新当前市值
            const marketValueCell = row.querySelector('[data-field="current_market_value"]');
            if (marketValueCell) {
                marketValueCell.textContent = rt.current_market_value?.toFixed(2) || '-';
            }
            
            // 更新今日盈亏
            const todayProfitCell = row.querySelector('[data-field="today_profit"]');
            if (todayProfitCell) {
                todayProfitCell.textContent = rt.today_profit?.toFixed(2) || '-';
                todayProfitCell.className = `realtime-cell today-profit ${this.getReturnClass(rt.today_profit)}`;
            }
        });
    }
    
    /**
     * 格式化百分比
     */
    formatPercent(value) {
        if (value === null || value === undefined) return '-';
        const sign = value > 0 ? '+' : '';
        return `${sign}${value.toFixed(2)}%`;
    }
    
    /**
     * 获取收益样式类
     */
    getReturnClass(value) {
        if (value === null || value === undefined) return '';
        if (value > 0) return 'text-success';
        if (value < 0) return 'text-danger';
        return 'text-muted';
    }
}

window.HoldingsTableRenderer = HoldingsTableRenderer;

/**
 * 使用示例：
 * 
 * // 初始化
 * const cacheManager = new HoldingsCacheManager({
 *     userId: 'default_user',
 *     realtimeRefreshInterval: 30000  // 30秒
 * });
 * 
 * const tableRenderer = new HoldingsTableRenderer('holdings-table-body', cacheManager);
 * 
 * // 加载数据
 * cacheManager.init();
 * 
 * // 手动刷新按钮
 * document.getElementById('refresh-btn').addEventListener('click', () => {
 *     cacheManager.manualRefresh();
 * });
 * 
 * // 页面卸载时清理
 * window.addEventListener('beforeunload', () => {
 *     cacheManager.destroy();
 * });
 */
