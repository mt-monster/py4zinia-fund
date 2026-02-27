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
     * 批量获取基金实时估值
     */
    async getRealtimeEstimates(fundCodes) {
        try {
            const response = await fetch('/api/funds/realtime-estimates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fund_codes: fundCodes })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return {
                success: data.success,
                data: data.data || {}
            };
        } catch (error) {
            console.warn('API Warning - getRealtimeEstimates:', error);
            return { success: false, data: {} };
        }
    },

    /**
     * 获取市场指数
     */
    async getMarketIndex() {
        try {
            const response = await fetch(FundConfig.api.marketIndex);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || '获取指数失败');
            }

            return {
                success: true,
                data: data.data
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
