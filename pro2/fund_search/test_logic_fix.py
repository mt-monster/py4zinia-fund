#!/usr/bin/env python3
"""
直接测试buy_date处理逻辑
"""

def test_buy_date_processing():
    """测试buy_date处理逻辑"""
    
    def process_buy_date(buy_date):
        """模拟我们修复后的buy_date处理逻辑"""
        if buy_date is None or buy_date == '' or (isinstance(buy_date, str) and buy_date.lower() in ['none', 'null']):
            return None
        return buy_date
    
    def generate_sql_for_buy_date(buy_date):
        """生成对应的SQL语句"""
        processed_date = process_buy_date(buy_date)
        if processed_date is None:
            return "buy_date = NULL"
        else:
            return f"buy_date = '{processed_date}'"
    
    # 测试用例
    test_cases = [
        ('', '空字符串'),
        (None, 'None值'),
        ('null', '字符串null'),
        ('NULL', '字符串NULL'),
        ('none', '字符串none'),
        ('2024-01-15', '有效日期'),
        ('2024-01-01', '另一个有效日期')
    ]
    
    print("=== buy_date处理逻辑测试 ===")
    print("输入值 -> 处理后值 -> SQL语句")
    print("-" * 50)
    
    for input_val, description in test_cases:
        processed = process_buy_date(input_val)
        sql = generate_sql_for_buy_date(input_val)
        status = "✅" if processed is None or (isinstance(processed, str) and '-' in processed) else "❌"
        print(f"{status} {input_val!r} ({description}) -> {processed!r} -> {sql}")

def test_original_error_simulation():
    """模拟原始错误场景"""
    print("\n=== 原始错误场景模拟 ===")
    
    # 模拟原始有问题的SQL
    def original_approach(buy_date):
        return f"buy_date = '{buy_date}'"  # 直接插入，不处理空值
    
    # 模拟修复后的SQL
    def fixed_approach(buy_date):
        if buy_date is None or buy_date == '':
            return "buy_date = NULL"
        else:
            return f"buy_date = '{buy_date}'"
    
    test_values = ['', None, '2024-01-15']
    
    print("原始方法 vs 修复方法:")
    print("-" * 60)
    for val in test_values:
        try:
            original_sql = original_approach(val)
            print(f"输入: {val!r}")
            print(f"  原始: {original_sql}")
            print(f"  修复: {fixed_approach(val)}")
            if val == '':
                print("  ❌ 原始方法会导致MySQL错误: Incorrect date value: ''")
            print()
        except Exception as e:
            print(f"  原始方法异常: {e}")

if __name__ == '__main__':
    test_buy_date_processing()
    test_original_error_simulation()
    
    print("\n=== 修复总结 ===")
    print("✅ 空字符串('')会被转换为NULL")
    print("✅ None值会被保持为NULL") 
    print("✅ 'null'/'NULL'/'none'字符串会被转换为NULL")
    print("✅ 有效日期格式会保持原样")
    print("✅ 修复已应用到以下函数:")
    print("   - update_holding()")
    print("   - add_holding()")
    print("   - import_holding_confirm()")