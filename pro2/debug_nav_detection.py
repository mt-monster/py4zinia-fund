#!/usr/bin/env python
# coding: utf-8

"""
调试净值识别
"""

import re

def debug_nav_detection():
    """调试净值识别逻辑"""
    test_texts = [
        "006257",           # 0: 基金代码
        "基金006257",       # 1: 基金格式
        "681.30",          # 2: 净值
        "+21.11",          # 3: 涨跌金额
        "000516",          # 4: 基金代码
        "基金000516",      # 5: 基金格式
        "664.00",          # 6: 净值
        "+83.08",          # 7: 涨跌金额
    ]
    
    print("=== 调试净值识别 ===")
    
    nav_pattern = re.compile(r'\b(\d+\.\d{2})\b')
    
    for i, text in enumerate(test_texts):
        print(f"{i}: {text}")
        
        # 模拟在基金代码后查找净值
        if text == "006257" or text == "基金006257":
            print(f"  从位置 {i} 开始查找净值...")
            
            # 查找后续3行
            for j in range(i + 1, min(i + 4, len(test_texts))):
                next_text = test_texts[j]
                print(f"    检查位置 {j}: {next_text}")
                
                # 检查是否包含+/-符号
                if '+' in next_text or '-' in next_text or '%' in next_text:
                    print(f"      跳过（包含+/-/%符号）")
                    continue
                
                # 检查是否是基金代码格式
                if next_text.startswith('基金') and len(next_text) == 9:
                    print(f"      跳过（基金代码格式）")
                    continue
                
                # 检查是否是纯6位数字
                if len(next_text) == 6 and next_text.isdigit():
                    print(f"      跳过（纯6位数字）")
                    continue
                
                # 查找净值模式
                nav_match = nav_pattern.search(next_text)
                if nav_match:
                    nav_value = float(nav_match.group(1))
                    if 0.1 <= nav_value <= 100:
                        print(f"      ✓ 找到净值: {nav_value}")
                        break
                    else:
                        print(f"      净值超出范围: {nav_value}")
                else:
                    print(f"      未匹配净值模式")
            
            print()

if __name__ == "__main__":
    debug_nav_detection()