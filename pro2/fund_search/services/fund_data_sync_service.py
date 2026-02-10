#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基金数据定时同步服务

同步策略：
1. 每日下午16:00：同步所有持仓基金的净值数据
2. 每日下午16:10：计算所有基金的绩效指标
3. 每日下午16:20：生成持仓快照
4. 每小时检查：处理失败的同步任务
"""

import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class FundDataSyncService:
    """
    基金数据定时同步服务
    
    负责：
    1. 日终净值数据同步
    2. 绩效指标计算
    3. 持仓快照生成
    """
    
    def __init__(self, cache_manager, db_manager):
        self.cache = cache_manager
        self.db = db_manager
        self.running = False
        self._thread = None
        self._lock = threading.Lock()
        
    def start(self):
        """启动定时任务"""
        if self.running:
            logger.warning("同步服务已在运行中")
            return
        
        self.running = True
        
        # 设置定时任务（下午4点左右错开执行）
        # 16:00 - 同步净值数据
        schedule.every().day.at("16:00").do(self._daily_nav_sync)
        
        # 16:10 - 计算绩效指标（错开10分钟）
        schedule.every().day.at("16:10").do(self._daily_performance_calc)
        
        # 16:20 - 生成持仓快照（再错开10分钟）
        schedule.every().day.at("16:20").do(self._generate_portfolio_snapshots)
        
        # 每小时检查失败的同步
        schedule.every().hour.do(self._retry_failed_syncs)
        
        # 启动后台线程
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()
        
        logger.info("基金数据同步服务已启动")
        logger.info("定时任务：16:00净值同步 | 16:10绩效计算 | 16:20快照生成")
    
    def stop(self):
        """停止定时任务"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("基金数据同步服务已停止")
    
    def _run_scheduler(self):
        """运行调度器"""
        while self.running:
            try:
                schedule.run_pending()
            except Exception as e:
                logger.error(f"调度器执行错误: {e}")
            time.sleep(60)  # 每分钟检查一次
    
    def _daily_nav_sync(self):
        """每日净值数据同步"""
        job_id = self._log_job_start('daily_nav_sync', 'daily')
        
        try:
            # 获取所有需要同步的基金
            fund_codes = self._get_sync_fund_codes()
            total = len(fund_codes)
            success = 0
            failed = 0
            
            logger.info(f"开始每日净值同步，共{total}只基金")
            
            for i, fund_code in enumerate(fund_codes, 1):
                try:
                    # 获取最近30天数据（增量）
                    df = self.cache.fetch_fund_nav_from_source(fund_code, days=30)
                    
                    if not df.empty:
                        self.cache.save_fund_nav_to_db(fund_code, df, 'akshare')
                        success += 1
                        logger.debug(f"[{i}/{total}] 同步成功: {fund_code}")
                    else:
                        failed += 1
                        self._record_sync_failure(fund_code, 'empty_data')
                        logger.warning(f"[{i}/{total}] 同步失败(无数据): {fund_code}")
                    
                    # 每10只基金暂停一下，避免请求过快
                    if i % 10 == 0:
                        time.sleep(2)
                        
                except Exception as e:
                    failed += 1
                    self._record_sync_failure(fund_code, str(e))
                    logger.error(f"[{i}/{total}] 同步异常: {fund_code}, {e}")
            
            self._log_job_end(job_id, 'success', total, success, failed)
            logger.info(f"每日净值同步完成: 成功{success}/{total}, 失败{failed}")
            
        except Exception as e:
            self._log_job_end(job_id, 'failed', 0, 0, 0, str(e))
            logger.error(f"每日净值同步任务失败: {e}")
    
    def _daily_performance_calc(self):
        """每日绩效指标计算"""
        job_id = self._log_job_start('daily_performance_calc', 'daily')
        
        try:
            # 获取所有有净值数据的基金
            fund_codes = self._get_perf_calc_fund_codes()
            total = len(fund_codes)
            success = 0
            failed = 0
            
            logger.info(f"开始每日绩效计算，共{total}只基金")
            
            for i, fund_code in enumerate(fund_codes, 1):
                try:
                    # 检查今天是否已计算
                    if self._is_performance_calculated_today(fund_code):
                        logger.debug(f"[{i}/{total}] 跳过(今日已计算): {fund_code}")
                        continue
                    
                    # 计算绩效
                    metrics = self.cache._calculate_performance_metrics(fund_code, days=365)
                    
                    if metrics:
                        self.cache.save_performance_to_db(fund_code, metrics)
                        success += 1
                        logger.debug(f"[{i}/{total}] 绩效计算成功: {fund_code}")
                    else:
                        failed += 1
                        logger.warning(f"[{i}/{total}] 绩效计算失败: {fund_code}")
                    
                    # 每5只基金暂停一下
                    if i % 5 == 0:
                        time.sleep(1)
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"[{i}/{total}] 绩效计算异常: {fund_code}, {e}")
            
            self._log_job_end(job_id, 'success', total, success, failed)
            logger.info(f"每日绩效计算完成: 成功{success}/{total}, 失败{failed}")
            
        except Exception as e:
            self._log_job_end(job_id, 'failed', 0, 0, 0, str(e))
            logger.error(f"每日绩效计算任务失败: {e}")
    
    def _generate_portfolio_snapshots(self):
        """生成用户持仓快照"""
        job_id = self._log_job_start('portfolio_snapshot', 'daily')
        
        try:
            # 获取所有用户的持仓
            sql = """
                SELECT DISTINCT user_id, fund_code, holding_shares, holding_amount
                FROM user_holdings
                WHERE holding_shares > 0
            """
            df = self.db.execute_query(sql)
            
            if df.empty:
                self._log_job_end(job_id, 'success', 0, 0, 0)
                return
            
            today = datetime.now().strftime('%Y-%m-%d')
            total = len(df)
            success = 0
            
            logger.info(f"开始生成持仓快照，共{total}条记录")
            
            for _, row in df.iterrows():
                try:
                    user_id = row['user_id']
                    fund_code = row['fund_code']
                    shares = row['holding_shares']
                    
                    # 获取今日净值
                    nav_sql = """
                        SELECT nav_value, daily_return
                        FROM fund_nav_cache
                        WHERE fund_code = %(fund_code)s
                          AND nav_date = %(today)s
                        LIMIT 1
                    """
                    nav_df = self.db.execute_query(nav_sql, {
                        'fund_code': fund_code,
                        'today': today
                    })
                    
                    if nav_df.empty:
                        # 如果今天的数据还没有，使用最新数据
                        nav_sql = """
                            SELECT nav_value, daily_return
                            FROM fund_nav_cache
                            WHERE fund_code = %(fund_code)s
                            ORDER BY nav_date DESC
                            LIMIT 1
                        """
                        nav_df = self.db.execute_query(nav_sql, {'fund_code': fund_code})
                    
                    if not nav_df.empty:
                        nav_value = float(nav_df.iloc[0]['nav_value'])
                        daily_return = float(nav_df.iloc[0]['daily_return']) if nav_df.iloc[0]['daily_return'] else 0
                        market_value = shares * nav_value
                        holding_profit = market_value - row['holding_amount']
                        
                        # 保存快照
                        insert_sql = """
                            INSERT INTO user_portfolio_snapshot
                            (user_id, snapshot_date, fund_code, holding_shares, nav_value,
                             market_value, daily_return, holding_profit)
                            VALUES (%(user_id)s, %(date)s, %(fund_code)s, %(shares)s,
                                    %(nav)s, %(market_value)s, %(return)s, %(profit)s)
                            ON DUPLICATE KEY UPDATE
                            holding_shares = %(shares)s,
                            nav_value = %(nav)s,
                            market_value = %(market_value)s,
                            daily_return = %(return)s,
                            holding_profit = %(profit)s,
                            updated_at = NOW()
                        """
                        
                        self.db.execute_sql(insert_sql, {
                            'user_id': user_id,
                            'date': today,
                            'fund_code': fund_code,
                            'shares': shares,
                            'nav': nav_value,
                            'market_value': market_value,
                            'return': daily_return,
                            'profit': holding_profit
                        })
                        
                        success += 1
                        
                except Exception as e:
                    logger.error(f"生成快照失败 {row.get('fund_code')}: {e}")
            
            self._log_job_end(job_id, 'success', total, success, total - success)
            logger.info(f"持仓快照生成完成: 成功{success}/{total}")
            
        except Exception as e:
            self._log_job_end(job_id, 'failed', 0, 0, 0, str(e))
            logger.error(f"生成持仓快照失败: {e}")
    
    def _retry_failed_syncs(self):
        """重试失败的同步任务"""
        try:
            # 获取最近失败且失败次数<3的基金
            sql = """
                SELECT fund_code, sync_fail_count
                FROM fund_cache_metadata
                WHERE sync_status = 'failed'
                  AND sync_fail_count < 3
                  AND last_sync_at < DATE_SUB(NOW(), INTERVAL 1 HOUR)
                LIMIT 10
            """
            df = self.db.execute_query(sql)
            
            if df.empty:
                return
            
            logger.info(f"重试{len(df)}只失败基金的同步")
            
            for _, row in df.iterrows():
                fund_code = row['fund_code']
                try:
                    df_nav = self.cache.fetch_fund_nav_from_source(fund_code, days=30)
                    if not df_nav.empty:
                        self.cache.save_fund_nav_to_db(fund_code, df_nav, 'akshare')
                        logger.info(f"重试同步成功: {fund_code}")
                except Exception as e:
                    logger.warning(f"重试同步失败: {fund_code}, {e}")
                    
        except Exception as e:
            logger.error(f"重试失败同步任务出错: {e}")
    
    def _get_sync_fund_codes(self) -> List[str]:
        """获取需要同步的基金代码列表"""
        try:
            # 1. 获取用户持仓的所有基金
            sql = """
                SELECT DISTINCT fund_code FROM user_holdings WHERE holding_shares > 0
                UNION
                SELECT DISTINCT fund_code FROM fund_cache_metadata 
                WHERE next_sync_at <= NOW() OR sync_status = 'pending'
            """
            df = self.db.execute_query(sql)
            
            if not df.empty:
                return df['fund_code'].tolist()
            
            return []
        except Exception as e:
            logger.error(f"获取同步基金列表失败: {e}")
            return []
    
    def _get_perf_calc_fund_codes(self) -> List[str]:
        """获取需要计算绩效的基金代码"""
        try:
            sql = """
                SELECT DISTINCT fund_code 
                FROM fund_nav_cache
                WHERE nav_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """
            df = self.db.execute_query(sql)
            
            if not df.empty:
                return df['fund_code'].tolist()
            
            return []
        except Exception as e:
            logger.error(f"获取绩效计算基金列表失败: {e}")
            return []
    
    def _is_performance_calculated_today(self, fund_code: str) -> bool:
        """检查今日是否已计算绩效 - 使用 fund_analysis_results"""
        try:
            sql = """
                SELECT 1 FROM fund_analysis_results
                WHERE fund_code = :fund_code
                  AND analysis_date = CURDATE()
                LIMIT 1
            """
            df = self.db.execute_query(sql, {'fund_code': fund_code})
            return not df.empty
        except Exception:
            return False
    
    def _record_sync_failure(self, fund_code: str, error_msg: str):
        """记录同步失败"""
        try:
            sql = """
                INSERT INTO fund_cache_metadata 
                (fund_code, sync_status, sync_fail_count, last_sync_at)
                VALUES (:fund_code, 'failed', 1, NOW())
                ON DUPLICATE KEY UPDATE
                sync_status = 'failed',
                sync_fail_count = sync_fail_count + 1,
                last_sync_at = NOW()
            """
            self.db.execute_sql(sql, {'fund_code': fund_code})
        except Exception as e:
            logger.error(f"记录同步失败失败: {e}")
    
    def _log_job_start(self, job_name: str, job_type: str) -> int:
        """记录任务开始"""
        try:
            sql = """
                INSERT INTO fund_sync_job_log (job_name, job_type, start_time, status)
                VALUES (%(name)s, %(type)s, NOW(), 'running')
            """
            self.db.execute_sql(sql, {'name': job_name, 'type': job_type})
            
            # 获取刚插入的ID
            result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
            return int(result.iloc[0]['id']) if not result.empty else 0
        except Exception as e:
            logger.error(f"记录任务开始失败: {e}")
            return 0
    
    def _log_job_end(self, job_id: int, status: str, total: int, 
                     success: int, failed: int, error_msg: str = None):
        """记录任务结束"""
        try:
            sql = """
                UPDATE fund_sync_job_log
                SET end_time = NOW(),
                    status = %(status)s,
                    total_count = %(total)s,
                    success_count = %(success)s,
                    fail_count = %(failed)s,
                    error_message = %(error)s
                WHERE id = %(id)s
            """
            self.db.execute_sql(sql, {
                'id': job_id,
                'status': status,
                'total': total,
                'success': success,
                'failed': failed,
                'error': error_msg
            })
        except Exception as e:
            logger.error(f"记录任务结束失败: {e}")
    
    def manual_sync_fund(self, fund_code: str) -> bool:
        """手动同步单只基金数据"""
        try:
            df = self.cache.fetch_fund_nav_from_source(fund_code, days=365)
            if not df.empty:
                self.cache.save_fund_nav_to_db(fund_code, df, 'akshare')
                
                # 计算并保存绩效
                metrics = self.cache._calculate_performance_metrics(fund_code, 365)
                if metrics:
                    self.cache.save_performance_to_db(fund_code, metrics)
                
                return True
            return False
        except Exception as e:
            logger.error(f"手动同步失败 {fund_code}: {e}")
            return False
