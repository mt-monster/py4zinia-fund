/**
 * 图表加载进度指示器模块
 * 提供骨架屏、进度条、分阶段加载功能
 */

class ChartLoadingManager {
    constructor() {
        this.progress = 0;
        this.currentStage = 0;
        this.stages = [
            { id: 'basic', name: '基础数据', icon: 'bi-database' },
            { id: 'matrix', name: '相关性矩阵', icon: 'bi-table' },
            { id: 'charts', name: '交互式图表', icon: 'bi-bar-chart-line' },
            { id: 'complete', name: '完成', icon: 'bi-check-circle' }
        ];
        this.container = null;
        this.isActive = false;
    }

    /**
     * 初始化进度指示器
     */
    init() {
        this.createProgressBar();
        this.injectStyles();
    }

    /**
     * 创建进度条DOM
     */
    createProgressBar() {
        const existing = document.getElementById('chart-loading-progress');
        if (existing) existing.remove();

        this.container = document.createElement('div');
        this.container.id = 'chart-loading-progress';
        this.container.className = 'loading-progress-container';
        this.container.innerHTML = `
            <div class="loading-progress-header">
                <div class="loading-progress-title">
                    <i class="bi bi-arrow-repeat"></i>
                    <span>正在加载分析数据...</span>
                </div>
                <div class="loading-progress-percent">0%</div>
            </div>
            <div class="loading-progress-bar">
                <div class="loading-progress-fill" style="width: 0%"></div>
            </div>
            <div class="loading-stages">
                ${this.stages.map((stage, index) => `
                    <div class="loading-stage" data-stage="${index}">
                        <i class="bi ${stage.icon}"></i>
                        <span>${stage.name}</span>
                    </div>
                `).join('')}
            </div>
        `;
        document.body.appendChild(this.container);
    }

    /**
     * 注入样式（如果CSS文件未加载）
     */
    injectStyles() {
        if (document.getElementById('chart-loading-styles')) return;
        
        const link = document.createElement('link');
        link.id = 'chart-loading-styles';
        link.rel = 'stylesheet';
        link.href = '/static/css/chart-loading.css';
        document.head.appendChild(link);
    }

    /**
     * 显示进度指示器
     */
    show() {
        this.isActive = true;
        this.progress = 0;
        this.currentStage = 0;
        this.updateUI();
        this.container.classList.add('active');
    }

    /**
     * 隐藏进度指示器
     */
    hide() {
        this.isActive = false;
        setTimeout(() => {
            this.container.classList.remove('active');
        }, 500);
    }

    /**
     * 更新进度
     * @param {number} percent - 进度百分比 (0-100)
     * @param {string} detail - 详细说明
     */
    updateProgress(percent, detail = '') {
        this.progress = Math.min(100, Math.max(0, percent));
        this.updateUI();
        
        if (detail) {
            const titleEl = this.container.querySelector('.loading-progress-title span');
            if (titleEl) titleEl.textContent = detail;
        }
    }

    /**
     * 设置当前阶段
     * @param {number} stageIndex - 阶段索引
     */
    setStage(stageIndex) {
        this.currentStage = stageIndex;
        this.updateStageUI();
    }

    /**
     * 更新UI
     */
    updateUI() {
        const fill = this.container.querySelector('.loading-progress-fill');
        const percent = this.container.querySelector('.loading-progress-percent');
        
        if (fill) fill.style.width = `${this.progress}%`;
        if (percent) percent.textContent = `${Math.round(this.progress)}%`;
        
        this.updateStageUI();
    }

    /**
     * 更新阶段UI
     */
    updateStageUI() {
        const stageEls = this.container.querySelectorAll('.loading-stage');
        stageEls.forEach((el, index) => {
            el.classList.remove('active', 'completed');
            if (index < this.currentStage) {
                el.classList.add('completed');
                el.querySelector('i').className = 'bi bi-check-circle-fill';
            } else if (index === this.currentStage) {
                el.classList.add('active');
                el.querySelector('i').className = `bi ${this.stages[index].icon}`;
            } else {
                el.querySelector('i').className = `bi ${this.stages[index].icon}`;
            }
        });
    }

    /**
     * 创建骨架屏
     * @param {string} type - 骨架屏类型: 'chart' | 'matrix'
     * @param {number} count - 数量
     */
    createSkeletons(type = 'chart', count = 4) {
        const container = document.getElementById('interactive-charts-content');
        if (!container) return;

        container.innerHTML = '';
        
        if (type === 'chart') {
            for (let i = 0; i < count; i++) {
                container.appendChild(this.createChartSkeleton());
            }
        } else if (type === 'matrix') {
            container.appendChild(this.createMatrixSkeleton());
        }
    }

    /**
     * 创建图表骨架屏
     */
    createChartSkeleton() {
        const wrapper = document.createElement('div');
        wrapper.className = 'chart-skeleton-wrapper';
        wrapper.innerHTML = `
            <div class="chart-skeleton-header">
                <div class="chart-skeleton-icon"></div>
                <div class="chart-skeleton-title"></div>
            </div>
            <div class="chart-skeleton-body">
                <div class="chart-skeleton-chart"></div>
                <div class="chart-skeleton-legend">
                    <div class="chart-skeleton-legend-item"></div>
                    <div class="chart-skeleton-legend-item"></div>
                </div>
            </div>
        `;
        return wrapper;
    }

    /**
     * 创建矩阵骨架屏
     */
    createMatrixSkeleton() {
        const wrapper = document.createElement('div');
        wrapper.className = 'matrix-skeleton';
        
        // 创建8x8的骨架矩阵
        for (let i = 0; i < 8; i++) {
            const row = document.createElement('div');
            row.className = 'matrix-skeleton-row';
            for (let j = 0; j < 8; j++) {
                const cell = document.createElement('div');
                cell.className = `matrix-skeleton-cell ${j === 0 || i === 0 ? 'header' : ''}`;
                row.appendChild(cell);
            }
            wrapper.appendChild(row);
        }
        return wrapper;
    }

    /**
     * 分阶段加载包装器
     * @param {Function} callback - 加载完成的回调
     */
    async loadWithProgress(callback) {
        this.show();
        this.createSkeletons('chart', 4);
        
        try {
            // 阶段1: 基础数据 (0-30%)
            this.setStage(0);
            this.updateProgress(10, '正在获取基础数据...');
            await this.delay(300);
            
            this.updateProgress(20, '正在处理基金信息...');
            await this.delay(200);
            
            this.updateProgress(30, '基础数据加载完成');
            await this.delay(100);
            
            // 阶段2: 相关性矩阵 (30-60%)
            this.setStage(1);
            this.updateProgress(40, '正在计算相关性矩阵...');
            await this.delay(300);
            
            this.updateProgress(50, '正在生成矩阵数据...');
            await this.delay(200);
            
            this.updateProgress(60, '相关性矩阵生成完成');
            await this.delay(100);
            
            // 阶段3: 交互式图表 (60-90%)
            this.setStage(2);
            this.updateProgress(70, '正在加载图表数据...');
            await this.delay(400);
            
            this.updateProgress(80, '正在渲染交互式图表...');
            
            // 执行实际的回调函数
            if (callback) await callback();
            
            this.updateProgress(90, '图表渲染完成');
            await this.delay(200);
            
            // 阶段4: 完成 (90-100%)
            this.setStage(3);
            this.updateProgress(100, '分析数据加载完成！');
            await this.delay(500);
            
        } finally {
            this.hide();
        }
    }

    /**
     * 延迟函数
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 创建全局实例
const chartLoadingManager = new ChartLoadingManager();

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartLoadingManager;
}
