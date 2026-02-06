/**
 * 配置模块 - 定义表头、常量等
 */
const FundConfig = {
    // 默认表头配置 - 与 /api/holdings 返回字段匹配
    defaultColumns: [
        { key: 'fund_code', label: '基金代码', visible: true, sortable: true },
        { key: 'fund_name', label: '基金名称', visible: true, sortable: true },
        { key: 'today_return', label: '日涨跌幅', visible: true, sortable: true, type: 'percent' },
        { key: 'prev_day_return', label: '昨日盈亏率', visible: true, sortable: true, type: 'percent' },
        { key: 'holding_amount', label: '持有金额', visible: true, sortable: true, type: 'currency' },
        { key: 'holding_profit', label: '持有收益', visible: true, sortable: true, type: 'currency' },
        { key: 'holding_profit_rate', label: '持有收益率', visible: true, sortable: true, type: 'percent' },
        { key: 'current_value', label: '当前市值', visible: true, sortable: true, type: 'currency' },
        { key: 'annualized_return', label: '年化收益', visible: true, sortable: true, type: 'percent' },
        { key: 'max_drawdown', label: '最大回撤', visible: true, sortable: true, type: 'percent' },
        { key: 'sharpe_ratio', label: '夏普比率', visible: true, sortable: true, type: 'number' },
        { key: 'sharpe_ratio_ytd', label: '夏普(今年以来)', visible: false, sortable: true, type: 'number' },
        { key: 'sharpe_ratio_1y', label: '夏普(近一年)', visible: false, sortable: true, type: 'number' },
        { key: 'sharpe_ratio_all', label: '夏普(成立以来)', visible: false, sortable: true, type: 'number' },
        { key: 'volatility', label: '波动率', visible: false, sortable: true, type: 'percent' },
        { key: 'calmar_ratio', label: '卡玛比率', visible: false, sortable: true, type: 'number' },
        { key: 'sortino_ratio', label: '索提诺比率', visible: false, sortable: true, type: 'number' },
        { key: 'composite_score', label: '综合评分', visible: true, sortable: true, type: 'number' }
    ],

    // API 端点
    api: {
        funds: '/api/holdings',  // 使用持仓接口而非基金分析接口
        fundDetail: '/api/fund/',
        importScreenshot: '/api/holdings/import/screenshot',
        analysis: '/api/analysis'
    },

    // 本地存储键
    storage: {
        columns: 'fund_columns_config',
        filters: 'fund_filters',
        settings: 'fund_settings'
    },

    // 分页配置
    pagination: {
        pageSize: 50,
        pageSizeOptions: [20, 50, 100, 200]
    }
};

// 全局状态
const FundState = {
    funds: [],
    filteredFunds: [],
    selectedFunds: new Set(),
    currentPage: 1,
    pageSize: FundConfig.pagination.pageSize,
    sortColumn: null,
    sortDirection: 'asc',
    filters: {},
    columnConfig: null,
    isLoading: false
};
