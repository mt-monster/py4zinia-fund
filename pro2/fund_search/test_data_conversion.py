#!/usr/bin/env python
# coding: utf-8

"""
测试OCR识别数据到数据库数据的转换逻辑
"""

# 模拟OCR识别返回的数据
ocr_data = [
    {
        'fund_code': '013048',
        'fund_name': '富国中证新能源汽车指数(LOF)C',
        'holding_amount': 276.65,
        'profit_amount': 13.45,
        'profit_rate': 5.31,
        'current_value': 290.10,
        'nav_value': 1.234,  # 假设的净值
        'confidence': 0.95,
        'source': 'ocr'
    },
    {
        'fund_code': '013277',
        'fund_name': '富国创业板ETF联接C',
        'holding_amount': 274.58,
        'profit_amount': 5.20,
        'profit_rate': 2.09,
        'current_value': 279.78,
        'nav_value': 1.156,  # 假设的净值
        'confidence': 0.92,
        'source': 'ocr'
    },
    {
        'fund_code': '006106',
        'fund_name': '易顺长城国宝化港股通灵活配置A',
        'holding_amount': 262.57,
        'profit_amount': 4.08,
        'profit_rate': 1.57,
        'current_value': 266.65,
        'nav_value': 1.089,  # 假设的净值
        'confidence': 0.88,
        'source': 'ocr'
    }
]

print("=" * 80)
print("OCR识别数据转换测试")
print("=" * 80)

for fund in ocr_data:
    print(f"\n基金: {fund['fund_name']} ({fund['fund_code']})")
    print(f"  持仓金额: ¥{fund['holding_amount']:.2f}")
    print(f"  盈亏金额: ¥{fund['profit_amount']:.2f}")
    print(f"  当前市值: ¥{fund['current_value']:.2f}")
    print(f"  净值: {fund['nav_value']:.3f}")
    
    # 计算持有份额和成本价
    holding_amount = fund['holding_amount']
    current_value = fund['current_value']
    nav_value = fund['nav_value']
    
    if current_value > 0 and nav_value > 0:
        # 持有份额 = 当前市值 / 当前净值
        holding_shares = current_value / nav_value
        # 成本价 = 持仓金额 / 持有份额
        cost_price = holding_amount / holding_shares if holding_shares > 0 else 0
        
        print(f"\n  转换后:")
        print(f"  持有份额: {holding_shares:.2f}")
        print(f"  成本价: ¥{cost_price:.4f}")
        
        # 验证：持有份额 * 成本价 应该等于持仓金额
        calculated_holding = holding_shares * cost_price
        print(f"\n  验证: {holding_shares:.2f} × {cost_price:.4f} = ¥{calculated_holding:.2f}")
        print(f"  原始持仓金额: ¥{holding_amount:.2f}")
        print(f"  差异: ¥{abs(calculated_holding - holding_amount):.2f}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
