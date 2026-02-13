/**
 * 图表错误处理模块
 * 提供统一的图表错误提示和重试机制
 */

const ChartErrorHandler = {
    // 显示图表错误
    showChartError: function(container, message, retryCallback) {
        const errorHtml = `
            <div class="chart-error-wrapper" style="padding: 40px; text-align: center;">
                <i class="bi bi-exclamation-triangle-fill" style="font-size: 3rem; color: #dc3545; margin-bottom: 20px; display: block;"></i>
                <h4 style="color: #6c757d; margin-bottom: 15px;">${message || '图表加载失败'}</h4>
                <p style="color: #adb5bd; margin-bottom: 20px;">请检查网络连接后重试</p>
                ${retryCallback ? `
                <button onclick="ChartErrorHandler.retry()" class="btn btn-primary btn-sm">
                    <i class="bi bi-arrow-clockwise"></i> 重新加载
                </button>
                ` : ''}
            </div>
        `;
        
        if (container && container.innerHTML !== undefined) {
            container.innerHTML = errorHtml;
        }
        
        // 存储重试回调
        if (retryCallback) {
            this._retryCallback = retryCallback;
        }
        
        return errorHtml;
    },
    
    // 重试加载
    retry: function() {
        if (this._retryCallback && typeof this._retryCallback === 'function') {
            this._retryCallback();
        }
    },
    
    // 显示空数据提示
    showEmptyData: function(container, message) {
        const emptyHtml = `
            <div class="chart-empty-wrapper" style="padding: 40px; text-align: center;">
                <i class="bi bi-inbox" style="font-size: 3rem; color: #6c757d; margin-bottom: 20px; display: block;"></i>
                <h4 style="color: #6c757d; margin-bottom: 15px;">${message || '暂无数据'}</h4>
                <p style="color: #adb5bd;">请选择更多基金进行分析</p>
            </div>
        `;
        
        if (container && container.innerHTML !== undefined) {
            container.innerHTML = emptyHtml;
        }
        
        return emptyHtml;
    },
    
    // 显示加载状态
    showLoading: function(container, message) {
        const loadingHtml = `
            <div class="chart-loading-wrapper" style="padding: 40px; text-align: center;">
                <div class="spinner-border text-primary" style="width: 3rem; height: 3rem; margin-bottom: 1rem;" role="status">
                    <span class="visually-hidden">加载中...</span>
                </div>
                <div style="color: #333; font-size: 1rem;">${message || '正在加载...'}</div>
            </div>
        `;
        
        if (container && container.innerHTML !== undefined) {
            container.innerHTML = loadingHtml;
        }
        
        return loadingHtml;
    },
    
    // 存储回调
    _retryCallback: null
};

// 导出到全局
window.ChartErrorHandler = ChartErrorHandler;

console.log('✅ chart-error-handler.js 模块加载完成');
