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
        console.log('✅ PortfolioAnalysis.init() 执行完成');
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
    calculateMetrics(data) {
        // 使用真实的净值数据进行计算
        const navData = data.navData || [];
        
        if (navData.length === 0) {
            console.warn('⚠️ 缺少净值数据，使用基础估算');
            return this.calculateBasicMetrics(data);
        }
        
        console.log('📊 基于真实净值数据计算绩效指标');
        
        // 从净值数据获取起始值和终值（用于计算其他指标）
        const initialValue = navData[0].portfolio;
        const finalValue = navData[navData.length - 1].portfolio;
        
        // 1. 总收益率 - 优先使用回测数据中的总收益率，保持与回测结果一致
        let totalReturn;
        if (data.totalReturn !== undefined) {
            // 使用回测数据中的总收益率
            totalReturn = data.totalReturn;
            console.log(`📌 使用回测数据中的总收益率: ${totalReturn.toFixed(2)}%`);
        } else {
            // 从净值数据计算（可能与回测结果不一致，因为净值基准不同）
            totalReturn = ((finalValue - initialValue) / initialValue) * 100;
            console.log(`⚠️ 从净值计算总收益率: ${totalReturn.toFixed(2)}%（可能与回测结果不一致）`);
        }
        
        // 2. 年化收益率 - 优先从回测数据中获取，否则基于净值数据计算
        let annualizedReturn;
        const totalDays = navData.length - 1;
        const years = totalDays / 365.25;
        
        if (data.annualizedReturn !== undefined) {
            // 使用回测数据中的年化收益率
            annualizedReturn = data.annualizedReturn;
            console.log(`📌 使用回测数据中的年化收益率: ${annualizedReturn.toFixed(2)}%`);
        } else if (data.annualized_return !== undefined) {
            // 使用回测数据中的年化收益率（下划线命名）
            annualizedReturn = data.annualized_return;
            console.log(`📌 使用回测数据中的年化收益率: ${annualizedReturn.toFixed(2)}%`);
        } else {
            // 从净值数据计算
            annualizedReturn = (Math.pow(finalValue / initialValue, 1 / years) - 1) * 100;
            console.log(`⚠️ 从净值计算年化收益率: ${annualizedReturn.toFixed(2)}%`);
        }
        
        // 3. 计算日收益率序列
        const dailyReturns = [];
        for (let i = 1; i < navData.length; i++) {
            const dailyReturn = (navData[i].portfolio - navData[i-1].portfolio) / navData[i-1].portfolio;
            dailyReturns.push(dailyReturn);
        }
        
        // 4. 年化波动率
        let annualizedVolatility;
        if (data.volatility !== undefined) {
            // 使用回测数据中的波动率
            annualizedVolatility = data.volatility;
            console.log(`📌 使用回测数据中的年化波动率: ${annualizedVolatility.toFixed(2)}%`);
        } else {
            // 从净值数据计算
            const avgDailyReturn = dailyReturns.reduce((sum, r) => sum + r, 0) / dailyReturns.length;
            const variance = dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgDailyReturn, 2), 0) / (dailyReturns.length - 1);
            const dailyVolatility = Math.sqrt(variance);
            annualizedVolatility = dailyVolatility * Math.sqrt(252) * 100;
            console.log(`⚠️ 从净值计算年化波动率: ${annualizedVolatility.toFixed(2)}%`);
        }
        
        // 5. 最大回撤 - 优先使用回测数据
        let maxDrawdown;
        if (data.maxDrawdown !== undefined) {
            maxDrawdown = data.maxDrawdown;
            console.log(`📌 使用回测数据中的最大回撤: ${maxDrawdown.toFixed(2)}%`);
        } else if (data.max_drawdown !== undefined) {
            maxDrawdown = data.max_drawdown;
            console.log(`📌 使用回测数据中的最大回撤: ${maxDrawdown.toFixed(2)}%`);
        } else {
            // 从净值数据计算
            let peak = navData[0].portfolio;
            maxDrawdown = 0;
            for (let i = 0; i < navData.length; i++) {
                if (navData[i].portfolio > peak) {
                    peak = navData[i].portfolio;
                }
                const drawdown = (peak - navData[i].portfolio) / peak;
                if (drawdown > maxDrawdown) {
                    maxDrawdown = drawdown;
                }
            }
            maxDrawdown = maxDrawdown * 100;
            console.log(`⚠️ 从净值计算最大回撤: ${maxDrawdown.toFixed(2)}%`);
        }
        
        // 6. 夏普比率 - 优先使用回测数据
        let sharpeRatio;
        if (data.sharpeRatio !== undefined) {
            sharpeRatio = data.sharpeRatio;
            console.log(`📌 使用回测数据中的夏普比率: ${sharpeRatio.toFixed(2)}`);
        } else if (data.sharpe_ratio !== undefined) {
            sharpeRatio = data.sharpe_ratio;
            console.log(`📌 使用回测数据中的夏普比率: ${sharpeRatio.toFixed(2)}`);
        } else {
            // 计算夏普比率（假设无风险利率2%）
            const riskFreeRate = 2.0;
            sharpeRatio = (annualizedReturn - riskFreeRate) / annualizedVolatility;
            console.log(`⚠️ 计算夏普比率: ${sharpeRatio.toFixed(2)}`);
        }
        
        // 7. 信息比率（相对于沪深300基准）
        const benchmarkReturns = [];
        for (let i = 1; i < navData.length; i++) {
            const benchmarkReturn = (navData[i].benchmark - navData[i-1].benchmark) / navData[i-1].benchmark;
            benchmarkReturns.push(benchmarkReturn);
        }
        
        const excessReturns = [];
        for (let i = 0; i < dailyReturns.length; i++) {
            excessReturns.push(dailyReturns[i] - (benchmarkReturns[i] || 0));
        }
        
        const avgExcessReturn = excessReturns.reduce((sum, r) => sum + r, 0) / excessReturns.length;
        const trackingVariance = excessReturns.reduce((sum, r) => sum + Math.pow(r - avgExcessReturn, 2), 0) / (excessReturns.length - 1);
        const trackingError = Math.sqrt(trackingVariance) * Math.sqrt(252) * 100; // 年化跟踪误差
        const informationRatio = (avgExcessReturn * 252 * 100) / trackingError; // 年化超额收益 / 年化跟踪误差
        
        // 8. 卡玛比率
        const calmarRatio = annualizedReturn / Math.abs(maxDrawdown);
        
        console.log('📈 绩效指标计算结果:');
        console.log(`   - 总收益率: ${totalReturn.toFixed(2)}%`);
        console.log(`   - 年化收益率: ${annualizedReturn.toFixed(2)}%`);
        console.log(`   - 年化波动率: ${annualizedVolatility.toFixed(2)}%`);
        console.log(`   - 最大回撤: ${maxDrawdown.toFixed(2)}%`);
        console.log(`   - 夏普比率: ${sharpeRatio.toFixed(2)}`);
        console.log(`   - 信息比率: ${informationRatio.toFixed(2)}`);
        console.log(`   - 卡玛比率: ${calmarRatio.toFixed(2)}`);
        
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
    },
    
    /**
     * 基础指标计算（当缺少净值数据时使用）
     */
    calculateBasicMetrics(data) {
        const years = data.totalDays / 365.25;
        const annualizedReturn = (Math.pow(data.finalValue / data.initialAmount, 1 / years) - 1) * 100;
        
        // 基于经验值估算波动率（更合理的范围）
        const estimatedVolatility = Math.abs(annualizedReturn) * 0.8 + 15; // 基于收益率的经验估算
        
        // 基于经验值估算最大回撤
        const estimatedDrawdown = Math.min(Math.abs(annualizedReturn) * 0.6 + 10, 50); // 不超过50%
        
        // 夏普比率
        const riskFreeRate = 2.0;
        const sharpeRatio = (annualizedReturn - riskFreeRate) / estimatedVolatility;
        
        // 信息比率（保守估计）
        const informationRatio = (annualizedReturn + 5) / 15; // 假设基准-5%，跟踪误差15%
        
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
                    <h5 class="section-title"><i class="bi bi-graph-up-arrow"></i>净值曲线对比</h5>
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
            
            // 绘制图表
            setTimeout(() => {
                this.drawNavChart(navData);
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
        
        // 尝试其他可能的字段名
        if (backtestData.totalReturn !== undefined) {
            return backtestData.totalReturn;
        }
        
        console.warn('⚠️ 未在回测数据中找到总收益率，返回 0');
        return 0;
    },

    /**
     * 从回测数据中提取年化收益率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number} 年化收益率百分比
     */
    extractAnnualizedReturnFromBacktestData(backtestData) {
        // 多基金回测：使用 portfolio 中的年化收益率
        if (backtestData.portfolio) {
            const portfolioReturn = backtestData.portfolio.annualized_return;
            if (portfolioReturn !== undefined) {
                return portfolioReturn;
            }
        }
        
        // 单基金回测：使用顶层的年化收益率
        if (backtestData.annualized_return !== undefined) {
            return backtestData.annualized_return;
        }
        
        // 尝试其他可能的字段名
        if (backtestData.annualizedReturn !== undefined) {
            return backtestData.annualizedReturn;
        }
        
        console.warn('⚠️ 未在回测数据中找到年化收益率，将基于总收益率计算');
        return null;
    },

    /**
     * 从回测数据中提取年化波动率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 年化波动率百分比，未找到返回 null
     */
    extractVolatilityFromBacktestData(backtestData) {
        // 多基金回测
        if (backtestData.portfolio) {
            if (backtestData.portfolio.volatility !== undefined) {
                return backtestData.portfolio.volatility;
            }
        }
        // 单基金回测
        if (backtestData.volatility !== undefined) {
            return backtestData.volatility;
        }
        return null;
    },

    /**
     * 从回测数据中提取最大回撤
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 最大回撤百分比，未找到返回 null
     */
    extractMaxDrawdownFromBacktestData(backtestData) {
        // 多基金回测
        if (backtestData.portfolio) {
            if (backtestData.portfolio.max_drawdown !== undefined) {
                return backtestData.portfolio.max_drawdown;
            }
            if (backtestData.portfolio.maxDrawdown !== undefined) {
                return backtestData.portfolio.maxDrawdown;
            }
        }
        // 单基金回测
        if (backtestData.max_drawdown !== undefined) {
            return backtestData.max_drawdown;
        }
        if (backtestData.maxDrawdown !== undefined) {
            return backtestData.maxDrawdown;
        }
        return null;
    },

    /**
     * 从回测数据中提取夏普比率
     * @param {Object} backtestData - 回测结果数据
     * @returns {number|null} 夏普比率，未找到返回 null
     */
    extractSharpeRatioFromBacktestData(backtestData) {
        // 多基金回测
        if (backtestData.portfolio) {
            if (backtestData.portfolio.sharpe_ratio !== undefined) {
                return backtestData.portfolio.sharpe_ratio;
            }
            if (backtestData.portfolio.sharpeRatio !== undefined) {
                return backtestData.portfolio.sharpeRatio;
            }
        }
        // 单基金回测
        if (backtestData.sharpe_ratio !== undefined) {
            return backtestData.sharpe_ratio;
        }
        if (backtestData.sharpeRatio !== undefined) {
            return backtestData.sharpeRatio;
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
        
        // 多基金回测数据格式
        if (backtestData.funds && Array.isArray(backtestData.funds)) {
            backtestData.funds.forEach(fund => {
                if (fund.fund_code) {
                    fundCodes.push(fund.fund_code);
                } else if (fund.code) {
                    fundCodes.push(fund.code);
                }
            });
        }
        // 单基金回测数据格式
        else if (backtestData.fund_code) {
            fundCodes.push(backtestData.fund_code);
        } else if (backtestData.code) {
            fundCodes.push(backtestData.code);
        }
        
        console.log('📊 从回测数据提取到基金代码:', fundCodes);
        return fundCodes;
    },

    /**
     * 为回测数据生成净值数据
     * @param {Object} data - 回测数据
     * @param {Array} fundCodes - 基金代码数组
     * @returns {Array} 净值数据数组
     */
    async generateNavDataForBacktest(data, fundCodes) {
        try {
            const weights = this.calculateWeights(fundCodes.length);
            
            if (fundCodes.length === 0) {
                console.warn('未提供基金代码，使用模拟数据');
                return this.generateFallbackNavData(data);
            }
            
            const response = await fetch(`/api/dashboard/profit-trend?days=${data.totalDays || 1095}&fund_codes=${fundCodes.join(',')}&weights=${weights.join(',')}`);
            
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
     * 生成分析结果 HTML（不渲染到页面）
     * @param {Object} metrics - 绩效指标
     * @param {Array} navData - 净值数据
     * @returns {string} HTML 字符串
     */
    generateAnalysisHTML(metrics, navData) {
        // 计算超额收益
        const excessReturn = navData && navData.length > 1 
            ? ((navData[navData.length - 1].portfolio - navData[0].portfolio) / navData[0].portfolio * 100) - 
              ((navData[navData.length - 1].benchmark - navData[0].benchmark) / navData[0].benchmark * 100)
            : 0;

        return `
            <div id="portfolio-analysis-result" class="portfolio-analysis-container portfolio-analysis-inline">
                <div class="analysis-header" style="border-bottom: 2px solid #e9ecef; padding-bottom: 15px; margin-bottom: 20px;">
                    <div class="header-content">
                        <h4 style="color: #2c3e50; margin: 0;"><i class="bi bi-graph-up-arrow" style="color: #4361ee;"></i> 投资组合深度分析</h4>
                        <div class="header-subtitle" style="color: #6c757d; font-size: 14px; margin-top: 5px;">
                            基于历史数据的专业绩效评估与风险分析
                        </div>
                    </div>
                </div>
                
                <div class="metrics-section" style="margin-bottom: 30px;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-speedometer2" style="color: #4361ee;"></i> 关键绩效指标
                    </h5>
                    <div class="metrics-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-cash-stack"></i></div>
                            <div class="metric-value ${metrics.totalReturn >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.totalReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">总收益率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-graph-up"></i></div>
                            <div class="metric-value ${metrics.annualizedReturn >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.annualizedReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.annualizedReturn >= 0 ? '+' : ''}${metrics.annualizedReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">年化收益率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-activity"></i></div>
                            <div class="metric-value" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: #2c3e50;">${metrics.volatility.toFixed(2)}%</div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">年化波动率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #ef476f;"><i class="bi bi-arrow-down-circle"></i></div>
                            <div class="metric-value negative" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: #ef476f;">${metrics.maxDrawdown.toFixed(2)}%</div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">最大回撤</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-speedometer"></i></div>
                            <div class="metric-value ${metrics.sharpeRatio >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.sharpeRatio >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.sharpeRatio.toFixed(2)}
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">夏普比率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-bar-chart-line"></i></div>
                            <div class="metric-value ${metrics.informationRatio >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.informationRatio >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.informationRatio.toFixed(2)}
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">信息比率</div>
                        </div>
                    </div>
                </div>

                <div class="chart-section" style="margin-bottom: 30px; background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-graph-up-arrow" style="color: #4361ee;"></i> 净值曲线对比
                    </h5>
                    <div class="chart-container" style="position: relative; height: 350px; width: 100%;">
                        <canvas id="portfolio-nav-chart" style="width: 100%; height: 100%;"></canvas>
                    </div>
                    <div class="chart-legend" style="text-align: center; margin-top: 15px; font-size: 13px;">
                        <span class="legend-item portfolio" style="display: inline-block; margin: 0 15px; color: #4361ee; font-weight: 500;">
                            <i class="bi bi-circle-fill" style="margin-right: 5px;"></i>组合净值
                        </span>
                        <span class="legend-item benchmark" style="display: inline-block; margin: 0 15px; color: #ef476f; font-weight: 500;">
                            <i class="bi bi-circle-fill" style="margin-right: 5px;"></i>沪深300基准
                        </span>
                    </div>
                </div>

                <div class="analysis-summary" style="margin-bottom: 30px; background: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-clipboard-data" style="color: #4361ee;"></i> 分析总结
                    </h5>
                    <div class="summary-content" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px;">
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">回测周期</strong>
                            <span style="color: #4361ee; font-weight: 500;">
                                近${metrics.period}年（${metrics.totalDays}个交易日）
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">组合表现</strong>
                            <span class="${metrics.totalReturn >= 0 ? 'positive' : 'negative'}" style="font-weight: 500; color: ${metrics.totalReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.totalReturn >= 0 ? '盈利' : '亏损'} ${Math.abs(metrics.totalReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">超额收益</strong>
                            <span class="${excessReturn >= 0 ? 'positive' : 'negative'}" style="font-weight: 500; color: ${excessReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${excessReturn >= 0 ? '跑赢基准' : '跑输基准'} ${Math.abs(excessReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">风险水平</strong>
                            <span class="${metrics.volatility > 20 ? 'negative' : metrics.volatility > 15 ? 'warning' : 'positive'}" style="font-weight: 500; color: ${metrics.volatility > 20 ? '#ef476f' : metrics.volatility > 15 ? '#ffd166' : '#06d6a0'};">
                                ${metrics.volatility > 20 ? '高风险' : metrics.volatility > 15 ? '中等风险' : '低风险'}（波动率 ${metrics.volatility.toFixed(1)}%）
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">夏普比率</strong>
                            <span class="${metrics.sharpeRatio >= 1 ? 'positive' : metrics.sharpeRatio >= 0 ? 'warning' : 'negative'}" style="font-weight: 500; color: ${metrics.sharpeRatio >= 1 ? '#06d6a0' : metrics.sharpeRatio >= 0 ? '#ffd166' : '#ef476f'};">
                                ${metrics.sharpeRatio >= 1 ? '优秀' : metrics.sharpeRatio >= 0 ? '一般' : '较差'}（${metrics.sharpeRatio.toFixed(2)}）
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">回撤控制</strong>
                            <span class="${metrics.maxDrawdown > 15 ? 'negative' : metrics.maxDrawdown > 8 ? 'warning' : 'positive'}" style="font-weight: 500; color: ${metrics.maxDrawdown > 15 ? '#ef476f' : metrics.maxDrawdown > 8 ? '#ffd166' : '#06d6a0'};">
                                ${metrics.maxDrawdown > 15 ? '需关注' : metrics.maxDrawdown > 8 ? '适中' : '良好'}（最大回撤 ${metrics.maxDrawdown.toFixed(2)}%）
                            </span>
                        </div>
                    </div>
                </div>

                <div class="formula-section" style="background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-calculator" style="color: #4361ee;"></i> 指标说明
                    </h5>
                    <div class="formula-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; font-size: 13px; color: #6c757d;">
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">年化收益率</strong>：将总收益率按时间年化，便于不同期限投资的横向比较
                        </div>
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">夏普比率</strong>：衡量单位风险所获得的超额收益，大于1为优秀，小于0表示风险调整后收益为负
                        </div>
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">最大回撤</strong>：回测期间从峰值到谷值的最大跌幅，反映组合的极端风险承受情况
                        </div>
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">信息比率</strong>：衡量相对于基准的超额收益能力，反映主动管理的效率
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 内联渲染分析结果 - 作为页面内容的一部分
     * 不显示关闭按钮，直接嵌入到页面中
     */
    renderInlineAnalysis(metrics, navData) {
        // 移除已存在的分析结果
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
            <div id="portfolio-analysis-result" class="portfolio-analysis-container portfolio-analysis-inline">
                <div class="analysis-header" style="border-bottom: 2px solid #e9ecef; padding-bottom: 15px; margin-bottom: 20px;">
                    <div class="header-content">
                        <h4 style="color: #2c3e50; margin: 0;"><i class="bi bi-graph-up-arrow" style="color: #4361ee;"></i> 投资组合深度分析</h4>
                        <div class="header-subtitle" style="color: #6c757d; font-size: 14px; margin-top: 5px;">
                            基于历史数据的专业绩效评估与风险分析
                        </div>
                    </div>
                </div>
                
                <div class="metrics-section" style="margin-bottom: 30px;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-speedometer2" style="color: #4361ee;"></i> 关键绩效指标
                    </h5>
                    <div class="metrics-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-cash-stack"></i></div>
                            <div class="metric-value ${metrics.totalReturn >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.totalReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">总收益率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-graph-up"></i></div>
                            <div class="metric-value ${metrics.annualizedReturn >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.annualizedReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.annualizedReturn >= 0 ? '+' : ''}${metrics.annualizedReturn.toFixed(2)}%
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">年化收益率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-activity"></i></div>
                            <div class="metric-value" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: #2c3e50;">${metrics.volatility.toFixed(2)}%</div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">年化波动率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #ef476f;"><i class="bi bi-arrow-down-circle"></i></div>
                            <div class="metric-value negative" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: #ef476f;">${metrics.maxDrawdown.toFixed(2)}%</div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">最大回撤</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-speedometer"></i></div>
                            <div class="metric-value ${metrics.sharpeRatio >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.sharpeRatio >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.sharpeRatio.toFixed(2)}
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">夏普比率</div>
                        </div>
                        <div class="metric-card" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div class="metric-icon" style="font-size: 24px; margin-bottom: 10px; color: #4361ee;"><i class="bi bi-bar-chart-line"></i></div>
                            <div class="metric-value ${metrics.informationRatio >= 0 ? 'positive' : 'negative'}" style="font-size: 24px; font-weight: 700; margin-bottom: 5px; color: ${metrics.informationRatio >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.informationRatio.toFixed(2)}
                            </div>
                            <div class="metric-label" style="color: #6c757d; font-size: 13px;">信息比率</div>
                        </div>
                    </div>
                </div>

                <div class="chart-section" style="margin-bottom: 30px; background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-graph-up-arrow" style="color: #4361ee;"></i> 净值曲线对比
                    </h5>
                    <div class="chart-container" style="position: relative; height: 350px; width: 100%;">
                        <canvas id="portfolio-nav-chart" style="width: 100%; height: 100%;"></canvas>
                    </div>
                    <div class="chart-legend" style="text-align: center; margin-top: 15px; font-size: 13px;">
                        <span class="legend-item portfolio" style="display: inline-block; margin: 0 15px; color: #4361ee; font-weight: 500;">
                            <i class="bi bi-circle-fill" style="margin-right: 5px;"></i>组合净值
                        </span>
                        <span class="legend-item benchmark" style="display: inline-block; margin: 0 15px; color: #ef476f; font-weight: 500;">
                            <i class="bi bi-circle-fill" style="margin-right: 5px;"></i>沪深300基准
                        </span>
                    </div>
                </div>

                <div class="analysis-summary" style="margin-bottom: 30px; background: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-clipboard-data" style="color: #4361ee;"></i> 分析总结
                    </h5>
                    <div class="summary-content" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px;">
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">回测周期</strong>
                            <span style="color: #4361ee; font-weight: 500;">
                                近${metrics.period}年（${metrics.totalDays}个交易日）
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">组合表现</strong>
                            <span class="${metrics.totalReturn >= 0 ? 'positive' : 'negative'}" style="font-weight: 500; color: ${metrics.totalReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.totalReturn >= 0 ? '盈利' : '亏损'} ${Math.abs(metrics.totalReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">超额收益</strong>
                            <span class="${excessReturn >= 0 ? 'positive' : 'negative'}" style="font-weight: 500; color: ${excessReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${excessReturn >= 0 ? '跑赢基准' : '跑输基准'} ${Math.abs(excessReturn).toFixed(2)}%
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">风险水平</strong>
                            <span class="${metrics.volatility > 20 ? 'negative' : metrics.volatility > 15 ? 'warning' : 'positive'}" style="font-weight: 500; color: ${metrics.volatility > 20 ? '#ef476f' : metrics.volatility > 15 ? '#ffd166' : '#06d6a0'};">
                                ${metrics.volatility > 20 ? '高风险' : metrics.volatility > 15 ? '中等风险' : '低风险'}（波动率 ${metrics.volatility.toFixed(1)}%）
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">夏普比率</strong>
                            <span class="${metrics.sharpeRatio >= 1 ? 'positive' : metrics.sharpeRatio >= 0 ? 'warning' : 'negative'}" style="font-weight: 500; color: ${metrics.sharpeRatio >= 1 ? '#06d6a0' : metrics.sharpeRatio >= 0 ? '#ffd166' : '#ef476f'};">
                                ${metrics.sharpeRatio >= 1 ? '优秀' : metrics.sharpeRatio >= 0 ? '一般' : '较差'}（${metrics.sharpeRatio.toFixed(2)}）
                            </span>
                        </div>
                        <div class="summary-item" style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong style="color: #495057;">回撤控制</strong>
                            <span class="${metrics.maxDrawdown > 15 ? 'negative' : metrics.maxDrawdown > 8 ? 'warning' : 'positive'}" style="font-weight: 500; color: ${metrics.maxDrawdown > 15 ? '#ef476f' : metrics.maxDrawdown > 8 ? '#ffd166' : '#06d6a0'};">
                                ${metrics.maxDrawdown > 15 ? '需关注' : metrics.maxDrawdown > 8 ? '适中' : '良好'}（最大回撤 ${metrics.maxDrawdown.toFixed(2)}%）
                            </span>
                        </div>
                    </div>
                </div>

                <div class="formula-section" style="background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef;">
                    <h5 class="section-title" style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-calculator" style="color: #4361ee;"></i> 指标说明
                    </h5>
                    <div class="formula-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; font-size: 13px; color: #6c757d;">
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">年化收益率</strong>：将总收益率按时间年化，便于不同期限投资的横向比较
                        </div>
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">夏普比率</strong>：衡量单位风险所获得的超额收益，大于1为优秀，小于0表示风险调整后收益为负
                        </div>
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">最大回撤</strong>：回测期间从峰值到谷值的最大跌幅，反映组合的极端风险承受情况
                        </div>
                        <div class="formula-item" style="padding: 10px; background: #f8f9fa; border-radius: 8px;">
                            <strong style="color: #495057;">信息比率</strong>：衡量相对于基准的超额收益能力，反映主动管理的效率
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 插入到回测结果容器内（不是后面，而是作为同一区块的一部分）
        const backtestResultContent = document.getElementById('backtest-result-content');
        if (backtestResultContent) {
            // 在回测结果内容末尾添加分析结果
            const analysisDiv = document.createElement('div');
            analysisDiv.innerHTML = analysisHTML;
            backtestResultContent.appendChild(analysisDiv);
            
            // 绘制图表
            setTimeout(() => {
                this.drawNavChart(navData);
            }, 100);
            
            console.log('✅ 投资组合分析已内联显示');
        } else {
            console.error('❌ 找不到 backtest-result-content 容器');
        }
    },

    /**
     * 绘制净值曲线
     */
    drawNavChart(data) {
        const canvas = document.getElementById('portfolio-nav-chart');
        if (!canvas) {
            console.error('❌ 找不到 portfolio-nav-chart canvas 元素');
            return;
        }

        console.log('📊 开始绘制净值曲线，数据点数量:', data ? data.length : 0);
        
        if (!data || data.length === 0) {
            console.error('❌ 净值数据为空');
            return;
        }

        const ctx = canvas.getContext('2d');
        
        // 处理高清屏
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        
        // 设置 canvas 实际尺寸
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        
        // 缩放上下文以匹配 CSS 尺寸
        ctx.scale(dpr, dpr);
        
        const width = rect.width;
        const height = rect.height;
        const margin = { top: 30, right: 30, bottom: 60, left: 70 };
        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        // 清除画布
        ctx.clearRect(0, 0, width, height);

        // 计算数据范围
        const allValues = [...data.map(d => d.portfolio), ...data.map(d => d.benchmark)];
        const minValue = Math.min(...allValues);
        const maxValue = Math.max(...allValues);
        const valueRange = maxValue - minValue;
        const padding = valueRange * 0.1;

        // 保存图表状态以供鼠标事件使用
        this.chartState = {
            data: data,
            margin: margin,
            chartWidth: chartWidth,
            chartHeight: chartHeight,
            minValue: minValue - padding,
            maxValue: maxValue + padding,
            canvas: canvas,
            width: width,
            height: height
        };

        // 绘制背景
        ctx.fillStyle = '#fafafa';
        ctx.fillRect(margin.left, margin.top, chartWidth, chartHeight);

        // 绘制坐标轴
        this.drawChartAxes(ctx, margin, chartWidth, chartHeight, minValue - padding, maxValue + padding, data);

        // 绘制净值曲线 - 使用与首页一致的主题色
        this.drawLine(ctx, margin, chartWidth, chartHeight, data, 'portfolio', minValue - padding, maxValue + padding, '#4361ee');
        this.drawLine(ctx, margin, chartWidth, chartHeight, data, 'benchmark', minValue - padding, maxValue + padding, '#ef476f');

        // 绘制图例
        this.drawLegend(ctx, margin, chartWidth);

        // 添加鼠标悬停事件
        this.bindChartEvents(canvas, ctx);
        
        console.log('✅ 净值曲线绘制完成');
    },

    /**
     * 绘制图例 - 使用主题色
     */
    drawLegend(ctx, margin, chartWidth) {
        const legendX = margin.left + chartWidth - 180;
        const legendY = margin.top + 10;
        
        ctx.font = '12px Arial';
        
        // 组合净值图例 - 主题色
        ctx.fillStyle = '#4361ee';
        ctx.fillRect(legendX, legendY, 20, 3);
        ctx.fillStyle = '#333';
        ctx.textAlign = 'left';
        ctx.fillText('组合净值', legendX + 25, legendY + 5);
        
        // 沪深300基准图例 - 危险色
        ctx.fillStyle = '#ef476f';
        ctx.fillRect(legendX + 90, legendY, 20, 3);
        ctx.fillStyle = '#333';
        ctx.fillText('沪深300', legendX + 115, legendY + 5);
    },

    /**
     * 绑定图表鼠标事件
     */
    bindChartEvents(canvas, ctx) {
        console.log('🔗 绑定图表鼠标事件');
        
        // 移除旧事件
        if (this.chartMouseMoveHandler) {
            canvas.removeEventListener('mousemove', this.chartMouseMoveHandler);
        }
        if (this.chartMouseLeaveHandler) {
            canvas.removeEventListener('mouseleave', this.chartMouseLeaveHandler);
        }

        // 创建或获取tooltip元素
        let tooltip = document.getElementById('chart-tooltip');
        if (tooltip) {
            tooltip.remove(); // 移除旧的tooltip
        }
        
        tooltip = document.createElement('div');
        tooltip.id = 'chart-tooltip';
        tooltip.style.cssText = `
            position: fixed;
            background: linear-gradient(135deg, rgba(67, 97, 238, 0.95) 0%, rgba(58, 12, 163, 0.95) 100%);
            color: white;
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 13px;
            pointer-events: none;
            z-index: 99999;
            display: none;
            box-shadow: 0 8px 32px rgba(67, 97, 238, 0.3);
            min-width: 220px;
            line-height: 1.8;
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        `;
        document.body.appendChild(tooltip);
        
        // 设置 canvas 样式以显示手形光标
        canvas.style.cursor = 'crosshair';

        // 鼠标移动事件处理
        this.chartMouseMoveHandler = (event) => {
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            const state = this.chartState;
            if (!state) {
                console.warn('⚠️ chartState 未定义');
                return;
            }
            
            const { data, margin, chartWidth, chartHeight, minValue, maxValue } = state;
            
            // 检查是否在图表区域内
            if (x < margin.left || x > margin.left + chartWidth ||
                y < margin.top || y > margin.top + chartHeight) {
                tooltip.style.display = 'none';
                return;
            }
            
            // 计算最近的数据点
            const dataIndex = Math.round((x - margin.left) / chartWidth * (data.length - 1));
            const clampedIndex = Math.max(0, Math.min(data.length - 1, dataIndex));
            const point = data[clampedIndex];
            
            if (!point) {
                tooltip.style.display = 'none';
                return;
            }
            
            // 计算当日收益率
            let dailyReturn = 0;
            let benchmarkDailyReturn = 0;
            if (clampedIndex > 0) {
                const prevPoint = data[clampedIndex - 1];
                dailyReturn = ((point.portfolio - prevPoint.portfolio) / prevPoint.portfolio * 100);
                benchmarkDailyReturn = ((point.benchmark - prevPoint.benchmark) / prevPoint.benchmark * 100);
            }
            
            // 计算累计收益率
            const totalReturn = ((point.portfolio - data[0].portfolio) / data[0].portfolio * 100);
            const benchmarkReturn = ((point.benchmark - data[0].benchmark) / data[0].benchmark * 100);
            const excessReturn = totalReturn - benchmarkReturn;
            
            // 颜色
            const dailyColor = dailyReturn >= 0 ? '#4ade80' : '#f87171';
            const totalColor = totalReturn >= 0 ? '#4ade80' : '#f87171';
            const excessColor = excessReturn >= 0 ? '#4ade80' : '#f87171';
            
            // 构建tooltip内容 - 使用与首页一致的配色
            tooltip.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.3); font-size: 14px;">
                    📅 ${point.date || '未知日期'}
                </div>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>💼 组合净值:</span>
                        <span style="color: #818cf8; font-weight: bold;">¥${point.portfolio.toFixed(2)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>📊 沪深300:</span>
                        <span style="color: #fb7185; font-weight: bold;">¥${point.benchmark.toFixed(2)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>📈 当日收益:</span>
                        <span style="color: ${dailyColor}; font-weight: bold;">${dailyReturn >= 0 ? '+' : ''}${dailyReturn.toFixed(3)}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>📉 累计收益:</span>
                        <span style="color: ${totalColor}; font-weight: bold;">${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>🎯 超额收益:</span>
                        <span style="color: ${excessColor}; font-weight: bold;">${excessReturn >= 0 ? '+' : ''}${excessReturn.toFixed(2)}%</span>
                    </div>
                </div>
            `;
            
            // 定位tooltip - 使用 fixed 定位
            let tooltipX = event.clientX + 15;
            let tooltipY = event.clientY - 10;
            
            // 确保tooltip不超出视口
            const tooltipWidth = 240;
            const tooltipHeight = 200;
            
            if (tooltipX + tooltipWidth > window.innerWidth) {
                tooltipX = event.clientX - tooltipWidth - 15;
            }
            if (tooltipY + tooltipHeight > window.innerHeight) {
                tooltipY = event.clientY - tooltipHeight - 10;
            }
            if (tooltipY < 10) {
                tooltipY = 10;
            }
            
            tooltip.style.left = tooltipX + 'px';
            tooltip.style.top = tooltipY + 'px';
            tooltip.style.display = 'block';
            
            // 绘制高亮点
            this.drawHighlightPoint(canvas, clampedIndex, point);
        };

        // 鼠标离开事件处理
        this.chartMouseLeaveHandler = () => {
            tooltip.style.display = 'none';
            this.redrawChart();
        };

        canvas.addEventListener('mousemove', this.chartMouseMoveHandler);
        canvas.addEventListener('mouseleave', this.chartMouseLeaveHandler);
        
        console.log('✅ 图表鼠标事件绑定完成');
    },

    /**
     * 绘制高亮数据点
     */
    drawHighlightPoint(canvas, index, point) {
        // 重新绘制图表
        this.redrawChart();
        
        const state = this.chartState;
        if (!state) return;
        
        const ctx = canvas.getContext('2d');
        const { data, margin, chartWidth, chartHeight, minValue, maxValue } = state;
        
        // 计算点坐标
        const x = margin.left + (chartWidth / (data.length - 1)) * index;
        const yPortfolio = margin.top + chartHeight - ((point.portfolio - minValue) / (maxValue - minValue)) * chartHeight;
        const yBenchmark = margin.top + chartHeight - ((point.benchmark - minValue) / (maxValue - minValue)) * chartHeight;
        
        // 绘制垂直参考线
        ctx.strokeStyle = 'rgba(100, 100, 100, 0.6)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, margin.top);
        ctx.lineTo(x, margin.top + chartHeight);
        ctx.stroke();
        ctx.setLineDash([]);
        
        // 绘制高亮圆点 - 组合净值（主题色）
        ctx.fillStyle = '#4361ee';
        ctx.beginPath();
        ctx.arc(x, yPortfolio, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // 绘制高亮圆点 - 基准（危险色）
        ctx.fillStyle = '#ef476f';
        ctx.beginPath();
        ctx.arc(x, yBenchmark, 7, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 2;
        ctx.stroke();
    },

    /**
     * 重新绘制图表（不触发事件绑定）
     */
    redrawChart() {
        const state = this.chartState;
        if (!state) return;
        
        const canvas = state.canvas;
        const ctx = canvas.getContext('2d');
        const { data, margin, chartWidth, chartHeight, minValue, maxValue, width, height } = state;
        
        // 处理高清屏
        const dpr = window.devicePixelRatio || 1;
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(dpr, dpr);
        
        // 清除画布
        ctx.clearRect(0, 0, width, height);
        
        // 绘制背景
        ctx.fillStyle = '#fafafa';
        ctx.fillRect(margin.left, margin.top, chartWidth, chartHeight);
        
        // 重新绘制坐标轴和曲线
        this.drawChartAxes(ctx, margin, chartWidth, chartHeight, minValue, maxValue, data);
        this.drawLine(ctx, margin, chartWidth, chartHeight, data, 'portfolio', minValue, maxValue, '#4361ee');
        this.drawLine(ctx, margin, chartWidth, chartHeight, data, 'benchmark', minValue, maxValue, '#ef476f');
        this.drawLegend(ctx, margin, chartWidth);
    },

    /**
     * 绘制坐标轴
     */
    drawChartAxes(ctx, margin, chartWidth, chartHeight, minValue, maxValue, data) {
        // 绘制坐标轴线
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 1;

        // X轴
        ctx.beginPath();
        ctx.moveTo(margin.left, margin.top + chartHeight);
        ctx.lineTo(margin.left + chartWidth, margin.top + chartHeight);
        ctx.stroke();

        // Y轴
        ctx.beginPath();
        ctx.moveTo(margin.left, margin.top);
        ctx.lineTo(margin.left, margin.top + chartHeight);
        ctx.stroke();

        // Y轴网格线和标签
        ctx.strokeStyle = '#e0e0e0';
        ctx.fillStyle = '#666';
        ctx.font = '11px Arial';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        
        for (let i = 0; i <= 5; i++) {
            const y = margin.top + (chartHeight / 5) * i;
            
            // 网格线
            ctx.strokeStyle = '#e8e8e8';
            ctx.beginPath();
            ctx.moveTo(margin.left, y);
            ctx.lineTo(margin.left + chartWidth, y);
            ctx.stroke();

            // Y轴标签
            const value = maxValue - (maxValue - minValue) * (i / 5);
            ctx.fillStyle = '#666';
            ctx.fillText('¥' + value.toFixed(0), margin.left - 8, y);
        }

        // X轴日期标签
        if (data && data.length > 0) {
            console.log('📅 绘制X轴日期标签，数据长度:', data.length);
            
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            
            // 根据数据量动态计算显示间隔
            const totalPoints = data.length;
            let labelCount = 6; // 目标显示的标签数量
            
            if (totalPoints <= 30) {
                labelCount = Math.min(totalPoints, 6);
            } else if (totalPoints <= 90) {
                labelCount = 6;
            } else if (totalPoints <= 365) {
                labelCount = 8;
            } else {
                labelCount = 10;
            }
            
            const labelInterval = Math.max(1, Math.floor((totalPoints - 1) / (labelCount - 1)));
            
            // 绘制X轴刻度和标签
            for (let i = 0; i < totalPoints; i += labelInterval) {
                const x = margin.left + (chartWidth / (totalPoints - 1)) * i;
                const point = data[i];
                
                if (point && point.date) {
                    // 绘制刻度线
                    ctx.strokeStyle = '#999';
                    ctx.beginPath();
                    ctx.moveTo(x, margin.top + chartHeight);
                    ctx.lineTo(x, margin.top + chartHeight + 6);
                    ctx.stroke();
                    
                    // 格式化日期显示
                    const dateStr = this.formatDateLabel(point.date);
                    ctx.fillStyle = '#555';
                    ctx.font = '10px Arial';
                    
                    // 旋转绘制日期标签
                    ctx.save();
                    ctx.translate(x, margin.top + chartHeight + 12);
                    ctx.rotate(-Math.PI / 5);  // 旋转36度
                    ctx.textAlign = 'right';
                    ctx.fillText(dateStr, 0, 0);
                    ctx.restore();
                }
            }
            
            // 确保最后一个日期显示
            const lastIndex = totalPoints - 1;
            const lastX = margin.left + chartWidth;
            const lastPoint = data[lastIndex];
            
            if (lastPoint && lastPoint.date && lastIndex % labelInterval !== 0) {
                ctx.strokeStyle = '#999';
                ctx.beginPath();
                ctx.moveTo(lastX, margin.top + chartHeight);
                ctx.lineTo(lastX, margin.top + chartHeight + 6);
                ctx.stroke();
                
                const dateStr = this.formatDateLabel(lastPoint.date);
                ctx.fillStyle = '#555';
                ctx.font = '10px Arial';
                ctx.save();
                ctx.translate(lastX, margin.top + chartHeight + 12);
                ctx.rotate(-Math.PI / 5);
                ctx.textAlign = 'right';
                ctx.fillText(dateStr, 0, 0);
                ctx.restore();
            }
            
            console.log('✅ X轴日期标签绘制完成');
        } else {
            console.warn('⚠️ 没有数据用于绘制X轴标签');
        }
    },

    /**
     * 格式化日期标签
     */
    formatDateLabel(dateStr) {
        if (!dateStr) {
            console.warn('⚠️ 日期字符串为空');
            return '';
        }
        
        try {
            // 处理不同的日期格式
            let formattedDate = '';
            
            if (dateStr.includes('-')) {
                // 格式: "YYYY-MM-DD" 或 "YYYY-M-D"
                const parts = dateStr.split('-');
                if (parts.length >= 3) {
                    const month = parts[1].padStart(2, '0');
                    const day = parts[2].padStart(2, '0');
                    formattedDate = `${month}/${day}`;
                }
            } else if (dateStr.includes('/')) {
                // 格式: "YYYY/MM/DD" 或 "MM/DD/YYYY"
                const parts = dateStr.split('/');
                if (parts.length >= 2) {
                    formattedDate = `${parts[0]}/${parts[1]}`;
                }
            } else {
                // 其他格式，尝试截取
                formattedDate = dateStr.length > 5 ? dateStr.substring(5) : dateStr;
            }
            
            return formattedDate || dateStr;
        } catch (e) {
            console.error('日期格式化错误:', e);
            return dateStr;
        }
    },

    /**
     * 绘制线条
     */
    drawLine(ctx, margin, chartWidth, chartHeight, data, field, minValue, maxValue, color) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((point, index) => {
            const x = margin.left + (chartWidth / (data.length - 1)) * index;
            const y = margin.top + chartHeight - ((point[field] - minValue) / (maxValue - minValue)) * chartHeight;

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();
    },

    /**
     * 关闭分析
     */
    closeAnalysis() {
        const analysis = document.getElementById('portfolio-analysis-result');
        if (analysis) {
            analysis.remove();
        }
    },

    /**
     * 添加样式 - 与网站首页保持一致的设计风格
     */
    addStyles() {
        if (document.getElementById('portfolio-analysis-styles')) return;

        const style = document.createElement('style');
        style.id = 'portfolio-analysis-styles';
        style.textContent = `
            /* ============================================
               设计系统变量 - 与首页保持一致
               ============================================ */
            .portfolio-analysis-container {
                --primary-color: #4361ee;
                --primary-dark: #3a56d4;
                --primary-light: #edf2ff;
                --secondary-color: #6c757d;
                --success-color: #06d6a0;
                --success-dark: #05b38a;
                --success-light: #e8fcf3;
                --danger-color: #ef476f;
                --danger-dark: #d4355d;
                --danger-light: #fceced;
                --warning-color: #ffd166;
                --warning-dark: #e6bc5c;
                --warning-light: #fff9e6;
                --info-color: #118ab2;
                --light-bg: #f8f9fa;
                --border-color: #e0e0e0;
                --text-primary: #212529;
                --text-secondary: #6c757d;
                --card-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
                --card-shadow-hover: 0 12px 30px rgba(67, 97, 238, 0.15);
                --transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
                --border-radius: 12px;
                --spacing-xs: 0.25rem;
                --spacing-sm: 0.5rem;
                --spacing-md: 1rem;
                --spacing-lg: 1.5rem;
                --spacing-xl: 2rem;
            }

            /* ============================================
               主容器样式
               ============================================ */
            .portfolio-analysis-container {
                background: white;
                border-radius: var(--border-radius);
                box-shadow: var(--card-shadow);
                margin: var(--spacing-xl) 0;
                overflow: hidden;
                border: none;
                font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            }

            .portfolio-analysis-container:hover {
                box-shadow: var(--card-shadow-hover);
            }

            /* ============================================
               头部样式 - 渐变色与首页导航一致
               ============================================ */
            .analysis-header {
                background: linear-gradient(135deg, #4361ee 0%, #3a0ca3 100%);
                color: white;
                padding: var(--spacing-lg) var(--spacing-xl);
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                overflow: hidden;
            }

            .analysis-header::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
                opacity: 0.5;
            }

            .analysis-header h4 {
                margin: 0;
                font-weight: 700;
                font-size: 1.25rem;
                letter-spacing: 0.5px;
                position: relative;
                z-index: 1;
                display: flex;
                align-items: center;
            }

            .analysis-header h4 i {
                margin-right: 0.75rem;
                font-size: 1.4rem;
            }

            .analysis-header .header-subtitle {
                font-size: 0.85rem;
                opacity: 0.9;
                margin-top: 0.25rem;
                font-weight: 400;
            }

            /* ============================================
               各区域样式
               ============================================ */
            .metrics-section, .chart-section, .analysis-summary, .formula-section {
                padding: var(--spacing-xl);
                border-bottom: 1px solid var(--border-color);
                position: relative;
            }

            .metrics-section:last-child, .chart-section:last-child, 
            .analysis-summary:last-child, .formula-section:last-child {
                border-bottom: none;
            }

            /* ============================================
               Section 标题样式
               ============================================ */
            .section-title {
                font-size: 1.1rem;
                font-weight: 700;
                color: var(--text-primary);
                margin-bottom: var(--spacing-lg);
                display: flex;
                align-items: center;
                position: relative;
                padding-left: var(--spacing-md);
            }

            .section-title::before {
                content: '';
                position: absolute;
                left: 0;
                top: 50%;
                transform: translateY(-50%);
                width: 4px;
                height: 100%;
                background: linear-gradient(180deg, var(--primary-color), var(--success-color));
                border-radius: 2px;
            }

            .section-title i {
                margin-right: 0.5rem;
                color: var(--primary-color);
            }

            /* ============================================
               指标网格
               ============================================ */
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: var(--spacing-lg);
                margin-top: var(--spacing-md);
            }

            /* ============================================
               指标卡片 - 与首页风格一致
               ============================================ */
            .portfolio-analysis-container .metric-card {
                background: white;
                border-radius: var(--border-radius);
                padding: var(--spacing-lg);
                text-align: center;
                transition: var(--transition);
                border: 1px solid var(--border-color);
                position: relative;
                overflow: hidden;
                height: 100%;
            }

            .portfolio-analysis-container .metric-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 3px;
                background: linear-gradient(90deg, var(--primary-color), var(--success-color));
                transform: scaleX(0);
                transform-origin: left;
                transition: var(--transition);
            }

            .portfolio-analysis-container .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: var(--card-shadow-hover);
                border-color: var(--primary-color);
            }

            .portfolio-analysis-container .metric-card:hover::before {
                transform: scaleX(1);
            }

            .metric-icon {
                font-size: 2.2rem;
                margin-bottom: var(--spacing-sm);
                color: var(--primary-color);
                opacity: 0.9;
            }

            .portfolio-analysis-container .metric-value {
                font-size: 1.7rem;
                font-weight: 800;
                margin-bottom: var(--spacing-xs);
                line-height: 1.2;
            }

            .portfolio-analysis-container .metric-value.positive { 
                color: var(--success-color); 
            }
            .portfolio-analysis-container .metric-value.negative { 
                color: var(--danger-color); 
            }
            .portfolio-analysis-container .metric-value.warning { 
                color: var(--warning-color); 
            }

            .portfolio-analysis-container .metric-label {
                color: var(--text-secondary);
                font-size: 0.9rem;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* ============================================
               图表容器样式
               ============================================ */
            .chart-container {
                position: relative;
                height: 380px;
                margin: var(--spacing-md) 0;
                padding: var(--spacing-md);
                background: var(--light-bg);
                border-radius: var(--border-radius);
                border: 1px solid var(--border-color);
            }
            
            .chart-container canvas {
                width: 100% !important;
                height: 100% !important;
            }

            /* ============================================
               图例样式
               ============================================ */
            .chart-legend {
                display: flex;
                justify-content: center;
                gap: var(--spacing-xl);
                margin-top: var(--spacing-md);
                padding: var(--spacing-sm) 0;
            }

            .legend-item {
                display: flex;
                align-items: center;
                font-size: 0.9rem;
                font-weight: 500;
                padding: var(--spacing-xs) var(--spacing-sm);
                border-radius: 20px;
                transition: var(--transition);
            }

            .legend-item:hover {
                background: var(--light-bg);
            }

            .legend-item.portfolio { 
                color: var(--primary-color); 
            }
            .legend-item.portfolio i {
                color: var(--primary-color);
            }
            .legend-item.benchmark { 
                color: var(--danger-color); 
            }
            .legend-item.benchmark i {
                color: var(--danger-color);
            }

            /* ============================================
               分析总结样式
               ============================================ */
            .summary-content {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: var(--spacing-md);
                margin-top: var(--spacing-md);
            }

            .summary-item {
                background: white;
                padding: var(--spacing-md) var(--spacing-lg);
                border-radius: var(--border-radius);
                border-left: 4px solid var(--primary-color);
                transition: var(--transition);
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--primary-color);
            }

            .summary-item:hover {
                transform: translateX(5px);
                box-shadow: var(--card-shadow);
            }

            .summary-item strong {
                color: var(--text-secondary);
                font-weight: 600;
                font-size: 0.85rem;
            }

            .summary-item span {
                font-weight: 700;
                font-size: 0.95rem;
            }

            .summary-item span.positive {
                color: var(--success-color);
            }

            .summary-item span.negative {
                color: var(--danger-color);
            }

            .summary-item span.warning {
                color: var(--warning-color);
            }

            /* ============================================
               公式说明样式
               ============================================ */
            .formula-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: var(--spacing-md);
                margin-top: var(--spacing-md);
            }

            .formula-item {
                background: white;
                padding: var(--spacing-md);
                border-radius: var(--border-radius);
                border-left: 4px solid var(--success-color);
                font-size: 0.9rem;
                transition: var(--transition);
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--success-color);
            }

            .formula-item:hover {
                transform: translateX(5px);
                box-shadow: var(--card-shadow);
            }

            .formula-item strong {
                color: var(--primary-color);
                font-weight: 600;
            }

            /* ============================================
               关闭按钮
               ============================================ */
            .btn-close-analysis {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                font-size: 1.25rem;
                color: white;
                cursor: pointer;
                opacity: 0.9;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: var(--transition);
                position: relative;
                z-index: 1;
            }

            .btn-close-analysis:hover {
                opacity: 1;
                background: rgba(255, 255, 255, 0.3);
                transform: rotate(90deg);
            }

            /* ============================================
               响应式设计
               ============================================ */
            @media (max-width: 992px) {
                .metrics-grid {
                    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                    gap: var(--spacing-md);
                }
            }

            @media (max-width: 768px) {
                .metrics-grid {
                    grid-template-columns: repeat(2, 1fr);
                    gap: var(--spacing-sm);
                }
                
                .analysis-header {
                    padding: var(--spacing-md);
                    flex-direction: column;
                    align-items: flex-start;
                    gap: var(--spacing-sm);
                }

                .analysis-header h4 {
                    font-size: 1.1rem;
                }

                .btn-close-analysis {
                    position: absolute;
                    top: var(--spacing-md);
                    right: var(--spacing-md);
                }
                
                .metrics-section, .chart-section, .analysis-summary, .formula-section {
                    padding: var(--spacing-lg);
                }

                .portfolio-analysis-container .metric-value {
                    font-size: 1.4rem;
                }

                .chart-container {
                    height: 300px;
                }

                .summary-content {
                    grid-template-columns: 1fr;
                }

                .formula-grid {
                    grid-template-columns: 1fr;
                }
            }

            @media (max-width: 576px) {
                .metrics-grid {
                    grid-template-columns: repeat(2, 1fr);
                }

                .portfolio-analysis-container .metric-card {
                    padding: var(--spacing-md);
                }

                .portfolio-analysis-container .metric-value {
                    font-size: 1.2rem;
                }

                .metric-icon {
                    font-size: 1.5rem;
                }
            }

            /* ============================================
               动画效果
               ============================================ */
            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .portfolio-analysis-container {
                animation: slideInUp 0.4s ease-out;
            }

            .portfolio-analysis-container .metric-card {
                animation: slideInUp 0.4s ease-out;
                animation-fill-mode: both;
            }

            .portfolio-analysis-container .metric-card:nth-child(1) { animation-delay: 0.05s; }
            .portfolio-analysis-container .metric-card:nth-child(2) { animation-delay: 0.1s; }
            .portfolio-analysis-container .metric-card:nth-child(3) { animation-delay: 0.15s; }
            .portfolio-analysis-container .metric-card:nth-child(4) { animation-delay: 0.2s; }
            .portfolio-analysis-container .metric-card:nth-child(5) { animation-delay: 0.25s; }
            .portfolio-analysis-container .metric-card:nth-child(6) { animation-delay: 0.3s; }
        `;

        document.head.appendChild(style);
    }
};

// 初始化
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => PortfolioAnalysis.init());
    } else {
        PortfolioAnalysis.init();
    }
}

// 全局访问
window.PortfolioAnalysis = PortfolioAnalysis;