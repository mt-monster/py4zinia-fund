/**
 * 主模块 - 初始化和事件绑定
 */
const FundApp = {
    /**
     * 初始化应用
     */
    async init() {
        try {
            // 初始化状态
            FundState.columnConfig = FundUtils.getStorage(FundConfig.storage.columns) || 
                                   FundUtils.deepClone(FundConfig.defaultColumns);
            
            // 初始化模块
            FundTable.init();
            FundScreenshot.setupDragDrop();
            
            // 绑定事件
            this.bindEvents();
            
            // 加载数据
            await this.loadData();
            
            // 更新市场指数
            this.updateMarketIndex();
            
            FundUtils.showNotification('页面加载完成', 'success');
        } catch (error) {
            console.error('App initialization error:', error);
            FundUtils.showNotification('页面加载失败: ' + error.message, 'error');
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 搜索框防抖
        const searchInput = document.getElementById('search-input');
        searchInput.addEventListener('input', FundUtils.debounce((e) => {
            FundFilters.handleSearch(e.target.value);
        }, 300));

        // 模态框背景点击关闭
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                e.target.classList.remove('active');
            }
        });

        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            // Ctrl+F 打开筛选
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                FundFilters.openModal();
            }
            
            // Escape 关闭模态框
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal-overlay.active').forEach(modal => {
                    modal.classList.remove('active');
                });
                document.getElementById('settings-panel').classList.remove('open');
            }
        });

        // 窗口大小变化
        window.addEventListener('resize', FundUtils.throttle(() => {
            // 可以在这里处理响应式逻辑
        }, 250));
    },

    /**
     * 加载数据
     */
    async loadData() {
        FundState.isLoading = true;
        FundTable.renderData(); // 显示加载状态

        try {
            const response = await FundAPI.getFunds({
                page: FundState.currentPage,
                pageSize: FundState.pageSize
            });

            if (response.success) {
                FundState.funds = response.data;
                FundState.filteredFunds = [...response.data];
                FundTable.renderData();
                FundFilters.updateCount();
            } else {
                FundUtils.showNotification('数据加载失败: ' + response.error, 'error');
                FundTable.renderData([]);
            }
        } catch (error) {
            console.error('Load data error:', error);
            FundUtils.showNotification('数据加载失败', 'error');
            FundTable.renderData([]);
        } finally {
            FundState.isLoading = false;
        }
    },

    /**
     * 更新市场指数
     */
    async updateMarketIndex() {
        try {
            const response = await FundAPI.getMarketIndex();
            if (response.success) {
                const indexElement = document.getElementById('index-value');
                indexElement.textContent = `${response.data.value} ${response.data.changePercent}`;
                indexElement.className = response.data.change > 0 ? 'cell-positive' : 'cell-negative';
            }
        } catch (error) {
            console.error('Update market index error:', error);
        }
    },

    /**
     * 刷新数据
     */
    async refreshData() {
        await this.loadData();
        FundUtils.showNotification('数据已刷新', 'success');
    },

    /**
     * 清空基金列表
     */
    async clearFundList() {
        if (!confirm('确定要清空所有基金吗？此操作不可恢复。')) {
            return;
        }

        try {
            // 这里应该调用API清空数据
            // 模拟清空
            FundState.funds = [];
            FundState.filteredFunds = [];
            FundState.selectedFunds.clear();
            
            FundTable.renderData();
            FundFilters.updateCount();
            
            FundUtils.showNotification('基金列表已清空', 'success');
        } catch (error) {
            console.error('Clear fund list error:', error);
            FundUtils.showNotification('清空失败', 'error');
        }
    },

    /**
     * 开始分析
     */
    async startAnalysis() {
        const selectedCount = FundState.selectedFunds.size;
        
        if (selectedCount < 2) {
            FundUtils.showNotification('请至少选择2只基金进行分析', 'warning');
            return;
        }

        if (selectedCount > 20) {
            FundUtils.showNotification('最多支持20只基金同时分析', 'warning');
            return;
        }

        const fundCodes = Array.from(FundState.selectedFunds);
        
        try {
            const response = await FundAPI.startAnalysis(fundCodes);
            
            if (response.success) {
                // 打开分析结果页面
                window.open(`/analysis?funds=${fundCodes.join(',')}`, '_blank');
                FundUtils.showNotification('分析请求已发送', 'success');
            } else {
                FundUtils.showNotification('分析请求失败: ' + response.error, 'error');
            }
        } catch (error) {
            console.error('Start analysis error:', error);
            FundUtils.showNotification('分析请求失败', 'error');
        }
    },

    /**
     * 搜索处理
     */
    handleSearchKeyup(event) {
        if (event.key === 'Enter') {
            const keyword = event.target.value.trim();
            FundFilters.handleSearch(keyword);
        }
    }
};

// 全局函数（供HTML调用）
function openFilterModal() { FundFilters.openModal(); }
function closeFilterModal() { FundFilters.closeModal(); }
function applyFilters() { FundFilters.apply(); }
function resetFilters() { FundFilters.reset(); }
function clearFilters() { FundFilters.clearAll(); }
function switchTab(tabName) { FundFilters.switchTab(tabName); }

function openScreenshotModal() { FundScreenshot.openModal(); }
function closeScreenshotModal() { FundScreenshot.closeModal(); }
function handleFileSelect(event) { FundScreenshot.handleFileSelect(event); }
function importFunds() { FundScreenshot.importFunds(); }

function openSettingsModal() { FundSettings.openModal(); }
function closeSettingsModal() { FundSettings.closeModal(); }
function saveColumnSettings() { FundSettings.save(); }
function resetColumns() { FundSettings.reset(); }

function toggleSelectAll() { FundTable.toggleSelectAll(); }
function startAnalysis() { FundApp.startAnalysis(); }
function clearFundList() { FundApp.clearFundList(); }
function refreshData() { FundApp.refreshData(); }
function handleSearchKeyup(event) { FundApp.handleSearchKeyup(event); }
function handleModalBackdrop(event) { /* 已在bindEvents中处理 */ }

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    FundApp.init();
});
