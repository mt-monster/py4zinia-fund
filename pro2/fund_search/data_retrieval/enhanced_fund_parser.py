#!/usr/bin/env python
# coding: utf-8

"""
增强版基金信息解析器
支持从基金名称查找对应的基金代码
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 常见基金名称到代码的映射（可以扩展）
FUND_NAME_CODE_MAPPING = {
    "天弘标普500": "007721",
    "天弘标普500发起": "007721", 
    "景顺长城全球半导体": "501225",
    "景顺长城全球半导体芯片": "501225",
    "广发北证50": "159673",
    "广发北证50成份": "159673",
    "富国全球科技": "100055",
    "富国全球科技互联网": "100055",
    "易方达战略新兴": "010391",
    "易方达战略新兴产业": "010391",
}

def parse_fund_info_enhanced(texts: List[str]) -> List[Dict]:
    """
    增强版基金信息解析，支持无代码识别
    
    参数：
    texts: OCR识别的文本列表
    
    返回：
    list: 解析出的基金列表
    """
    funds = []
    
    # 基金代码的正则表达式（6位数字）
    code_pattern = re.compile(r'\b(\d{6})\b')
    
    # 净值的正则表达式（数字.数字格式）
    nav_pattern = re.compile(r'\b(\d+\.\d{2})\b')
    
    # 涨跌幅的正则表达式
    change_pattern = re.compile(r'[+\-]\d+\.\d+%?')
    
    def is_fund_name(text):
        """判断是否为基金名称"""
        # 包含中文且长度适中
        if not re.search(r'[\u4e00-\u9fa5]', text):
            return False
        
        # 排除明显不是基金名称的文本
        exclude_patterns = [
            r'^\d+\.\d+$',  # 纯数字
            r'^[+\-]\d+',   # 涨跌幅
            r'%$',          # 百分比
            r'^全部\(',     # 全部(53)
            r'^我的',       # 我的持有
            r'^基金',       # 基金持仓
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text):
                return False
        
        return True
    
    def find_fund_code_by_name(fund_name):
        """根据基金名称查找代码"""
        # 清理基金名称
        clean_name = re.sub(r'\([^)]*\)', '', fund_name)  # 移除括号内容
        clean_name = re.sub(r'[A-Z]$', '', clean_name)    # 移除末尾字母
        clean_name = clean_name.strip()
        
        # 在映射表中查找
        for name_key, code in FUND_NAME_CODE_MAPPING.items():
            if name_key in clean_name or clean_name in name_key:
                return code
        
        return None
    
    # 遍历文本，查找基金信息
    i = 0
    while i < len(texts):
        text = texts[i].strip()
        
        # 方法1：查找6位数字代码
        code_match = code_pattern.search(text)
        if code_match:
            fund_code = code_match.group(1)
            
            # 查找基金名称（通常在代码前面）
            name_before = text[:code_match.start()].strip()
            if name_before and len(name_before) > 2:
                fund_name = clean_fund_name(name_before)
                funds.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'confidence': 0.9,
                    'source': 'code_match'
                })
                logger.info(f"通过代码识别基金: {fund_code} - {fund_name}")
        
        # 方法2：通过基金名称查找代码
        elif is_fund_name(text) and len(text) > 4:
            fund_code = find_fund_code_by_name(text)
            if fund_code:
                fund_name = clean_fund_name(text)
                
                # 查找可能的净值
                nav_value = None
                if i + 1 < len(texts):
                    next_text = texts[i + 1]
                    nav_match = nav_pattern.search(next_text)
                    if nav_match:
                        nav_value = float(nav_match.group(1))
                
                funds.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'nav_value': nav_value,
                    'confidence': 0.8,
                    'source': 'name_match'
                })
                logger.info(f"通过名称识别基金: {fund_code} - {fund_name} (净值: {nav_value})")
        
        i += 1
    
    # 去重
    unique_funds = []
    seen_codes = set()
    for fund in funds:
        if fund['fund_code'] not in seen_codes:
            unique_funds.append(fund)
            seen_codes.add(fund['fund_code'])
    
    return unique_funds

def clean_fund_name(name: str) -> str:
    """
    清理基金名称
    """
    # 移除常见的后缀标识
    name = re.sub(r'\(QDII[^)]*\)', '', name)
    name = re.sub(r'\(LOF\)', '', name)
    name = re.sub(r'\(FOF\)', '', name)
    
    # 移除末尾的字母分类
    name = re.sub(r'[A-Z]$', '', name)
    
    # 移除多余的空格
    name = ' '.join(name.split())
    
    return name.strip()

def add_fund_mapping(fund_name: str, fund_code: str):
    """
    添加新的基金名称到代码映射
    """
    FUND_NAME_CODE_MAPPING[fund_name] = fund_code
    logger.info(f"添加基金映射: {fund_name} -> {fund_code}")

def get_fund_mappings():
    """
    获取当前的基金映射表
    """
    return FUND_NAME_CODE_MAPPING.copy()

if __name__ == "__main__":
    # 测试增强版解析器
    test_texts = [
        "基金持仓",
        "天弘标准普尔500指数发起式证券投资基金(QDII-FOF)A",
        "681.30",
        "+21.11",
        "景顺长城全球半导体芯片股票型证券投资基金A",
        "664.00",
        "+83.08",
        "广发北证50成份指数证券投资基金A",
        "568.11"
    ]
    
    funds = parse_fund_info_enhanced(test_texts)
    print(f"识别到 {len(funds)} 只基金:")
    for fund in funds:
        print(f"  {fund['fund_code']} - {fund['fund_name']} (来源: {fund['source']})")