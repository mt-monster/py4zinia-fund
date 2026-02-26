/**
 * 图表工具箱模块
 * 提供下载图片、全屏切换、数据查看、刷新按钮功能
 */

class ChartToolbox {
    constructor(chartInstance, containerId, options = {}) {
        this.chart = chartInstance;
        this.containerId = containerId;
        this.container = document.getElementById(containerId)?.parentElement;
        this.options = {
            allowDownload: true,
            allowFullscreen: true,
            allowDataView: true,
            allowRefresh: true,
            ...options
        };
        this.originalParent = null;
        this.isFullscreen = false;
    }

    /**
     * 初始化工具箱
     */
    init() {
        if (!this.container) {
            console.error(`❌ 找不到图表容器: ${this.containerId}`);
            return;
        }
        
        this.renderToolbox();
        this.attachEvents();
    }

    /**
     * 渲染工具箱HTML
     */
    renderToolbox() {
        const toolbox = document.createElement('div');
        toolbox.className = 'chart-toolbox';
        toolbox.innerHTML = `
            ${this.options.allowDownload ? `
                <button class="toolbox-btn" data-action="download" title="下载图片">
                    <i class="bi bi-download"></i>
                </button>
            ` : ''}
            ${this.options.allowFullscreen ? `
                <button class="toolbox-btn" data-action="fullscreen" title="全屏查看">
                    <i class="bi bi-fullscreen"></i>
                </button>
            ` : ''}
            ${this.options.allowDataView ? `
                <button class="toolbox-btn" data-action="dataview" title="查看数据">
                    <i class="bi bi-table"></i>
                </button>
            ` : ''}
            ${this.options.allowRefresh ? `
                <button class="toolbox-btn" data-action="refresh" title="刷新">
                    <i class="bi bi-arrow-clockwise"></i>
                </button>
            ` : ''}
        `;
        
        // 插入到chart-header
        const header = this.container.querySelector('.chart-header');
        if (header) {
            const existingToolbar = header.querySelector('.chart-toolbar');
            if (existingToolbar) {
                existingToolbar.prepend(toolbox);
            } else {
                header.insertBefore(toolbox, header.firstChild);
            }
        }
    }

    /**
     * 附加事件监听
     */
    attachEvents() {
        this.container.addEventListener('click', (e) => {
            const btn = e.target.closest('.toolbox-btn');
            if (!btn) return;

            const action = btn.dataset.action;
            switch (action) {
                case 'download':
                    this.downloadImage();
                    break;
                case 'fullscreen':
                    this.toggleFullscreen(btn);
                    break;
                case 'dataview':
                    this.showDataView();
                    break;
                case 'refresh':
                    this.refresh();
                    break;
            }
        });
    }

    /**
     * 下载图片
     */
    downloadImage() {
        if (!this.chart) return;
        
        const canvas = this.chart.canvas;
        const url = canvas.toDataURL('image/png', 1.0);
        
        const link = document.createElement('a');
        link.download = `${this.containerId}_${new Date().toISOString().slice(0, 10)}.png`;
        link.href = url;
        link.click();
        
        this.showToast('图片已下载');
    }

    /**
     * 切换全屏
     */
    toggleFullscreen(btn) {
        if (this.isFullscreen) {
            this.exitFullscreen(btn);
        } else {
            this.enterFullscreen(btn);
        }
    }

    /**
     * 进入全屏
     */
    enterFullscreen(btn) {
        this.originalParent = this.container.parentElement;
        
        // 创建全屏容器
        const fullscreenContainer = document.createElement('div');
        fullscreenContainer.className = 'chart-fullscreen-overlay';
        fullscreenContainer.innerHTML = `
            <div class="fullscreen-header">
                <h3>${this.container.querySelector('.chart-title')?.textContent || '图表'}</h3>
                <button class="exit-fullscreen-btn">
                    <i class="bi bi-fullscreen-exit"></i> 退出全屏
                </button>
            </div>
            <div class="fullscreen-body"></div>
        `;
        
        document.body.appendChild(fullscreenContainer);
        fullscreenContainer.querySelector('.fullscreen-body').appendChild(this.container);
        
        // 更新图表尺寸
        this.resizeChart();
        
        // 更新按钮图标
        btn.innerHTML = '<i class="bi bi-fullscreen-exit"></i>';
        btn.title = '退出全屏';
        
        this.isFullscreen = true;
        
        // 退出按钮事件
        fullscreenContainer.querySelector('.exit-fullscreen-btn').addEventListener('click', () => {
            this.exitFullscreen(btn);
        });
        
        // ESC键退出
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.exitFullscreen(btn);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    /**
     * 退出全屏
     */
    exitFullscreen(btn) {
        const overlay = document.querySelector('.chart-fullscreen-overlay');
        if (overlay && this.originalParent) {
            this.originalParent.appendChild(this.container);
            overlay.remove();
        }
        
        // 恢复图表尺寸
        this.resizeChart();
        
        // 更新按钮图标
        btn.innerHTML = '<i class="bi bi-fullscreen"></i>';
        btn.title = '全屏查看';
        
        this.isFullscreen = false;
    }

    /**
     * 调整图表尺寸
     */
    resizeChart() {
        setTimeout(() => {
            if (this.chart) {
                this.chart.resize();
            }
        }, 100);
    }

    /**
     * 显示数据视图
     */
    showDataView() {
        if (!this.chart || !this.chart.data) return;
        
        const modal = document.createElement('div');
        modal.className = 'data-view-modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="this.parentElement.remove()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>数据视图</h3>
                    <button class="modal-close" onclick="this.closest('.data-view-modal').remove()">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                <div class="modal-body">
                    ${this.buildDataTable()}
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.data-view-modal').remove()">关闭</button>
                    <button class="btn btn-primary" onclick="chartToolboxManager.exportCSV('${this.containerId}')">
                        <i class="bi bi-download"></i> 导出CSV
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        this.modalElement = modal;
    }

    /**
     * 构建数据表格
     */
    buildDataTable() {
        const data = this.chart.data;
        if (!data.labels || !data.datasets) return '<p>无数据</p>';
        
        let html = '<div class="data-table-wrapper"><table class="data-table">';
        
        // 表头
        html += '<thead><tr><th>标签</th>';
        data.datasets.forEach(ds => {
            html += `<th>${ds.label || '数据'}</th>`;
        });
        html += '</tr></thead>';
        
        // 表体
        html += '<tbody>';
        const maxRows = Math.min(data.labels.length, 100); // 最多显示100行
        for (let i = 0; i < maxRows; i++) {
            html += `<tr><td>${data.labels[i]}</td>`;
            data.datasets.forEach(ds => {
                const value = ds.data[i];
                const displayValue = typeof value === 'number' ? value.toFixed(4) : (value || '-');
                html += `<td>${displayValue}</td>`;
            });
            html += '</tr>';
        }
        if (data.labels.length > maxRows) {
            html += `<tr><td colspan="${data.datasets.length + 1}" class="more-data">
                ... 还有 ${data.labels.length - maxRows} 行数据
            </td></tr>`;
        }
        html += '</tbody></table></div>';
        
        return html;
    }

    /**
     * 刷新图表
     */
    refresh() {
        const btn = this.container.querySelector('[data-action="refresh"]');
        if (btn) {
            btn.classList.add('rotating');
            setTimeout(() => btn.classList.remove('rotating'), 1000);
        }
        
        // 触发自定义刷新事件
        const event = new CustomEvent('chartRefresh', {
            detail: { chartId: this.containerId }
        });
        document.dispatchEvent(event);
        
        this.showToast('正在刷新...');
    }

    /**
     * 显示提示
     */
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'chart-toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 2000);
    }
}

/**
 * 图表工具箱管理器
 */
class ChartToolboxManager {
    constructor() {
        this.toolboxes = new Map();
    }

    /**
     * 为图表添加工具箱
     */
    addToolbox(chartInstance, containerId, options) {
        const toolbox = new ChartToolbox(chartInstance, containerId, options);
        toolbox.init();
        this.toolboxes.set(containerId, toolbox);
        return toolbox;
    }

    /**
     * 获取工具箱实例
     */
    getToolbox(containerId) {
        return this.toolboxes.get(containerId);
    }

    /**
     * 导出CSV
     */
    exportCSV(containerId) {
        const toolbox = this.toolboxes.get(containerId);
        if (!toolbox || !toolbox.chart) return;

        const data = toolbox.chart.data;
        if (!data.labels || !data.datasets) return;

        // 构建CSV内容
        let csv = '标签,' + data.datasets.map(ds => ds.label || '数据').join(',') + '\n';
        
        data.labels.forEach((label, i) => {
            const row = [label];
            data.datasets.forEach(ds => {
                row.push(ds.data[i] ?? '');
            });
            csv += row.join(',') + '\n';
        });

        // 下载
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${containerId}_data_${new Date().toISOString().slice(0, 10)}.csv`;
        link.click();
        
        toolbox.showToast('CSV已导出');
    }
}

// 创建全局实例
const chartToolboxManager = new ChartToolboxManager();

// 添加样式
const chartToolboxStyle = document.createElement('style');
chartToolboxStyle.textContent = `
    .chart-toolbox {
        display: flex;
        gap: 0.25rem;
        margin-right: auto;
    }
    
    .chart-toolbox .toolbox-btn {
        width: 28px;
        height: 28px;
        border: none;
        background: transparent;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--text-secondary);
        transition: all 0.2s;
    }
    
    .chart-toolbox .toolbox-btn:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }
    
    .chart-toolbox .toolbox-btn.rotating i {
        animation: rotate 1s linear;
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    /* 全屏样式 */
    .chart-fullscreen-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.9);
        z-index: 9999;
        display: flex;
        flex-direction: column;
    }
    
    .fullscreen-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 2rem;
        background: rgba(0,0,0,0.5);
        color: white;
    }
    
    .fullscreen-header h3 {
        margin: 0;
    }
    
    .exit-fullscreen-btn {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.3);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
    }
    
    .fullscreen-body {
        flex: 1;
        padding: 2rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .fullscreen-body .chart-wrapper {
        width: 100%;
        height: 100%;
        max-width: 1200px;
    }
    
    .fullscreen-body .chart-body {
        height: calc(100% - 50px);
    }
    
    /* 数据视图模态框 */
    .data-view-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 10000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .data-view-modal .modal-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
    }
    
    .data-view-modal .modal-content {
        position: relative;
        background: white;
        border-radius: 8px;
        width: 90%;
        max-width: 800px;
        max-height: 80vh;
        display: flex;
        flex-direction: column;
    }
    
    .data-view-modal .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .data-view-modal .modal-header h3 {
        margin: 0;
    }
    
    .data-view-modal .modal-close {
        background: none;
        border: none;
        font-size: 1.25rem;
        cursor: pointer;
        color: #6b7280;
    }
    
    .data-view-modal .modal-body {
        flex: 1;
        overflow: auto;
        padding: 1rem;
    }
    
    .data-view-modal .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        padding: 1rem;
        border-top: 1px solid #e5e7eb;
    }
    
    .data-table-wrapper {
        overflow: auto;
        max-height: 400px;
    }
    
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }
    
    .data-table th,
    .data-table td {
        padding: 0.5rem;
        border: 1px solid #e5e7eb;
        text-align: left;
    }
    
    .data-table th {
        background: #f9fafb;
        font-weight: 600;
        position: sticky;
        top: 0;
    }
    
    .data-table tr:hover {
        background: #f3f4f6;
    }
    
    .data-table .more-data {
        text-align: center;
        color: #6b7280;
        font-style: italic;
    }
    
    /* Toast提示 */
    .chart-toast {
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 9999px;
        animation: slideUp 0.3s ease;
        z-index: 10001;
    }
    
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(100%); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
`;
document.head.appendChild(chartToolboxStyle);

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChartToolbox, ChartToolboxManager };
}
