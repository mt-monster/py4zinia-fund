/**
 * 截图导入模块 - 与原始版本功能完全一致
 */
const FundScreenshot = {
    currentImage: null,
    recognizedFunds: [],

    /**
     * 打开模态框
     */
    openModal() {
        const modal = document.getElementById('screenshot-modal');
        if (modal) {
            modal.classList.add('active');
            this.reset();
        }
    },

    /**
     * 关闭模态框
     */
    closeModal() {
        const modal = document.getElementById('screenshot-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        this.reset();
    },

    /**
     * 重置状态
     */
    reset() {
        this.currentImage = null;
        this.recognizedFunds = [];

        const screenshotInput = document.getElementById('screenshot-input');
        const uploadArea = document.getElementById('upload-area');
        const previewSection = document.getElementById('preview-section');
        const importBtn = document.getElementById('import-btn');
        const recognitionResult = document.getElementById('recognition-result');

        if (screenshotInput) screenshotInput.value = '';
        if (uploadArea) uploadArea.style.display = 'block';
        if (previewSection) previewSection.style.display = 'none';
        if (importBtn) {
            importBtn.disabled = true;
            importBtn.textContent = '确认导入';
        }
        if (recognitionResult) recognitionResult.innerHTML = '';
    },

    /**
     * 处理文件选择
     */
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            FundUtils.showNotification('请选择图片文件', 'error');
            return;
        }

        // 检查文件大小 (10MB限制)
        if (file.size > 10 * 1024 * 1024) {
            FundUtils.showNotification('图片文件过大，请选择小于10MB的图片', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.currentImage = e.target.result;
            this.showPreview();
            this.recognizeFunds();
        };
        reader.readAsDataURL(file);
    },

    /**
     * 显示预览
     */
    showPreview() {
        const uploadArea = document.getElementById('upload-area');
        const previewSection = document.getElementById('preview-section');
        const imagePreview = document.getElementById('image-preview');

        if (uploadArea) uploadArea.style.display = 'none';
        if (previewSection) previewSection.style.display = 'block';
        if (imagePreview) imagePreview.src = this.currentImage;
    },

    /**
     * 识别基金 - 调用真实API
     */
    async recognizeFunds() {
        if (!this.currentImage) return;

        const resultDiv = document.getElementById('recognition-result');
        const importBtn = document.getElementById('import-btn');

        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="loading-state" style="text-align: center; padding: var(--space-6);">
                    <i class="bi bi-hourglass-split" style="font-size: 32px; color: var(--primary);"></i>
                    <p style="margin-top: var(--space-3); color: var(--text-secondary);">正在识别基金持仓信息...</p>
                </div>
            `;
        }

        try {
            // 调用真实的OCR识别API
            const response = await fetch('/api/holdings/import/screenshot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: this.currentImage,
                    use_gpu: false,
                    ocr_engine: 'baidu'  // 默认使用百度OCR
                })
            });

            const data = await response.json();

            if (data.success) {
                // 保存识别到的基金数据
                this.recognizedFunds = data.data || [];
                // 显示识别结果
                this.renderRecognitionResult(data);
                // 启用导入按钮
                if (importBtn) importBtn.disabled = false;
            } else {
                // 显示错误信息
                this.renderRecognitionError(data.error || '识别失败', data.suggestion);
            }
        } catch (error) {
            console.error('识别失败:', error);
            this.renderRecognitionError('网络错误，请重试');
        }
    },

    /**
     * 渲染识别结果
     */
    renderRecognitionResult(data) {
        const resultDiv = document.getElementById('recognition-result');
        if (!resultDiv) return;

        const funds = data.data || [];

        if (funds.length === 0) {
            resultDiv.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: var(--space-6); color: var(--text-tertiary);">
                    <i class="bi bi-inbox" style="font-size: 48px; opacity: 0.5;"></i>
                    <p style="margin-top: var(--space-3);">未识别到基金</p>
                </div>
            `;
            return;
        }

        // 计算投资组合汇总
        const totalHolding = funds.reduce((sum, f) => sum + (f.holding_amount || 0), 0);
        const totalProfit = funds.reduce((sum, f) => sum + (f.profit_amount || 0), 0);
        const totalValue = funds.reduce((sum, f) => sum + (f.current_value || 0), 0);

        resultDiv.innerHTML = `
            <div style="margin-bottom: var(--space-4);">
                <h4 style="margin-bottom: var(--space-3);">
                    <i class="bi bi-check-circle-fill" style="color: var(--success);"></i>
                    识别成功 (${funds.length}只基金)
                </h4>
                
                <!-- 投资组合汇总 -->
                <div style="background: var(--bg-secondary); padding: var(--space-4); border-radius: var(--border-radius-md); margin-bottom: var(--space-4);">
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-4); text-align: center;">
                        <div>
                            <div style="font-size: var(--text-xs); color: var(--text-tertiary);">持仓成本</div>
                            <div style="font-size: var(--text-lg); font-weight: 600; color: var(--text-primary);">¥${totalHolding.toFixed(2)}</div>
                        </div>
                        <div>
                            <div style="font-size: var(--text-xs); color: var(--text-tertiary);">累计收益</div>
                            <div style="font-size: var(--text-lg); font-weight: 600; color: ${totalProfit >= 0 ? 'var(--success)' : 'var(--danger)'};">
                                ${totalProfit >= 0 ? '+' : ''}¥${totalProfit.toFixed(2)}
                            </div>
                        </div>
                        <div>
                            <div style="font-size: var(--text-xs); color: var(--text-tertiary);">当前市值</div>
                            <div style="font-size: var(--text-lg); font-weight: 600; color: var(--primary);">¥${totalValue.toFixed(2)}</div>
                        </div>
                    </div>
                </div>

                <!-- 基金列表 -->
                <table class="fund-table" style="width: 100%; margin-top: var(--space-3);">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: var(--space-2);">基金代码</th>
                            <th style="text-align: left; padding: var(--space-2);">基金名称</th>
                            <th style="text-align: right; padding: var(--space-2);">持仓金额</th>
                            <th style="text-align: right; padding: var(--space-2);">收益</th>
                            <th style="text-align: center; padding: var(--space-2);">置信度</th>
                            <th style="text-align: center; padding: var(--space-2);">删除</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${funds.map((fund, index) => `
                            <tr>
                                <td style="padding: var(--space-2);">${fund.fund_code}</td>
                                <td style="padding: var(--space-2);">${fund.fund_name}</td>
                                <td style="text-align: right; padding: var(--space-2);">¥${(fund.holding_amount || 0).toFixed(2)}</td>
                                <td style="text-align: right; padding: var(--space-2); color: ${(fund.profit_amount || 0) >= 0 ? 'var(--success)' : 'var(--danger)'};">
                                    ${(fund.profit_amount || 0) >= 0 ? '+' : ''}¥${(fund.profit_amount || 0).toFixed(2)}
                                </td>
                                <td style="text-align: center; padding: var(--space-2);">
                                    <span style="background: ${(fund.confidence || 0) >= 0.9 ? 'var(--success-light)' : 'var(--warning-light)'}; 
                                                 color: ${(fund.confidence || 0) >= 0.9 ? 'var(--success)' : 'var(--warning)'};
                                                 padding: 2px 8px; border-radius: 10px; font-size: var(--text-xs);">
                                        ${((fund.confidence || 0) * 100).toFixed(0)}%
                                    </span>
                                </td>
                                <td style="text-align: center; padding: var(--space-2);">
                                    <button onclick="FundScreenshot.deleteFund(${index})" 
                                            style="background: var(--danger-light); 
                                                   color: var(--danger); 
                                                   border: none; 
                                                   padding: 4px 12px; 
                                                   border-radius: var(--border-radius-sm); 
                                                   cursor: pointer; 
                                                   font-size: var(--text-xs);">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    },

    /**
     * 渲染识别错误
     */
    renderRecognitionError(error, suggestion) {
        const resultDiv = document.getElementById('recognition-result');
        if (!resultDiv) return;

        resultDiv.innerHTML = `
            <div style="text-align: center; padding: var(--space-6); color: var(--danger);">
                <i class="bi bi-exclamation-circle" style="font-size: 48px;"></i>
                <p style="margin-top: var(--space-3); font-weight: 500;">${error}</p>
                ${suggestion ? `<p style="color: var(--text-tertiary); font-size: var(--text-sm); margin-top: var(--space-2);">${suggestion}</p>` : ''}
            </div>
        `;
    },

    /**
     * 导入基金 - 调用真实API保存到数据库
     */
    async importFunds() {
        if (this.recognizedFunds.length === 0) return;

        const importBtn = document.getElementById('import-btn');
        if (importBtn) {
            importBtn.disabled = true;
            importBtn.textContent = '导入中...';
        }

        try {
            // 准备导入数据 - 从识别结果计算持有份额和成本价
            const fundsToImport = this.recognizedFunds.map(fund => {
                const holding_amount = fund.holding_amount || 0;
                const profit_amount = fund.profit_amount || 0;
                const current_value = fund.current_value || (holding_amount + profit_amount);
                const nav_value = fund.nav_value;

                let holding_shares = 0;
                let cost_price = 0;

                // 如果有净值，使用精确计算
                if (nav_value && nav_value > 0 && current_value > 0) {
                    holding_shares = current_value / nav_value;
                    if (holding_shares > 0) {
                        cost_price = holding_amount / holding_shares;
                    }
                } else {
                    // 没有净值，使用简化方法
                    holding_shares = holding_amount;
                    cost_price = 1.0;
                }

                return {
                    fund_code: fund.fund_code,
                    fund_name: fund.fund_name,
                    holding_shares: holding_shares,
                    cost_price: cost_price,
                    buy_date: fund.buy_date || new Date().toISOString().split('T')[0],
                    confidence: fund.confidence || 0
                };
            }).filter(fund => fund.fund_code && fund.holding_shares > 0);

            if (fundsToImport.length === 0) {
                FundUtils.showNotification('识别到的数据不完整，无法保存', 'error');
                if (importBtn) {
                    importBtn.disabled = false;
                    importBtn.textContent = '确认导入';
                }
                return;
            }

            // 调用导入API
            console.log('准备导入的数据:', fundsToImport);
            const response = await fetch('/api/holdings/import/confirm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: 'default_user',
                    funds: fundsToImport
                })
            });
            
            console.log('API响应状态:', response.status);
            const data = await response.json();
            console.log('API响应数据:', data);

            if (data.success) {
                FundUtils.showNotification(`成功导入 ${data.imported_count} 只基金`, 'success');

                // 关闭模态框
                this.closeModal();

                // 刷新基金列表
                setTimeout(() => {
                    FundApp.refreshData();
                }, 500);
            } else {
                FundUtils.showNotification('导入失败: ' + (data.error || '未知错误'), 'error');
                if (importBtn) {
                    importBtn.disabled = false;
                    importBtn.textContent = '确认导入';
                }
            }
        } catch (error) {
            console.error('导入失败:', error);
            FundUtils.showNotification('导入失败: 网络错误', 'error');
            if (importBtn) {
                importBtn.disabled = false;
                importBtn.textContent = '确认导入';
            }
        }
    },

    /**
     * 删除基金
     */
    deleteFund(index) {
        console.log('=== deleteFund 调用开始 ===');
        console.log('传入索引:', index);
        console.log('FundScreenshot 对象:', this);
        console.log('当前 recognizedFunds:', this.recognizedFunds);
        console.log('recognizedFunds 长度:', this.recognizedFunds ? this.recognizedFunds.length : 'undefined');
        
        // 检查 FundScreenshot 对象是否存在
        if (!this || !this.recognizedFunds) {
            console.error('FundScreenshot 对象或 recognizedFunds 未定义');
            alert('删除功能暂时不可用，请刷新页面后重试');
            return;
        }
        
        // 检查索引是否有效
        if (index < 0 || index >= this.recognizedFunds.length) {
            console.error('无效索引:', index, '数组长度:', this.recognizedFunds.length);
            alert(`删除失败：无效的基金索引 ${index}，有效范围: 0-${this.recognizedFunds.length - 1}`);
            return;
        }
        
        // 获取要删除的基金信息
        const fundToDelete = this.recognizedFunds[index];
        console.log('要删除的基金:', fundToDelete);
        
        if (!fundToDelete) {
            console.error('索引位置没有基金数据:', index);
            alert('删除失败：该位置没有基金数据');
            return;
        }
        
        const fundName = fundToDelete.fund_name || '未知基金';
        
        // 显示确认对话框
        const confirmMsg = `警告：此操作不可撤销！\n\n确定要删除基金「${fundName}」吗？\n\n删除后，该基金将从识别结果中移除，且无法恢复。`;
        
        if (confirm(confirmMsg)) {
            try {
                console.log('开始删除操作...');
                
                // 从识别结果中移除基金
                const deletedFund = this.recognizedFunds.splice(index, 1)[0];
                console.log('已删除基金:', deletedFund);
                console.log('删除后 recognizedFunds:', this.recognizedFunds);
                
                // 重新渲染识别结果
                this.renderRecognitionResult({ data: this.recognizedFunds });
                
                // 显示成功通知
                if (FundUtils && typeof FundUtils.showNotification === 'function') {
                    FundUtils.showNotification(`成功删除基金: ${deletedFund.fund_name}`, 'success');
                } else {
                    alert(`成功删除基金: ${deletedFund.fund_name}`);
                }
                
                console.log('删除操作完成');
            } catch (error) {
                console.error('删除基金失败:', error);
                if (FundUtils && typeof FundUtils.showNotification === 'function') {
                    FundUtils.showNotification('删除失败，请重试', 'error');
                } else {
                    alert('删除失败，请重试');
                }
            }
        } else {
            console.log('用户取消删除操作');
        }
        
        console.log('=== deleteFund 调用结束 ===');
    },

    /**
     * 设置拖拽上传
     */
    setupDragDrop() {
        const uploadArea = document.getElementById('upload-area');
        if (!uploadArea) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => {
                uploadArea.classList.remove('dragover');
            });
        });

        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type.startsWith('image/')) {
                    // 检查文件大小
                    if (file.size > 10 * 1024 * 1024) {
                        FundUtils.showNotification('图片文件过大，请选择小于10MB的图片', 'error');
                        return;
                    }

                    const reader = new FileReader();
                    reader.onload = (event) => {
                        this.currentImage = event.target.result;
                        this.showPreview();
                        this.recognizeFunds();
                    };
                    reader.readAsDataURL(file);
                } else {
                    FundUtils.showNotification('请上传图片文件', 'error');
                }
            }
        });
    }
};

// 将 FundScreenshot 暴露给全局作用域，使 HTML 中的 onclick 事件可以访问
window.FundScreenshot = FundScreenshot;
