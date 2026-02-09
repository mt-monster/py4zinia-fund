"""
基金类型服务模块 - 基于中国证监会官方分类标准

根据《公开募集证券投资基金运作管理办法》及相关指引：
- 股票型基金：股票资产占基金资产比例不低于80%
- 债券型基金：债券资产占基金资产比例不低于80%
- 混合型基金：投资于股票、债券和货币市场工具，但不符合股票型、债券型基金要求的基金
- 货币型基金：仅投资于货币市场工具的基金
- 指数型基金：采用被动投资策略跟踪某一标的指数的基金
- QDII基金：合格境内机构投资者基金
- ETF基金：交易型开放式指数基金
- FOF基金：基金中基金（投资其他基金份额不低于80%）
"""

import logging
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class FundType(Enum):
    """证监会标准基金类型枚举"""
    STOCK = "stock"           # 股票型基金
    BOND = "bond"             # 债券型基金
    HYBRID = "hybrid"         # 混合型基金
    MONEY_MARKET = "money"    # 货币型基金
    INDEX = "index"           # 指数型基金
    QDII = "qdii"             # QDII基金
    ETF = "etf"               # ETF基金
    FOF = "fof"               # FOF基金
    UNKNOWN = "unknown"       # 未知类型


# 基金类型中文名称映射
FUND_TYPE_CN = {
    FundType.STOCK: "股票型",
    FundType.BOND: "债券型",
    FundType.HYBRID: "混合型",
    FundType.MONEY_MARKET: "货币型",
    FundType.INDEX: "指数型",
    FundType.QDII: "QDII",
    FundType.ETF: "ETF",
    FundType.FOF: "FOF",
    FundType.UNKNOWN: "未知"
}

# 基金类型CSS类名映射（前端展示用）
FUND_TYPE_CSS_CLASS = {
    FundType.STOCK: "fund-type-stock",
    FundType.BOND: "fund-type-bond",
    FundType.HYBRID: "fund-type-hybrid",
    FundType.MONEY_MARKET: "fund-type-money",
    FundType.INDEX: "fund-type-index",
    FundType.QDII: "fund-type-qdii",
    FundType.ETF: "fund-type-etf",
    FundType.FOF: "fund-type-fof",
    FundType.UNKNOWN: "fund-type-unknown"
}

# 基金类型颜色映射（用于图表等）
FUND_TYPE_COLORS = {
    FundType.STOCK: "#28a745",       # 绿色
    FundType.BOND: "#17a2b8",        # 青色
    FundType.HYBRID: "#ffc107",      # 黄色
    FundType.MONEY_MARKET: "#6c757d", # 灰色
    FundType.INDEX: "#007bff",       # 蓝色
    FundType.QDII: "#9b59b6",        # 紫色
    FundType.ETF: "#e74c3c",         # 红色
    FundType.FOF: "#fd7e14",         # 橙色
    FundType.UNKNOWN: "#adb5bd"      # 浅灰
}


class FundTypeService:
    """基金类型服务类"""
    
    @staticmethod
    def classify_fund(fund_name: str, fund_code: str = "", official_type: str = "") -> FundType:
        """
        根据基金名称、代码和官方类型综合判断基金类型
        
        优先级：官方类型 > 名称关键词 > 代码特征
        
        Args:
            fund_name: 基金名称
            fund_code: 基金代码（可选）
            official_type: 官方基金类型（可选）
            
        Returns:
            FundType: 基金类型枚举
        """
        if not fund_name and not official_type:
            return FundType.UNKNOWN
        
        # 首先尝试解析官方类型
        if official_type:
            fund_type = FundTypeService._parse_official_type(official_type)
            if fund_type != FundType.UNKNOWN:
                return fund_type
        
        # 根据基金名称判断
        if fund_name:
            fund_type = FundTypeService._classify_by_name(fund_name)
            if fund_type != FundType.UNKNOWN:
                return fund_type
        
        # 根据基金代码判断（ETF通常有特定代码特征）
        if fund_code:
            fund_type = FundTypeService._classify_by_code(fund_code)
            if fund_type != FundType.UNKNOWN:
                return fund_type
        
        return FundType.UNKNOWN
    
    @staticmethod
    def _parse_official_type(official_type: str) -> FundType:
        """解析官方基金类型"""
        if not official_type:
            return FundType.UNKNOWN
        
        type_str = str(official_type).lower().strip()
        
        # ETF类型（最高优先级，特殊类型）
        if any(kw in type_str for kw in ['etf', '交易型开放式']):
            return FundType.ETF
        
        # QDII类型
        if 'qdii' in type_str or '境外' in type_str or '全球' in type_str:
            return FundType.QDII
        
        # FOF类型
        if 'fof' in type_str or '基金中基金' in type_str:
            return FundType.FOF
        
        # 指数型
        if any(kw in type_str for kw in ['指数', '指数型', '被动']):
            return FundType.INDEX
        
        # 货币型
        if any(kw in type_str for kw in ['货币', '现金', '理财']):
            return FundType.MONEY_MARKET
        
        # 债券型
        if any(kw in type_str for kw in ['债券', '债', '固收', '纯债', '信用债', '利率债']):
            return FundType.BOND
        
        # 股票型（需要排除混合型后再判断）
        if any(kw in type_str for kw in ['股票', '股票型', 'equity']):
            if '混合' not in type_str:
                return FundType.STOCK
        
        # 混合型
        if any(kw in type_str for kw in ['混合', '灵活配置', '偏股', '偏债', '平衡']):
            return FundType.HYBRID
        
        return FundType.UNKNOWN
    
    @staticmethod
    def _classify_by_name(fund_name: str) -> FundType:
        """根据基金名称判断类型"""
        if not fund_name:
            return FundType.UNKNOWN
        
        name = str(fund_name).upper().strip()
        
        # ETF基金（最高优先级 - 特殊交易品种）
        if any(kw in name for kw in ['ETF', '交易型开放式']):
            return FundType.ETF
        
        # QDII基金（次高优先级 - 跨境投资）
        if any(kw in name for kw in ['QDII', '全球', '海外', '美国', '香港', '亚太', 
                                      '环球', '德国', '日本', '印度', '越南', '欧洲', 
                                      '纳斯达克', '标普', '恒生', '道琼斯']):
            return FundType.QDII
        
        # FOF基金
        if 'FOF' in name or '基金中基金' in name:
            return FundType.FOF
        
        # 指数型基金（包含联接基金）
        if any(kw in name for kw in ['指数', 'INDEX', '沪深300', '中证500', '上证50',
                                      '创业板', '科创板', '联接', '联接A', '联接C',
                                      '中证红利', '中证白酒', '中证医疗', '中证新能源']):
            return FundType.INDEX
        
        # 货币型基金
        if any(kw in name for kw in ['货币', '现金', '活期宝', '余额宝']):
            return FundType.MONEY_MARKET
        
        # 债券型基金
        if any(kw in name for kw in ['债券', '纯债', '信用债', '利率债', '短债', 
                                      '中短债', '可转债', '固收', '稳健']):
            # 排除包含"股票"的混合情况
            if not any(kw in name for kw in ['股票', '偏股']):
                return FundType.BOND
        
        # 股票型基金
        if any(kw in name for kw in ['股票', 'EQUITY', 'GROWTH', 'VALUE', '精选', 
                                      '优选', '成长', '价值', '红利']):
            # 排除混合型和指数型
            if not any(kw in name for kw in ['混合', '指数', 'ETF']):
                return FundType.STOCK
        
        # 混合型基金（兜底类型之一）
        if any(kw in name for kw in ['混合', 'MIX', '灵活配置', '偏股', '偏债', '平衡']):
            return FundType.HYBRID
        
        return FundType.UNKNOWN
    
    @staticmethod
    def _classify_by_code(fund_code: str) -> FundType:
        """根据基金代码特征判断类型"""
        if not fund_code:
            return FundType.UNKNOWN
        
        code = str(fund_code).strip()
        
        # ETF基金代码特征（沪市51/56开头，深市15/16开头）
        if code.startswith(('51', '56', '15', '16', '58')) and len(code) == 6:
            # 进一步验证：ETF通常是6位数字
            return FundType.ETF
        
        # LOF基金代码特征
        if code.startswith(('16', '50')) and len(code) == 6:
            return FundType.INDEX  # LOF多为指数基金
        
        return FundType.UNKNOWN
    
    @staticmethod
    def get_fund_type_info(fund_type: FundType) -> Dict:
        """
        获取基金类型的完整信息
        
        Returns:
            Dict: 包含类型代码、中文名、CSS类、颜色等信息的字典
        """
        return {
            'code': fund_type.value,
            'name_cn': FUND_TYPE_CN.get(fund_type, '未知'),
            'css_class': FUND_TYPE_CSS_CLASS.get(fund_type, 'fund-type-unknown'),
            'color': FUND_TYPE_COLORS.get(fund_type, '#adb5bd'),
            'enum': fund_type
        }
    
    @staticmethod
    def get_all_fund_types() -> List[Dict]:
        """获取所有基金类型列表"""
        return [
            FundTypeService.get_fund_type_info(ft)
            for ft in FundType
            if ft != FundType.UNKNOWN
        ]
    
    @staticmethod
    def normalize_fund_type(fund_type_str: str) -> str:
        """
        标准化基金类型字符串为类型代码
        
        Args:
            fund_type_str: 任意形式的基金类型字符串
            
        Returns:
            str: 标准化的类型代码
        """
        fund_type = FundTypeService.classify_fund("", official_type=fund_type_str)
        return fund_type.value
    
    @staticmethod
    def batch_classify(funds: List[Dict]) -> List[Dict]:
        """
        批量分类基金
        
        Args:
            funds: 基金字典列表，每个字典应包含 fund_name, fund_code, fund_type(可选)
            
        Returns:
            List[Dict]: 添加了fund_type_code, fund_type_cn, fund_type_class字段的基金列表
        """
        result = []
        for fund in funds:
            fund_name = fund.get('fund_name', '')
            fund_code = fund.get('fund_code', '')
            official_type = fund.get('fund_type', '')
            
            fund_type = FundTypeService.classify_fund(fund_name, fund_code, official_type)
            type_info = FundTypeService.get_fund_type_info(fund_type)
            
            fund_copy = fund.copy()
            fund_copy['fund_type_code'] = type_info['code']
            fund_copy['fund_type_cn'] = type_info['name_cn']
            fund_copy['fund_type_class'] = type_info['css_class']
            fund_copy['fund_type_color'] = type_info['color']
            result.append(fund_copy)
        
        return result


# 便捷函数，供其他模块直接调用
def classify_fund(fund_name: str = "", fund_code: str = "", official_type: str = "") -> str:
    """
    便捷函数：判断基金类型并返回类型代码
    
    Returns:
        str: 基金类型代码 (stock, bond, hybrid, money, index, qdii, etf, fof, unknown)
    """
    fund_type = FundTypeService.classify_fund(fund_name, fund_code, official_type)
    return fund_type.value


def get_fund_type_display(fund_type_code: str) -> str:
    """
    便捷函数：获取基金类型的中文显示名称
    
    Args:
        fund_type_code: 类型代码
        
    Returns:
        str: 中文名称
    """
    try:
        fund_type = FundType(fund_type_code.lower())
        return FUND_TYPE_CN.get(fund_type, '未知')
    except ValueError:
        return '未知'


def get_fund_type_css_class(fund_type_code: str) -> str:
    """
    便捷函数：获取基金类型的CSS类名
    
    Args:
        fund_type_code: 类型代码
        
    Returns:
        str: CSS类名
    """
    try:
        fund_type = FundType(fund_type_code.lower())
        return FUND_TYPE_CSS_CLASS.get(fund_type, 'fund-type-unknown')
    except ValueError:
        return 'fund-type-unknown'
