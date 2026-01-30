/**
 * 设置模块 - 表头管理
 */
const FundSettings = {
    /**
     * 打开设置面板
     */
    openModal() {
        document.getElementById('settings-panel').classList.add('open');
        this.renderColumnSettings();
    },

    /**
     * 关闭设置面板
     */
    closeModal() {
        document.getElementById('settings-panel').classList.remove('open');
    },

    /**
     * 渲染列设置
     */
    renderColumnSettings() {
        const container = document.getElementById('settings-body');

        container.innerHTML = `
            <div class="form-group">
                <label class="form-label">选择要显示的列（拖拽排序）</label>
                <div class="column-list" id="column-list">
                    ${FundState.columnConfig.map((col, index) => `
                        <div class="column-item" data-index="${index}" draggable="true">
                            <i class="bi bi-grip-vertical" style="cursor: move;"></i>
                            <input type="checkbox" 
                                   ${col.visible ? 'checked' : ''} 
                                   onchange="FundSettings.toggleColumn(${index})">
                            <span>${col.label}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        this.setupDragSort();
    },

    /**
     * 切换列显示
     */
    toggleColumn(index) {
        FundState.columnConfig[index].visible = !FundState.columnConfig[index].visible;
    },

    /**
     * 设置拖拽排序
     */
    setupDragSort() {
        const list = document.getElementById('column-list');
        let draggedItem = null;

        list.addEventListener('dragstart', (e) => {
            draggedItem = e.target.closest('.column-item');
            e.target.closest('.column-item').style.opacity = '0.5';
        });

        list.addEventListener('dragend', (e) => {
            e.target.closest('.column-item').style.opacity = '1';
            draggedItem = null;
        });

        list.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = this.getDragAfterElement(list, e.clientY);
            if (afterElement == null) {
                list.appendChild(draggedItem);
            } else {
                list.insertBefore(draggedItem, afterElement);
            }
        });
    },

    /**
     * 获取拖拽后的位置
     */
    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.column-item:not([style*="opacity: 0.5"])')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;

            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    },

    /**
     * 保存列设置
     */
    save() {
        // 更新顺序
        const list = document.getElementById('column-list');
        const items = list.querySelectorAll('.column-item');
        const newOrder = [];

        items.forEach(item => {
            const index = parseInt(item.dataset.index);
            newOrder.push(FundState.columnConfig[index]);
        });

        FundState.columnConfig = newOrder;
        FundTable.saveColumnConfig();
        FundTable.renderHeader();
        FundTable.renderData();

        FundUtils.showNotification('设置已保存', 'success');
        this.closeModal();
    },

    /**
     * 恢复默认设置
     */
    reset() {
        if (!confirm('确定要恢复默认设置吗？')) return;

        FundState.columnConfig = FundUtils.deepClone(FundConfig.defaultColumns);
        this.renderColumnSettings();
    }
};
