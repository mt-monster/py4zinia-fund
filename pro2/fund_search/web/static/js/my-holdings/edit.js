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
    renderForm() {
        const formBody = document.getElementById('edit-form-body');
        if (!formBody || !this.currentFund) return;

        formBody.innerHTML = `
            <div class="form-group">
                <label for="edit-fund-code">基金代码</label>
                <input type="text" id="edit-fund-code" value="${this.currentFund.fund_code}" readonly class="form-control readonly">
            </div>
            <div class="form-group">
                <label for="edit-fund-name">基金名称</label>
                <input type="text" id="edit-fund-name" value="${this.currentFund.fund_name || ''}" class="form-control">
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
    },

    /**
     * 保存编辑
     */
    async save() {
        if (!this.currentFund) return;

        const fundCode = document.getElementById('edit-fund-code')?.value;
        const fundName = document.getElementById('edit-fund-name')?.value;
        const holdingShares = parseFloat(document.getElementById('edit-holding-shares')?.value) || 0;
        const costPrice = parseFloat(document.getElementById('edit-cost-price')?.value) || 0;
        const holdingAmount = parseFloat(document.getElementById('edit-holding-amount')?.value) || 0;
        const buyDate = document.getElementById('edit-buy-date')?.value;
        const notes = document.getElementById('edit-notes')?.value;

        if (!fundCode) {
            FundUtils.showNotification('基金代码不能为空', 'error');
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
