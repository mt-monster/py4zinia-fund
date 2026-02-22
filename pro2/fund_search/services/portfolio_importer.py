#!/usr/bin/env python
# coding: utf-8

"""
持仓信息提取和导入系统
从OCR识别的截图中提取持仓信息并导入到MySQL数据库
"""

import re
import logging
from typing import Dict, List, Optional
from datetime import datetime
from data_retrieval.fetchers.akshare_fund_lookup import lookup_fund_info

logger = logging.getLogger(__name__)


class PortfolioImporter:
    """持仓导入器 - MySQL版本"""
    
    def __init__(self, db_manager=None):
        """
        初始化持仓导入器
        
        Args:
            db_manager: 数据库管理器实例，如果为None则自动创建
        """
        if db_manager is None:
            from data_access.enhanced_database import EnhancedDatabaseManager
            from shared.enhanced_config import DATABASE_CONFIG
            db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
        
        self.db = db_manager
        self._ensure_portfolio_table()
    
    def extract_portfolio_from_ocr(self, ocr_texts: List[str]) -> List[Dict]:
        """
        从OCR文本中提取持仓信息
        
        参数：
            ocr_texts: OCR识别的文本列表
            
        返回：
            list: 提取的持仓信息列表
        """
        holdings = []
        
        # 正则表达式模式
        nav_pattern = re.compile(r'\b(\d+\.\d{2})\b')  # 净值格式
        change_amount_pattern = re.compile(r'[+\-](\d+\.\d{2})')  # 涨跌金额
        change_percent_pattern = re.compile(r'[+\-](\d+\.\d{2})%')  # 涨跌百分比
        
        def is_fund_name(text):
            """判断是否为基金名称"""
            if not re.search(r'[\u4e00-\u9fa5]', text):
                return False
            
            exclude_patterns = [
                r'^\d+\.\d+$',  # 纯数字
                r'^[+\-]\d+',   # 涨跌幅
                r'%$',          # 百分比
                r'^全部\(',     # 全部(53)
                r'^我的',       # 我的持有
                r'^基金',       # 基金持仓
                r'^交易',       # 交易相关
                r'^\d+笔',      # 交易笔数
            ]
            
            for pattern in exclude_patterns:
                if re.search(pattern, text):
                    return False
            
            return len(text) > 3  # 基金名称通常较长
        
        i = 0
        while i < len(ocr_texts):
            text = ocr_texts[i].strip()
            
            # 查找基金名称
            if is_fund_name(text):
                holding = {
                    'fund_name': text,
                    'nav_value': None,
                    'change_amount': None,
                    'change_percent': None,
                    'fund_code': None,
                    'position_value': None,  # 持仓金额
                    'shares': None,          # 持有份额
                }
                
                # 查找后续的数值信息
                for j in range(i + 1, min(i + 5, len(ocr_texts))):
                    next_text = ocr_texts[j].strip()
                    
                    # 净值
                    if holding['nav_value'] is None:
                        nav_match = nav_pattern.search(next_text)
                        if nav_match and not re.search(r'[+\-%]', next_text):
                            holding['nav_value'] = float(nav_match.group(1))
                            continue
                    
                    # 涨跌金额
                    if holding['change_amount'] is None:
                        change_match = change_amount_pattern.search(next_text)
                        if change_match and '%' not in next_text:
                            holding['change_amount'] = float(change_match.group(1))
                            if next_text.startswith('-'):
                                holding['change_amount'] *= -1
                            continue
                    
                    # 涨跌百分比
                    if holding['change_percent'] is None:
                        percent_match = change_percent_pattern.search(next_text)
                        if percent_match:
                            holding['change_percent'] = float(percent_match.group(1))
                            if next_text.startswith('-'):
                                holding['change_percent'] *= -1
                            continue
                
                # 通过akshare查找基金代码
                try:
                    fund_info = lookup_fund_info(text)
                    if fund_info:
                        holding['fund_code'] = fund_info['fund_code']
                        holding['fund_name_full'] = fund_info['fund_name']
                        logger.info(f"找到基金: {holding['fund_code']} - {fund_info['fund_name']}")
                    else:
                        logger.warning(f"未找到基金代码: {text}")
                except Exception as e:
                    logger.error(f"查找基金代码时出错: {e}")
                
                # 计算持仓金额（如果有净值和涨跌金额）
                if holding['nav_value'] and holding['change_amount']:
                    # 根据涨跌金额反推持仓金额
                    if holding['change_percent']:
                        # 持仓金额 = 涨跌金额 / (涨跌百分比 / 100)
                        holding['position_value'] = abs(holding['change_amount']) / (abs(holding['change_percent']) / 100)
                
                holdings.append(holding)
                logger.info(f"提取持仓: {holding['fund_name']} - 净值: {holding['nav_value']}")
            
            i += 1
        
        return holdings
    
    def import_to_database(self, holdings: List[Dict], user_id: str = "default") -> bool:
        """
        将持仓信息导入到MySQL数据库
        
        参数：
            holdings: 持仓信息列表
            user_id: 用户ID
            
        返回：
            bool: 是否成功
        """
        if not holdings:
            logger.warning("没有持仓数据需要导入")
            return False
        
        try:
            import_time = datetime.now()
            success_count = 0
            
            for holding in holdings:
                if not holding.get('fund_code'):
                    logger.warning(f"跳过没有基金代码的持仓: {holding.get('fund_name', '未知')}")
                    continue
                
                try:
                    # 检查是否已存在该基金的持仓
                    check_sql = """
                        SELECT id FROM user_portfolio 
                        WHERE user_id = %s AND fund_code = %s
                    """
                    result = self.db.execute_query(check_sql, (user_id, holding['fund_code']))
                    
                    if not result.empty:
                        # 更新现有持仓
                        update_sql = """
                            UPDATE user_portfolio SET
                                fund_name = %s,
                                nav_value = %s,
                                change_amount = %s,
                                change_percent = %s,
                                position_value = %s,
                                shares = %s,
                                last_updated = %s
                            WHERE user_id = %s AND fund_code = %s
                        """
                        params = (
                            holding.get('fund_name_full', holding['fund_name']),
                            holding.get('nav_value'),
                            holding.get('change_amount'),
                            holding.get('change_percent'),
                            holding.get('position_value'),
                            holding.get('shares'),
                            import_time,
                            user_id,
                            holding['fund_code']
                        )
                        self.db.execute_sql(update_sql, params)
                        logger.info(f"更新持仓: {holding['fund_code']}")
                    else:
                        # 插入新持仓
                        insert_sql = """
                            INSERT INTO user_portfolio (
                                user_id, fund_code, fund_name, nav_value,
                                change_amount, change_percent, position_value,
                                shares, created_at, last_updated
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        params = (
                            user_id,
                            holding['fund_code'],
                            holding.get('fund_name_full', holding['fund_name']),
                            holding.get('nav_value'),
                            holding.get('change_amount'),
                            holding.get('change_percent'),
                            holding.get('position_value'),
                            holding.get('shares'),
                            import_time,
                            import_time
                        )
                        self.db.execute_sql(insert_sql, params)
                        logger.info(f"新增持仓: {holding['fund_code']}")
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"导入持仓失败 {holding.get('fund_code')}: {e}")
                    continue
            
            logger.info(f"成功导入 {success_count}/{len(holdings)} 个持仓")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"导入持仓到数据库失败: {e}")
            return False
    
    def _ensure_portfolio_table(self):
        """确保持仓表存在（MySQL版本）"""
        try:
            sql = """
                CREATE TABLE IF NOT EXISTS user_portfolio (
                    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
                    user_id VARCHAR(50) NOT NULL DEFAULT 'default' COMMENT '用户ID',
                    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
                    fund_name VARCHAR(200) COMMENT '基金名称',
                    nav_value DECIMAL(10,4) COMMENT '单位净值',
                    change_amount DECIMAL(10,2) COMMENT '涨跌金额',
                    change_percent DECIMAL(6,2) COMMENT '涨跌百分比',
                    position_value DECIMAL(15,2) COMMENT '持仓金额',
                    shares DECIMAL(15,4) COMMENT '持有份额',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
                    UNIQUE KEY uk_user_fund (user_id, fund_code),
                    INDEX idx_user_id (user_id),
                    INDEX idx_fund_code (fund_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                COMMENT='用户持仓表 - 存储从截图导入的持仓信息'
            """
            self.db.execute_sql(sql)
            logger.info("user_portfolio 表检查/创建成功")
        except Exception as e:
            logger.error(f"创建 user_portfolio 表失败: {e}")
    
    def get_user_portfolio(self, user_id: str = "default") -> List[Dict]:
        """
        获取用户持仓列表
        
        参数：
            user_id: 用户ID
            
        返回：
            list: 持仓列表
        """
        try:
            sql = """
                SELECT * FROM user_portfolio 
                WHERE user_id = %s
                ORDER BY last_updated DESC
            """
            result = self.db.execute_query(sql, (user_id,))
            
            if result.empty:
                return []
            
            # 转换为字典列表
            holdings = result.to_dict('records')
            return holdings
            
        except Exception as e:
            logger.error(f"获取用户持仓失败: {e}")
            return []
    
    def delete_portfolio(self, fund_code: str, user_id: str = "default") -> bool:
        """
        删除指定持仓
        
        Args:
            fund_code: 基金代码
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            sql = "DELETE FROM user_portfolio WHERE user_id = %s AND fund_code = %s"
            affected = self.db.execute_sql(sql, (user_id, fund_code))
            if affected > 0:
                logger.info(f"删除持仓成功: {fund_code}")
                return True
            else:
                logger.warning(f"未找到要删除的持仓: {fund_code}")
                return False
        except Exception as e:
            logger.error(f"删除持仓失败 {fund_code}: {e}")
            return False
    
    def clear_user_portfolio(self, user_id: str = "default") -> bool:
        """
        清空用户所有持仓
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            sql = "DELETE FROM user_portfolio WHERE user_id = %s"
            affected = self.db.execute_sql(sql, (user_id,))
            logger.info(f"清空用户 {user_id} 的持仓，删除 {affected} 条记录")
            return True
        except Exception as e:
            logger.error(f"清空持仓失败: {e}")
            return False


def import_portfolio_from_screenshot(ocr_texts: List[str], user_id: str = "default") -> Dict:
    """
    从截图OCR文本导入持仓（简化接口）
    
    参数：
        ocr_texts: OCR识别的文本列表
        user_id: 用户ID
        
    返回：
        dict: 导入结果
    """
    importer = PortfolioImporter()
    
    # 提取持仓信息
    holdings = importer.extract_portfolio_from_ocr(ocr_texts)
    
    if not holdings:
        return {
            'success': False,
            'message': '未能从截图中提取到持仓信息',
            'holdings_count': 0
        }
    
    # 导入到数据库
    success = importer.import_to_database(holdings, user_id)
    
    return {
        'success': success,
        'message': f'成功导入 {len(holdings)} 个持仓' if success else '导入失败',
        'holdings_count': len(holdings),
        'holdings': holdings
    }


def parse_excel_file(file_path: str) -> List[Dict]:
    """
    解析Excel文件中的持仓数据
    
    参数:
        file_path: Excel文件路径
        
    返回:
        持仓数据列表
    """
    import pandas as pd
    
    try:
        df = pd.read_excel(file_path)
        holdings = []
        
        # 字段映射（支持中英文）
        column_mapping = {
            '基金代码': 'fund_code',
            '基金名称': 'fund_name',
            '持仓金额': 'holding_amount',
            '持仓份额': 'holding_shares',
            '单位净值': 'nav',
        }
        
        for _, row in df.iterrows():
            holding = {}
            for col, key in column_mapping.items():
                if col in row:
                    value = row[col]
                    # 将基金代码转换为字符串，并确保格式正确
                    if key == 'fund_code' and value is not None:
                        value = str(value).strip()
                        # 如果是纯数字，确保是6位格式
                        if value.isdigit():
                            value = value.zfill(6)
                    holding[key] = value
            if holding:
                holdings.append(holding)
        
        return holdings
    except Exception as e:
        logger.error(f"解析Excel文件失败: {str(e)}")
        return []


def validate_holding_data(data: Dict) -> tuple:
    """
    验证持仓数据有效性
    
    参数:
        data: 持仓数据字典
        
    返回:
        (是否有效, 错误信息列表)
    """
    errors = []
    
    # 检查必需字段
    if not data.get('fund_code'):
        errors.append("缺少基金代码")
    
    # 验证基金代码格式
    fund_code = data.get('fund_code', '')
    if fund_code and (len(fund_code) != 6 or not fund_code.isdigit()):
        errors.append(f"基金代码格式无效: {fund_code}")
    
    # 验证持仓金额
    holding_amount = data.get('holding_amount')
    if holding_amount is not None:
        try:
            amount = float(holding_amount)
            if amount < 0:
                errors.append("持仓金额不能为负数")
        except (ValueError, TypeError):
            errors.append("持仓金额必须是数值")
    
    # 验证持仓份额
    holding_shares = data.get('holding_shares')
    if holding_shares is not None:
        try:
            shares = float(holding_shares)
            if shares < 0:
                errors.append("持仓份额不能为负数")
        except (ValueError, TypeError):
            errors.append("持仓份额必须是数值")
    
    is_valid = len(errors) == 0
    return is_valid, errors


if __name__ == "__main__":
    # 测试代码
    test_texts = [
        "基金持仓",
        "天弘标普500发起(QDII-FOF)A",
        "681.30",
        "+21.11",
        "+3.20%",
        "景顺长城全球半导体芯片股票A",
        "664.00",
        "+83.08",
        "+15.08%"
    ]
    
    result = import_portfolio_from_screenshot(test_texts)
    print(f"导入结果: {result}")
