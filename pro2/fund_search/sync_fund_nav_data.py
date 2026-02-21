#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金历史净值数据同步脚本
从akshare获取基金历史数据并存入数据库

功能：
1. 批量获取多只基金的历史净值数据
2. 将数据存入 fund_analysis_results 表
3. 支持增量更新（只获取最新数据）
4. 支持全量更新（重新获取所有数据）

使用方法：
    # 同步指定基金的数据
    python sync_fund_nav_data.py --codes 006614,017962,006718
    
    # 同步用户持仓的所有基金
    python sync_fund_nav_data.py --sync-holdings
    
    # 全量更新（重新获取所有历史数据）
    python sync_fund_nav_data.py --sync-holdings --full
    
    # 设置定时任务（每日更新）
    python sync_fund_nav_data.py --sync-holdings --schedule
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import time
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import pandas as pd
import akshare as ak
from sqlalchemy import text

from data_retrieval.enhanced_database import EnhancedDatabaseManager
from shared.enhanced_config import DATABASE_CONFIG

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('sync_fund_nav.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class FundNavDataSync:
    """基金净值数据同步器"""
    
    def __init__(self):
        self.db = EnhancedDatabaseManager(DATABASE_CONFIG)
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'inserted': 0,
            'updated': 0
        }
    
    def get_fund_codes_from_holdings(self) -> List[str]:
        """从用户持仓表中获取基金代码列表"""
        try:
            sql = "SELECT DISTINCT fund_code FROM user_holdings"
            with self.db.engine.connect() as conn:
                result = conn.execute(text(sql))
                codes = [row[0] for row in result.fetchall()]
            logger.info(f"从持仓表获取到 {len(codes)} 只基金: {codes}")
            return codes
        except Exception as e:
            logger.error(f"获取持仓基金失败: {e}")
            return []
    
    def get_fund_name(self, fund_code: str) -> str:
        """获取基金名称"""
        try:
            # 先尝试从fund_basic_info获取
            sql = "SELECT fund_name FROM fund_basic_info WHERE fund_code = %s"
            with self.db.engine.connect() as conn:
                result = conn.execute(text(sql), (fund_code,))
                row = result.fetchone()
                if row and row[0]:
                    return row[0]
            
            # 再尝试从fund_analysis_results获取
            sql = """
            SELECT fund_name FROM fund_analysis_results 
            WHERE fund_code = %s AND fund_name IS NOT NULL 
            ORDER BY analysis_date DESC LIMIT 1
            """
            with self.db.engine.connect() as conn:
                result = conn.execute(text(sql), (fund_code,))
                row = result.fetchone()
                if row and row[0]:
                    return row[0]
            
            # 最后使用akshare获取（仅在数据库中没有时才尝试）
            try:
                # 首先尝试从数据库获取基金名称
                sql = """
                SELECT fund_name FROM fund_basic_info 
                WHERE fund_code = :fund_code AND fund_name IS NOT NULL
                UNION
                SELECT fund_name FROM fund_analysis_results 
                WHERE fund_code = :fund_code AND fund_name IS NOT NULL
                ORDER BY LENGTH(fund_name) DESC 
                LIMIT 1
                """
                with self.db.engine.connect() as conn:
                    result = conn.execute(text(sql), {'fund_code': fund_code})
                    row = result.fetchone()
                    if row and row[0]:
                        return row[0]
                
                # 如果数据库中也没有，暂时返回基金代码（避免akshare错误）
                logger.debug(f"数据库中未找到基金 {fund_code} 的名称，使用代码作为名称")
                return fund_code
                
                # 注释掉有问题的akshare调用
                # fund_list = ak.fund_name_em()
                # if not fund_list.empty and '基金代码' in fund_list.columns and '基金简称' in fund_list.columns:
                #     # 查找对应基金代码的名称
                #     fund_row = fund_list[fund_list['基金代码'] == fund_code]
                #     if not fund_row.empty:
                #         fund_name = fund_row.iloc[0]['基金简称']
                #         if fund_name and fund_name != fund_code:
                #             # 缓存到数据库
                #             try:
                #                 cache_sql = """
                #                 INSERT INTO fund_basic_info (fund_code, fund_name) 
                #                 VALUES (:fund_code, :fund_name)
                #                 ON DUPLICATE KEY UPDATE fund_name = VALUES(fund_name)
                #                 """
                #                 with self.db.engine.connect() as conn:
                #                     conn.execute(text(cache_sql), {
                #                         'fund_code': fund_code,
                #                         'fund_name': fund_name
                #                     })
                #                     conn.commit()
                #             except Exception as cache_e:
                #                 logger.debug(f"缓存基金名称失败: {cache_e}")
                #             return fund_name
            except Exception as e:
                logger.debug(f"获取基金名称失败: {e}")
                return fund_code
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 名称失败: {e}")
            return fund_code
    
    def get_existing_data_range(self, fund_code: str) -> Optional[tuple]:
        """获取数据库中已有的数据日期范围"""
        try:
            sql = """
            SELECT MIN(analysis_date) as min_date, MAX(analysis_date) as max_date, COUNT(*) as count
            FROM fund_analysis_results 
            WHERE fund_code = :fund_code AND current_estimate IS NOT NULL
            """
            with self.db.engine.connect() as conn:
                result = conn.execute(text(sql), {'fund_code': fund_code})
                row = result.fetchone()
                if row and row[0]:
                    return (row[0], row[1], row[2])
            return None
        except Exception as e:
            logger.error(f"获取现有数据范围失败 {fund_code}: {e}")
            return None
    
    def fetch_fund_nav_from_akshare(self, fund_code: str) -> Optional[pd.DataFrame]:
        """从akshare获取基金历史净值数据"""
        try:
            logger.info(f"从akshare获取基金 {fund_code} 数据...")
            start_time = time.time()
            
            # 使用akshare获取基金净值
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            
            elapsed = time.time() - start_time
            
            if df is None or df.empty:
                logger.warning(f"基金 {fund_code} 无历史数据")
                return None
            
            # 重命名列
            df = df.rename(columns={
                '净值日期': 'date',
                '单位净值': 'nav',
                '日增长率': 'daily_return'
            })
            
            # 转换日期
            df['date'] = pd.to_datetime(df['date'])
            
            # 转换数值
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            if 'daily_return' in df.columns:
                df['daily_return'] = pd.to_numeric(df['daily_return'], errors='coerce')
            
            # 计算日收益率（如果没有）
            if 'daily_return' not in df.columns or df['daily_return'].isna().all():
                df['daily_return'] = df['nav'].pct_change() * 100
            
            # 移除NaN
            df = df.dropna(subset=['date', 'nav'])
            
            logger.info(f"基金 {fund_code} 获取成功: {len(df)} 条记录, 耗时: {elapsed:.2f}s")
            return df
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 数据失败: {e}")
            return None
    
    def sync_fund_data(self, fund_code: str, fund_name: Optional[str] = None, 
                       full_update: bool = False) -> bool:
        """同步单只基金的数据"""
        self.stats['total'] += 1
        
        try:
            # 获取基金名称
            if not fund_name:
                fund_name = self.get_fund_name(fund_code)
            
            # 获取现有数据范围
            existing_range = None if full_update else self.get_existing_data_range(fund_code)
            
            if existing_range:
                logger.info(f"基金 {fund_code} 数据库已有数据: {existing_range[0]} 至 {existing_range[1]}, "
                          f"共 {existing_range[2]} 条，将增量更新")
            
            # 从akshare获取数据
            df = self.fetch_fund_nav_from_akshare(fund_code)
            if df is None or df.empty:
                self.stats['failed'] += 1
                return False
            
            # 过滤已存在的数据（增量更新）
            if existing_range and not full_update:
                last_date = pd.Timestamp(existing_range[1])
                new_data = df[df['date'] > last_date]
                if len(new_data) == 0:
                    logger.info(f"基金 {fund_code} 无新数据，跳过")
                    self.stats['skipped'] += 1
                    return True
                logger.info(f"基金 {fund_code} 新数据: {len(new_data)} 条")
                df = new_data
            
            # 准备插入数据
            records = []
            for _, row in df.iterrows():
                records.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'analysis_date': row['date'].date() if hasattr(row['date'], 'date') else row['date'],
                    'current_estimate': float(row['nav']),
                    'today_return': float(row['daily_return']) if pd.notna(row.get('daily_return')) else 0.0
                })
            
            if not records:
                self.stats['skipped'] += 1
                return True
            
            # 批量插入/更新数据
            inserted, updated = self._bulk_upsert_records(records)
            self.stats['inserted'] += inserted
            self.stats['updated'] += updated
            
            logger.info(f"基金 {fund_code} 同步完成: 插入 {inserted} 条, 更新 {updated} 条")
            self.stats['success'] += 1
            return True
            
        except Exception as e:
            logger.error(f"同步基金 {fund_code} 失败: {e}")
            import traceback
            traceback.print_exc()
            self.stats['failed'] += 1
            return False
    
    def _bulk_upsert_records(self, records: List[Dict]) -> tuple:
        """批量插入或更新记录"""
        inserted = 0
        updated = 0
        
        try:
            # 使用INSERT ... ON DUPLICATE KEY UPDATE
            sql = """
            INSERT INTO fund_analysis_results 
            (fund_code, fund_name, analysis_date, current_estimate, today_return)
            VALUES (:fund_code, :fund_name, :analysis_date, :current_estimate, :today_return)
            ON DUPLICATE KEY UPDATE
            fund_name = VALUES(fund_name),
            current_estimate = VALUES(current_estimate),
            today_return = VALUES(today_return)
            """
            
            with self.db.engine.connect() as conn:
                for record in records:
                    try:
                        result = conn.execute(text(sql), record)
                        if result.rowcount == 1:
                            inserted += 1
                        elif result.rowcount == 2:
                            updated += 1
                    except Exception as e:
                        logger.warning(f"插入记录失败: {e}")
                conn.commit()
                
        except Exception as e:
            logger.error(f"批量插入失败: {e}")
        
        return inserted, updated
    
    def sync_multiple_funds(self, fund_codes: List[str], full_update: bool = False):
        """同步多只基金的数据"""
        logger.info(f"=" * 70)
        logger.info(f"开始同步 {len(fund_codes)} 只基金的历史数据")
        logger.info(f"模式: {'全量更新' if full_update else '增量更新'}")
        logger.info(f"=" * 70)
        
        start_time = time.time()
        
        for i, code in enumerate(fund_codes, 1):
            logger.info(f"\n[{i}/{len(fund_codes)}] 正在处理基金 {code}...")
            self.sync_fund_data(code, full_update=full_update)
            
            # 添加小延迟避免请求过快
            if i < len(fund_codes):
                time.sleep(0.5)
        
        elapsed = time.time() - start_time
        
        # 输出统计
        logger.info(f"\n" + "=" * 70)
        logger.info(f"同步完成！总耗时: {elapsed:.2f} 秒")
        logger.info(f"统计:")
        logger.info(f"  - 总基金数: {self.stats['total']}")
        logger.info(f"  - 成功: {self.stats['success']}")
        logger.info(f"  - 失败: {self.stats['failed']}")
        logger.info(f"  - 跳过: {self.stats['skipped']}")
        logger.info(f"  - 插入记录: {self.stats['inserted']}")
        logger.info(f"  - 更新记录: {self.stats['updated']}")
        logger.info(f"=" * 70)


def setup_scheduler():
    """设置定时任务"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        # 每日16:30执行（收盘后）
        scheduler.add_job(
            lambda: main(['--sync-holdings']),
            CronTrigger(hour=16, minute=30),
            id='fund_nav_sync',
            name='基金净值数据同步'
        )
        
        scheduler.start()
        logger.info("定时任务已设置: 每日 16:30 自动同步基金净值数据")
        return scheduler
        
    except ImportError:
        logger.warning("未安装 apscheduler，无法设置定时任务")
        logger.info("请使用系统定时任务（crontab/Task Scheduler）执行: python sync_fund_nav_data.py --sync-holdings")
        return None


def main(args=None):
    """主函数"""
    parser = argparse.ArgumentParser(description='基金历史净值数据同步工具')
    parser.add_argument('--codes', type=str, help='指定基金代码，逗号分隔，如: 006614,017962')
    parser.add_argument('--sync-holdings', action='store_true', help='同步用户持仓的所有基金')
    parser.add_argument('--full', action='store_true', help='全量更新（重新获取所有历史数据）')
    parser.add_argument('--schedule', action='store_true', help='启动定时任务模式')
    
    if args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args)
    
    # 设置定时任务模式
    if args.schedule:
        scheduler = setup_scheduler()
        if scheduler:
            logger.info("定时任务运行中，按 Ctrl+C 停止...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                scheduler.shutdown()
                logger.info("定时任务已停止")
        return
    
    # 获取基金代码列表
    fund_codes = []
    
    if args.codes:
        fund_codes = [code.strip() for code in args.codes.split(',')]
    elif args.sync_holdings:
        syncer = FundNavDataSync()
        fund_codes = syncer.get_fund_codes_from_holdings()
        if not fund_codes:
            logger.error("持仓表中没有基金数据")
            return 1
    else:
        parser.print_help()
        return 1
    
    # 执行同步
    syncer = FundNavDataSync()
    syncer.sync_multiple_funds(fund_codes, full_update=args.full)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
