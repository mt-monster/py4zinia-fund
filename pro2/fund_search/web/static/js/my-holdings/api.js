/**
 * API 模块 - 处理所有后端通信
 */
const FundAPI = {
    /**
     * 获取基金列表
     */
    async getFunds(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`${FundConfig.api.funds}?${queryString}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            // /api/holdings 返回的是 data 字段，不是 funds 字段
            return {
                success: data.success,
                data: data.data || [],
                total: data.total || 0
            };
        } catch (error) {
            console.error('API Error - getFunds:', error);
            return {
                success: false,
                error: error.message,
                data: [],
                total: 0
            };
        }
    },

    /**
     * 获取基金详情
     */
    async getFundDetail(fundCode) {
        try {
            const response = await fetch(`${FundConfig.api.fundDetail}${fundCode}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return {
                success: true,
                data: data
            };
        } catch (error) {
            console.error('API Error - getFundDetail:', error);
            return {
                success: false,
                error: error.message
            };
        }
    },

    /**
     * 导入截图
     */
    async importScreenshot(imageData) {
        try {
            const response = await fetch(FundConfig.api.importScreenshot, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageData
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return {
                success: true,
                data: data
            };
        } catch (error) {
            console.error('API Error - importScreenshot:', error);
            return {
                success: false,
                error: error.message
            };
        }
    },

    /**
     * 开始分析
     */
    async startAnalysis(fundCodes) {
        try {
            const response = await fetch(FundConfig.api.analysis, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    funds: fundCodes
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return {
                success: true,
                data: data
            };
        } catch (error) {
            console.error('API Error - startAnalysis:', error);
            return {
                success: false,
                error: error.message
            };
        }
    },

    /**
     * 获取市场指数
     */
    async getMarketIndex() {
        try {
            // 模拟数据，实际应该调用真实API
            return {
                success: true,
                data: {
                    name: '沪深300',
                    value: '3,456.78',
                    change: '+12.34',
                    changePercent: '+0.36%'
                }
            };
        } catch (error) {
            console.error('API Error - getMarketIndex:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
};
