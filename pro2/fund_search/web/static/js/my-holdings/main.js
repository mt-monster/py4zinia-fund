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
                FundFilters.togglePanel();
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
                FundFilters.updateResultCount();
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
                const value = Number(response.data.value);
                const change = Number(response.data.change);
                const changePercent = Number(response.data.changePercent);
                const formattedValue = Number.isNaN(value) ? '--' : value.toFixed(2);
                const formattedChangePercent = Number.isNaN(changePercent)
                    ? '--'
                    : `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
                indexElement.textContent = `${formattedValue} ${formattedChangePercent}`;
                indexElement.className = change >= 0 ? 'cell-positive' : 'cell-negative';
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
            console.log('🎯 开始相关性分析，选中的基金:', fundCodes);
            
            const response = await fetch('/api/holdings/analyze/correlation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ fund_codes: fundCodes })
            });

            const result = await response.json();
            console.log('📊 API响应结果:', result);
            
            if (result.success) {
                // 添加基金代码到数据中
                result.data.fund_codes = fundCodes;
                
                console.log('💾 准备存储到sessionStorage的数据:', result.data);
                
                // 使用 sessionStorage 存储数据，避免URL过长
                sessionStorage.setItem('correlationAnalysisData', JSON.stringify(result.data));
                console.log('✅ 数据已存储到sessionStorage');
                
                window.location.href = '/correlation-analysis';
            } else {
                FundUtils.showNotification('分析失败: ' + (result.error || '未知错误'), 'error');
                this.setAnalysisButtonLoading(false);
            }
        } catch (error) {
            console.error('❌ 分析失败:', error);
            FundUtils.showNotification('分析失败: 网络错误', 'error');
            this.setAnalysisButtonLoading(false);
        }
    },

    /**
     * 开始投资建议分析 - 跳转到独立页面
     */
    async startInvestmentAdvice() {
        // 获取选中的基金代码
        const fundCodes = FundTable.getSelectedFundCodes();
        
        if (fundCodes.length === 0) {
            FundUtils.showNotification('请先选择至少一只基金', 'warning');
            return;
        }
        
        // 设置按钮加载状态
        this.setInvestmentAdviceButtonLoading(true);
        
        try {
            console.log('💡 开始投资建议分析，选中的基金:', fundCodes);
            
            // 存储数据到sessionStorage
            sessionStorage.setItem('investmentAdviceData', JSON.stringify({
                fund_codes: fundCodes,
                timestamp: new Date().toISOString()
            }));
            console.log('✅ 数据已存储到sessionStorage');
            
            // 跳转到投资建议页面
            window.location.href = '/investment-advice';
        } catch (error) {
            console.error('❌ 投资建议分析启动失败:', error);
            FundUtils.showNotification('启动失败: ' + error.message, 'error');
            this.setInvestmentAdviceButtonLoading(false);
        }
    },

    /**
     * 设置投资建议按钮加载状态
     */
    setInvestmentAdviceButtonLoading(isLoading) {
        const adviceBtn = document.getElementById('investment-advice-btn');
        if (!adviceBtn) return;
        
        const btnIcon = adviceBtn.querySelector('i');
        
        if (isLoading) {
            adviceBtn.disabled = true;
            adviceBtn.classList.add('btn-loading');
            if (btnIcon) {
                btnIcon.className = 'bi bi-hourglass-split';
            }
        } else {
            adviceBtn.disabled = false;
            adviceBtn.classList.remove('btn-loading');
            if (btnIcon) {
                btnIcon.className = 'bi bi-lightbulb';
            }
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
            if (btnText && btnText !== analysisBtn) btnText.textContent = '相关性分析';
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
function startInvestmentAdvice() { FundApp.startInvestmentAdvice(); }
function clearFundList() { FundApp.clearFundList(); }
function refreshData() { FundApp.refreshData(); }
function handleSearchKeyup(event) { FundApp.handleSearchKeyup(event); }
function handleModalBackdrop(event) { /* 已在bindEvents中处理 */ }

/**
 * 手工导入模块
 */
const FundManualImport = {
    selectedFund: null,
    importHistory: [],
    
    /**
     * 打开手工导入模态框
     */
    openModal() {
        const modal = document.getElementById('manual-import-modal');
        if (modal) {
            modal.classList.add('active');
            this.resetForm();
            this.loadImportHistory();
        }
    },
    
    /**
     * 关闭手工导入模态框
     */
    closeModal() {
        const modal = document.getElementById('manual-import-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        this.resetForm();
    },
    
    /**
     * 重置表单
     */
    resetForm() {
        document.getElementById('fund-search-input').value = '';
        document.getElementById('holding-amount').value = '';
        document.getElementById('buy-date').value = new Date().toISOString().split('T')[0];
        document.getElementById('fund-search-results').style.display = 'none';
        document.getElementById('fund-info').style.display = 'none';
        document.getElementById('confirm-import-btn').disabled = true;
        this.selectedFund = null;
    },
    
    /**
     * 处理基金搜索
     */
    async handleSearch(event) {
        const input = event.target;
        const value = input.value.trim();
        const resultsContainer = document.getElementById('fund-search-results');
        
        if (value.length < 1) {
            resultsContainer.style.display = 'none';
            return;
        }
        
        try {
            // 调用API搜索基金
            const response = await fetch(`/api/fund/search?keyword=${encodeURIComponent(value)}`);
            const data = await response.json();
            
            if (data.success && data.data.length > 0) {
                resultsContainer.innerHTML = data.data.map(fund => `
                    <div class="search-result-item" onclick="FundManualImport.selectFund(${JSON.stringify(fund).replace(/"/g, '&quot;')})" 
                         style="padding: 10px; cursor: pointer; border-bottom: 1px solid #eee;">
                        <div style="font-weight: 500;">${fund.fund_code} ${fund.fund_name}</div>
                        <div style="font-size: 12px; color: #666;">${fund.fund_type || ''}</div>
                    </div>
                `).join('');
                resultsContainer.style.display = 'block';
            } else {
                resultsContainer.innerHTML = '<div style="padding: 10px; color: #666;">未找到匹配的基金</div>';
                resultsContainer.style.display = 'block';
            }
        } catch (error) {
            console.error('搜索基金失败:', error);
            resultsContainer.innerHTML = '<div style="padding: 10px; color: #d9534f;">搜索失败，请重试</div>';
            resultsContainer.style.display = 'block';
        }
    },
    
    /**
     * 选择基金
     */
    selectFund(fund) {
        this.selectedFund = fund;
        document.getElementById('fund-search-input').value = `${fund.fund_code} ${fund.fund_name}`;
        document.getElementById('fund-search-results').style.display = 'none';
        
        // 显示基金信息
        const fundInfoContent = document.getElementById('fund-info-content');
        fundInfoContent.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div><strong>基金代码:</strong> ${fund.fund_code}</div>
                <div><strong>基金名称:</strong> ${fund.fund_name}</div>
                <div><strong>基金类型:</strong> ${fund.fund_type || '--'}</div>
                <div><strong>最新净值:</strong> ${fund.nav_value ? `¥${fund.nav_value}` : '--'}</div>
                <div><strong>净值日期:</strong> ${fund.nav_date || '--'}</div>
                <div><strong>日涨跌幅:</strong> ${fund.daily_change ? `${fund.daily_change}%` : '--'}</div>
            </div>
        `;
        document.getElementById('fund-info').style.display = 'block';
        
        // 启用确认导入按钮
        document.getElementById('confirm-import-btn').disabled = false;
    },
    
    /**
     * 确认手工导入
     */
    async confirmImport() {
        const holdingAmount = parseFloat(document.getElementById('holding-amount').value);
        const buyDate = document.getElementById('buy-date').value;
        
        // 验证输入
        if (!this.selectedFund) {
            FundUtils.showNotification('请先选择基金', 'error');
            return;
        }
        
        if (isNaN(holdingAmount) || holdingAmount <= 0) {
            FundUtils.showNotification('请输入有效的持有金额', 'error');
            return;
        }
        
        if (!buyDate) {
            FundUtils.showNotification('请选择购买日期', 'error');
            return;
        }
        
        try {
            // 准备导入数据
            const fundData = {
                fund_code: this.selectedFund.fund_code,
                fund_name: this.selectedFund.fund_name,
                holding_shares: holdingAmount / (this.selectedFund.nav_value || 1),
                cost_price: this.selectedFund.nav_value || 1,
                buy_date: buyDate,
                confidence: 1.0
            };
            
            // 调用API导入基金
            const response = await fetch('/api/holdings/import/confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: 'default_user',
                    funds: [fundData]
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 记录导入历史
                this.addToImportHistory({
                    fund_code: this.selectedFund.fund_code,
                    fund_name: this.selectedFund.fund_name,
                    holding_amount: holdingAmount,
                    buy_date: buyDate,
                    import_date: new Date().toISOString(),
                    status: 'success'
                });
                
                FundUtils.showNotification(`成功导入基金: ${this.selectedFund.fund_name}`, 'success');
                
                // 关闭模态框并刷新数据
                this.closeModal();
                await FundApp.refreshData();
            } else {
                // 记录导入失败历史
                this.addToImportHistory({
                    fund_code: this.selectedFund.fund_code,
                    fund_name: this.selectedFund.fund_name,
                    holding_amount: holdingAmount,
                    buy_date: buyDate,
                    import_date: new Date().toISOString(),
                    status: 'failed',
                    error: data.error
                });
                
                FundUtils.showNotification('导入失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('导入基金失败:', error);
            
            // 记录导入失败历史
            this.addToImportHistory({
                fund_code: this.selectedFund.fund_code,
                fund_name: this.selectedFund.fund_name,
                holding_amount: holdingAmount,
                buy_date: buyDate,
                import_date: new Date().toISOString(),
                status: 'failed',
                error: '网络错误'
            });
            
            FundUtils.showNotification('导入失败: 网络错误', 'error');
        }
    },
    
    /**
     * 加载导入历史
     */
    loadImportHistory() {
        const history = FundUtils.getStorage('fund_import_history') || [];
        this.importHistory = history;
        this.renderImportHistory();
    },
    
    /**
     * 添加到导入历史
     */
    addToImportHistory(record) {
        this.importHistory.unshift(record);
        // 只保留最近20条历史记录
        if (this.importHistory.length > 20) {
            this.importHistory = this.importHistory.slice(0, 20);
        }
        FundUtils.setStorage('fund_import_history', this.importHistory);
        this.renderImportHistory();
    },
    
    /**
     * 渲染导入历史
     */
    renderImportHistory() {
        const historyList = document.getElementById('import-history-list');
        
        if (this.importHistory.length === 0) {
            historyList.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 40px 0; color: #6c757d;">
                    <i class="bi bi-clock-history" style="font-size: 48px; margin-bottom: 15px;"></i>
                    <p>暂无导入历史</p>
                </div>
            `;
            return;
        }
        
        historyList.innerHTML = this.importHistory.map(record => `
            <div style="padding: 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 500;">${record.fund_code} ${record.fund_name}</div>
                    <div style="font-size: 12px; color: #666; margin-top: 4px;">
                        持有金额: ¥${record.holding_amount.toFixed(2)} | 购买日期: ${record.buy_date}
                    </div>
                    <div style="font-size: 11px; color: #999; margin-top: 2px;">
                        导入时间: ${new Date(record.import_date).toLocaleString()}
                    </div>
                </div>
                <div style="padding: 4px 8px; border-radius: 4px; font-size: 12px;
                     background: ${record.status === 'success' ? '#d4edda' : '#f8d7da'};
                     color: ${record.status === 'success' ? '#155724' : '#721c24'};">
                    ${record.status === 'success' ? '成功' : '失败'}
                </div>
            </div>
        `).join('');
    }
};

/**
 * 切换手工导入标签页
 */
function switchManualImportTab(tabName) {
    // 切换标签按钮状态
    const tabButtons = document.querySelectorAll('[data-tab]');
    tabButtons.forEach(btn => {
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // 切换内容
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // 如果切换到历史标签，重新加载历史
    if (tabName === 'history') {
        FundManualImport.loadImportHistory();
    }
}

/**
 * 处理基金搜索输入 - 添加防抖以防止重复搜索
 * 3秒防抖，显著减少不必要的API调用
 */
let searchTimeout;
function handleFundSearch(event) {
    // 清除之前的定时器
    clearTimeout(searchTimeout);
    
    // 设置新的定时器，3秒后执行搜索
    searchTimeout = setTimeout(() => {
        FundManualImport.handleSearch(event);
    }, 3000);
}

/**
 * 确认手工导入
 */
function confirmManualImport() {
    FundManualImport.confirmImport();
}

/**
 * 打开手工导入模态框
 */
function openManualImportModal() {
    FundManualImport.openModal();
}

/**
 * 关闭手工导入模态框
 */
function closeManualImportModal() {
    FundManualImport.closeModal();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    FundApp.init();
});
