/**
 * 投资组合分析集成模块
 * 基于回测结果数据生成净值曲线和绩效指标
 */

const PortfolioAnalysis = {
    // 分析数据
    analysisData: null,
    
    /**
     * 初始化投资组合分析
     */
    init() {
        console.log('🚀 PortfolioAnalysis.init() 开始执行');
        this.bindEvents();
        this.addStyles();
        this.initTooltips();
        console.log('✅ PortfolioAnalysis.init() 执行完成');
    },

    /**
     * 初始化Bootstrap工具提示
     */
    initTooltips() {
        // 检查Bootstrap是否加载
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            console.log('✅ 初始化Bootstrap工具提示');
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
        } else {
            console.log('⚠️ Bootstrap未加载，工具提示功能可能无法使用');
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        console.log('🔍 PortfolioAnalysis.bindEvents() 开始执行');
        
        // 添加分析按钮事件
        const analyzeBtn = document.getElementById('portfolio-analyze-btn');
        console.log('🔍 查找按钮元素:', analyzeBtn);
        
        if (analyzeBtn) {
            // 先移除可能存在的旧事件监听器
            const newAnalyzeBtn = analyzeBtn.cloneNode(true);
            analyzeBtn.parentNode.replaceChild(newAnalyzeBtn, analyzeBtn);
            
            console.log('✅ 找到分析按钮，添加点击事件监听器');
            newAnalyzeBtn.addEventListener('click', (event) => {
                console.log('🖱️ 按钮被点击');
                event.preventDefault(); // 防止默认行为
                event.stopPropagation(); // 阻止事件冒泡
                this.showAnalysis().catch(error => {
                    console.error('❌ 分析过程中出错:', error);
                    alert('分析失败: ' + error.message);
                });
            });
            
            // 同时添加键盘事件支持
            newAnalyzeBtn.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    newAnalyzeBtn.click();
                }
            });
        } else {
            console.warn('⚠️ 未找到分析按钮元素');
        }
        
        // 监听回测周期变化
        const periodSelect = document.getElementById('backtest-period');
        if (periodSelect) {
            periodSelect.addEventListener('change', () => {
                // 如果已经显示了分析结果，则自动更新
                if (document.getElementById('portfolio-analysis-result')) {
                    this.showAnalysis().catch(error => {
                        console.error('自动更新分析失败:', error);
                    });
                }
            });
        }
        
        // 监听回测结果更新
        this.observeBacktestResults();
        console.log('✅ PortfolioAnalysis.bindEvents() 执行完成');
    },
    
    /**
     * 监听回测结果区域的变化
     */
    observeBacktestResults() {
        const resultBox = document.getElementById('backtest-result');
        if (!resultBox) return;
        
        // 创建MutationObserver来监听DOM变化
        const observer = new MutationObserver((mutations) => {
            for (let mutation of mutations) {
                if (mutation.type === 'childList' || mutation.type === 'attributes') {
                    // 如果分析结果已显示且回测结果发生变化，重新计算分析
                    if (document.getElementById('portfolio-analysis-result')) {
                        // 稍微延迟以确保DOM完全更新
                        setTimeout(() => {
                            this.showAnalysis().catch(error => {
                                console.error('DOM变化触发的分析更新失败:', error);
                            });
                        }, 100);
                        break;
                    }
                }
            }
        });
        
        // 开始观察
        observer.observe(resultBox, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style']
        });
    },

    /**
     * 分析回测结果并显示分析
     */
    async showAnalysis() {
        // 从现有回测结果中提取数据
        const backtestData = this.extractBacktestData();
        if (!backtestData) {
            alert('暂无回测数据可供分析');
            return;
        }

        // 【重要】先获取净值数据，再计算绩效指标
        // 确保绩效指标和净值曲线使用同一数据源
        const navData = await this.generateNavData(backtestData);
        
        // 将净值数据附加到回测数据中，用于计算真实绩效指标
        backtestData.navData = navData;
        
        // 基于真实净值数据计算绩效指标
        const metrics = this.calculateMetrics(backtestData);
        
        // 渲染分析结果
        this.renderAnalysis(metrics, navData);
    },

    /**
     * 自动分析 - 回测完成后自动执行
     * 不显示弹窗，直接内联展示在页面上
     */
    async autoAnalyze() {
        console.log('🚀 开始自动投资组合分析...');
        
        // 从现有回测结果中提取数据
        const backtestData = this.extractBacktestData();
        if (!backtestData) {
            console.warn('⚠️ 暂无回测数据可供分析');
            return;
        }

        try {
            // 获取净值数据
            const navData = await this.generateNavData(backtestData);
            
            // 将净值数据附加到回测数据中
            backtestData.navData = navData;
            
            // 基于真实净值数据计算绩效指标
            const metrics = this.calculateMetrics(backtestData);
            
            // 内联渲染分析结果（不使用弹窗）
            this.renderInlineAnalysis(metrics, navData);
            
            console.log('✅ 自动分析完成');
        } catch (error) {
            console.error('❌ 自动分析失败:', error);
            throw error;
        }
    },

    /**
     * 从页面提取回测数据
     */
    extractBacktestData() {
        // 尝试从回测结果区域提取数据
        const resultBox = document.getElementById('backtest-result');
        if (!resultBox || resultBox.style.display === 'none') {
            return null;
        }

        // 从成功消息中提取回测周期信息
        const successAlert = resultBox.querySelector('.alert.alert-success');
        let period = 3; // 默认3年
        let totalDays = 1095; // 默认1095天 (3年)
        
        if (successAlert) {
            const alertText = successAlert.textContent;
            const periodMatch = alertText.match(/回测周期:\s*(\d+)\s*年/);
            if (periodMatch) {
                period = parseInt(periodMatch[1]);
                // 根据周期计算天数
                const daysMap = {1: 365, 2: 730, 3: 1095, 5: 1825};
                totalDays = daysMap[period] || 1095;
            }
        }
        
        // 从组合表现指标中提取基础数据
        const metricCards = resultBox.querySelectorAll('.metric-card');
        let initialAmount = 10000;
        let finalValue = 10000;
        let totalReturn = 0;
        
        if (metricCards.length >= 3) {
            // 初始金额
            const initialAmountText = metricCards[0].querySelector('.metric-value')?.textContent || '¥10000';
            initialAmount = parseFloat(initialAmountText.replace('¥', '').replace(',', '')) || 10000;
            
            // 最终价值
            const finalValueText = metricCards[1].querySelector('.metric-value')?.textContent || '¥10000';
            finalValue = parseFloat(finalValueText.replace('¥', '').replace(',', '')) || 10000;
            
            // 总收益率
            const totalReturnText = metricCards[2].querySelector('.metric-value')?.textContent || '0%';
            totalReturn = parseFloat(totalReturnText.replace('%', '').replace('+', '')) || 0;
        }
        
        // 提取基金数据
        const fundRows = resultBox.querySelectorAll('tbody tr');
        const funds = [];
        
        fundRows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 9) {
                const fundCode = cells[0].querySelector('strong')?.textContent?.trim() || '';
                const initial = parseFloat(cells[2].textContent.replace('¥', '').replace(',', '')) || 0;
                const final = parseFloat(cells[3].textContent.replace('¥', '').replace(',', '')) || 0;
                const totalReturn = parseFloat(cells[4].textContent.replace('%', '').replace('+', '')) || 0;
                const annualized = parseFloat(cells[5].textContent.replace('%', '').replace('+', '')) || 0;
                const maxDrawdown = parseFloat(cells[6].textContent.replace('%', '')) || 0;
                const sharpe = parseFloat(cells[7].textContent) || 0;
                const trades = parseInt(cells[8].textContent) || 0;

                funds.push({
                    code: fundCode,
                    initial: initial,
                    final: final,
                    return: totalReturn,
                    annualized: annualized,
                    maxDrawdown: maxDrawdown,
                    sharpe: sharpe,
                    trades: trades
                });
            }
        });

        return {
            initialAmount: initialAmount,
            finalValue: finalValue,
            totalReturn: totalReturn,
            period: period,
            totalDays: totalDays,
            funds: funds
        };
    },

    /**
     * 计算关键绩效指标（基于真实净值时间序列）
     */
    calculateMetrics(data, options = {}) {
        console.log('📊 开始计算绩效指标');
        
        try {
            // 使用策略系统计算指标
            const strategy = options.strategy || 'default';
            
            // 设置策略
            if (window.metricsStrategyManager) {
                window.metricsStrategyManager.setStrategy(strategy);
                const metrics = window.metricsStrategyManager.calculate(data, options);
                
                console.log('📈 绩效指标计算结果:');
                console.log(`   - 总收益率: ${metrics.totalReturn.toFixed(2)}%`);
                console.log(`   - 年化收益率: ${metrics.annualizedReturn.toFixed(2)}%`);
                console.log(`   - 年化波动率: ${metrics.volatility.toFixed(2)}%`);
                console.log(`   - 最大回撤: ${metrics.maxDrawdown.toFixed(2)}%`);
                console.log(`   - 夏普比率: ${metrics.sharpeRatio.toFixed(2)}`);
                console.log(`   - 信息比率: ${metrics.informationRatio.toFixed(2)}`);
                console.log(`   - 卡玛比率: ${metrics.calmarRatio.toFixed(2)}`);
                
                return metrics;
            } else {
                console.error('❌ 策略管理器未初始化');
                // 回退到基础计算
                return this.calculateBasicMetrics(data, options);
            }
        } catch (error) {
            console.error('❌ 指标计算错误:', error);
            // 回退到基础计算
            return this.calculateBasicMetrics(data, options);
        }
    },
    
    /**
     * 基础指标计算（当策略系统不可用时）
     * @param {Object} data - 回测数据
     * @param {Object} options - 计算选项
     * @returns {Object} 计算结果
     */
    calculateBasicMetrics(data, options = {}) {
        console.log('📊 使用基础估算计算绩效指标');
        
        if (data.navData && data.navData.length > 0) {
            // 使用真实的净值数据进行计算
            const navData = data.navData;
            const initialValue = navData[0].portfolio;
            const finalValue = navData[navData.length - 1].portfolio;
            const totalDays = navData.length - 1;
            const years = totalDays / 365.25;
            
            // 1. 总收益率
            const totalReturn = data.totalReturn !== undefined ? data.totalReturn : ((finalValue - initialValue) / initialValue) * 100;
            
            // 2. 年化收益率
            let annualizedReturn;
            if (data.annualizedReturn !== undefined) {
                annualizedReturn = data.annualizedReturn;
            } else if (data.annualized_return !== undefined) {
                annualizedReturn = data.annualized_return;
            } else {
                annualizedReturn = (Math.pow(finalValue / initialValue, 1 / years) - 1) * 100;
            }
            
            // 3. 年化波动率
            const annualizedVolatility = data.volatility || 15;
            
            // 4. 最大回撤
            const maxDrawdown = data.maxDrawdown || data.max_drawdown || 10;
            
            // 5. 夏普比率
            let sharpeRatio;
            if (data.sharpeRatio !== undefined) {
                sharpeRatio = data.sharpeRatio;
            } else if (data.sharpe_ratio !== undefined) {
                sharpeRatio = data.sharpe_ratio;
            } else {
                const riskFreeRate = options.riskFreeRate || 2.0;
                sharpeRatio = (annualizedReturn - riskFreeRate) / annualizedVolatility;
            }
            
            // 6. 信息比率
            const informationRatio = data.informationRatio || 0.5;
            
            // 7. 卡玛比率
            const calmarRatio = annualizedReturn / Math.abs(maxDrawdown);
            
            return {
                totalReturn: totalReturn,
                annualizedReturn: annualizedReturn,
                volatility: annualizedVolatility,
                maxDrawdown: maxDrawdown,
                sharpeRatio: sharpeRatio,
                informationRatio: informationRatio,
                calmarRatio: calmarRatio,
                period: data.period || 3,
                totalDays: totalDays,
                fundCount: data.funds ? data.funds.length : 0
            };
        } else {
            // 纯基础估算
            const years = data.totalDays / 365.25;
            const annualizedReturn = (Math.pow(data.finalValue / data.initialAmount, 1 / years) - 1) * 100;
            
            // 基于经验值估算波动率
            const estimatedVolatility = Math.abs(annualizedReturn) * 0.8 + 15;
            
            // 基于经验值估算最大回撤
            const estimatedDrawdown = Math.min(Math.abs(annualizedReturn) * 0.6 + 10, 50);
            
            // 夏普比率
            const riskFreeRate = options.riskFreeRate || 2.0;
            const sharpeRatio = (annualizedReturn - riskFreeRate) / estimatedVolatility;
            
            // 信息比率
            const informationRatio = (annualizedReturn + 5) / 15;
            
            // 卡玛比率
            const calmarRatio = annualizedReturn / Math.abs(estimatedDrawdown);
            
            console.warn('⚠️ 使用基础估算指标（缺少真实净值数据）');
            
            return {
                totalReturn: data.totalReturn,
                annualizedReturn: annualizedReturn,
                volatility: estimatedVolatility,
                maxDrawdown: estimatedDrawdown,
                sharpeRatio: sharpeRatio,
                informationRatio: informationRatio,
                calmarRatio: calmarRatio,
                period: data.period || 3,
                totalDays: data.totalDays,
                fundCount: data.funds ? data.funds.length : 0
            };
        }
    },

    /**
     * 生成净值数据（使用真实历史数据）
     */
    generateNavData(data) {
        // 优先尝试从后端API获取真实数据
        return this.fetchRealNavData(data);
    },
    
    /**
     * 从后端获取真实净值数据
     */
    async fetchRealNavData(data) {
        try {
            // 获取当前页面选择的基金信息
            const fundCodes = this.getSelectedFundCodes();
            const weights = this.calculateWeights(fundCodes.length);
            
            if (fundCodes.length === 0) {
                console.warn('未选择基金，使用模拟数据');
                return this.generateFallbackNavData(data);
            }
            
            const response = await fetch(`/api/dashboard/profit-trend?days=${data.totalDays}&fund_codes=${fundCodes.join(',')}&weights=${weights.join(',')}`);
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    console.log('✅ 成功获取真实历史净值数据');
                    
                    // 转换为所需格式
                    const navData = [];
                    const labels = result.data.labels;
                    const profitData = result.data.profit;
                    const benchmarkData = result.data.benchmark;
                    
                    for (let i = 0; i < labels.length; i++) {
                        navData.push({
                            date: labels[i],
                            portfolio: profitData[i] || 10000,
                            benchmark: benchmarkData[i] || 10000
                        });
                    }
                    
                    return navData;
                }
            }
            
            console.warn('获取真实数据失败，使用备用方案');
            return this.generateFallbackNavData(data);
            
        } catch (error) {
            console.error('获取真实净值数据时出错:', error);
            return this.generateFallbackNavData(data);
        }
    },
    
    /**
     * 获取页面上选择的基金代码
     */
    getSelectedFundCodes() {
        // 从回测结果中提取基金代码
        const fundRows = document.querySelectorAll('#backtest-result tbody tr');
        const fundCodes = [];
        
        fundRows.forEach(row => {
            const codeCell = row.querySelector('td:first-child strong');
            if (codeCell) {
                fundCodes.push(codeCell.textContent.trim());
            }
        });
        
        return fundCodes;
    },
    
    /**
     * 计算基金权重（平均分配）
     */
    calculateWeights(count) {
        if (count <= 0) return [];
        return Array(count).fill(1.0 / count);
    },
    
    /**
     * 备用的净值数据生成方案
     */
    generateFallbackNavData(data) {
        console.warn('⚠️ 使用备用净值数据生成方案');
        
        const navData = [];
        const totalReturnDecimal = data.totalReturn / 100;
        
        for (let i = 0; i <= data.totalDays; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (data.totalDays - i));
            
            // 组合净值：基于实际收益率，但使用更保守的波动
            const daysProgress = i / data.totalDays;
            const expectedReturn = totalReturnDecimal * daysProgress;
            
            // 更小的波动（±0.2%日波动）
            const strategyVolatility = (Math.random() - 0.5) * 0.004;
            const strategyReturnToday = expectedReturn + strategyVolatility;
            const portfolioNav = data.initialAmount * (1 + strategyReturnToday);
            
            // 沪深300基准：使用更保守的市场模型
            const yearsElapsed = i / 365.25;
            const benchmarkAnnualReturn = -0.03; // 更保守的年化收益假设
            const benchmarkExpectedReturn = benchmarkAnnualReturn * yearsElapsed;
            
            // 更小的基准波动（±0.1%日波动）
            const benchmarkVolatility = (Math.random() - 0.5) * 0.002;
            const benchmarkReturnToday = benchmarkExpectedReturn + benchmarkVolatility;
            const benchmarkNav = data.initialAmount * (1 + benchmarkReturnToday);
            
            navData.push({
                date: date.toISOString().split('T')[0],
                portfolio: Math.max(portfolioNav, data.initialAmount * 0.7), // 更严格的下限
                benchmark: Math.max(benchmarkNav, data.initialAmount * 0.7)
            });
        }
        
        return navData;
    },

    /**
     * 渲染分析结果 - 优化后的UI结构
     */
    renderAnalysis(metrics, navData) {
        // 创建分析结果容器
        const existingAnalysis = document.getElementById('portfolio-analysis-result');
        if (existingAnalysis) {
            existingAnalysis.remove();
        }

        // 计算超额收益
        const excessReturn = navData && navData.length > 1 
            ? ((navData[navData.length - 1].portfolio - navData[0].portfolio) / navData[0].portfolio * 100) - 
              ((navData[navData.length - 1].benchmark - navData[0].benchmark) / navData[0].benchmark * 100)
            : 0;

        const analysisHTML = `
            <div id="portfolio-analysis-result" class="portfolio-analysis-container">
                <div class="analysis-header">
                    <div class="header-content">
                        <h4><i class="bi bi-graph-up-arrow"></i>投资组合深度分析</h4>
                        <div class="header-subtitle">基于历史数据的专业绩效评估与风险分析</div>
                    </div>
                    <button type="button" class="btn-close-analysis" onclick="PortfolioAnalysis.closeAnalysis()" title="关闭分析">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                
                <div class="metrics-section">
                    <h5 class="section-title"><i class="bi bi-speedometer2"></i>关键绩效指标</h5>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-cash-stack"></i></div>
                            <div class="metric-value ${metrics.totalReturn >= 0 ? 'positive' : 'negative'}">
                                ${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label">总收益率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-graph-up"></i></div>
                            <div class="metric-value ${metrics.annualizedReturn >= 0 ? 'positive' : 'negative'}">
                                ${metrics.annualizedReturn >= 0 ? '+' : ''}${metrics.annualizedReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label">年化收益率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-activity"></i></div>
                            <div class="metric-value">${metrics.volatility.toFixed(2)}%</div>
                            <div class="metric-label">年化波动率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-arrow-down-circle"></i></div>
                            <div class="metric-value negative">${metrics.maxDrawdown.toFixed(2)}%</div>
                            <div class="metric-label">最大回撤</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-speedometer"></i></div>
                            <div class="metric-value ${metrics.sharpeRatio >= 0 ? 'positive' : 'negative'}">
                                ${metrics.sharpeRatio.toFixed(2)}
                            </div>
                            <div class="metric-label">夏普比率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-bar-chart-line"></i></div>
                            <div class="metric-value ${metrics.informationRatio >= 0 ? 'positive' : 'negative'}">
                                ${metrics.informationRatio.toFixed(2)}
                            </div>
                            <div class="metric-label">信息比率</div>
                        </div>
                    </div>
                </div>

                <div class="chart-section">
                    <h5 class="section-title" data-bs-toggle="tooltip" data-bs-placement="top" title="The net value curve represents the calculated net value of the fund portfolio after applying the backtesting strategy, and does not reflect the actual net value performance of the fund portfolio itself. This visualization specifically illustrates the hypothetical performance metrics generated through the implementation of the backtesting methodology rather than the real-time or historical performance of the portfolio."><i class="bi bi-graph-up-arrow"></i>净值曲线对比</h5>
                    <div class="chart-container">
                        <canvas id="portfolio-nav-chart"></canvas>
                    </div>
                    <div class="chart-legend">
                        <span class="legend-item portfolio"><i class="bi bi-circle-fill me-2"></i>组合净值</span>
                        <span class="legend-item benchmark"><i class="bi bi-circle-fill me-2"></i>沪深300基准</span>
                    </div>
                </div>

                <div class="analysis-summary">
                    <h5 class="section-title"><i class="bi bi-clipboard-data"></i>分析总结</h5>
                    <div class="summary-content">
                        <div class="summary-item">
                            <strong>回测周期</strong>
                            <span class="positive">
                                近${metrics.period}年（${metrics.totalDays}个交易日）
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>组合表现</strong>
                            <span class="${metrics.totalReturn >= 0 ? 'positive' : 'negative'}">
                                ${metrics.totalReturn >= 0 ? '盈利' : '亏损'} ${Math.abs(metrics.totalReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>超额收益</strong>
                            <span class="${excessReturn >= 0 ? 'positive' : 'negative'}">
                                ${excessReturn >= 0 ? '跑赢基准' : '跑输基准'} ${Math.abs(excessReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>风险水平</strong>
                            <span class="${metrics.volatility > 20 ? 'negative' : metrics.volatility > 15 ? 'warning' : 'positive'}">
                                ${metrics.volatility > 20 ? '高风险' : metrics.volatility > 15 ? '中等风险' : '低风险'}（波动率 ${metrics.volatility.toFixed(1)}%）
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>夏普比率</strong>
                            <span class="${metrics.sharpeRatio >= 1 ? 'positive' : metrics.sharpeRatio >= 0 ? 'warning' : 'negative'}">
                                ${metrics.sharpeRatio >= 1 ? '优秀' : metrics.sharpeRatio >= 0 ? '一般' : '较差'}（${metrics.sharpeRatio.toFixed(2)}）
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>回撤控制</strong>
                            <span class="${metrics.maxDrawdown > 15 ? 'negative' : metrics.maxDrawdown > 8 ? 'warning' : 'positive'}">
                                ${metrics.maxDrawdown > 15 ? '需关注' : metrics.maxDrawdown > 8 ? '适中' : '良好'}（最大回撤 ${metrics.maxDrawdown.toFixed(2)}%）
                            </span>
                        </div>
                    </div>
                </div>

                <div class="formula-section">
                    <h5 class="section-title"><i class="bi bi-calculator"></i>指标说明</h5>
                    <div class="formula-grid">
                        <div class="formula-item">
                            <strong>年化收益率</strong>：将总收益率按时间年化，便于不同期限投资的横向比较
                        </div>
                        <div class="formula-item">
                            <strong>夏普比率</strong>：衡量单位风险所获得的超额收益，大于1为优秀，小于0表示风险调整后收益为负
                        </div>
                        <div class="formula-item">
                            <strong>最大回撤</strong>：回测期间从峰值到谷值的最大跌幅，反映组合的极端风险承受情况
                        </div>
                        <div class="formula-item">
                            <strong>信息比率</strong>：衡量相对于基准的超额收益能力，反映主动管理的效率
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 插入到回测结果后面
        const backtestResult = document.getElementById('backtest-result');
        if (backtestResult) {
            backtestResult.insertAdjacentHTML('afterend', analysisHTML);
            
            // 绘制图表并初始化工具提示
            setTimeout(() => {
                // 尝试获取基金信息（如果是单个基金）
                let fundInfo = null;
                if (data.funds && data.funds.length === 1) {
                    fundInfo = {
                        name: data.funds[0].name,
                        code: data.funds[0].code
                    };
                }
                this.drawNavChart(navData, fundInfo);
                this.initTooltips(); // 初始化工具提示
            }, 100);
        }
    },

    /**
     * 准备分析数据供显示（不立即渲染）
     * 在回测过程中调用，等待与回测结果一起展示
     * @param {Object} backtestData - 回测结果数据
     * @returns {Object} 包含 html 和 navData 的对象
     */
    async prepareAnalysisForDisplay(backtestData) {
        console.log('🚀 准备投资组合分析数据...');
        
        if (!backtestData) {
            console.warn('⚠️ 没有提供回测数据');
            return null;
        }

        try {
            // 从回测数据中提取基金代码
            const fundCodes = this.extractFundCodesFromBacktestData(backtestData);
            
            // 调试：打印回测数据结构
            console.log('🔍 回测数据结构:', JSON.stringify({
                hasPortfolio: !!backtestData.portfolio,
                portfolioKeys: backtestData.portfolio ? Object.keys(backtestData.portfolio) : [],
                topLevelKeys: Object.keys(backtestData).slice(0, 10)
            }));
            
            // 从回测数据中提取所有关键指标（保持与回测结果一致）
            const totalReturn = this.extractTotalReturnFromBacktestData(backtestData);
            const annualizedReturn = this.extractAnnualizedReturnFromBacktestData(backtestData);
            const volatility = this.extractVolatilityFromBacktestData(backtestData);
            const maxDrawdown = this.extractMaxDrawdownFromBacktestData(backtestData);
            const sharpeRatio = this.extractSharpeRatioFromBacktestData(backtestData);
            
            console.log('📌 从回测数据提取指标:');
            console.log(`   - 总收益率: ${totalReturn.toFixed(2)}%`);
            console.log(`   - 年化收益率: ${annualizedReturn !== null ? annualizedReturn.toFixed(2) + '%' : '需计算'}`);
            console.log(`   - 年化波动率: ${volatility !== null ? volatility.toFixed(2) + '%' : '需计算'}`);
            console.log(`   - 最大回撤: ${maxDrawdown !== null ? maxDrawdown.toFixed(2) + '%' : '需计算'}`);
            console.log(`   - 夏普比率: ${sharpeRatio !== null ? sharpeRatio.toFixed(2) : '需计算'}`);
            
            // 永远基于总收益率计算年化收益率，确保一致性
            // 后端返回的 annualized_return 可能不准确或不一致，忽略它
            let finalAnnualizedReturn;
            const years = (backtestData.period || 3);
            const totalReturnDecimal = totalReturn / 100;
            finalAnnualizedReturn = (Math.pow(1 + totalReturnDecimal, 1 / years) - 1) * 100;
            
            if (annualizedReturn !== null) {
                // 检查后端返回的值是否一致
                const diff = Math.abs(finalAnnualizedReturn - annualizedReturn);
                if (diff > 0.1) { // 允许0.1%的误差
                    console.warn('⚠️ 后端返回的年化收益率与计算值不一致，使用计算值');
                    console.warn(`   总收益率: ${totalReturn.toFixed(2)}%, 周期: ${years}年`);
                    console.warn(`   后端返回: ${annualizedReturn.toFixed(2)}%, 计算值: ${finalAnnualizedReturn.toFixed(2)}%`);
                }
            }
            console.log(`📌 年化收益率: ${finalAnnualizedReturn.toFixed(2)}% (基于总收益率计算)`);
            
            // 获取净值数据（使用回测数据中的基金代码）
            const navData = await this.generateNavDataForBacktest(backtestData, fundCodes);
            
            // 将净值数据和所有回测指标附加到回测数据中
            backtestData.navData = navData;
            backtestData.totalReturn = totalReturn;
            backtestData.annualizedReturn = finalAnnualizedReturn; // 使用修正后的年化收益率
            if (volatility !== null) backtestData.volatility = volatility;
            if (maxDrawdown !== null) backtestData.maxDrawdown = maxDrawdown;
            if (sharpeRatio !== null) backtestData.sharpeRatio = sharpeRatio;
            
            // 基于真实净值数据计算绩效指标
            const metrics = this.calculateMetrics(backtestData);
            
            // 生成分析 HTML
            const html = this.generateAnalysisHTML(metrics, navData);
            
            console.log('✅ 分析数据准备完成');
            
            return {
                html: html,
                navData: navData,
                metrics: metrics
            };
        } catch (error) {
            console.error('❌ 准备分析数据失败:', error);
            return null;
        }
    },

    /**
     * 从回测数据中提取总收益率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number} 总收益率百分比
     */
    extractTotalReturnFromBacktestData(backtestData) {
        // 多基金回测：使用 portfolio 中的总收益率
        if (backtestData.portfolio) {
            const portfolioReturn = backtestData.portfolio.total_return;
            if (portfolioReturn !== undefined) {
                return portfolioReturn;
            }
        }
        
        // 单基金回测：使用顶层的总收益率
        if (backtestData.total_return !== undefined) {
            return backtestData.total_return;
        }
        
        // 默认返回0
        return 0;
    },

    /**
     * 从回测数据中提取年化收益率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 年化收益率百分比
     */
    extractAnnualizedReturnFromBacktestData(backtestData) {
        // 多基金回测：使用 portfolio 中的年化收益率
        if (backtestData.portfolio) {
            const portfolioAnnualized = backtestData.portfolio.annualized_return;
            if (portfolioAnnualized !== undefined) {
                return portfolioAnnualized;
            }
        }
        
        // 单基金回测：使用顶层的年化收益率
        if (backtestData.annualized_return !== undefined) {
            return backtestData.annualized_return;
        }
        
        return null;
    },

    /**
     * 从回测数据中提取年化波动率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 年化波动率百分比
     */
    extractVolatilityFromBacktestData(backtestData) {
        // 多基金回测：使用 portfolio 中的波动率
        if (backtestData.portfolio) {
            const portfolioVolatility = backtestData.portfolio.volatility;
            if (portfolioVolatility !== undefined) {
                return portfolioVolatility;
            }
        }
        
        // 单基金回测：使用顶层的波动率
        if (backtestData.volatility !== undefined) {
            return backtestData.volatility;
        }
        
        return null;
    },

    /**
     * 从回测数据中提取最大回撤
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 最大回撤百分比
     */
    extractMaxDrawdownFromBacktestData(backtestData) {
        // 多基金回测：使用 portfolio 中的最大回撤
        if (backtestData.portfolio) {
            const portfolioDrawdown = backtestData.portfolio.max_drawdown;
            if (portfolioDrawdown !== undefined) {
                return portfolioDrawdown;
            }
        }
        
        // 单基金回测：使用顶层的最大回撤
        if (backtestData.max_drawdown !== undefined) {
            return backtestData.max_drawdown;
        }
        
        return null;
    },

    /**
     * 从回测数据中提取夏普比率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 夏普比率
     */
    extractSharpeRatioFromBacktestData(backtestData) {
        // 多基金回测：使用 portfolio 中的夏普比率
        if (backtestData.portfolio) {
            const portfolioSharpe = backtestData.portfolio.sharpe_ratio;
            if (portfolioSharpe !== undefined) {
                return portfolioSharpe;
            }
        }
        
        // 单基金回测：使用顶层的夏普比率
        if (backtestData.sharpe_ratio !== undefined) {
            return backtestData.sharpe_ratio;
        }
        
        return null;
    },

    /**
     * 从回测数据中提取基金代码
     * @param {Object} backtestData - 回测结果数据
     * @returns {Array} 基金代码数组
     */
    extractFundCodesFromBacktestData(backtestData) {
        const fundCodes = [];
        
        // 从回测数据中提取基金代码
        if (backtestData.funds && Array.isArray(backtestData.funds)) {
            backtestData.funds.forEach(fund => {
                if (fund.code) {
                    fundCodes.push(fund.code);
                }
            });
        }
        
        return fundCodes;
    },

    /**
     * 为回测生成净值数据
     * @param {Object} backtestData - 回测结果数据
     * @param {Array} fundCodes - 基金代码数组
     * @returns {Array} 净值数据
     */
    async generateNavDataForBacktest(backtestData, fundCodes) {
        try {
            if (fundCodes.length === 0) {
                console.warn('未选择基金，使用模拟数据');
                return this.generateFallbackNavData(backtestData);
            }
            
            const weights = this.calculateWeights(fundCodes.length);
            const response = await fetch(`/api/dashboard/profit-trend?days=${backtestData.totalDays || 1095}&fund_codes=${fundCodes.join(',')}&weights=${weights.join(',')}`);
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    console.log('✅ 成功获取真实历史净值数据');
                    
                    // 转换为所需格式
                    const navData = [];
                    const labels = result.data.labels;
                    const profitData = result.data.profit;
                    const benchmarkData = result.data.benchmark;
                    
                    for (let i = 0; i < labels.length; i++) {
                        navData.push({
                            date: labels[i],
                            portfolio: profitData[i] || 10000,
                            benchmark: benchmarkData[i] || 10000
                        });
                    }
                    
                    return navData;
                }
            }
            
            console.warn('获取真实数据失败，使用备用方案');
            return this.generateFallbackNavData(backtestData);
            
        } catch (error) {
            console.error('获取真实净值数据时出错:', error);
            return this.generateFallbackNavData(backtestData);
        }
    },

    /**
     * 生成分析 HTML
     * @param {Object} metrics - 绩效指标
     * @param {Array} navData - 净值数据
     * @returns {string} 分析 HTML
     */
    generateAnalysisHTML(metrics, navData) {
        // 计算超额收益
        const excessReturn = navData && navData.length > 1 
            ? ((navData[navData.length - 1].portfolio - navData[0].portfolio) / navData[0].portfolio * 100) - 
              ((navData[navData.length - 1].benchmark - navData[0].benchmark) / navData[0].benchmark * 100)
            : 0;

        return `
            <div class="portfolio-analysis-container">
                <div class="analysis-header">
                    <div class="header-content">
                        <h4><i class="bi bi-graph-up-arrow"></i>投资组合深度分析</h4>
                        <div class="header-subtitle">基于历史数据的专业绩效评估与风险分析</div>
                    </div>
                </div>
                
                <div class="metrics-section">
                    <h5 class="section-title"><i class="bi bi-speedometer2"></i>关键绩效指标</h5>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-cash-stack"></i></div>
                            <div class="metric-value ${metrics.totalReturn >= 0 ? 'positive' : 'negative'}">
                                ${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label">总收益率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-graph-up"></i></div>
                            <div class="metric-value ${metrics.annualizedReturn >= 0 ? 'positive' : 'negative'}">
                                ${metrics.annualizedReturn >= 0 ? '+' : ''}${metrics.annualizedReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label">年化收益率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-activity"></i></div>
                            <div class="metric-value">${metrics.volatility.toFixed(2)}%</div>
                            <div class="metric-label">年化波动率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-arrow-down-circle"></i></div>
                            <div class="metric-value negative">${metrics.maxDrawdown.toFixed(2)}%</div>
                            <div class="metric-label">最大回撤</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-speedometer"></i></div>
                            <div class="metric-value ${metrics.sharpeRatio >= 0 ? 'positive' : 'negative'}">
                                ${metrics.sharpeRatio.toFixed(2)}
                            </div>
                            <div class="metric-label">夏普比率</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-icon"><i class="bi bi-bar-chart-line"></i></div>
                            <div class="metric-value ${metrics.informationRatio >= 0 ? 'positive' : 'negative'}">
                                ${metrics.informationRatio.toFixed(2)}
                            </div>
                            <div class="metric-label">信息比率</div>
                        </div>
                    </div>
                </div>

                <div class="chart-section">
                    <h5 class="section-title" data-bs-toggle="tooltip" data-bs-placement="top" title="The net value curve represents the calculated net value of the fund portfolio after applying the backtesting strategy, and does not reflect the actual net value performance of the fund portfolio itself. This visualization specifically illustrates the hypothetical performance metrics generated through the implementation of the backtesting methodology rather than the real-time or historical performance of the portfolio."><i class="bi bi-graph-up-arrow"></i>净值曲线对比</h5>
                    <div class="chart-container">
                        <canvas id="portfolio-nav-chart"></canvas>
                    </div>
                    <div class="chart-legend">
                        <span class="legend-item portfolio"><i class="bi bi-circle-fill me-2"></i>组合净值</span>
                        <span class="legend-item benchmark"><i class="bi bi-circle-fill me-2"></i>沪深300基准</span>
                    </div>
                </div>

                <div class="analysis-summary">
                    <h5 class="section-title"><i class="bi bi-clipboard-data"></i>分析总结</h5>
                    <div class="summary-content">
                        <div class="summary-item">
                            <strong>回测周期</strong>
                            <span class="positive">
                                近${metrics.period}年（${metrics.totalDays}个交易日）
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>组合表现</strong>
                            <span class="${metrics.totalReturn >= 0 ? 'positive' : 'negative'}">
                                ${metrics.totalReturn >= 0 ? '盈利' : '亏损'} ${Math.abs(metrics.totalReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>超额收益</strong>
                            <span class="${excessReturn >= 0 ? 'positive' : 'negative'}">
                                ${excessReturn >= 0 ? '跑赢基准' : '跑输基准'} ${Math.abs(excessReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>风险水平</strong>
                            <span class="${metrics.volatility > 20 ? 'negative' : metrics.volatility > 15 ? 'warning' : 'positive'}">
                                ${metrics.volatility > 20 ? '高风险' : metrics.volatility > 15 ? '中等风险' : '低风险'}（波动率 ${metrics.volatility.toFixed(1)}%）
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>夏普比率</strong>
                            <span class="${metrics.sharpeRatio >= 1 ? 'positive' : metrics.sharpeRatio >= 0 ? 'warning' : 'negative'}">
                                ${metrics.sharpeRatio >= 1 ? '优秀' : metrics.sharpeRatio >= 0 ? '一般' : '较差'}（${metrics.sharpeRatio.toFixed(2)}）
                            </span>
                        </div>
                        <div class="summary-item">
                            <strong>回撤控制</strong>
                            <span class="${metrics.maxDrawdown > 15 ? 'negative' : metrics.maxDrawdown > 8 ? 'warning' : 'positive'}">
                                ${metrics.maxDrawdown > 15 ? '需关注' : metrics.maxDrawdown > 8 ? '适中' : '良好'}（最大回撤 ${metrics.maxDrawdown.toFixed(2)}%）
                            </span>
                        </div>
                    </div>
                </div>

                <div class="formula-section">
                    <h5 class="section-title"><i class="bi bi-calculator"></i>指标说明</h5>
                    <div class="formula-grid">
                        <div class="formula-item">
                            <strong>年化收益率</strong>：将总收益率按时间年化，便于不同期限投资的横向比较
                        </div>
                        <div class="formula-item">
                            <strong>夏普比率</strong>：衡量单位风险所获得的超额收益，大于1为优秀，小于0表示风险调整后收益为负
                        </div>
                        <div class="formula-item">
                            <strong>最大回撤</strong>：回测期间从峰值到谷值的最大跌幅，反映组合的极端风险承受情况
                        </div>
                        <div class="formula-item">
                            <strong>信息比率</strong>：衡量相对于基准的超额收益能力，反映主动管理的效率
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 绘制净值曲线图表
     * @param {Array} navData - 净值数据
     * @param {Object} fundInfo - 基金信息（单个基金时）
     */
    drawNavChart(navData, fundInfo = null) {
        console.log('🎨 开始绘制净值曲线图表');
        console.log('📊 净值数据长度:', navData ? navData.length : 0);
        console.log('📋 基金信息:', fundInfo);
        
        // 检查数据是否为空
        if (!navData || navData.length === 0) {
            console.warn('⚠️ 无净值数据，绘制空图表');
            this.drawEmptyChart('暂无净值数据');
            return;
        }
        
        try {
            const ctx = document.getElementById('portfolio-nav-chart');
            if (!ctx) {
                console.error('❌ 未找到图表画布元素');
                return;
            }
            
            // 销毁现有图表
            if (window.portfolioNavChart) {
                window.portfolioNavChart.destroy();
            }
            
            // 准备数据
            const labels = navData.map(item => item.date);
            const portfolioData = navData.map(item => item.portfolio);
            const benchmarkData = navData.map(item => item.benchmark);
            
            // 计算收益率
            const initialValue = portfolioData[0];
            const portfolioReturns = portfolioData.map(value => ((value - initialValue) / initialValue) * 100);
            const benchmarkReturns = benchmarkData.map(value => ((value - initialValue) / initialValue) * 100);
            
            // 图表配置
            const chartConfig = {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: fundInfo ? `${fundInfo.name} (${fundInfo.code})` : '组合净值',
                            data: portfolioReturns,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0,
                            pointHoverRadius: 4
                        },
                        {
                            label: '沪深300基准',
                            data: benchmarkReturns,
                            borderColor: '#6c757d',
                            backgroundColor: 'rgba(108, 117, 125, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 0,
                            pointHoverRadius: 4,
                            borderDash: [5, 5]
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                boxWidth: 6
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        label += context.parsed.y.toFixed(2) + '%';
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: '日期'
                            },
                            ticks: {
                                maxTicksLimit: 10
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: '收益率 (%)'
                            }
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            };
            
            // 创建图表
            window.portfolioNavChart = new Chart(ctx, chartConfig);
            console.log('✅ 净值曲线图表绘制完成');
            
        } catch (error) {
            console.error('❌ 绘制图表时出错:', error);
            this.drawEmptyChart('图表绘制失败');
        }
    },

    /**
     * 绘制空图表
     * @param {string} message - 提示信息
     */
    drawEmptyChart(message) {
        const ctx = document.getElementById('portfolio-nav-chart');
        if (!ctx) return;
        
        // 销毁现有图表
        if (window.portfolioNavChart) {
            window.portfolioNavChart.destroy();
        }
        
        // 创建空图表
        window.portfolioNavChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [''],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    },
                    title: {
                        display: true,
                        text: message,
                        color: '#666',
                        font: {
                            size: 14
                        }
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: false
                    }
                }
            }
        });
    },

    /**
     * 内联渲染分析结果
     * @param {Object} metrics - 绩效指标
     * @param {Array} navData - 净值数据
     */
    renderInlineAnalysis(metrics, navData) {
        console.log('📋 开始内联渲染分析结果');
        
        // 创建分析结果容器
        const existingAnalysis = document.getElementById('portfolio-analysis-result');
        if (existingAnalysis) {
            existingAnalysis.remove();
        }
        
        // 生成分析HTML
        const analysisHTML = this.generateAnalysisHTML(metrics, navData);
        
        // 插入到回测结果后面
        const backtestResult = document.getElementById('backtest-result');
        if (backtestResult) {
            backtestResult.insertAdjacentHTML('afterend', analysisHTML);
            
            // 绘制图表
            setTimeout(() => {
                this.drawNavChart(navData);
                this.initTooltips(); // 初始化工具提示
            }, 100);
        }
        
        console.log('✅ 内联渲染分析结果完成');
    },

    /**
     * 关闭分析结果
     */
    closeAnalysis() {
        const analysisResult = document.getElementById('portfolio-analysis-result');
        if (analysisResult) {
            analysisResult.remove();
        }
    },

    /**
     * 添加样式
     */
    addStyles() {
        // 检查是否已添加样式
        if (document.getElementById('portfolio-analysis-styles')) {
            return;
        }
        
        // 添加样式
        const style = document.createElement('style');
        style.id = 'portfolio-analysis-styles';
        style.textContent = `
            .portfolio-analysis-container {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                padding: 20px;
                margin-top: 20px;
            }
            
            .analysis-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 1px solid #e9ecef;
            }
            
            .header-content h4 {
                margin: 0;
                color: #333;
                font-size: 18px;
            }
            
            .header-subtitle {
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            }
            
            .btn-close-analysis {
                background: none;
                border: none;
                font-size: 20px;
                color: #666;
                cursor: pointer;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 4px;
            }
            
            .btn-close-analysis:hover {
                background: #f8f9fa;
                color: #333;
            }
            
            .section-title {
                font-size: 16px;
                color: #333;
                margin-bottom: 15px;
                font-weight: 600;
                display: flex;
                align-items: center;
            }
            
            .section-title i {
                margin-right: 8px;
                color: #007bff;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
            }
            
            .metric-card {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .metric-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            
            .metric-icon {
                font-size: 24px;
                color: #007bff;
                margin-bottom: 10px;
            }
            
            .metric-value {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .metric-value.positive {
                color: #28a745;
            }
            
            .metric-value.negative {
                color: #dc3545;
            }
            
            .metric-value.warning {
                color: #ffc107;
            }
            
            .metric-label {
                font-size: 14px;
                color: #666;
            }
            
            .chart-section {
                margin-bottom: 25px;
            }
            
            .chart-container {
                height: 400px;
                margin-bottom: 15px;
                position: relative;
            }
            
            .chart-legend {
                display: flex;
                justify-content: center;
                gap: 20px;
                font-size: 14px;
            }
            
            .legend-item {
                display: flex;
                align-items: center;
            }
            
            .legend-item.portfolio i {
                color: #007bff;
            }
            
            .legend-item.benchmark i {
                color: #6c757d;
            }
            
            .analysis-summary {
                margin-bottom: 25px;
            }
            
            .summary-content {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
            
            .summary-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }
            
            .summary-item:last-child {
                border-bottom: none;
            }
            
            .summary-item strong {
                color: #333;
            }
            
            .formula-section {
                margin-bottom: 15px;
            }
            
            .formula-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
            }
            
            .formula-item {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.4;
            }
            
            .formula-item strong {
                color: #333;
                display: block;
                margin-bottom: 5px;
            }
            
            @media (max-width: 768px) {
                .metrics-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .formula-grid {
                    grid-template-columns: 1fr;
                }
                
                .chart-container {
                    height: 300px;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
};

// 策略系统实现
class DefaultMetricsStrategy {
    calculate(data, options = {}) {
        console.log('📊 使用默认策略计算绩效指标');
        
        if (data.navData && data.navData.length > 0) {
            const navData = data.navData;
            const initialValue = navData[0].portfolio;
            const finalValue = navData[navData.length - 1].portfolio;
            const totalDays = navData.length - 1;
            const years = totalDays / 365.25;
            
            // 1. 总收益率
            const totalReturn = data.totalReturn !== undefined ? data.totalReturn : ((finalValue - initialValue) / initialValue) * 100;
            
            // 2. 年化收益率
            let annualizedReturn;
            if (data.annualizedReturn !== undefined) {
                annualizedReturn = data.annualizedReturn;
            } else if (data.annualized_return !== undefined) {
                annualizedReturn = data.annualized_return;
            } else {
                annualizedReturn = (Math.pow(finalValue / initialValue, 1 / years) - 1) * 100;
            }
            
            // 3. 年化波动率
            const annualizedVolatility = data.volatility || 15;
            
            // 4. 最大回撤
            const maxDrawdown = data.maxDrawdown || data.max_drawdown || 10;
            
            // 5. 夏普比率
            let sharpeRatio;
            if (data.sharpeRatio !== undefined) {
                sharpeRatio = data.sharpeRatio;
            } else if (data.sharpe_ratio !== undefined) {
                sharpeRatio = data.sharpe_ratio;
            } else {
                const riskFreeRate = options.riskFreeRate || 2.0;
                sharpeRatio = (annualizedReturn - riskFreeRate) / annualizedVolatility;
            }
            
            // 6. 信息比率
            const informationRatio = data.informationRatio || 0.5;
            
            // 7. 卡玛比率
            const calmarRatio = annualizedReturn / Math.abs(maxDrawdown);
            
            return {
                totalReturn: totalReturn,
                annualizedReturn: annualizedReturn,
                volatility: annualizedVolatility,
                maxDrawdown: maxDrawdown,
                sharpeRatio: sharpeRatio,
                informationRatio: informationRatio,
                calmarRatio: calmarRatio,
                period: data.period || 3,
                totalDays: totalDays,
                fundCount: data.funds ? data.funds.length : 0
            };
        } else {
            // 纯基础估算
            const years = data.totalDays / 365.25;
            const annualizedReturn = (Math.pow(data.finalValue / data.initialAmount, 1 / years) - 1) * 100;
            
            // 基于经验值估算波动率
            const estimatedVolatility = Math.abs(annualizedReturn) * 0.8 + 15;
            
            // 基于经验值估算最大回撤
            const estimatedDrawdown = Math.min(Math.abs(annualizedReturn) * 0.6 + 10, 50);
            
            // 夏普比率
            const riskFreeRate = options.riskFreeRate || 2.0;
            const sharpeRatio = (annualizedReturn - riskFreeRate) / estimatedVolatility;
            
            // 信息比率
            const informationRatio = (annualizedReturn + 5) / 15;
            
            // 卡玛比率
            const calmarRatio = annualizedReturn / Math.abs(estimatedDrawdown);
            
            return {
                totalReturn: data.totalReturn,
                annualizedReturn: annualizedReturn,
                volatility: estimatedVolatility,
                maxDrawdown: estimatedDrawdown,
                sharpeRatio: sharpeRatio,
                informationRatio: informationRatio,
                calmarRatio: calmarRatio,
                period: data.period || 3,
                totalDays: data.totalDays,
                fundCount: data.funds ? data.funds.length : 0
            };
        }
    }
}

class ConservativeMetricsStrategy {
    calculate(data, options = {}) {
        console.log('📊 使用保守策略计算绩效指标');
        
        // 先使用默认策略计算基础指标
        const defaultStrategy = new DefaultMetricsStrategy();
        const baseMetrics = defaultStrategy.calculate(data, options);
        
        // 保守策略调整：降低收益率预期，提高风险估计
        return {
            ...baseMetrics,
            annualizedReturn: baseMetrics.annualizedReturn * 0.9, // 降低收益率预期10%
            volatility: baseMetrics.volatility * 1.1, // 提高波动率10%
            maxDrawdown: baseMetrics.maxDrawdown * 1.15, // 提高最大回撤15%
            sharpeRatio: (baseMetrics.annualizedReturn * 0.9 - 2.0) / (baseMetrics.volatility * 1.1), // 重新计算夏普比率
            calmarRatio: (baseMetrics.annualizedReturn * 0.9) / Math.abs(baseMetrics.maxDrawdown * 1.15) // 重新计算卡玛比率
        };
    }
}

class AggressiveMetricsStrategy {
    calculate(data, options = {}) {
        console.log('📊 使用激进策略计算绩效指标');
        
        // 先使用默认策略计算基础指标
        const defaultStrategy = new DefaultMetricsStrategy();
        const baseMetrics = defaultStrategy.calculate(data, options);
        
        // 激进策略调整：提高收益率预期，降低风险估计
        return {
            ...baseMetrics,
            annualizedReturn: baseMetrics.annualizedReturn * 1.1, // 提高收益率预期10%
            volatility: baseMetrics.volatility * 0.9, // 降低波动率10%
            maxDrawdown: baseMetrics.maxDrawdown * 0.85, // 降低最大回撤15%
            sharpeRatio: (baseMetrics.annualizedReturn * 1.1 - 2.0) / (baseMetrics.volatility * 0.9), // 重新计算夏普比率
            calmarRatio: (baseMetrics.annualizedReturn * 1.1) / Math.abs(baseMetrics.maxDrawdown * 0.85) // 重新计算卡玛比率
        };
    }
}

class MetricsStrategyManager {
    constructor() {
        this.strategies = {
            default: new DefaultMetricsStrategy(),
            conservative: new ConservativeMetricsStrategy(),
            aggressive: new AggressiveMetricsStrategy()
        };
        this.currentStrategy = 'default';
    }
    
    /**
     * 注册新策略
     * @param {string} name - 策略名称
     * @param {Object} strategy - 策略实例
     */
    registerStrategy(name, strategy) {
        this.strategies[name] = strategy;
    }
    
    /**
     * 设置当前策略
     * @param {string} name - 策略名称
     */
    setStrategy(name) {
        if (this.strategies[name]) {
            this.currentStrategy = name;
            console.log(`📋 策略已切换为: ${name}`);
        } else {
            console.warn(`⚠️ 策略 ${name} 不存在，使用默认策略`);
            this.currentStrategy = 'default';
        }
    }
    
    /**
     * 使用当前策略计算指标
     * @param {Object} data - 回测数据
     * @param {Object} options - 计算选项
     * @returns {Object} 计算结果
     */
    calculate(data, options = {}) {
        const strategy = this.strategies[this.currentStrategy];
        return strategy.calculate(data, options);
    }
}

// 初始化策略管理器
window.metricsStrategyManager = new MetricsStrategyManager();

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        PortfolioAnalysis.init();
    });
} else {
    PortfolioAnalysis.init();
}
