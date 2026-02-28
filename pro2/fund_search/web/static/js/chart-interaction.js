/**
 * 图表联动交互模块
 * 实现点击矩阵/列表 → 高亮图表 → 滚动定位 → 更新数据的联动效果
 */

class ChartInteractionManager {
    constructor() {
        this.currentHighlightedPair = null;
        this.highlightColors = {
            fund1: 'rgba(239, 68, 68, 0.8)',   // 红色高亮
            fund2: 'rgba(16, 185, 129, 0.8)'   // 绿色高亮
        };
        this.originalColors = new Map();
    }

    /**
     * 高亮指定基金对的图表
     * @param {string} fund1Code - 基金1代码
     * @param {string} fund2Code - 基金2代码
     * @param {string} fund1Name - 基金1名称
     * @param {string} fund2Name - 基金2名称
     */
    highlightPair(fund1Code, fund2Code, fund1Name, fund2Name) {
        console.log(`🎯 高亮基金对: ${fund1Name} vs ${fund2Name}`);
        
        this.currentHighlightedPair = { fund1Code, fund2Code, fund1Name, fund2Name };
        
        // 1. 滚动到图表区域
        this.scrollToCharts();
        
        // 2. 高亮净值走势图表
        this.highlightLineChart(fund1Code, fund2Code);
        
        // 3. 高亮散点图
        this.highlightScatterChart(fund1Code, fund2Code);
        
        // 4. 更新分布图
        this.updateDistributionChart(fund1Code, fund2Code);
        
        // 5. 显示联动提示
        this.showInteractionHint(fund1Name, fund2Name);
    }

    /**
     * 滚动到图表区域
     */
    scrollToCharts() {
        const chartsSection = document.getElementById('interactive-charts-section');
        if (chartsSection) {
            chartsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // 展开所有折叠的图表
            if (typeof collapsibleChartManager !== 'undefined') {
                collapsibleChartManager.expandAll();
            }
        }
    }

    /**
     * 高亮净值走势图表
     */
    highlightLineChart(fund1Code, fund2Code) {
        const chart = correlationCharts.line;
        if (!chart || !chart.data || !chart.data.datasets) return;

        // 保存原始颜色
        if (!this.originalColors.has('line')) {
            this.originalColors.set('line', chart.data.datasets.map(ds => ({
                borderColor: ds.borderColor,
                backgroundColor: ds.backgroundColor
            })));
        }

        // 高亮相关基金，淡化其他
        chart.data.datasets.forEach((dataset, index) => {
            const isFund1 = dataset.label && dataset.label.includes(fund1Code);
            const isFund2 = dataset.label && dataset.label.includes(fund2Code);
            
            if (isFund1) {
                dataset.borderColor = this.highlightColors.fund1;
                dataset.backgroundColor = this.highlightColors.fund1.replace('0.8', '0.2');
                dataset.borderWidth = 3;
                dataset.order = 0; // 置顶
            } else if (isFund2) {
                dataset.borderColor = this.highlightColors.fund2;
                dataset.backgroundColor = this.highlightColors.fund2.replace('0.8', '0.2');
                dataset.borderWidth = 3;
                dataset.order = 1;
            } else {
                // 淡化其他基金
                dataset.borderColor = 'rgba(200, 200, 200, 0.3)';
                dataset.backgroundColor = 'rgba(200, 200, 200, 0.05)';
                dataset.borderWidth = 1;
                dataset.order = 10;
            }
        });

        chart.update('none');
    }


    /**
     * 更新分布图
     */
    updateDistributionChart(fund1Code, fund2Code) {
        // 触发懒加载获取新数据
        const event = new CustomEvent('loadPairDetail', {
            detail: { fund1: fund1Code, fund2: fund2Code }
        });
        document.dispatchEvent(event);
    }

    /**
     * 显示联动提示
     */
    showInteractionHint(fund1Name, fund2Name) {
        // 创建临时提示
        const hint = document.createElement('div');
        hint.className = 'interaction-hint';
        hint.innerHTML = `
            <i class="bi bi-arrow-down-circle"></i>
            <span>正在查看: <strong>${fund1Name}</strong> vs <strong>${fund2Name}</strong></span>
            <button onclick="chartInteractionManager.resetHighlight()">重置</button>
        `;
        
        document.body.appendChild(hint);
        
        // 3秒后自动移除
        setTimeout(() => {
            hint.remove();
        }, 5000);
    }

    /**
     * 重置高亮
     */
    resetHighlight() {
        console.log('🔄 重置图表高亮');
        
        // 恢复净值走势图表
        const lineColors = this.originalColors.get('line');
        if (lineColors && correlationCharts.line) {
            correlationCharts.line.data.datasets.forEach((dataset, index) => {
                if (lineColors[index]) {
                    dataset.borderColor = lineColors[index].borderColor;
                    dataset.backgroundColor = lineColors[index].backgroundColor;
                    dataset.borderWidth = 2;
                    dataset.order = index;
                }
            });
            correlationCharts.line.update('none');
        }
        
        this.currentHighlightedPair = null;
        
        // 移除提示
        document.querySelectorAll('.interaction-hint').forEach(el => el.remove());
    }

    /**
     * 添加矩阵单元格点击事件
     */
    attachMatrixEvents() {
        const matrix = document.querySelector('.correlation-matrix');
        if (!matrix) return;

        matrix.addEventListener('click', (e) => {
            const cell = e.target.closest('.corr-cell');
            if (!cell) return;

            const row = cell.closest('tr');
            const fund1Code = row?.dataset.fundCode;
            const fund2Code = cell.dataset.fundCode;
            
            if (fund1Code && fund2Code && fund1Code !== fund2Code) {
                const fund1Name = row.querySelector('th')?.textContent || fund1Code;
                const fund2Name = cell.dataset.fundName || fund2Code;
                
                this.highlightPair(fund1Code, fund2Code, fund1Name, fund2Name);
            }
        });

        // 添加悬停效果
        matrix.addEventListener('mouseover', (e) => {
            const cell = e.target.closest('.corr-cell');
            if (cell) {
                cell.style.transform = 'scale(1.1)';
                cell.style.zIndex = '10';
            }
        });

        matrix.addEventListener('mouseout', (e) => {
            const cell = e.target.closest('.corr-cell');
            if (cell) {
                cell.style.transform = '';
                cell.style.zIndex = '';
            }
        });
    }

    /**
     * 添加组合列表点击事件
     */
    attachPairsListEvents() {
        const pairsList = document.getElementById('top-pairs-content');
        if (!pairsList) return;

        pairsList.addEventListener('click', (e) => {
            const pairItem = e.target.closest('.pair-item');
            if (!pairItem) return;

            const fund1Code = pairItem.dataset.fund1;
            const fund2Code = pairItem.dataset.fund2;
            const fund1Name = pairItem.dataset.fund1Name;
            const fund2Name = pairItem.dataset.fund2Name;

            if (fund1Code && fund2Code) {
                this.highlightPair(fund1Code, fund2Code, fund1Name, fund2Name);
            }
        });
    }
}

// 创建全局实例
const chartInteractionManager = new ChartInteractionManager();

// 添加CSS动画
const chartInteractionStyle = document.createElement('style');
chartInteractionStyle.textContent = `
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    .interaction-hint {
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 9999px;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        z-index: 1000;
        animation: slideUp 0.3s ease;
    }
    
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(100%); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    
    .interaction-hint button {
        background: rgba(255,255,255,0.2);
        border: none;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        cursor: pointer;
        font-size: 0.875rem;
    }
    
    .interaction-hint button:hover {
        background: rgba(255,255,255,0.3);
    }
    
    .corr-cell {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .pair-item {
        cursor: pointer;
    }
`;
document.head.appendChild(chartInteractionStyle);

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartInteractionManager;
}
