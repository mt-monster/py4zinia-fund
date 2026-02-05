#!/usr/bin/env python
# coding: utf-8

"""
智能基金解析器
支持识别"基金XXXXXX"格式和手工导入功能
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from .akshare_fund_lookup import lookup_fund_info

logger = logging.getLogger(__name__)

class SmartFundParser:
    """智能基金解析器"""
    
    def __init__(self):
        self.manual_import_suggestions = []
    
    def parse_fund_info_smart(self, texts: List[str]) -> Tuple[List[Dict], List[str]]:
        """
        智能解析基金信息（优化版）

        参数：
        texts: OCR识别的文本列表

        返回：
        tuple: (成功识别的基金列表, 需要手工导入的文本列表)
        """
        funds = []
        manual_import_needed = []

        # 记录所有OCR识别的文本，用于调试
        logger.info(f"OCR识别到的所有文本 ({len(texts)} 项): {texts}")

        # 步骤1：预处理过滤UI元素
        texts = self._preprocess_texts(texts)
        logger.info(f"过滤后的文本 ({len(texts)} 项): {texts}")

        # 步骤2：尝试重组被分割的基金名称（简化版）
        texts = self._reconstruct_fund_names_v2(texts)
        logger.info(f"重组后的文本 ({len(texts)} 项): {texts}")
        
        # 基金代码的正则表达式（6位数字）
        code_pattern = re.compile(r'\b(\d{6})\b')
        
        # "基金XXXXXX"格式的正则表达式
        fund_code_format_pattern = re.compile(r'^基金(\d{6})$')
        
        # 净值的正则表达式（数字.数字格式）
        nav_pattern = re.compile(r'\b(\d+\.\d{2})\b')
        
        i = 0
        while i < len(texts):
            text = texts[i].strip()
            
            # 方法1：识别"基金XXXXXX"格式
            fund_code_match = fund_code_format_pattern.match(text)
            if fund_code_match:
                fund_code = fund_code_match.group(1)
                
                # 通过akshare查找基金信息
                fund_info = self._lookup_fund_by_code(fund_code)
                
                if fund_info:
                    # 查找可能的净值
                    nav_value = self._find_nav_value(texts, i)
                    
                    fund_data = {
                        'fund_code': fund_code,
                        'fund_name': fund_info['fund_name'],
                        'nav_value': nav_value,
                        'confidence': 0.9,
                        'source': 'code_format_match',
                        'original_text': text,
                        'holding_amount': None,  # 持仓金额
                        'profit_amount': None,   # 盈亏金额
                        'profit_rate': None      # 盈亏率
                    }
                    
                    funds.append(fund_data)
                    logger.info(f"通过代码格式识别基金: {fund_code} - {fund_info['fund_name']}")
                else:
                    # 基金代码无效，需要手工导入
                    manual_import_needed.append({
                        'text': text,
                        'reason': f'基金代码 {fund_code} 无效或不存在',
                        'suggested_code': fund_code
                    })
                    logger.warning(f"基金代码无效: {fund_code}")
            
            # 方法2：识别纯6位数字代码
            elif code_pattern.match(text) and len(text) == 6:
                fund_code = text
                
                # 排除明显不是基金代码的6位数字
                if self._is_likely_non_fund_number(fund_code):
                    logger.debug(f"跳过可能的非基金6位数字: {fund_code}")
                    i += 1
                    continue
                
                # 先验证这是否是一个有效的基金代码，避免误识别其他6位数字
                fund_info = self._lookup_fund_by_code(fund_code)
                
                if fund_info:
                    # 查找可能的净值
                    nav_value = self._find_nav_value(texts, i)
                    
                    fund_data = {
                        'fund_code': fund_code,
                        'fund_name': fund_info['fund_name'],
                        'nav_value': nav_value,
                        'confidence': 0.85,
                        'source': 'pure_code_match',
                        'original_text': text,
                        'holding_amount': None,
                        'profit_amount': None,
                        'profit_rate': None
                    }
                    
                    funds.append(fund_data)
                    logger.info(f"通过纯代码识别基金: {fund_code} - {fund_info['fund_name']}")
                else:
                    # 基金代码无效，可能是其他6位数字（金额、日期等），跳过而不是加入手工导入
                    logger.debug(f"跳过无效的6位数字: {fund_code} (可能是金额或其他数字)")
                    # 不加入 manual_import_needed，因为这很可能不是基金代码
            
            # 方法3：识别可能的基金名称（包含中文且长度适中）
            elif self._is_potential_fund_name(text):
                logger.debug(f"尝试通过名称识别: {text}")
                # 尝试通过名称查找
                fund_info = self._lookup_fund_by_name(text)
                
                if fund_info:
                    # 查找可能的净值和持仓信息
                    nav_value = self._find_nav_value(texts, i)
                    holding_info = self._find_holding_info(texts, i)
                    
                    fund_data = {
                        'fund_code': fund_info['fund_code'],
                        'fund_name': fund_info['fund_name'],
                        'nav_value': nav_value,
                        'confidence': 0.8,
                        'source': 'name_match',
                        'original_text': text,
                        'holding_amount': holding_info.get('holding_amount'),
                        'profit_amount': holding_info.get('profit_amount'),
                        'profit_rate': holding_info.get('profit_rate')
                    }
                    
                    funds.append(fund_data)
                    logger.info(f"通过名称识别基金: {fund_info['fund_code']} - {fund_info['fund_name']}")
                else:
                    # 无法识别，需要手工导入
                    manual_import_needed.append({
                        'text': text,
                        'reason': '无法通过名称找到匹配的基金',
                        'suggested_name': text
                    })
                    logger.debug(f"无法识别基金名称: {text}")
            else:
                logger.debug(f"跳过非基金文本: {text}")
            
            i += 1
        
        # 去重处理
        logger.info(f"去重前识别到 {len(funds)} 个基金记录")
        for i, fund in enumerate(funds):
            logger.debug(f"  {i+1}. {fund['fund_code']} - {fund['fund_name']} (来源: {fund['source']}, 置信度: {fund['confidence']})")
        
        funds = self._deduplicate_funds(funds)
        logger.info(f"去重后保留 {len(funds)} 个基金")
        
        for i, fund in enumerate(funds):
            logger.info(f"  最终 {i+1}. {fund['fund_code']} - {fund['fund_name']} (来源: {fund['source']})")
        
        return funds, manual_import_needed
    
    def _deduplicate_funds(self, funds: List[Dict]) -> List[Dict]:
        """去重基金列表，保留置信度最高的记录，并合并净值等信息"""
        if not funds:
            return funds
        
        # 按基金代码分组
        fund_groups = {}
        for fund in funds:
            fund_code = fund['fund_code']
            if fund_code not in fund_groups:
                fund_groups[fund_code] = []
            fund_groups[fund_code].append(fund)
        
        # 每组保留置信度最高的记录，并合并其他信息
        deduplicated_funds = []
        for fund_code, group in fund_groups.items():
            if len(group) > 1:
                logger.info(f"发现重复基金 {fund_code}，共 {len(group)} 条记录，进行去重")
            
            # 按置信度排序，取最高的
            best_fund = max(group, key=lambda x: x['confidence'])
            
            # 如果有多个相同置信度的记录，优先选择"基金XXXXXX"格式
            same_confidence_funds = [f for f in group if f['confidence'] == best_fund['confidence']]
            if len(same_confidence_funds) > 1:
                # 优先级：code_format_match > pure_code_match > name_match
                priority_order = {
                    'code_format_match': 3,
                    'pure_code_match': 2, 
                    'name_match': 1
                }
                
                best_fund = max(same_confidence_funds, 
                              key=lambda x: priority_order.get(x['source'], 0))
                
                logger.info(f"相同置信度，选择优先级更高的来源: {best_fund['source']}")
            
            # 合并净值信息：从所有记录中找到最佳的净值
            if best_fund.get('nav_value') is None:
                for fund in group:
                    if fund.get('nav_value') is not None:
                        best_fund['nav_value'] = fund['nav_value']
                        logger.info(f"从其他记录合并净值: {fund['nav_value']}")
                        break
            
            # 合并持仓信息：从所有记录中找到最完整的持仓信息
            if best_fund.get('holding_amount') is None:
                for fund in group:
                    if fund.get('holding_amount') is not None:
                        best_fund['holding_amount'] = fund['holding_amount']
                        logger.debug(f"从其他记录合并持仓金额: {fund['holding_amount']}")
                        break
            
            if best_fund.get('profit_amount') is None:
                for fund in group:
                    if fund.get('profit_amount') is not None:
                        best_fund['profit_amount'] = fund['profit_amount']
                        logger.debug(f"从其他记录合并盈亏金额: {fund['profit_amount']}")
                        break
            
            if best_fund.get('profit_rate') is None:
                for fund in group:
                    if fund.get('profit_rate') is not None:
                        best_fund['profit_rate'] = fund['profit_rate']
                        logger.debug(f"从其他记录合并盈亏率: {fund['profit_rate']}%")
                        break
            
            deduplicated_funds.append(best_fund)
            
            if len(group) > 1:
                logger.info(f"去重完成: {fund_code} - {best_fund['fund_name']} (来源: {best_fund['source']}, 净值: {best_fund.get('nav_value', 'N/A')})")
        
        return deduplicated_funds
    
    def _lookup_fund_by_code(self, fund_code: str) -> Optional[Dict]:
        """通过基金代码查找基金信息"""
        try:
            from .akshare_fund_lookup import AkshareFundLookup
            
            lookup = AkshareFundLookup()
            fund_list = lookup.get_fund_list()
            
            if fund_list.empty:
                return None
            
            # 查找匹配的基金代码
            matching_funds = fund_list[fund_list['基金代码'] == fund_code]
            
            if not matching_funds.empty:
                fund_row = matching_funds.iloc[0]
                return {
                    'fund_code': fund_code,
                    'fund_name': fund_row['基金简称'],
                    'fund_type': fund_row.get('基金类型', ''),
                    'similarity': 1.0
                }
            
            return None
            
        except Exception as e:
            logger.error(f"查找基金代码 {fund_code} 时出错: {e}")
            return None
    
    def _lookup_fund_by_name(self, fund_name: str) -> Optional[Dict]:
        """通过基金名称查找基金信息"""
        try:
            fund_info = lookup_fund_info(fund_name)
            return fund_info
        except Exception as e:
            logger.error(f"查找基金名称 {fund_name} 时出错: {e}")
            return None
    
    def _find_nav_value(self, texts: List[str], current_index: int) -> Optional[float]:
        """在当前位置附近查找净值"""
        nav_pattern = re.compile(r'\b(\d+\.\d{2})\b')
        
        # 在后续几行中查找净值
        for j in range(current_index + 1, min(current_index + 4, len(texts))):
            if j >= len(texts):
                break
                
            text = texts[j].strip()
            
            # 跳过包含+/-符号的文本（涨跌幅）
            if '+' in text or '-' in text or '%' in text:
                continue
            
            # 跳过基金代码格式
            if text.startswith('基金') and len(text) == 9:
                continue
            
            # 跳过纯6位数字（可能是其他基金代码）
            if len(text) == 6 and text.isdigit():
                continue
            
            nav_match = nav_pattern.search(text)
            if nav_match:
                try:
                    nav_value = float(nav_match.group(1))
                    # 净值通常在0.1到100之间
                    if 0.1 <= nav_value <= 100:
                        logger.debug(f"找到净值 {nav_value} 在位置 {j}: {text}")
                        return nav_value
                except ValueError:
                    continue
        
        return None
    
    def _find_holding_info(self, texts: List[str], current_index: int) -> Dict:
        """在当前位置附近查找持仓信息（持仓金额、盈亏金额、盈亏率、昨日收益）"""
        holding_info = {
            'holding_amount': None,
            'profit_amount': None,
            'profit_rate': None,
            'yesterday_profit': None,  # 新增昨日收益
            'yesterday_profit_rate': None,  # 新增昨日收益率
        }
        
        # 收集当前基金相关的所有数值文本
        collected_values = []
        
        # 在后续几行中查找持仓相关数据（通常基金名称后面的2-6行是相关数据）
        for j in range(current_index + 1, min(current_index + 10, len(texts))):
            if j >= len(texts):
                break
                
            text = texts[j].strip()
            
            # 如果遇到另一个基金名称，停止搜索
            if self._is_fund_name_start(text) and len(text) > 4:
                break
            
            # 跳过交易信息行（如"交易：1笔买入中合计10.00元"）
            if '交易' in text or '笔' in text or '合计' in text:
                continue
            
            # 收集数值信息
            value_info = self._parse_value_text(text)
            if value_info:
                collected_values.append(value_info)
        
        # 智能分配数值到对应字段
        self._assign_values_to_fields(collected_values, holding_info)
        
        return holding_info
    
    def _parse_value_text(self, text: str) -> Optional[Dict]:
        """解析数值文本，返回类型和值"""
        text = text.strip()
        
        # 持仓金额格式（正数，如283.37, 228.32, 321.03）
        amount_match = re.match(r'^(\d{2,5}\.\d{2})$', text)
        if amount_match:
            value = float(amount_match.group(1))
            # 持仓金额通常在50-100000之间
            if 50 <= value <= 100000:
                return {'type': 'amount', 'value': value, 'text': text}
        
        # 带符号的金额（如+0.75, -1.57, -14.91, -15.80）- 盈亏金额
        profit_match = re.match(r'^([+\-])(\d+\.\d{2})$', text)
        if profit_match:
            sign = 1 if profit_match.group(1) == '+' else -1
            value = sign * float(profit_match.group(2))
            return {'type': 'profit_amount', 'value': value, 'text': text}
        
        # 百分比格式（如-5.17%, -6.94%, +3.20%）- 盈亏率
        rate_match = re.match(r'^([+\-])?(\d+\.\d{1,2})%$', text)
        if rate_match:
            sign = 1 if rate_match.group(1) != '-' else -1
            value = sign * float(rate_match.group(2))
            return {'type': 'profit_rate', 'value': value, 'text': text}
        
        return None
    
    def _assign_values_to_fields(self, values: List[Dict], holding_info: Dict):
        """智能分配数值到对应字段
        
        基于截图布局规则：
        - 第一列：金额（持仓金额）
        - 第二列：昨日收益（带+/-符号）
        - 第三列：持仓收益（带+/-符号，绝对值通常较大）
        - 第四列：收益率（带%符号）
        """
        amounts = [v for v in values if v['type'] == 'amount']
        profit_amounts = [v for v in values if v['type'] == 'profit_amount']
        profit_rates = [v for v in values if v['type'] == 'profit_rate']
        
        # 分配持仓金额（取最大的金额作为持仓金额）
        if amounts:
            holding_info['holding_amount'] = max(amounts, key=lambda x: x['value'])['value']
            logger.debug(f"识别持仓金额: {holding_info['holding_amount']}")
        
        # 分配盈亏金额
        if profit_amounts:
            if len(profit_amounts) >= 2:
                # 按绝对值排序，较小的是昨日收益，较大的是持仓收益
                sorted_profits = sorted(profit_amounts, key=lambda x: abs(x['value']))
                holding_info['yesterday_profit'] = sorted_profits[0]['value']
                holding_info['profit_amount'] = sorted_profits[-1]['value']
                logger.debug(f"识别昨日收益: {holding_info['yesterday_profit']}, 持仓收益: {holding_info['profit_amount']}")
            else:
                # 只有一个盈亏金额，作为持仓收益
                holding_info['profit_amount'] = profit_amounts[0]['value']
                logger.debug(f"识别持仓收益: {holding_info['profit_amount']}")
        
        # 分配收益率（通常只有一个收益率，是持仓收益率）
        if profit_rates:
            holding_info['profit_rate'] = profit_rates[0]['value']
            logger.debug(f"识别收益率: {holding_info['profit_rate']}%")
    
    def _extract_holding_amount(self, text: str) -> Optional[float]:
        """提取持仓金额"""
        # 匹配持仓金额格式（通常是较大的数字，如681.30, 664.00）
        amount_pattern = re.compile(r'^(\d{2,4}\.\d{2})$')
        match = amount_pattern.match(text)
        
        if match:
            try:
                amount = float(match.group(1))
                # 持仓金额通常在100-10000之间
                if 100 <= amount <= 10000:
                    return amount
            except ValueError:
                pass
        
        return None
    
    def _extract_profit_amount(self, text: str) -> Optional[float]:
        """提取盈亏金额"""
        # 匹配盈亏金额格式（带+/-符号，如+21.11, -83.08）
        profit_pattern = re.compile(r'^([+\-])(\d+\.\d{2})$')
        match = profit_pattern.match(text)
        
        if match:
            try:
                sign = match.group(1)
                amount = float(match.group(2))
                return amount if sign == '+' else -amount
            except ValueError:
                pass
        
        return None
    
    def _extract_profit_rate(self, text: str) -> Optional[float]:
        """提取盈亏率"""
        # 匹配盈亏率格式（带%符号，如+3.20%, -15.08%）
        rate_pattern = re.compile(r'^([+\-])(\d+\.\d{2})%$')
        match = rate_pattern.match(text)
        
        if match:
            try:
                sign = match.group(1)
                rate = float(match.group(2))
                return rate if sign == '+' else -rate
            except ValueError:
                pass
        
        return None
    
    def _is_potential_fund_name(self, text: str) -> bool:
        """判断是否为潜在的基金名称"""
        # 必须包含中文
        if not re.search(r'[\u4e00-\u9fa5]', text):
            return False
        
        # 长度要适中
        if len(text) < 2 or len(text) > 50:  # 降低最小长度，因为名称可能被分割
            return False
        
        # 排除过于通用的词汇
        generic_words = ['基金', '股票', '债券', '混合', '指数', '货币', '数A', '数C', '业股票A', '业股票C']
        if text in generic_words:
            logger.debug(f"排除过于通用的词汇: {text}")
            return False
        
        # 排除明显不是基金名称的文本
        exclude_patterns = [
            r'^\d+\.\d+$',      # 纯数字
            r'^[+\-]\d+',       # 涨跌幅
            r'%$',              # 百分比
            r'^全部\(',         # 全部(53)
            r'^股票型\(',       # 股票型(8)
            r'^债券型\(',       # 债券型(0)
            r'^混合型\(',       # 混合型(x)
            r'^货币型\(',       # 货币型(x)
            r'^指数型\(',       # 指数型(x)
            r'^QDII型\(',       # QDII型(x)
            r'^我的',           # 我的持有
            r'^基金持仓',       # 基金持仓
            r'^交易',           # 交易相关
            r'^\d+笔',          # 交易笔数
            r'^基金\d{6}$',     # 基金代码格式（已在其他地方处理）
            r'^持仓',           # 持仓相关
            r'^资产',           # 资产相关
            r'^总计',           # 总计
            r'^合计',           # 合计
            r'^余额',           # 余额
            r'^可用',           # 可用资金
            r'^冻结',           # 冻结资金
            r'^\d+元$',         # 纯金额
            r'^\d+\.\d+元$',    # 带小数的金额
            r'^昨日',           # 昨日相关
            r'^今日',           # 今日相关
            r'^当前',           # 当前相关
            r'^最新',           # 最新相关
            r'盈亏',            # 盈亏相关
            r'^份额',           # 份额
            r'^净值',           # 净值
            r'^\d{4}-\d{2}-\d{2}$',  # 日期格式
            r'^\d{2}:\d{2}$',   # 时间格式
            r'^基金名称$',      # 表头
            r'^持仓收益',       # 表头
            r'^金额排序$',      # 排序选项
            r'^理财师$',        # 界面元素
            r'^基金圈$',        # 界面元素
            r'^自选$',          # 界面元素
            r'^全球投资$',      # 界面元素
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text):
                logger.debug(f"排除非基金文本: {text} (匹配模式: {pattern})")
                return False
        
        return True

    def _is_likely_non_fund_number(self, number: str) -> bool:
        """判断6位数字是否可能不是基金代码"""
        if len(number) != 6 or not number.isdigit():
            return True

        # 排除明显不是基金代码的数字模式
        num = int(number)

        # 排除过小的数字（通常基金代码不会太小）
        if num < 1000:
            return True

        # 排除常见的金额模式（如100000, 200000等整数万元）
        if num % 10000 == 0 and num <= 999999:
            return True

        # 排除日期相关的数字（如202401, 202312等）
        if number.startswith('20') and 2020 <= num // 100 <= 2030:
            return True

        # 排除时间相关的数字（如120000表示12:00:00）
        if number.startswith('1') or number.startswith('2'):
            hour = int(number[:2])
            minute = int(number[2:4])
            second = int(number[4:6])
            if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                return True

        return False

    def _preprocess_texts(self, texts: List[str]) -> List[str]:
        """预处理：过滤UI元素和无关文本"""
        filtered = []

        for text in texts:
            text = text.strip()
            if not text:
                continue

            # 过滤UI元素
            if self._is_ui_element(text):
                logger.debug(f"过滤UI元素: {text}")
                continue

            # 过滤时间格式
            if re.match(r'^\d{1,2}:\d{2}$', text):
                logger.debug(f"过滤时间: {text}")
                continue

            # 过滤信号/网络图标
            if text in ['5G', '4G', 'WiFi', 'LTE', '<', '>']:
                logger.debug(f"过滤信号图标: {text}")
                continue

            filtered.append(text)

        return filtered

    def _is_ui_element(self, text: str) -> bool:
        """判断是否是UI元素而非基金数据"""
        ui_patterns = [
            r'^\d+%$',                    # 百分比如 78%
            r'^全部\(\d+\)$',              # 全部(50)
            r'^股票型\(\d+\)',             # 股票型(8)
            r'^债券型\(\d+\)',             # 债券型(0)
            r'^混\d+基金',                 # 混1基金
            r'^交易[：:]',                  # 交易提示
            r'^合计',                      # 合计
            r'^\d+笔',                     # 1笔买入
            r'^买入中$',                   # 买入中
            r'^[￥$]',                     # 货币符号
            r'^基金$', r'^自选$', r'^持仓$', r'^全球投资$', r'^基金圈$',  # 底部导航
            r'^理财师$', r'^我的持有$', r'^持有收益排序$',  # 界面元素
            r'^金额[/／]昨日收益',          # 表头
            r'^持仓收益[/／]率$',           # 表头
        ]

        return any(re.match(p, text) for p in ui_patterns)

    def _reconstruct_fund_names_v2(self, texts: List[str]) -> List[str]:
        """增强版：重组被OCR分割的基金名称，支持更复杂的分割情况"""
        reconstructed = []
        skip_indices = set()

        for i, text in enumerate(texts):
            if i in skip_indices:
                continue

            text = text.strip()
            if not text:
                continue

            # 只处理可能是基金名称开头的文本
            if not self._is_fund_name_start(text):
                reconstructed.append(text)
                continue

            # 尝试向后组合，最多看4个文本
            combined = text
            combined_indices = [i]
            
            for j in range(i + 1, min(i + 5, len(texts))):
                next_text = texts[j].strip()
                
                # 如果遇到数值数据，停止组合
                if self._is_holding_data(next_text):
                    break
                
                # 如果是另一个基金名称的开头（且不是ETF/LOF等后缀），停止组合
                if self._is_fund_name_start(next_text) and len(next_text) > 3:
                    # 但如果下一个文本是ETF开头或者括号开头，应该继续合并
                    if not next_text.startswith('ETF') and not next_text.startswith('('):
                        break
                
                # 如果是明确的基金名称延续，合并
                if self._is_strict_fund_name_continuation(next_text, combined):
                    combined += next_text
                    combined_indices.append(j)
                    skip_indices.add(j)
                # 如果是短片段且可能是名称的一部分
                elif self._is_possible_name_fragment(next_text, combined):
                    combined += next_text
                    combined_indices.append(j)
                    skip_indices.add(j)
                else:
                    break

            reconstructed.append(combined)
            if len(combined_indices) > 1:
                logger.debug(f"名称重组: {[texts[idx] for idx in combined_indices]} -> {combined}")

        return reconstructed

    def _is_strict_fund_name_continuation(self, text: str, current_name: str) -> bool:
        """严格判断是否是基金名称的延续"""
        if not text:
            return False
            
        # 排除明显不是名称的文本
        if re.match(r'^[\d\.\+\-]', text):  # 数字开头
            return False
        if any(c in text for c in ['%', '￥', '$', '元', '份']):  # 包含金额符号
            return False
        if text in ['基金', '理财', '证监会批准', '民生银行资金监管', '资金安全险']:
            return False
        
        # 常见的基金名称后续片段（这些应该与前面的名称合并）
        fund_suffixes = [
            'ETF联接', 'ETF', 'LOF', 'QDII', 'FOF',
            '联接A', '联接C', '联接', '股票A', '股票C', '混合A', '混合C',
            '指数A', '指数C', '债券A', '债券C',
            '(QDII)', '(LOF)', '(FOF)', '(QDII)A', '(QDII)C',
            '严选', '精选', '优选', '增强', '成长', '价值', '龙头',
            '印度', '中证', '沪深', '银行', '科技', '医药', '消费',
        ]
        
        # 如果文本以ETF开头，很可能是ETF联接A等后缀
        if text.startswith('ETF'):
            return True
        
        for suffix in fund_suffixes:
            if suffix in text:
                return True
        
        # 如果当前名称不完整（没有A/C后缀），且下一个片段是类型标识
        if not re.search(r'[AC]$', current_name):
            if re.match(r'^[AC]$', text):  # 单独的A或C
                return True
        
        # 短中文片段且不包含明显的非名称词
        if len(text) <= 8 and re.search(r'[\u4e00-\u9fa5]', text):
            exclude_words = ['交易', '买入', '卖出', '赎回', '持仓', '收益', '盈亏', 
                           '全部', '昨日', '今日', '合计', '元', '份', '笔']
            if not any(word in text for word in exclude_words):
                return True
        
        return False
    
    def _is_possible_name_fragment(self, text: str, current_name: str) -> bool:
        """判断是否是可能的名称片段（更宽松的判断）"""
        if not text or len(text) > 10:
            return False
        
        # 数字开头排除
        if re.match(r'^[\d\.\+\-]', text):
            return False
        
        # 特殊分类标识
        special_patterns = [
            r'^\(QDII',  # (QDII开头
            r'^[AC]$',   # 单独的A或C
            r'^混合[AC]?$',
            r'^股票[AC]?$',
            r'^债券[AC]?$',
            r'^指数[AC]?$',
        ]
        
        for pattern in special_patterns:
            if re.match(pattern, text):
                return True
        
        return False

    def _reconstruct_fund_names(self, texts: List[str]) -> List[str]:
        """尝试重组被OCR分割的基金名称，同时保留持仓信息（旧版，保留兼容）"""
        reconstructed = []
        i = 0
        
        while i < len(texts):
            text = texts[i].strip()
            
            # 检查是否是基金名称的开头部分
            if self._is_fund_name_start(text):
                # 尝试与后续文本组合
                combined_name = text
                j = i + 1
                holding_data = []  # 收集持仓相关数据
                
                # 向后查找可能的名称片段和持仓数据，最多查找8个后续文本
                while j < len(texts) and j < i + 9:
                    next_text = texts[j].strip()
                    
                    # 如果是持仓相关数据（金额、盈亏等），保存但不合并到名称中
                    if self._is_holding_data(next_text):
                        holding_data.append(next_text)
                        logger.debug(f"收集持仓数据: {next_text}")
                        j += 1
                        continue
                    
                    # 如果是基金名称的后续部分，合并
                    if self._is_fund_name_continuation(next_text):
                        combined_name += next_text
                        logger.debug(f"合并基金名称片段: '{text}' + '{next_text}' -> '{combined_name}'")
                        j += 1
                    else:
                        break
                
                # 如果组合后的名称更有可能是基金名称，使用组合后的
                if j > i + 1 and self._is_likely_complete_fund_name(combined_name):
                    reconstructed.append(combined_name)
                    # 将收集到的持仓数据也添加到重组后的文本中
                    reconstructed.extend(holding_data)
                    logger.debug(f"重组基金名称: '{text}' + 后续片段 -> '{combined_name}', 持仓数据: {holding_data}")
                    # 跳过已经处理的文本
                    i = j
                    continue
            
            # 如果不是基金名称开头或无法组合，保持原文本
            reconstructed.append(text)
            i += 1
        
        return reconstructed
    
    def _is_holding_data(self, text: str) -> bool:
        """判断是否是持仓相关数据"""
        if not text:
            return False
        
        # 持仓金额格式（如681.30, 664.00）
        if re.match(r'^\d{2,4}\.\d{2}$', text):
            return True
        
        # 盈亏金额格式（如+21.11, -83.08）
        if re.match(r'^[+\-]\d+\.\d{2}$', text):
            return True
        
        # 盈亏率格式（如+3.20%, -15.08%）
        if re.match(r'^[+\-]\d+\.\d{2}%$', text):
            return True
        
        return False
    
    def _is_numeric_or_symbol(self, text: str) -> bool:
        """判断是否是纯数字或符号"""
        if not text:
            return True
        
        # 纯数字、金额、百分比、符号等
        numeric_patterns = [
            r'^\d+\.\d+$',      # 小数
            r'^[+\-]\d+',       # 带符号的数字
            r'%$',              # 百分比
            r'^\d+$',           # 整数
            r'^[+\-]$',         # 单独的符号
        ]
        
        for pattern in numeric_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _is_fund_name_start(self, text: str) -> bool:
        """判断是否是基金名称的开头部分"""
        if not text or len(text) < 2:
            return False
        
        # 包含中文且不是明显的非基金文本
        if not re.search(r'[\u4e00-\u9fa5]', text):
            return False
        
        # 常见基金公司名称开头模式（按首字母排序，覆盖主流基金公司）
        fund_start_patterns = [
            # A-B
            r'^安信',           # 安信基金
            r'^宝盈',           # 宝盈基金
            r'^北信瑞丰',       # 北信瑞丰
            r'^博时',           # 博时基金
            r'^博道',           # 博道基金
            # C-D
            r'^财通',           # 财通基金
            r'^长城',           # 长城基金
            r'^长盛',           # 长盛基金
            r'^长信',           # 长信基金
            r'^创金合信',       # 创金合信
            r'^大成',           # 大成基金
            r'^德邦',           # 德邦基金
            r'^东方',           # 东方基金
            r'^东吴',           # 东吴基金
            # F-G
            r'^方正富邦',       # 方正富邦
            r'^富安达',         # 富安达
            r'^富国',           # 富国基金
            r'^富荣',           # 富荣基金
            r'^工银',           # 工银瑞信
            r'^光大',           # 光大保德信
            r'^广发',           # 广发基金
            r'^国富',           # 国富基金
            r'^国海',           # 国海富兰克林
            r'^国金',           # 国金基金
            r'^国联',           # 国联安基金
            r'^国融',           # 国融基金
            r'^国寿安保',       # 国寿安保
            r'^国泰',           # 国泰基金
            r'^国投瑞银',       # 国投瑞银
            # H
            r'^海富通',         # 海富通基金
            r'^恒生',           # 恒生前海
            r'^恒越',           # 恒越基金
            r'^红塔红土',       # 红塔红土
            r'^红土创新',       # 红土创新
            r'^弘毅',           # 弘毅远方
            r'^宏利',           # 宏利基金
            r'^华安',           # 华安基金
            r'^华宝',           # 华宝基金
            r'^华富',           # 华富基金
            r'^华商',           # 华商基金
            r'^华泰',           # 华泰柏瑞
            r'^华夏',           # 华夏基金
            r'^汇安',           # 汇安基金
            r'^汇丰晋信',       # 汇丰晋信
            r'^汇添富',         # 汇添富基金
            # J-K
            r'^嘉合',           # 嘉合基金
            r'^嘉实',           # 嘉实基金
            r'^建信',           # 建信基金
            r'^交银',           # 交银施罗德
            r'^金信',           # 金信基金
            r'^金鹰',           # 金鹰基金
            r'^金元顺安',       # 金元顺安
            r'^景顺',           # 景顺长城
            r'^九泰',           # 九泰基金
            r'^凯石',           # 凯石基金
            # L-M
            r'^蓝海',           # 蓝海华腾
            r'^民生',           # 民生加银
            r'^摩根',           # 摩根基金
            # N-P
            r'^南方',           # 南方基金
            r'^南华',           # 南华基金
            r'^农银',           # 农银汇理
            r'^诺安',           # 诺安基金
            r'^诺德',           # 诺德基金
            r'^鹏华',           # 鹏华基金
            r'^鹏扬',           # 鹏扬基金
            r'^浦银安盛',       # 浦银安盛
            r'^平安',           # 平安基金
            # Q-R
            r'^前海',           # 前海开源
            r'^融通',           # 融通基金
            r'^睿远',           # 睿远基金
            # S
            r'^上海',           # 上海东方证券
            r'^上投',           # 上投摩根
            r'^申万',           # 申万菱信
            r'^泰达',           # 泰达宏利
            r'^泰信',           # 泰信基金
            r'^泰康',           # 泰康资产
            r'^天弘',           # 天弘基金
            r'^天治',           # 天治基金
            # W-X
            r'^万家',           # 万家基金
            r'^西部',           # 西部利得
            r'^先锋',           # 先锋基金
            r'^新华',           # 新华基金
            r'^鑫元',           # 鑫元基金
            r'^信达澳银',       # 信达澳亚
            r'^信诚',           # 信诚基金
            r'^兴全',           # 兴全基金
            r'^兴银',           # 兴银基金
            r'^兴业',           # 兴业基金
            # Y
            r'^易方达',         # 易方达基金
            r'^银河',           # 银河基金
            r'^银华',           # 银华基金
            r'^英大',           # 英大基金
            r'^永赢',           # 永赢基金
            r'^圆信永丰',       # 圆信永丰
            # Z
            r'^招商',           # 招商基金
            r'^浙商',           # 浙商基金
            r'^中庚',           # 中庚基金
            r'^中海',           # 中海基金
            r'^中航',           # 中航基金
            r'^中欧',           # 中欧基金
            r'^中融',           # 中融基金
            r'^中泰',           # 中泰证券
            r'^中信',           # 中信保诚
            r'^中信建投',       # 中信建投
            r'^中银',           # 中银基金
            r'^中邮',           # 中邮创业
            r'^中加',           # 中加基金
            r'^中金',           # 中金基金
            # ETF联接等特殊格式
            r'^[A-Z]',          # 以大写字母开头（如ETF名称）
        ]
        
        for pattern in fund_start_patterns:
            if re.search(pattern, text):
                return True
        
        # 如果文本较长且包含基金相关关键词，也可能是基金名称开头
        if len(text) >= 3:
            fund_keywords = ['基金', '股票', '债券', '混合', '指数', '货币', 'ETF', 'LOF', 'QDII', 'FOF', '联接', '增强', '精选', '优选', '龙头', '成长', '价值', '稳健', '灵活配置']
            for keyword in fund_keywords:
                if keyword in text:
                    return True
        
        return False
    
    def _is_fund_name_continuation(self, text: str) -> bool:
        """判断是否是基金名称的后续部分"""
        if not text:
            return False
        
        # 常见的基金名称后续部分
        continuation_patterns = [
            r'^导体',           # "半导体"的后半部分
            r'^数[A-Z]',        # "指数A"的后半部分
            r'^\s*网股票',      # "互联网股票"的后半部分
            r'^业股票',         # "产业股票"的后半部分
            r'^\([A-Z]+\)',     # 括号内的分类如(QDII)
            r'^[A-Z]$',         # 单个字母如A、C
            r'^股票',           # 股票
            r'^债券',           # 债券
            r'^混合',           # 混合
            r'^指数',           # 指数
            r'^货币',           # 货币
            r'^\(QDII',         # QDII相关
            r'^\(LOF\)',        # LOF
            r'^\(FOF\)',        # FOF
        ]
        
        for pattern in continuation_patterns:
            if re.search(pattern, text):
                return True
        
        # 如果是短文本且包含中文，也可能是名称片段
        if len(text) <= 8 and re.search(r'[\u4e00-\u9fa5]', text):
            # 但排除明显的干扰项
            exclude_short = ['基金', '持仓', '收益', '交易', '全部', '股票型', '债券型']
            if text not in exclude_short:
                return True
        
        return False
    
    def _is_likely_complete_fund_name(self, name: str) -> bool:
        """判断组合后的名称是否像完整的基金名称"""
        if not name or len(name) < 4:
            return False
        
        # 包含基金相关关键词
        fund_keywords = ['基金', '股票', '债券', '混合', '指数', '货币', 'ETF', 'LOF', 'QDII', 'FOF']
        has_keyword = any(keyword in name for keyword in fund_keywords)
        
        # 包含中文
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', name))
        
        # 长度合理
        reasonable_length = 6 <= len(name) <= 40
        
        return has_keyword and has_chinese and reasonable_length
    
    def generate_manual_import_prompt(self, manual_items: List[Dict]) -> str:
        """生成手工导入提示"""
        if not manual_items:
            return ""
        
        prompt = "以下内容无法自动识别，建议手工导入：\n\n"
        
        for i, item in enumerate(manual_items, 1):
            prompt += f"{i}. 识别文本: {item['text']}\n"
            prompt += f"   原因: {item['reason']}\n"
            
            if 'suggested_code' in item:
                prompt += f"   建议代码: {item['suggested_code']}\n"
            elif 'suggested_name' in item:
                prompt += f"   建议名称: {item['suggested_name']}\n"
            
            prompt += "\n"
        
        prompt += "请手工确认基金代码和名称，或提供更清晰的截图。"
        
        return prompt

def parse_fund_info_with_manual_fallback(texts: List[str]) -> Dict:
    """
    解析基金信息，支持手工导入提示
    
    参数：
    texts: OCR识别的文本列表
    
    返回：
    dict: 包含识别结果和手工导入建议的字典
    """
    parser = SmartFundParser()
    funds, manual_items = parser.parse_fund_info_smart(texts)
    
    result = {
        'success': len(funds) > 0,
        'funds': funds,
        'funds_count': len(funds),
        'manual_import_needed': len(manual_items) > 0,
        'manual_items': manual_items,
        'manual_prompt': parser.generate_manual_import_prompt(manual_items) if manual_items else ""
    }
    
    return result

# 模块级函数，供测试使用
def parse_fund_code(code_str: str) -> Optional[str]:
    """
    解析基金代码
    
    参数:
        code_str: 可能包含基金代码的字符串
        
    返回:
        标准化的6位基金代码，如果无效则返回None
    """
    if not code_str:
        return None
    
    # 清理字符串
    code_str = code_str.strip()
    
    # 移除可能的后缀
    if '.' in code_str:
        code_str = code_str.split('.')[0]
    
    # 检查是否为6位数字
    if len(code_str) == 6 and code_str.isdigit():
        return code_str
    
    # 尝试匹配"基金XXXXXX"格式
    fund_pattern = re.compile(r'基金(\d{6})')
    match = fund_pattern.search(code_str)
    if match:
        return match.group(1)
    
    return None


def validate_fund_data(data: Dict) -> tuple:
    """
    验证基金数据完整性
    
    参数:
        data: 基金数据字典
        
    返回:
        (是否有效, 错误信息列表)
    """
    errors = []
    
    # 检查必需字段
    required_fields = ['fund_code', 'fund_name']
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"缺少必需字段: {field}")
    
    # 验证基金代码格式
    if 'fund_code' in data and data['fund_code']:
        code = data['fund_code']
        if len(code) != 6 or not code.isdigit():
            errors.append(f"基金代码格式无效: {code}")
    
    # 验证数值字段
    numeric_fields = ['nav', 'daily_return', 'holding_amount']
    for field in numeric_fields:
        if field in data and data[field] is not None:
            try:
                float(data[field])
            except (ValueError, TypeError):
                errors.append(f"字段 {field} 必须是数值类型")
    
    is_valid = len(errors) == 0
    return is_valid, errors


if __name__ == "__main__":
    # 测试代码
    test_texts = [
        "基金006257",
        "664.00",
        "+83.08",
        "基金000516", 
        "681.30",
        "007721",
        "568.11",
        "天弘标普500发起",
        "429.02"
    ]
    
    result = parse_fund_info_with_manual_fallback(test_texts)
    
    print(f"识别成功: {result['success']}")
    print(f"识别基金数量: {result['funds_count']}")
    
    for fund in result['funds']:
        print(f"  {fund['fund_code']} - {fund['fund_name']} (净值: {fund.get('nav_value', 'N/A')})")
    
    if result['manual_import_needed']:
        print(f"\n需要手工导入: {len(result['manual_items'])} 项")
        print(result['manual_prompt'])