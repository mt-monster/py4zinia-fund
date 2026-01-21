#!/usr/bin/env python
# coding: utf-8

"""
测试OCR配置
"""

from fund_search.data_retrieval.fund_screenshot_ocr import parse_fund_info
from fund_search.data_retrieval.ocr_config import get_ocr_engine, get_confidence_threshold

def test_ocr_config():
    """测试OCR配置"""
    print(f"当前OCR引擎: {get_ocr_engine()}")
    print(f"置信度阈值: {get_confidence_threshold()}")
    
    # 测试文本解析
    test_texts = [
        '天弘标普500发起(QDII-FOF)A',
        '007721',
        '景顺长城全球半导体芯片股票A(QDII-LOF)(人民币)',
        '501225'
    ]
    
    funds = parse_fund_info(test_texts)
    print(f"解析结果: 识别到 {len(funds)} 只基金")
    for fund in funds:
        print(f'  {fund["fund_code"]} - {fund["fund_name"]}')

if __name__ == "__main__":
    test_ocr_config()