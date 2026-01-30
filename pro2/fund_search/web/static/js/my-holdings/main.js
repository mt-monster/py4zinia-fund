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
            
            // 页面加载完成（不显示提示）
        } catch (error) {
            console.error('App initialization error:', error);
            // 页面加载错误（静默处理，不显示提示）
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
                // 数据加载失败（静默处理）
                console.warn('数据加载失败:', response.error);
                FundTable.renderData([]);
            }
        } catch (error) {
            console.error('Load data error:', error);
            // 数据加载异常（静默处理）
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
        if (!confirm('确定要清空所有基金吗？此操作将删除数据库中的所有持仓记录，不可恢复。')) {
            return;
        }

        try {
            // 调用API清空数据库中的持仓记录
            const response = await fetch('/api/holdings/clear?user_id=default_user', {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 清空前端状态
                FundState.funds = [];
                FundState.filteredFunds = [];
                FundState.selectedFunds.clear();
                
                FundTable.renderData();
                FundFilters.updateCount();
                
                FundUtils.showNotification('基金列表已清空', 'success');
            } else {
                FundUtils.showNotification('清空失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('Clear fund list error:', error);
            FundUtils.showNotification('清空失败: 网络错误', 'error');
        }
    },

    /**
     * 开始分析 - 与原始版本功能完全一致
     */
    async startAnalysis() {
        const analysisBtn = document.getElementById('analysis-btn');
        
        // 如果按钮正在加载中，防止重复提交
        if (analysisBtn && analysisBtn.disabled) {
            return;
        }
        
        const selectedCount = FundState.selectedFunds.size;
        
        if (selectedCount < 2) {
            FundUtils.showNotification('请至少选择2只基金进行相关性分析', 'error');
            return;
        }

        const fundCodes = Array.from(FundState.selectedFunds);
        
        // 设置按钮为加载状态
        this.setAnalysisButtonLoading(true);
        
        // 显示加载状态
        FundUtils.showNotification('正在分析基金相关性，请稍候...', 'info');
        
        try {
            const response = await fetch('/api/holdings/analyze/correlation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ fund_codes: fundCodes })
            });

            const result = await response.json();
            if (result.success) {
                // 添加基金代码到数据中
                result.data.fund_codes = fundCodes;
                
                // 跳转到相关性分析页面，传递数据
                const dataParam = encodeURIComponent(JSON.stringify(result.data));
                window.location.href = `/correlation-analysis?data=${dataParam}`;
            } else {
                FundUtils.showNotification('分析失败: ' + (result.error || '未知错误'), 'error');
                this.setAnalysisButtonLoading(false);
            }
        } catch (error) {
            console.error('分析失败:', error);
            FundUtils.showNotification('分析失败: 网络错误', 'error');
            this.setAnalysisButtonLoading(false);
        }
    },

    /**
     * 设置分析按钮加载状态 - 与原始版本一致
     */
    setAnalysisButtonLoading(isLoading) {
        const analysisBtn = document.getElementById('analysis-btn');
        if (!analysisBtn) return;
        
        const btnText = analysisBtn.querySelector('.btn-text') || analysisBtn;
        const btnIcon = analysisBtn.querySelector('i');
        
        if (isLoading) {
            // 禁用按钮，显示加载状态
            analysisBtn.disabled = true;
            analysisBtn.classList.add('btn-loading');
            if (btnText && btnText !== analysisBtn) btnText.textContent = '分析中...';
            if (btnIcon) {
                btnIcon.className = 'bi bi-hourglass-split';
            }
        } else {
            // 恢复按钮状态
            analysisBtn.disabled = false;
            analysisBtn.classList.remove('btn-loading');
            if (btnText && btnText !== analysisBtn) btnText.textContent = '综合分析';
            if (btnIcon) {
                btnIcon.className = 'bi bi-chart-line';
            }
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
