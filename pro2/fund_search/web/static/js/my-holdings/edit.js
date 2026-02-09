/**
 * 基金编辑模块
 */
const FundEdit = {
    currentFund: null,

    /**
     * 打开编辑模态框
     */
    openModal(fund) {
        this.currentFund = fund;
        this.renderForm();
        
        const modal = document.getElementById('edit-modal');
        if (modal) {
            modal.classList.add('active');
        }
    },

    /**
     * 关闭编辑模态框
     */
    closeModal() {
        const modal = document.getElementById('edit-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        this.currentFund = null;
    },

    /**
     * 渲染编辑表单
     */
    async renderForm() {
        const formBody = document.getElementById('edit-form-body');
        if (!formBody || !this.currentFund) return;

        // 检查基金名称是否为空或无效（如"基金xxx"格式）
        let fundName = this.currentFund.fund_name || '';
        const fundCode = this.currentFund.fund_code;
        
        // 如果基金名称为空或者是默认格式（如"基金100055"），尝试从API获取正确名称
        if (!fundName || fundName === '' || fundName === `基金${fundCode}` || (fundName.includes('基金') && fundName.includes(fundCode))) {
            try {
                const response = await fetch(`/api/fund/${fundCode}`);
                const result = await response.json();
                if (result.success && result.data && result.data.fund_name) {
                    fundName = result.data.fund_name;
                    // 更新 currentFund 以便后续使用
                    this.currentFund.fund_name = fundName;
                }
            } catch (error) {
                console.error('获取基金名称失败:', error);
            }
        }

        formBody.innerHTML = `
            <div class="form-group">
                <label for="edit-fund-code">基金代码</label>
                <input type="text" id="edit-fund-code" value="${fundCode}" class="form-control" maxlength="6" placeholder="请输入6位基金代码">
                <div id="fund-code-validation" class="validation-message" style="display: none;"></div>
            </div>
            <div class="form-group">
                <label for="edit-fund-name">基金名称</label>
                <input type="text" id="edit-fund-name" value="${fundName}" class="form-control" placeholder="请输入基金名称">
            </div>
            <div class="form-group">
                <label for="edit-holding-shares">持有份额</label>
                <input type="number" id="edit-holding-shares" value="${this.currentFund.holding_shares || 0}" step="0.0001" class="form-control">
            </div>
            <div class="form-group">
                <label for="edit-cost-price">成本价</label>
                <input type="number" id="edit-cost-price" value="${this.currentFund.cost_price || 0}" step="0.0001" class="form-control">
            </div>
            <div class="form-group">
                <label for="edit-holding-amount">持仓金额</label>
                <input type="number" id="edit-holding-amount" value="${this.currentFund.holding_amount || 0}" step="0.01" class="form-control">
            </div>
            <div class="form-group">
                <label for="edit-buy-date">买入日期</label>
                <input type="date" id="edit-buy-date" value="${this.currentFund.buy_date || ''}" class="form-control">
            </div>
            <div class="form-group">
                <label for="edit-notes">备注</label>
                <textarea id="edit-notes" rows="3" class="form-control">${this.currentFund.notes || ''}</textarea>
            </div>
        `;

        // 确保基金名称字段正确显示
        setTimeout(() => {
            const fundNameInput = document.getElementById('edit-fund-name');
            if (fundNameInput && fundNameInput.value !== fundName) {
                fundNameInput.value = fundName;
                console.log(`初始化时修正基金名称显示: ${fundName}`);
            }
        }, 50);

        // 防抖函数
        function debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }

        // 基金代码验证和自动匹配
        const validateFundCode = debounce(async function() {
            const fundCodeInput = document.getElementById('edit-fund-code');
            const fundNameInput = document.getElementById('edit-fund-name');
            const validationDiv = document.getElementById('fund-code-validation');
            
            const fundCode = fundCodeInput.value.trim();
            
            // 清除之前的验证状态
            validationDiv.style.display = 'none';
            fundCodeInput.classList.remove('valid', 'invalid');
            
            // 基本格式验证
            if (!fundCode) {
                return;
            }
            
            if (fundCode.length !== 6 || !/^\d{6}$/.test(fundCode)) {
                validationDiv.textContent = '基金代码必须是6位数字';
                validationDiv.className = 'validation-message error';
                validationDiv.style.display = 'block';
                fundCodeInput.classList.add('invalid');
                return;
            }
            
            // 显示加载状态
            validationDiv.textContent = '正在验证基金代码...';
            validationDiv.className = 'validation-message loading';
            validationDiv.style.display = 'block';
            
            try {
                // 调用API验证基金代码
                const response = await fetch(`/api/fund/${fundCode}`);
                const result = await response.json();
                
                if (result.success && result.data) {
                    // 基金代码有效，自动填充基金名称
                    const fundName = result.data.fund_name || `基金${fundCode}`;
                    fundNameInput.value = fundName;
                    
                    // 多重确保UI更新
                    fundNameInput.dispatchEvent(new Event('input', { bubbles: true }));
                    fundNameInput.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // 强制刷新显示
                    setTimeout(() => {
                        fundNameInput.focus();
                        fundNameInput.blur();
                    }, 10);
                    
                    validationDiv.textContent = `✓ 找到基金: ${fundName}`;
                    validationDiv.className = 'validation-message success';
                    fundCodeInput.classList.add('valid');
                } else {
                    // 基金代码无效
                    validationDiv.textContent = '未找到对应的基金代码';
                    validationDiv.className = 'validation-message error';
                    fundCodeInput.classList.add('invalid');
                    
                    // 清空基金名称
                    fundNameInput.value = '';
                }
            } catch (error) {
                console.error('基金代码验证失败:', error);
                validationDiv.textContent = '验证失败，请稍后重试';
                validationDiv.className = 'validation-message error';
                fundCodeInput.classList.add('invalid');
                
                // 清空基金名称
                fundNameInput.value = '';
            }
        }, 500); // 500ms防抖延迟

        // 绑定金额计算
        const sharesInput = document.getElementById('edit-holding-shares');
        const priceInput = document.getElementById('edit-cost-price');
        const amountInput = document.getElementById('edit-holding-amount');

        const updateAmount = () => {
            const shares = parseFloat(sharesInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            amountInput.value = (shares * price).toFixed(2);
        };

        sharesInput?.addEventListener('input', updateAmount);
        priceInput?.addEventListener('input', updateAmount);
        
        // 绑定基金代码输入事件
        const fundCodeInput = document.getElementById('edit-fund-code');
        if (fundCodeInput) {
            fundCodeInput.addEventListener('input', function(e) {
                // 限制只能输入数字
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
                // 触发验证
                validateFundCode();
            });
            
            // 输入完成后的额外验证（失去焦点时）
            fundCodeInput.addEventListener('blur', validateFundCode);
        }
    },

    /**
     * 保存编辑
     */
    async save() {
        if (!this.currentFund) return;

        const fundCodeInput = document.getElementById('edit-fund-code');
        const fundNameInput = document.getElementById('edit-fund-name');
        const fundCode = fundCodeInput?.value;
        const fundName = fundNameInput?.value;
        const holdingShares = parseFloat(document.getElementById('edit-holding-shares')?.value) || 0;
        const costPrice = parseFloat(document.getElementById('edit-cost-price')?.value) || 0;
        const holdingAmount = parseFloat(document.getElementById('edit-holding-amount')?.value) || 0;
        const buyDate = document.getElementById('edit-buy-date')?.value;
        const notes = document.getElementById('edit-notes')?.value;

        // 验证基金代码
        if (!fundCode) {
            FundUtils.showNotification('基金代码不能为空', 'error');
            return;
        }

        if (fundCode.length !== 6 || !/^\d{6}$/.test(fundCode)) {
            FundUtils.showNotification('基金代码必须是6位数字', 'error');
            fundCodeInput.focus();
            return;
        }

        // 检查基金代码是否有效（通过CSS类判断）
        if (fundCodeInput.classList.contains('invalid')) {
            FundUtils.showNotification('请输入有效的基金代码', 'error');
            fundCodeInput.focus();
            return;
        }

        if (!fundName) {
            FundUtils.showNotification('基金名称不能为空', 'error');
            fundNameInput.focus();
            return;
        }

        try {
            const response = await fetch(`/api/holdings/${fundCode}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: 'default_user',
                    fund_code: fundCode,
                    fund_name: fundName,
                    holding_shares: holdingShares,
                    cost_price: costPrice,
                    holding_amount: holdingAmount,
                    buy_date: buyDate,
                    notes: notes
                })
            });

            const data = await response.json();

            if (data.success) {
                FundUtils.showNotification('保存成功', 'success');
                this.closeModal();
                // 刷新数据
                FundApp.refreshData();
            } else {
                FundUtils.showNotification('保存失败: ' + (data.error || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('保存基金失败:', error);
            FundUtils.showNotification('保存失败: 网络错误', 'error');
        }
    }
};
