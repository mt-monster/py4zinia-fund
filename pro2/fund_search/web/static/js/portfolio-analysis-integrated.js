/**
 * 投资组合分析集成模块
 * 基于回测结果数据生成净值曲线和绩效指标
 */

const PortfolioAnalysis = {
    // 分析数据
    analysisData: null,
    chartState: null,
    isDrawing: false,
    eventsBound: false,  // 防止重复绑定事件
    
    // 缩放和查看状态
    viewState: {
        scale: 1,
        offsetX: 0,  // 水平偏移（像素）
        isDragging: false,
        lastMouseX: 0,
        minScale: 0.5,
        maxScale: 10
    },
    
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
     * 重置所有回测结果和状态
     * 在开始新的回测前调用，清除之前的所有数据和图表
     */
    reset() {
        console.log('🔄 PortfolioAnalysis.reset() 开始清除之前的结果...');
        
        // 1. 清除全局回测结果
        if (window.lastBacktestResult) {
            window.lastBacktestResult = null;
            console.log('  ✅ 已清除 window.lastBacktestResult');
        }
        
        // 2. 重置图表状态
        this.chartState = null;
        this.isDrawing = false;
        
        // 3. 重置视图状态
        this.resetViewState();
        
        // 4. 移除图表容器（如果存在）
        const chartContainer = document.getElementById('nav-chart-container');
        if (chartContainer) {
            chartContainer.remove();
            console.log('  ✅ 已移除图表容器 nav-chart-container');
        }
        
        // 5. 移除投资组合分析结果（如果存在）
        const analysisResult = document.getElementById('portfolio-analysis-result');
        if (analysisResult) {
            analysisResult.remove();
            console.log('  ✅ 已移除投资组合分析结果 portfolio-analysis-result');
        }
        
        // 6. 移除 tooltip（如果存在）
        const tooltip = document.getElementById('nav-chart-tooltip');
        if (tooltip) {
            tooltip.remove();
            console.log('  ✅ 已移除图表 tooltip');
        }
        
        // 7. 重置事件绑定标志
        this.eventsBound = false;
        
        console.log('✅ PortfolioAnalysis.reset() 完成，所有状态已重置');
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        console.log('🔍 PortfolioAnalysis.bindEvents() 开始执行');
        
        // 注意：不再需要绑定"分析"按钮，因为分析现在自动内联显示
        // 回测完成后会自动调用 prepareAnalysisForDisplay() 和 displayMultiFundResults()
        console.log('💡 投资组合分析采用自动内联模式，无需手动触发');
        
        // 监听回测结果更新（保留，用于检测回测结果DOM变化）
        this.observeBacktestResults();
        console.log('✅ PortfolioAnalysis.bindEvents() 执行完成');
    },
    
    /**
     * 监听回测结果区域的变化
     * 注意：现在只用于日志记录和调试，不再自动触发重新分析
     */
    observeBacktestResults() {
        const resultBox = document.getElementById('backtest-result');
        if (!resultBox) {
            console.log('💡 backtest-result 容器未找到，跳过监听');
            return;
        }
        
        console.log('👀 开始监听回测结果区域的DOM变化（仅日志）');
        
        // 创建MutationObserver来监听DOM变化
        const observer = new MutationObserver((mutations) => {
            for (let mutation of mutations) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    console.log('🔍 检测到回测结果区域DOM变化:', mutation);
                }
            }
        });
        
        // 开始监听（简化配置）
        observer.observe(resultBox, {
            childList: true,
            subtree: false
        });
    },

    /**
     * 准备分析数据供显示
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
            // 从回测数据中提取指标
            const metrics = this.extractMetricsFromBacktest(backtestData);
            
            // 获取净值数据
            const navData = this.extractNavDataFromBacktest(backtestData);
            
            // 生成分析 HTML
            const html = this.generateAnalysisHTML(metrics);
            
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
     * 从回测数据提取指标
     */
    extractMetricsFromBacktest(backtestData) {
        const portfolio = backtestData.portfolio || backtestData;
        
        // 提取基本指标
        const totalReturn = portfolio.total_return || 0;
        const years = backtestData.period || 3;
        const annualizedReturn = ((Math.pow(1 + totalReturn / 100, 1 / years) - 1) * 100);
        
        // 提取组合表现指标（初始金额、最终价值）
        const initialAmount = portfolio.initial_amount || 0;
        const finalValue = portfolio.final_value || portfolio.total_value || 0;
        
        return {
            totalReturn: totalReturn,
            annualizedReturn: annualizedReturn,
            volatility: portfolio.volatility || 15,
            maxDrawdown: portfolio.max_drawdown || 0,
            sharpeRatio: portfolio.sharpe_ratio || 0,
            informationRatio: 0,
            calmarRatio: annualizedReturn / (portfolio.max_drawdown || 1),
            period: years,
            totalDays: years * 252,
            initialAmount: initialAmount,
            finalValue: finalValue
        };
    },

    /**
     * 从回测数据提取净值数据
     */
    extractNavDataFromBacktest(backtestData) {
        // 优先使用 portfolio_equity_curve（多基金回测）
        if (backtestData.portfolio_equity_curve && backtestData.portfolio_equity_curve.length > 0) {
            console.log('📊 使用 portfolio_equity_curve 数据，数据点数:', backtestData.portfolio_equity_curve.length);
            const data = backtestData.portfolio_equity_curve.map(point => ({
                date: point.date,
                portfolio: point.value || point.portfolio_value || point.portfolio || 1,
                benchmark: point.benchmark_value || 1  // 使用后端提供的基准值
            }));
            console.log('📊 首条数据:', data[0]);
            console.log('📊 末条数据:', data[data.length - 1]);
            
            // 检查基准值是否有变化
            const firstBenchmark = data[0]?.benchmark;
            const lastBenchmark = data[data.length - 1]?.benchmark;
            const uniqueBenchmarks = new Set(data.map(d => d.benchmark.toFixed(2))).size;
            const changePercent = ((lastBenchmark / firstBenchmark - 1) * 100).toFixed(2);
            
            console.log('📊 基准值统计:', {
                first: firstBenchmark,
                last: lastBenchmark,
                change: changePercent + '%',
                uniqueValues: uniqueBenchmarks,
                totalPoints: data.length
            });
            
            // 检查中间是否有长时间不变的基准值
            let unchangedStreak = 0;
            let maxUnchangedStreak = 0;
            let streakStartIndex = 0;
            let maxStreakStartIndex = 0;
            
            for (let i = 1; i < data.length; i++) {
                if (Math.abs(data[i].benchmark - data[i-1].benchmark) < 0.01) {
                    if (unchangedStreak === 0) streakStartIndex = i - 1;
                    unchangedStreak++;
                    if (unchangedStreak > maxUnchangedStreak) {
                        maxUnchangedStreak = unchangedStreak;
                        maxStreakStartIndex = streakStartIndex;
                    }
                } else {
                    unchangedStreak = 0;
                }
            }
            
            if (maxUnchangedStreak > 10) {
                const startDate = data[maxStreakStartIndex]?.date;
                const endDate = data[maxStreakStartIndex + maxUnchangedStreak]?.date;
                console.warn('⚠️ 检测到基准值连续', maxUnchangedStreak, '天无变化（', startDate, '至', endDate, '），可能存在数据问题');
                console.warn('   建议：检查后端日志，确认沪深300数据是否正确获取');
            }
            
            // 如果基准值完全没有变化，给出更严重的警告
            if (uniqueBenchmarks === 1) {
                console.error('❌ 错误：所有基准值完全相同！可能原因：');
                console.error('   1. 后端无法获取沪深300历史数据');
                console.error('   2. 回测日期范围超出了沪深300数据的可用范围');
                console.error('   3. 日期格式不匹配导致无法查找对应价格');
                console.error('   请检查后端日志（特别是 "沪深300数据获取结果" 和 "寻找基准价格" 相关日志）');
                
                // 检查原始数据
                const rawPoint = backtestData.portfolio_equity_curve?.[0];
                console.error('   原始数据第一个点:', rawPoint);
                console.error('   原始数据是否有 benchmark_value 字段:', rawPoint?.hasOwnProperty('benchmark_value'));
            } else if (changePercent === '0.00' && uniqueBenchmarks > 1) {
                console.warn('⚠️ 警告：基准值首尾相同但中间有变化，可能是数据对齐问题');
            }
            
            return data;
        }
        
        // 尝试使用 equity_curve（单基金回测）
        if (backtestData.equity_curve && backtestData.equity_curve.length > 0) {
            console.log('📊 使用 equity_curve 数据');
            return backtestData.equity_curve.map(point => ({
                date: point.date,
                portfolio: point.value || point.portfolio || point.nav || 1,
                benchmark: point.benchmark || point.benchmark_value || 1
            }));
        }
        
        // 尝试从 funds[0].equity_curve 获取（兼容旧格式）
        if (backtestData.funds && backtestData.funds[0]?.equity_curve?.length > 0) {
            console.log('📊 使用 funds[0].equity_curve 数据');
            const fundCurve = backtestData.funds[0].equity_curve;
            return fundCurve.map((point, index) => ({
                date: point.date,
                portfolio: point.value || point.nav || 1,
                benchmark: point.benchmark || 1
            }));
        }
        
        console.warn('⚠️ 未找到净值曲线数据');
        return null;
    },

    /**
     * 生成分析结果 HTML
     */
    generateAnalysisHTML(metrics) {
        // 格式化金额显示
        const formatCurrency = (value) => {
            if (value === undefined || value === null) return '¥0.00';
            return '¥' + value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        };
        
        return `
            <div id="portfolio-analysis-result" class="portfolio-analysis-container">
                <div class="metrics-section" style="margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 12px;">
                    <h5 style="color: #2c3e50; margin-bottom: 15px; font-size: 16px;">
                        <i class="bi bi-speedometer2" style="color: #4361ee;"></i> 关键绩效指标
                    </h5>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                        <!-- 组合表现指标：初始金额 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 20px; font-weight: 700; color: #2c3e50;">
                                ${formatCurrency(metrics.initialAmount)}
                            </div>
                            <div style="color: #6c757d; font-size: 13px;">初始金额</div>
                        </div>
                        <!-- 组合表现指标：最终价值 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 20px; font-weight: 700; color: ${metrics.finalValue >= metrics.initialAmount ? '#06d6a0' : '#ef476f'};">
                                ${formatCurrency(metrics.finalValue)}
                            </div>
                            <div style="color: #6c757d; font-size: 13px;">最终价值</div>
                        </div>
                        <!-- 关键绩效指标：总收益率 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 24px; font-weight: 700; color: ${metrics.totalReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%
                            </div>
                            <div style="color: #6c757d; font-size: 13px;">总收益率</div>
                        </div>
                        <!-- 关键绩效指标：年化收益率 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 24px; font-weight: 700; color: ${metrics.annualizedReturn >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.annualizedReturn >= 0 ? '+' : ''}${metrics.annualizedReturn.toFixed(2)}%
                            </div>
                            <div style="color: #6c757d; font-size: 13px;">年化收益率</div>
                        </div>
                        <!-- 关键绩效指标：年化波动率 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 24px; font-weight: 700; color: #2c3e50;">${metrics.volatility.toFixed(2)}%</div>
                            <div style="color: #6c757d; font-size: 13px;">年化波动率</div>
                        </div>
                        <!-- 关键绩效指标：最大回撤 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 24px; font-weight: 700; color: #ef476f;">${metrics.maxDrawdown.toFixed(2)}%</div>
                            <div style="color: #6c757d; font-size: 13px;">最大回撤</div>
                        </div>
                        <!-- 关键绩效指标：夏普比率 -->
                        <div style="background: white; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6;">
                            <div style="font-size: 24px; font-weight: 700; color: ${metrics.sharpeRatio >= 0 ? '#06d6a0' : '#ef476f'};">
                                ${metrics.sharpeRatio.toFixed(2)}
                            </div>
                            <div style="color: #6c757d; font-size: 13px;">夏普比率</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 重置视图状态
     */
    resetViewState() {
        this.viewState.scale = 1;
        this.viewState.offsetX = 0;
        this.viewState.isDragging = false;
    },

    /**
     * 获取当前可视范围的数据
     */
    getVisibleDataRange() {
        if (!this.chartState || !this.chartState.data) return null;
        
        const { data, chartWidth } = this.chartState;
        const totalPoints = data.length;
        
        // 根据缩放比例计算可见的数据点数
        const visiblePoints = Math.max(10, Math.floor(totalPoints / this.viewState.scale));
        
        // 计算起始索引（考虑水平偏移）
        const maxOffset = Math.max(0, totalPoints - visiblePoints);
        const offsetRatio = this.viewState.offsetX / chartWidth;
        let startIndex = Math.floor(offsetRatio * totalPoints);
        startIndex = Math.max(0, Math.min(startIndex, maxOffset));
        
        const endIndex = Math.min(startIndex + visiblePoints, totalPoints);
        
        return {
            startIndex,
            endIndex,
            visibleData: data.slice(startIndex, endIndex)
        };
    },

    /**
     * 绘制净值曲线图表 - 主入口函数
     */
    drawNavChart(data, isHighlight = false) {
        // 如果是高亮绘制，不需要检查 isDrawing 标志
        if (!isHighlight && this.isDrawing) {
            console.warn('⚠️ 图表绘制中，跳过重复调用');
            return;
        }
        
        if (!isHighlight) {
            this.isDrawing = true;
        }

        try {
            // 只在首次绘制时输出日志
            if (!isHighlight) {
                console.log('📊 开始绘制净值曲线，数据点数量:', data ? data.length : 0);
            }
            
            if (!data || data.length === 0) {
                console.error('❌ 净值数据为空');
                return;
            }

            // 查找或创建 canvas 容器
            let chartContainer = document.getElementById('nav-chart-container');
            if (!chartContainer) {
                // 尝试在回测结果区域后创建图表容器
                const backtestResult = document.getElementById('backtest-result');
                if (!backtestResult) {
                    console.error('❌ 找不到 backtest-result 容器');
                    return;
                }
                
                // 创建图表容器，放在回测结果内容之后
                const backtestContent = document.getElementById('backtest-result-content');
                chartContainer = document.createElement('div');
                chartContainer.id = 'nav-chart-container';
                chartContainer.style.cssText = 'position: relative; height: 400px; margin: 20px 0; background: #fff; border-radius: 12px; padding: 20px; border: 1px solid #e9ecef; transition: all 0.3s ease;';
                chartContainer.innerHTML = `
                    <div class="chart-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h6 class="mb-0"><i class="bi bi-graph-line me-2"></i>净值曲线对比</h6>
                        <button id="fullscreen-btn" class="btn btn-sm btn-outline-secondary" title="全屏查看">
                            <i class="bi bi-fullscreen"></i> 全屏
                        </button>
                    </div>
                    <div class="chart-wrapper" style="position: relative; height: 320px;">
                        <canvas id="navChart"></canvas>
                    </div>
                    <div class="chart-controls" style="position: absolute; bottom: 10px; right: 10px; display: flex; gap: 5px; z-index: 10;">
                        <button id="zoom-in-btn" class="btn btn-sm btn-outline-primary" title="放大">+</button>
                        <button id="zoom-out-btn" class="btn btn-sm btn-outline-primary" title="缩小">-</button>
                        <button id="reset-zoom-btn" class="btn btn-sm btn-outline-secondary" title="重置">⟲</button>
                    </div>
                    <div class="chart-hint" style="position: absolute; bottom: 10px; left: 10px; font-size: 12px; color: #666;">
                        提示：使用鼠标滚轮缩放，拖拽移动视图
                    </div>
                `;
                
                if (backtestContent) {
                    backtestContent.appendChild(chartContainer);
                } else {
                    backtestResult.appendChild(chartContainer);
                }
            }

            const canvas = document.getElementById('navChart');
            if (!canvas) {
                console.error('❌ 找不到 navChart canvas');
                return;
            }

            if (typeof canvas.getBoundingClientRect !== 'function') {
                console.error('❌ canvas 不支持 getBoundingClientRect');
                return;
            }

            const ctx = canvas.getContext('2d');
            
            // 处理高清屏
            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.parentElement.getBoundingClientRect();
            if (!rect || rect.width === 0 || rect.height === 0) {
                console.warn('⚠️ canvas 父容器尺寸无效');
                return;
            }
            
            // 只在非高亮模式下设置 canvas 尺寸
            if (!isHighlight) {
                // 设置 canvas 实际尺寸
                canvas.width = rect.width * dpr;
                canvas.height = rect.height * dpr;
                canvas.style.width = rect.width + 'px';
                canvas.style.height = rect.height + 'px';
                
                // 缩放上下文以匹配 CSS 尺寸
                ctx.scale(dpr, dpr);
            }
            
            const width = rect.width;
            const height = rect.height;
            const margin = { top: 30, right: 30, bottom: 50, left: 70 };
            const chartWidth = width - margin.left - margin.right;
            const chartHeight = height - margin.top - margin.bottom;

            // 只在非高亮模式下清除画布并绘制完整图表
            if (!isHighlight) {
                // 清除画布
                ctx.clearRect(0, 0, width, height);

                // 获取基金详细数据
                let fundsWithDetails = window.lastBacktestResult?.funds || [];
                
                console.log('📊 lastBacktestResult:', window.lastBacktestResult);
                console.log('📊 funds数组:', fundsWithDetails.length);
                console.log('📊 trades:', window.lastBacktestResult?.trades?.length);
                console.log('📊 equity_curve:', window.lastBacktestResult?.equity_curve?.length);
                
                // 单个基金回测时，如果没有funds数组但有trades，构造一个虚拟的fund对象
                if (fundsWithDetails.length === 0 && window.lastBacktestResult?.trades) {
                    const singleFund = {
                        fund_code: window.lastBacktestResult.fund_code || '基金',
                        fund_name: window.lastBacktestResult.fund_name || window.lastBacktestResult.fund_code || '基金',
                        equity_curve: window.lastBacktestResult.equity_curve || [],
                        trades: window.lastBacktestResult.trades || []
                    };
                    fundsWithDetails = [singleFund];
                    console.log('📊 单基金回测：构造虚拟fund对象', singleFund);
                }

                // 根据缩放状态计算可见数据范围
                let displayData = data;
                let startIndex = 0;
                const totalPoints = data.length;
                
                if (this.viewState.scale > 1) {
                    // 缩放时显示部分数据
                    const visiblePoints = Math.max(10, Math.floor(totalPoints / this.viewState.scale));
                    const maxOffset = totalPoints - visiblePoints;
                    
                    // 根据 offsetX 计算起始索引
                    const offsetRatio = -this.viewState.offsetX / (chartWidth * this.viewState.scale);
                    startIndex = Math.floor(offsetRatio * totalPoints);
                    startIndex = Math.max(0, Math.min(startIndex, maxOffset));
                    
                    const endIndex = Math.min(startIndex + visiblePoints, totalPoints);
                    displayData = data.slice(startIndex, endIndex);
                } else {
                    // 重置偏移
                    this.viewState.offsetX = 0;
                }

                // 计算数据范围（基于所有数据，保持Y轴稳定）
                let allValues = [...data.map(d => d.portfolio), ...data.map(d => d.benchmark)];
                
                fundsWithDetails.forEach(fund => {
                    if (fund.equity_curve && fund.equity_curve.length > 0) {
                        allValues = allValues.concat(fund.equity_curve.map(p => p.value));
                    }
                });
                
                const minValue = Math.min(...allValues);
                const maxValue = Math.max(...allValues);
                const valueRange = maxValue - minValue;
                const padding = valueRange * 0.1;

                // 保存图表状态（使用原始数据，保持坐标映射正确）
                this.chartState = {
                    data: data,
                    fundsWithDetails: fundsWithDetails,
                    margin: margin,
                    chartWidth: chartWidth,
                    chartHeight: chartHeight,
                    minValue: minValue - padding,
                    maxValue: maxValue + padding,
                    canvas: canvas,
                    width: width,
                    height: height,
                    dpr: dpr
                };

                // 绘制背景
                ctx.fillStyle = '#fafafa';
                ctx.fillRect(margin.left, margin.top, chartWidth, chartHeight);

                // 绘制坐标轴
                this.drawChartAxes(ctx, margin, chartWidth, chartHeight, minValue - padding, maxValue + padding, displayData);

                // 绘制基金净值曲线（只在数据范围内绘制）
                const fundColors = [
                    '#9C27B0', '#FF6B6B', '#4ECDC4', '#FFD93D', 
                    '#6BCF7F', '#FF8C42', '#95E1D3', '#F38181'
                ];
                
                fundsWithDetails.forEach((fund, index) => {
                    if (fund.equity_curve && fund.equity_curve.length > 0) {
                        const color = fundColors[index % fundColors.length];
                        // 根据当前显示范围裁剪基金曲线
                        const fundStartIndex = Math.min(startIndex, fund.equity_curve.length - 1);
                        const fundEndIndex = Math.min(startIndex + displayData.length, fund.equity_curve.length);
                        const visibleFundCurve = fund.equity_curve.slice(fundStartIndex, fundEndIndex);
                        
                        this.drawFundLine(ctx, margin, chartWidth, chartHeight, visibleFundCurve, 
                            minValue - padding, maxValue + padding, color, 1.5);
                    }
                });

                // 绘制买卖点标记（根据当前显示范围）
                console.log('📊 准备绘制买卖点标记，基金数量:', fundsWithDetails.length);
                fundsWithDetails.forEach((fund, index) => {
                    console.log(`📊 基金 ${index}:`, fund.fund_code, '交易次数:', fund.trades?.length);
                    if (fund.trades && fund.trades.length > 0) {
                        const color = fundColors[index % fundColors.length];
                        this.drawTradeMarkersInRange(ctx, margin, chartWidth, chartHeight, fund, 
                            minValue - padding, maxValue + padding, color, startIndex, displayData.length);
                    }
                });

                // 绘制组合净值曲线（实线）
                this.drawLine(ctx, margin, chartWidth, chartHeight, displayData, 'portfolio', 
                    minValue - padding, maxValue + padding, '#4361ee', 3, false);
                
                // 绘制基准曲线（虚线）
                this.drawLine(ctx, margin, chartWidth, chartHeight, displayData, 'benchmark', 
                    minValue - padding, maxValue + padding, '#ef476f', 3, true);

                // 绘制图例
                this.drawLegendWithFunds(ctx, margin, chartWidth, fundsWithDetails, fundColors);

                // 绑定事件（只绑定一次）
                if (!this.eventsBound) {
                    this.bindChartEvents(canvas);
                    this.bindZoomControls();
                    this.eventsBound = true;
                }
                
                console.log('✅ 净值曲线绘制完成');
            }
        } catch (error) {
            console.error('❌ 绘制净值曲线时出错:', error);
        } finally {
            if (!isHighlight) {
                this.isDrawing = false;
            }
        }
    },

    /**
     * 绘制坐标轴
     */
    drawChartAxes(ctx, margin, chartWidth, chartHeight, minValue, maxValue, data) {
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        
        // 绘制网格线
        for (let i = 0; i <= 5; i++) {
            const y = margin.top + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(margin.left, y);
            ctx.lineTo(margin.left + chartWidth, y);
            ctx.stroke();
            
            // Y轴标签
            const value = maxValue - (maxValue - minValue) * (i / 5);
            ctx.fillStyle = '#666';
            ctx.font = '12px Arial';
            ctx.textAlign = 'right';
            ctx.fillText(value.toFixed(2), margin.left - 10, y + 4);
        }
        
        // X轴标签
        const dateCount = data.length;
        const step = Math.max(1, Math.floor(dateCount / 6));
        for (let i = 0; i < dateCount; i += step) {
            const x = margin.left + (chartWidth / (dateCount - 1)) * i;
            const date = new Date(data[i].date);
            const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
            
            ctx.fillStyle = '#666';
            ctx.font = '11px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(dateStr, x, margin.top + chartHeight + 20);
        }
    },

    /**
     * 绘制线条
     * @param {boolean} isDashed - 是否使用虚线样式
     */
    drawLine(ctx, margin, chartWidth, chartHeight, data, field, minValue, maxValue, color, lineWidth, isDashed = false) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        
        // 设置虚线样式
        if (isDashed) {
            ctx.setLineDash([8, 4]);  // 8像素实线，4像素空白
        } else {
            ctx.setLineDash([]);  // 实线
        }
        
        ctx.beginPath();
        
        const valueRange = maxValue - minValue;
        
        data.forEach((point, index) => {
            const x = margin.left + (chartWidth / (data.length - 1)) * index;
            const y = margin.top + chartHeight - ((point[field] - minValue) / valueRange) * chartHeight;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        ctx.setLineDash([]);  // 重置为实线
    },

    /**
     * 绘制基金净值曲线
     */
    drawFundLine(ctx, margin, chartWidth, chartHeight, equityCurve, minValue, maxValue, color, lineWidth) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        
        const valueRange = maxValue - minValue;
        
        equityCurve.forEach((point, index) => {
            const x = margin.left + (chartWidth / (equityCurve.length - 1)) * index;
            const y = margin.top + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        ctx.setLineDash([]);
    },

    /**
     * 绘制买卖点标记
     */
    drawTradeMarkers(ctx, margin, chartWidth, chartHeight, fund, minValue, maxValue, color) {
        this.drawTradeMarkersInRange(ctx, margin, chartWidth, chartHeight, fund, minValue, maxValue, color, 0, fund.equity_curve?.length || 0);
    },

    /**
     * 绘制指定范围内的买卖点标记
     */
    drawTradeMarkersInRange(ctx, margin, chartWidth, chartHeight, fund, minValue, maxValue, color, startIndex, visibleCount) {
        const valueRange = maxValue - minValue;
        
        if (!fund.equity_curve || !fund.trades) {
            console.log('📊 没有 equity_curve 或 trades 数据');
            return;
        }
        
        // 统计买入卖出数量
        const buyTrades = fund.trades.filter(t => t.type === 'buy' || t.action === 'buy');
        const sellTrades = fund.trades.filter(t => t.type === 'sell' || t.action === 'sell' || t.action === 'stop_loss');
        console.log('📊 交易统计:', {买入: buyTrades.length, 卖出: sellTrades.length, 总交易: fund.trades.length});
        
        const endIndex = startIndex + visibleCount;
        let drawnCount = 0;
        let buyCount = 0;
        let sellCount = 0;
        
        fund.trades.forEach((trade, idx) => {
            // 标准化日期格式（只取前10个字符 YYYY-MM-DD）
            const tradeDate = trade.date?.substring(0, 10);
            const dateIndex = fund.equity_curve.findIndex(p => p.date?.substring(0, 10) === tradeDate);
            
            if (dateIndex === -1) return;
            
            // 只绘制在可见范围内的标记
            if (dateIndex < startIndex || dateIndex >= endIndex) return;
            
            // 判断交易类型（支持 type 和 action 字段）
            const isBuy = trade.type === 'buy' || trade.action === 'buy';
            const isSell = trade.type === 'sell' || trade.action === 'sell' || trade.action === 'stop_loss';
            
            if (!isBuy && !isSell) {
                console.log(`📊 交易 ${idx} 类型未知:`, trade.type, trade.action);
                return;
            }
            
            drawnCount++;
            if (isBuy) buyCount++;
            if (isSell) sellCount++;
            
            // 计算在可见区域内的相对位置
            const relativeIndex = dateIndex - startIndex;
            const x = margin.left + (chartWidth / (visibleCount - 1)) * relativeIndex;
            
            // 使用交易价格或对应日期的净值
            let tradeValue = trade.price;
            if (!tradeValue && dateIndex < fund.equity_curve.length) {
                tradeValue = fund.equity_curve[dateIndex].value;
            }
            if (!tradeValue) tradeValue = minValue + valueRange * 0.5;
            
            const y = margin.top + chartHeight - ((tradeValue - minValue) / valueRange) * chartHeight;
            
            const markerColor = isBuy ? '#06d6a0' : '#ef476f';
            const markerSize = 8;
            
            // 确保标记在画布范围内
            const clampedX = Math.max(margin.left + 10, Math.min(margin.left + chartWidth - 10, x));
            const clampedY = Math.max(margin.top + 10, Math.min(margin.top + chartHeight - 10, y));
            
            // 绘制三角形标记（买入向上，卖出向下）
            ctx.fillStyle = markerColor;
            ctx.beginPath();
            if (isBuy) {
                // 买入：向上三角形 ▲
                ctx.moveTo(clampedX, clampedY - markerSize);
                ctx.lineTo(clampedX - markerSize, clampedY + markerSize);
                ctx.lineTo(clampedX + markerSize, clampedY + markerSize);
            } else {
                // 卖出：向下三角形 ▼
                ctx.moveTo(clampedX, clampedY + markerSize);
                ctx.lineTo(clampedX - markerSize, clampedY - markerSize);
                ctx.lineTo(clampedX + markerSize, clampedY - markerSize);
            }
            ctx.closePath();
            ctx.fill();
            
            // 白色边框
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // 绘制买入/卖出文字标签
            ctx.fillStyle = markerColor;
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'center';
            // 确保标签在画布内
            let labelY = isBuy ? clampedY - markerSize - 3 : clampedY + markerSize + 12;
            labelY = Math.max(margin.top + 15, Math.min(margin.top + chartHeight - 5, labelY));
            ctx.fillText(isBuy ? '买' : '卖', clampedX, labelY);
        });
        
        console.log('📊 买卖点绘制完成:', {总计: drawnCount, 买入: buyCount, 卖出: sellCount});
    },

    /**
     * 绘制图例 - 支持多行布局和自动换行
     */
    drawLegendWithFunds(ctx, margin, chartWidth, fundsWithDetails, fundColors) {
        const lineHeight = 22;  // 行高
        const itemSpacing = 15; // 图例项之间的间距
        const markerWidth = 20; // 颜色标记宽度
        const markerTextGap = 8; // 标记与文字之间的间距
        const maxTextWidth = 120; // 最大文字宽度（超过则截断）
        
        let currentX = margin.left;
        let currentY = 15;
        
        // 辅助函数：截断过长的文本
        const truncateText = (text, maxWidth) => {
            if (!text) return '';
            let width = ctx.measureText(text).width;
            if (width <= maxWidth) return text;
            
            let truncated = text;
            while (width > maxWidth && truncated.length > 0) {
                truncated = truncated.slice(0, -1);
                width = ctx.measureText(truncated + '...').width;
            }
            return truncated + '...';
        };
        
        // 辅助函数：检查是否需要换行
        const checkWrap = (itemWidth) => {
            if (currentX + itemWidth > margin.left + chartWidth) {
                currentX = margin.left;
                currentY += lineHeight;
            }
        };
        
        // 绘制单个图例项（带颜色标记的文本）
        const drawLegendItem = (color, text, isLine = true, isDashed = false) => {
            ctx.font = '11px Arial';
            const displayText = truncateText(text, maxTextWidth);
            const textWidth = ctx.measureText(displayText).width;
            const itemWidth = markerWidth + markerTextGap + textWidth + itemSpacing;
            
            checkWrap(itemWidth);
            
            // 绘制颜色标记
            if (isLine) {
                ctx.strokeStyle = color;
                ctx.lineWidth = 3;
                if (isDashed) {
                    ctx.setLineDash([8, 4]);
                } else {
                    ctx.setLineDash([]);
                }
                ctx.beginPath();
                ctx.moveTo(currentX, currentY);
                ctx.lineTo(currentX + markerWidth, currentY);
                ctx.stroke();
                ctx.setLineDash([]);
            } else {
                ctx.fillStyle = color;
                ctx.fillRect(currentX, currentY - 3, markerWidth, 6);
            }
            
            // 绘制文字
            ctx.fillStyle = '#333';
            ctx.textAlign = 'left';
            ctx.fillText(displayText, currentX + markerWidth + markerTextGap, currentY + 4);
            
            currentX += itemWidth;
        };
        
        // 绘制三角形标记（买入/卖出）
        const drawTriangleMarker = (color, isUp, text) => {
            const markerSize = 6;
            const textWidth = ctx.measureText(truncateText(text, 40)).width;
            const itemWidth = markerSize * 2 + markerTextGap + textWidth + itemSpacing;
            
            checkWrap(itemWidth);
            
            ctx.fillStyle = color;
            ctx.beginPath();
            if (isUp) {
                // 向上三角形（买入）
                ctx.moveTo(currentX + markerSize, currentY - markerSize + 2);
                ctx.lineTo(currentX, currentY + markerSize / 2);
                ctx.lineTo(currentX + markerSize * 2, currentY + markerSize / 2);
            } else {
                // 向下三角形（卖出）
                ctx.moveTo(currentX + markerSize, currentY + markerSize - 2);
                ctx.lineTo(currentX, currentY - markerSize / 2);
                ctx.lineTo(currentX + markerSize * 2, currentY - markerSize / 2);
            }
            ctx.closePath();
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            ctx.fillStyle = '#333';
            ctx.fillText(text, currentX + markerSize * 2 + markerTextGap, currentY + 4);
            
            currentX += itemWidth;
        };
        
        // 1. 绘制组合净值
        drawLegendItem('#4361ee', '组合净值', true, false);
        
        // 2. 绘制基准（虚线样式）
        drawLegendItem('#ef476f', '沪深300基准', true, true);
        
        // 3. 绘制各基金
        fundsWithDetails.forEach((fund, index) => {
            const color = fundColors[index % fundColors.length];
            const displayName = fund.fund_name || fund.fund_code || `基金${index + 1}`;
            drawLegendItem(color, displayName, true, false);
        });
        
        // 4. 绘制买卖点标记图例（如果有交易数据）
        if (fundsWithDetails.some(f => f.trades && f.trades.length > 0)) {
            drawTriangleMarker('#06d6a0', true, '买入');
            drawTriangleMarker('#ef476f', false, '卖出');
        }
    },

    /**
     * 绑定缩放控制按钮
     */
    bindZoomControls() {
        // 使用事件委托，避免重复绑定
        const chartContainer = document.getElementById('nav-chart-container');
        if (!chartContainer) return;
        
        chartContainer.addEventListener('click', (e) => {
            const target = e.target.closest('button');
            if (!target) return;
            
            if (target.id === 'zoom-in-btn') {
                e.stopPropagation();
                this.zoomIn();
            } else if (target.id === 'zoom-out-btn') {
                e.stopPropagation();
                this.zoomOut();
            } else if (target.id === 'reset-zoom-btn') {
                e.stopPropagation();
                this.resetZoom();
            } else if (target.id === 'fullscreen-btn') {
                e.stopPropagation();
                this.toggleFullscreen();
            }
        });
        
        // 监听全屏变化事件
        document.addEventListener('fullscreenchange', () => {
            this.handleFullscreenChange();
        });
    },

    /**
     * 切换全屏模式
     */
    toggleFullscreen() {
        const chartContainer = document.getElementById('nav-chart-container');
        if (!chartContainer) return;
        
        if (!document.fullscreenElement) {
            // 进入全屏
            chartContainer.requestFullscreen().then(() => {
                console.log('📊 进入全屏模式');
            }).catch(err => {
                console.error('❌ 进入全屏失败:', err);
            });
        } else {
            // 退出全屏
            document.exitFullscreen().then(() => {
                console.log('📊 退出全屏模式');
            }).catch(err => {
                console.error('❌ 退出全屏失败:', err);
            });
        }
    },

    /**
     * 处理全屏状态变化
     */
    handleFullscreenChange() {
        const chartContainer = document.getElementById('nav-chart-container');
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        const chartWrapper = chartContainer?.querySelector('.chart-wrapper');
        
        if (!chartContainer) return;
        
        if (document.fullscreenElement) {
            // 全屏模式样式
            chartContainer.style.height = '100vh';
            chartContainer.style.padding = '20px';
            chartContainer.style.display = 'flex';
            chartContainer.style.flexDirection = 'column';
            if (chartWrapper) chartWrapper.style.height = 'calc(100vh - 100px)';
            if (fullscreenBtn) {
                fullscreenBtn.innerHTML = '<i class="bi bi-fullscreen-exit"></i> 退出';
                fullscreenBtn.title = '退出全屏';
            }
            // 重新绘制图表以适应新尺寸
            setTimeout(() => this.refreshChart(), 100);
        } else {
            // 恢复普通模式样式
            chartContainer.style.height = '400px';
            chartContainer.style.padding = '20px';
            chartContainer.style.display = 'block';
            if (chartWrapper) chartWrapper.style.height = '320px';
            if (fullscreenBtn) {
                fullscreenBtn.innerHTML = '<i class="bi bi-fullscreen"></i> 全屏';
                fullscreenBtn.title = '全屏查看';
            }
            // 重新绘制图表
            setTimeout(() => this.refreshChart(), 100);
        }
    },

    /**
     * 放大
     */
    zoomIn() {
        if (this.viewState.scale < this.viewState.maxScale) {
            this.viewState.scale *= 1.2;
            console.log('🔍 放大到:', this.viewState.scale.toFixed(2));
            this.refreshChart();
        }
    },

    /**
     * 缩小
     */
    zoomOut() {
        if (this.viewState.scale > this.viewState.minScale) {
            this.viewState.scale /= 1.2;
            console.log('🔍 缩小到:', this.viewState.scale.toFixed(2));
            this.refreshChart();
        }
    },

    /**
     * 重置缩放
     */
    resetZoom() {
        this.viewState.scale = 1;
        this.viewState.offsetX = 0;
        console.log('🔍 重置视图');
        this.refreshChart();
    },

    /**
     * 刷新图表（根据当前视图状态）
     */
    refreshChart() {
        if (!this.chartState || !this.chartState.data) return;
        
        // 重置绘制标志，允许重新绘制
        this.isDrawing = false;
        this.drawNavChart(this.chartState.data);
    },

    /**
     * 绑定鼠标事件 - 悬停效果、缩放和拖拽
     */
    bindChartEvents(canvas) {
        if (!canvas) return;
        
        // 鼠标移动事件（悬停效果）
        const handleMouseMove = (e) => {
            // 如果正在拖拽，处理拖拽逻辑
            if (this.viewState.isDragging) {
                const dx = e.clientX - this.viewState.lastMouseX;
                this.viewState.offsetX += dx;
                this.viewState.lastMouseX = e.clientX;
                
                // 限制偏移范围
                const maxOffset = 0;
                const minOffset = -this.chartState.chartWidth * (this.viewState.scale - 1);
                this.viewState.offsetX = Math.max(minOffset, Math.min(maxOffset, this.viewState.offsetX));
                
                // 重新绘制
                this.refreshChart();
                return;
            }
            
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const state = this.chartState;
            if (!state) return;
            
            if (x < state.margin.left || x > state.margin.left + state.chartWidth ||
                y < state.margin.top || y > state.margin.top + state.chartHeight) {
                this.hideTooltip();
                canvas.style.cursor = 'default';
                return;
            }
            
            canvas.style.cursor = 'pointer';
            
            const dataIndex = Math.round(((x - state.margin.left) / state.chartWidth) * (state.data.length - 1));
            if (dataIndex < 0 || dataIndex >= state.data.length) return;
            
            this.showTooltip(canvas, x, y, state.data[dataIndex], dataIndex);
        };
        
        // 鼠标离开事件
        const handleMouseLeave = () => {
            this.viewState.isDragging = false;
            this.hideTooltip();
            canvas.style.cursor = 'default';
        };
        
        // 鼠标按下事件（开始拖拽）
        const handleMouseDown = (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const state = this.chartState;
            if (!state) return;
            
            // 只有在图表区域内才能拖拽
            if (x >= state.margin.left && x <= state.margin.left + state.chartWidth &&
                y >= state.margin.top && y <= state.margin.top + state.chartHeight) {
                this.viewState.isDragging = true;
                this.viewState.lastMouseX = e.clientX;
                canvas.style.cursor = 'grabbing';
            }
        };
        
        // 鼠标释放事件（结束拖拽）
        const handleMouseUp = () => {
            this.viewState.isDragging = false;
            canvas.style.cursor = 'pointer';
        };
        
        // 滚轮事件（缩放）
        const handleWheel = (e) => {
            e.preventDefault();
            
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const state = this.chartState;
            if (!state) return;
            
            // 只在图表区域内响应滚轮
            if (x < state.margin.left || x > state.margin.left + state.chartWidth ||
                y < state.margin.top || y > state.margin.top + state.chartHeight) {
                return;
            }
            
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = this.viewState.scale * zoomFactor;
            
            if (newScale >= this.viewState.minScale && newScale <= this.viewState.maxScale) {
                this.viewState.scale = newScale;
                this.refreshChart();
            }
        };
        
        // 添加事件监听器
        canvas.addEventListener('mousemove', handleMouseMove);
        canvas.addEventListener('mouseleave', handleMouseLeave);
        canvas.addEventListener('mousedown', handleMouseDown);
        document.addEventListener('mouseup', handleMouseUp);
        canvas.addEventListener('wheel', handleWheel, { passive: false });
    },

    /**
     * 隐藏 Tooltip
     */
    hideTooltip() {
        const tooltip = document.getElementById('nav-chart-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    },

    /**
     * 显示Tooltip
     */
    showTooltip(canvas, x, y, data, index) {
        let tooltip = document.getElementById('nav-chart-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'nav-chart-tooltip';
            tooltip.style.cssText = `
                position: absolute;
                background: rgba(255, 255, 255, 0.98);
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                pointer-events: none;
                z-index: 10000;
                min-width: 200px;
            `;
            canvas.parentElement.appendChild(tooltip);
        }
        
        const state = this.chartState;
        const portfolioReturn = ((data.portfolio - state.data[0].portfolio) / 
            state.data[0].portfolio * 100).toFixed(2);
        const benchmarkReturn = ((data.benchmark - state.data[0].benchmark) / 
            state.data[0].benchmark * 100).toFixed(2);
        
        const portfolioEmoji = portfolioReturn >= 0 ? '📈' : '📉';
        const benchmarkEmoji = benchmarkReturn >= 0 ? '📈' : '📉';
        
        tooltip.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 8px; color: #212529; border-bottom: 1px solid #eee; padding-bottom: 6px;">
                📅 ${data.date}
            </div>
            <div style="margin-bottom: 6px;">
                <span style="color: #4361ee;">●</span> <strong>组合净值:</strong> ¥${data.portfolio.toFixed(4)}
                <br><span style="color: #666; padding-left: 20px;">${portfolioEmoji} ${portfolioReturn >= 0 ? '+' : ''}${portfolioReturn}%</span>
            </div>
            <div>
                <span style="color: #ef476f;">●</span> <strong>沪深300:</strong> ¥${data.benchmark.toFixed(4)}
                <br><span style="color: #666; padding-left: 20px;">${benchmarkEmoji} ${benchmarkReturn >= 0 ? '+' : ''}${benchmarkReturn}%</span>
            </div>
        `;
        
        const rect = canvas.getBoundingClientRect();
        let tooltipX = x + 15;
        let tooltipY = y - 10;
        
        if (tooltipX + 220 > rect.width) {
            tooltipX = x - 220;
        }
        if (tooltipY < 0) {
            tooltipY = y + 20;
        }
        
        tooltip.style.left = tooltipX + 'px';
        tooltip.style.top = tooltipY + 'px';
        tooltip.style.display = 'block';
    },

    /**
     * 清除高亮（已废弃，使用 hideTooltip 替代）
     */
    clearHighlight(canvas) {
        this.hideTooltip();
    },

    /**
     * 高亮数据点（已废弃，使用 showTooltip 替代）
     */
    highlightDataPoint(canvas, index) {
        // 不再调用 drawNavChart，避免无限重绘
        // 仅更新 tooltip 位置
    },

    /**
     * 添加样式
     */
    addStyles() {
        if (document.getElementById('portfolio-analysis-styles')) return;

        const style = document.createElement('style');
        style.id = 'portfolio-analysis-styles';
        style.textContent = `
            .portfolio-analysis-container {
                --primary-color: #4361ee;
                --success-color: #06d6a0;
                --danger-color: #ef476f;
                --card-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
                --border-radius: 12px;
            }
            
            .portfolio-analysis-container {
                background: white;
                border-radius: var(--border-radius);
                box-shadow: var(--card-shadow);
                margin: 20px 0;
                overflow: hidden;
            }
            
            #nav-chart-tooltip {
                animation: fadeIn 0.15s ease-out;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(5px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .chart-controls button {
                width: 32px;
                height: 32px;
                padding: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                font-weight: bold;
            }
            
            .chart-controls button:hover {
                transform: scale(1.1);
            }
            
            #navChart {
                cursor: pointer;
            }
            
            #navChart:active {
                cursor: grabbing;
            }
            
            /* 全屏模式样式 */
            #nav-chart-container:fullscreen {
                background: white;
                padding: 20px;
                overflow: auto;
            }
            
            #nav-chart-container:-webkit-full-screen {
                background: white;
                padding: 20px;
                overflow: auto;
            }
            
            #nav-chart-container:-moz-full-screen {
                background: white;
                padding: 20px;
                overflow: auto;
            }
            
            #nav-chart-container:fullscreen .chart-header {
                flex-shrink: 0;
            }
            
            #nav-chart-container:fullscreen .chart-wrapper {
                flex: 1;
                min-height: 0;
            }
            
            #nav-chart-container:fullscreen canvas {
                width: 100% !important;
                height: 100% !important;
            }
            
            /* 全屏按钮样式 */
            #fullscreen-btn {
                width: auto !important;
                padding: 0.25rem 0.75rem !important;
                font-size: 12px;
                font-weight: normal;
            }
            
            #fullscreen-btn i {
                margin-right: 4px;
            }
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
