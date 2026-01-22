#!/usr/bin/env python
# coding: utf-8

"""
持仓信息提取和导入系统
从OCR识别的截图中提取持仓信息并导入到数据库
"""

import re
import logging
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
from .akshare_fund_lookup import lookup_fund_info

logger = logging.getLogger(__name__)

class PortfolioImporter:
    """持仓导入器"""
    
    def __init__(self, db_path: str = "fund_analysis.db"):
        self.db_path = db_path
    
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
                    # 这是一个估算，实际可能需要更复杂的计算
                    if holding['change_percent']:
                        # 持仓金额 = 涨跌金额 / (涨跌百分比 / 100)
                        holding['position_value'] = abs(holding['change_amount']) / (abs(holding['change_percent']) / 100)
                
                holdings.append(holding)
                logger.info(f"提取持仓: {holding['fund_name']} - 净值: {holding['nav_value']}")
            
            i += 1
        
        return holdings
    
    def import_to_database(self, holdings: List[Dict], user_id: str = "default") -> bool:
        """
        将持仓信息导入到数据库
        
        参数：
        holdings: 持仓信息列表
        user_id: 用户ID
        
        返回：
        bool: 是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否存在持仓表，如果不存在则创建
            self._ensure_portfolio_table(cursor)
            
            import_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            success_count = 0
            
            for holding in holdings:
                if not holding.get('fund_code'):
                    logger.warning(f"跳过没有基金代码的持仓: {holding['fund_name']}")
                    continue
                
                try:
                    # 检查是否已存在该基金的持仓
                    cursor.execute("""
                        SELECT id FROM user_portfolio 
                        WHERE user_id = ? AND fund_code = ?
                    """, (user_id, holding['fund_code']))
                    
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 更新现有持仓
                        cursor.execute("""
                            UPDATE user_portfolio SET
                                fund_name = ?,
                                nav_value = ?,
                                change_amount = ?,
                                change_percent = ?,
                                position_value = ?,
                                shares = ?,
                                last_updated = ?
                            WHERE user_id = ? AND fund_code = ?
                        """, (
                            holding.get('fund_name_full', holding['fund_name']),
                            holding.get('nav_value'),
                            holding.get('change_amount'),
                            holding.get('change_percent'),
                            holding.get('position_value'),
                            holding.get('shares'),
                            import_time,
                            user_id,
                            holding['fund_code']
                        ))
                        logger.info(f"更新持仓: {holding['fund_code']}")
                    else:
                        # 插入新持仓
                        cursor.execute("""
                            INSERT INTO user_portfolio (
                                user_id, fund_code, fund_name, nav_value,
                                change_amount, change_percent, position_value,
                                shares, created_at, last_updated
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
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
                        ))
                        logger.info(f"新增持仓: {holding['fund_code']}")
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"导入持仓失败 {holding['fund_code']}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            logger.info(f"成功导入 {success_count}/{len(holdings)} 个持仓")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"导入持仓到数据库失败: {e}")
            return False
    
    def _ensure_portfolio_table(self, cursor):
        """确保持仓表存在"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                fund_code TEXT NOT NULL,
                fund_name TEXT,
                nav_value REAL,
                change_amount REAL,
                change_percent REAL,
                position_value REAL,
                shares REAL,
                created_at TEXT,
                last_updated TEXT,
                UNIQUE(user_id, fund_code)
            )
        """)
    
    def get_user_portfolio(self, user_id: str = "default") -> List[Dict]:
        """
        获取用户持仓列表
        
        参数：
        user_id: 用户ID
        
        返回：
        list: 持仓列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM user_portfolio 
                WHERE user_id = ?
                ORDER BY last_updated DESC
            """, (user_id,))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            portfolio = []
            for row in rows:
                portfolio.append(dict(zip(columns, row)))
            
            conn.close()
            return portfolio
            
        except Exception as e:
            logger.error(f"获取用户持仓失败: {e}")
            return []

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