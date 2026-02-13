/**
 * 图表折叠/展开功能模块
 * 提供图表折叠、展开、全屏、下载等功能
 */

class CollapsibleChartManager {
    constructor() {
        this.charts = new Map(); // 存储图表实例
        this.collapsedState = new Map(); // 存储折叠状态
        this.init();
    }

    init() {
        this.injectStyles();
    }

    /**
     * 注入样式
     */
    injectStyles() {
        if (document.getElementById('chart-collapsible-styles')) return;
        
        const link = document.createElement('link');
        link.id = 'chart-collapsible-styles';
        link.rel = 'stylesheet';
        link.href = '/static/css/chart-collapsible.css';
        document.head.appendChild(link);
    }

    /**
     * 创建可折叠图表包装器
     * @param {string} canvasId - Canvas元素ID
     * @param {string} title - 图表标题
     * @param {Object} options - 配置选项
     */
    createCollapsibleWrapper(canvasId, title, options = {}) {
        const wrapper = document.createElement('div');
        wrapper.className = 'chart-wrapper collapsible';
        wrapper.id = `wrapper-${canvasId}`;
        
        if (options.spanFull) {
            wrapper.classList.add('span-full');
        }

        wrapper.innerHTML = `
            <div class="chart-header" onclick="collapsibleChartManager.toggleCollapse('${canvasId}')">
                <div class="chart-header-title">
                    <i class="bi bi-graph-up"></i>
                    <h3>${title}</h3>
                    ${options.badge ? `<span class="chart-status-badge">${options.badge}</span>` : ''}
                </div>
                <span class="chart-counter" id="counter-${canvasId}"></span>
                <div class="chart-toolbar" onclick="event.stopPropagation()">
                    <button class="chart-tool-btn chart-enter-fullscreen" 
                            onclick="collapsibleChartManager.toggleFullscreen('${canvasId}')" 
                            title="全屏查看">
                        <i class="bi bi-fullscreen"></i>
                    </button>
                    <button class="chart-tool-btn chart-exit-fullscreen" 
                            onclick="collapsibleChartManager.toggleFullscreen('${canvasId}')" 
                            title="退出全屏">
                        <i class="bi bi-fullscreen-exit"></i>
                    </button>
                    <div class="chart-menu">
                        <button class="chart-tool-btn" onclick="collapsibleChartManager.toggleMenu('${canvasId}')" title="更多操作">
                            <i class="bi bi-three-dots-vertical"></i>
                        </button>
                        <div class="chart-menu-dropdown" id="menu-${canvasId}">
                            <div class="chart-menu-item" onclick="collapsibleChartManager.downloadChart('${canvasId}')">
                                <i class="bi bi-download"></i>
                                <span>下载图片</span>
                            </div>
                            <div class="chart-menu-item" onclick="collapsibleChartManager.viewData('${canvasId}')">
                                <i class="bi bi-table"></i>
                                <span>查看数据</span>
                            </div>
                            <div class="chart-menu-divider"></div>
                            <div class="chart-menu-item" onclick="collapsibleChartManager.refreshChart('${canvasId}')">
                                <i class="bi bi-arrow-clockwise"></i>
                                <span>刷新数据</span>
                            </div>
                        </div>
                    </div>
                    <button class="chart-tool-btn chart-collapse-btn" id="collapse-btn-${canvasId}" title="折叠/展开">
                        <i class="bi bi-chevron-up"></i>
                    </button>
                </div>
            </div>
            <div class="chart-body" id="body-${canvasId}">
                <canvas id="${canvasId}" class="chart-canvas"></canvas>
            </div>
            <div class="chart-preview">
                <span class="chart-preview-text">图表已折叠，点击展开查看</span>
            </div>
        `;

        // 恢复之前的折叠状态
        if (this.collapsedState.get(canvasId)) {
            setTimeout(() => this.collapse(canvasId, false), 0);
        }

        return wrapper;
    }

    /**
     * 切换折叠/展开
     * @param {string} canvasId - Canvas元素ID
     */
    toggleCollapse(canvasId) {
        const isCollapsed = this.collapsedState.get(canvasId);
        if (isCollapsed) {
            this.expand(canvasId);
        } else {
            this.collapse(canvasId);
        }
    }

    /**
     * 折叠图表
     * @param {string} canvasId - Canvas元素ID
     * @param {boolean} saveState - 是否保存状态
     */
    collapse(canvasId, saveState = true) {
        const body = document.getElementById(`body-${canvasId}`);
        const btn = document.getElementById(`collapse-btn-${canvasId}`);
        
        if (body) body.classList.add('collapsed');
        if (btn) btn.classList.add('collapsed');
        
        if (saveState) {
            this.collapsedState.set(canvasId, true);
        }

        console.log(`📊 图表 ${canvasId} 已折叠`);
    }

    /**
     * 展开图表
     * @param {string} canvasId - Canvas元素ID
     */
    expand(canvasId) {
        const body = document.getElementById(`body-${canvasId}`);
        const btn = document.getElementById(`collapse-btn-${canvasId}`);
        
        if (body) body.classList.remove('collapsed');
        if (btn) btn.classList.remove('collapsed');
        
        this.collapsedState.set(canvasId, false);

        // 如果有关联的Chart实例，需要调整大小
        const chart = this.charts.get(canvasId);
        if (chart) {
            setTimeout(() => chart.resize(), 300);
        }

        console.log(`📊 图表 ${canvasId} 已展开`);
    }

    /**
     * 切换全屏模式
     * @param {string} canvasId - Canvas元素ID
     */
    toggleFullscreen(canvasId) {
        const wrapper = document.getElementById(`wrapper-${canvasId}`);
        if (!wrapper) return;

        if (wrapper.classList.contains('fullscreen')) {
            // 退出全屏
            wrapper.classList.remove('fullscreen');
            document.body.style.overflow = '';
            
            // 恢复原始大小
            const chart = this.charts.get(canvasId);
            if (chart) {
                setTimeout(() => chart.resize(), 100);
            }
        } else {
            // 进入全屏
            wrapper.classList.add('fullscreen');
            document.body.style.overflow = 'hidden';
            
            // 调整图表大小
            const chart = this.charts.get(canvasId);
            if (chart) {
                setTimeout(() => chart.resize(), 100);
            }
        }

        console.log(`📊 图表 ${canvasId} 全屏状态: ${wrapper.classList.contains('fullscreen')}`);
    }

    /**
     * 切换菜单显示
     * @param {string} canvasId - Canvas元素ID
     */
    toggleMenu(canvasId) {
        const menu = document.getElementById(`menu-${canvasId}`);
        const menuBtn = menu?.previousElementSibling;
        
        if (!menu) return;

        const isActive = menu.parentElement.classList.contains('active');
        
        // 关闭所有其他菜单
        document.querySelectorAll('.chart-menu.active').forEach(m => {
            m.classList.remove('active');
        });

        if (!isActive) {
            menu.parentElement.classList.add('active');
            
            // 点击外部关闭菜单
            const closeMenu = (e) => {
                if (!menu.parentElement.contains(e.target)) {
                    menu.parentElement.classList.remove('active');
                    document.removeEventListener('click', closeMenu);
                }
            };
            
            setTimeout(() => {
                document.addEventListener('click', closeMenu);
            }, 0);
        }
    }

    /**
     * 下载图表图片
     * @param {string} canvasId - Canvas元素ID
     */
    downloadChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        // 创建一个临时链接
        const link = document.createElement('a');
        link.download = `chart-${canvasId}-${new Date().toISOString().split('T')[0]}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();

        // 关闭菜单
        const menu = document.getElementById(`menu-${canvasId}`);
        if (menu) menu.parentElement.classList.remove('active');

        console.log(`📊 图表 ${canvasId} 已下载`);
    }

    /**
     * 查看图表数据
     * @param {string} canvasId - Canvas元素ID
     */
    viewData(canvasId) {
        const chart = this.charts.get(canvasId);
        if (!chart) {
            alert('暂无数据可查看');
            return;
        }

        // 获取图表数据
        const data = chart.data;
        
        // 创建数据表格弹窗
        this.showDataModal(canvasId, data);

        // 关闭菜单
        const menu = document.getElementById(`menu-${canvasId}`);
        if (menu) menu.parentElement.classList.remove('active');
    }

    /**
     * 显示数据弹窗
     * @param {string} canvasId - Canvas元素ID
     * @param {Object} data - 图表数据
     */
    showDataModal(canvasId, data) {
        // 创建弹窗
        const modal = document.createElement('div');
        modal.className = 'data-modal-overlay';
        modal.innerHTML = `
            <div class="data-modal">
                <div class="data-modal-header">
                    <h3>图表数据</h3>
                    <button class="data-modal-close" onclick="this.closest('.data-modal-overlay').remove()">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                <div class="data-modal-body">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>标签</th>
                                ${data.datasets.map((ds, i) => `<th>${ds.label || '数据' + (i+1)}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${data.labels.map((label, i) => `
                                <tr>
                                    <td>${label}</td>
                                    ${data.datasets.map(ds => `<td>${ds.data[i]?.toFixed ? ds.data[i].toFixed(4) : ds.data[i]}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        // 添加弹窗样式
        if (!document.getElementById('data-modal-styles')) {
            const style = document.createElement('style');
            style.id = 'data-modal-styles';
            style.textContent = `
                .data-modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10000;
                    padding: 2rem;
                }
                .data-modal {
                    background: white;
                    border-radius: 0.75rem;
                    max-width: 800px;
                    width: 100%;
                    max-height: 80vh;
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
                }
                .data-modal-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 1rem 1.5rem;
                    border-bottom: 1px solid #e5e7eb;
                }
                .data-modal-header h3 {
                    margin: 0;
                    font-size: 1.125rem;
                    font-weight: 600;
                }
                .data-modal-close {
                    background: none;
                    border: none;
                    font-size: 1.25rem;
                    color: #6b7280;
                    cursor: pointer;
                    padding: 0.25rem;
                    border-radius: 0.375rem;
                }
                .data-modal-close:hover {
                    background: #f3f4f6;
                }
                .data-modal-body {
                    padding: 1.5rem;
                    overflow: auto;
                }
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 0.875rem;
                }
                .data-table th,
                .data-table td {
                    padding: 0.625rem;
                    text-align: left;
                    border-bottom: 1px solid #e5e7eb;
                }
                .data-table th {
                    font-weight: 600;
                    background: #f9fafb;
                    position: sticky;
                    top: 0;
                }
                .data-table tr:hover td {
                    background: #f9fafb;
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(modal);
    }

    /**
     * 刷新图表数据
     * @param {string} canvasId - Canvas元素ID
     */
    async refreshChart(canvasId) {
        // 关闭菜单
        const menu = document.getElementById(`menu-${canvasId}`);
        if (menu) menu.parentElement.classList.remove('active');

        // 触发自定义事件，由外部处理刷新逻辑
        const event = new CustomEvent('chartRefresh', { 
            detail: { canvasId } 
        });
        document.dispatchEvent(event);

        console.log(`📊 图表 ${canvasId} 刷新请求已发送`);
    }

    /**
     * 注册图表实例
     * @param {string} canvasId - Canvas元素ID
     * @param {Chart} chart - Chart.js实例
     */
    registerChart(canvasId, chart) {
        this.charts.set(canvasId, chart);
    }

    /**
     * 更新图表计数器
     * @param {string} canvasId - Canvas元素ID
     * @param {string} text - 计数文本
     */
    updateCounter(canvasId, text) {
        const counter = document.getElementById(`counter-${canvasId}`);
        if (counter) counter.textContent = text;
    }

    /**
     * 折叠所有图表
     */
    collapseAll() {
        this.charts.forEach((chart, canvasId) => {
            this.collapse(canvasId);
        });
    }

    /**
     * 展开所有图表
     */
    expandAll() {
        this.charts.forEach((chart, canvasId) => {
            this.expand(canvasId);
        });
    }
}

// 创建全局实例
const collapsibleChartManager = new CollapsibleChartManager();

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CollapsibleChartManager;
}
