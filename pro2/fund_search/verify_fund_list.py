#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证基金列表获取

检查预加载的基金列表是否是市场上真实存在的场外基金。

使用示例:
    python verify_fund_list.py
    
    # 查看前50只基金
    python verify_fund_list.py --limit 50
    
    # 保存到文件
    python verify_fund_list.py --output fund_list.txt
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_fund_list_from_market():
    """从市场获取基金列表"""
    try:
        import akshare as ak
        
        logger.info("正在从市场获取场外开放式基金列表...")
        
        # 方法1: 使用 fund_open_fund_daily_em
        try:
            fund_df = ak.fund_open_fund_daily_em()
            if not fund_df.empty and '基金代码' in fund_df.columns:
                codes = fund_df['基金代码'].unique().tolist()
                names = fund_df['基金简称'].tolist() if '基金简称' in fund_df.columns else [''] * len(codes)
                valid_funds = [(c, n) for c, n in zip(codes, names) 
                              if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                logger.info(f"✓ 从 fund_open_fund_daily_em 获取到 {len(valid_funds)} 只场外基金")
                return valid_funds
        except Exception as e:
            logger.warning(f"方法1失败: {e}")
        
        # 方法2: 使用 fund_name_em 并过滤
        try:
            fund_df = ak.fund_name_em()
            if not fund_df.empty and '基金代码' in fund_df.columns:
                codes = fund_df['基金代码'].unique().tolist()
                names = fund_df['基金简称'].tolist() if '基金简称' in fund_df.columns else [''] * len(codes)
                
                # 过滤有效的场外基金
                valid_funds = []
                for c, n in zip(codes, names):
                    if isinstance(c, str) and len(c) == 6 and c.isdigit():
                        # 排除场内基金代码（ETF、LOF等）
                        if not c.startswith(('51', '15', '16', '50', '18')):
                            valid_funds.append((c, n))
                
                logger.info(f"✓ 从 fund_name_em 获取到 {len(valid_funds)} 只场外基金")
                return valid_funds
        except Exception as e:
            logger.warning(f"方法2失败: {e}")
        
        return []
        
    except Exception as e:
        logger.error(f"获取基金列表失败: {e}")
        return []


def analyze_fund_list(funds):
    """分析基金列表"""
    if not funds:
        logger.warning("基金列表为空")
        return
    
    codes = [f[0] for f in funds]
    
    print("\n" + "=" * 60)
    print("基金列表分析")
    print("=" * 60)
    
    print(f"\n总数量: {len(funds)} 只")
    
    # 按代码前缀统计
    prefixes = {}
    for code in codes:
        prefix = code[:2]
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    
    print("\n按代码前缀分布:")
    for prefix, count in sorted(prefixes.items(), key=lambda x: -x[1])[:10]:
        print(f"  {prefix}xxxx: {count} 只")
    
    # 检查是否有场内基金代码
    etf_prefixes = ['51', '15', '16', '50', '18']
    etf_count = sum(1 for c in codes if c[:2] in etf_prefixes)
    if etf_count > 0:
        print(f"\n⚠ 警告: 发现 {etf_count} 只可能是场内基金的代码")
    else:
        print("\n✓ 未发现明显的场内基金代码")
    
    # 显示前20只基金
    print("\n前20只基金:")
    for i, (code, name) in enumerate(funds[:20], 1):
        print(f"  {i}. {code} - {name}")


def verify_fund_data(fund_code):
    """验证单只基金数据是否可以获取"""
    try:
        from data_retrieval.optimized_fund_data import OptimizedFundData
        
        fetcher = OptimizedFundData()
        df = fetcher.get_fund_nav_history(fund_code, use_batch=True)
        
        if not df.empty:
            return True, len(df)
        return False, 0
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description='验证基金列表获取')
    parser.add_argument('--limit', type=int, default=0, help='限制显示数量，0表示全部')
    parser.add_argument('--output', type=str, help='输出到文件')
    parser.add_argument('--verify', action='store_true', help='验证基金数据可获取性')
    parser.add_argument('--verify-count', type=int, default=10, help='验证的基金数量')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("基金列表验证工具")
    print("=" * 60)
    
    # 获取基金列表
    funds = get_fund_list_from_market()
    
    if not funds:
        logger.error("无法获取基金列表")
        return 1
    
    # 分析基金列表
    analyze_fund_list(funds[:args.limit] if args.limit > 0 else funds)
    
    # 验证数据可获取性
    if args.verify:
        print("\n" + "=" * 60)
        print(f"数据可获取性验证（随机{args.verify_count}只）")
        print("=" * 60)
        
        import random
        sample = random.sample(funds, min(args.verify_count, len(funds)))
        
        success_count = 0
        for code, name in sample:
            success, info = verify_fund_data(code)
            if success:
                print(f"  ✓ {code} ({name[:20]}...): {info} 条数据")
                success_count += 1
            else:
                print(f"  ✗ {code} ({name[:20]}...): {info}")
        
        print(f"\n验证结果: {success_count}/{len(sample)} 只基金数据可获取")
    
    # 保存到文件
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write("基金代码,基金名称\n")
            for code, name in funds:
                f.write(f"{code},{name}\n")
        print(f"\n✓ 基金列表已保存到: {args.output}")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
