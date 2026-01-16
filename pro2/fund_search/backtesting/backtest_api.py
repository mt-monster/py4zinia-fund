#!/usr/bin/env python
# coding: utf-8

"""
回测API模块
Backtest API Module

提供策略回测的API接口实现：
- 执行回测
- 获取回测状态
- 获取回测结果
- 交易记录筛选
- CSV导出
"""

import logging
import uuid
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import pandas as pd

from .strategy_models import StrategyConfig, FilterCondition
from .custom_strategy_backtest import (
    CustomStrategyBacktest, BacktestResult, TradeRecord,
    run_custom_backtest
)
from .performance_metrics import PerformanceCalculator, PerformanceMetrics

logger = logging.getLogger(__name__)


class BacktestStatus(str, Enum):
    """回测状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class BacktestTask:
    """回测任务"""
    task_id: str
    strategy_id: int
    status: BacktestStatus = BacktestStatus.PENDING
    progress: float = 0.0
    result: Optional[BacktestResult] = None
    error_message: str = ''
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'strategy_id': self.strategy_id,
            'status': self.status.value,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class BacktestTaskManager:
    """
    回测任务管理器
    
    管理回测任务的创建、执行和状态查询
    """
    
    def __init__(self):
        """初始化任务管理器"""
        self._tasks: Dict[str, BacktestTask] = {}
        self._lock = threading.Lock()
    
    def create_task(self, strategy_id: int) -> str:
        """
        创建回测任务
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())[:8]
        task = BacktestTask(
            task_id=task_id,
            strategy_id=strategy_id
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[BacktestTask]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象或None
        """
        with self._lock:
            return self._tasks.get(task_id)
    
    def update_task_status(
        self, 
        task_id: str, 
        status: BacktestStatus,
        progress: float = 0.0,
        error_message: str = ''
    ):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 进度
            error_message: 错误信息
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                task.progress = progress
                task.error_message = error_message
                if status in [BacktestStatus.COMPLETED, BacktestStatus.FAILED]:
                    task.completed_at = datetime.now()
    
    def set_task_result(self, task_id: str, result: BacktestResult):
        """
        设置任务结果
        
        Args:
            task_id: 任务ID
            result: 回测结果
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.result = result
                task.status = BacktestStatus.COMPLETED
                task.progress = 100.0
                task.completed_at = datetime.now()
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        清理过期任务
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        now = datetime.now()
        with self._lock:
            expired_tasks = [
                task_id for task_id, task in self._tasks.items()
                if (now - task.created_at).total_seconds() > max_age_hours * 3600
            ]
            for task_id in expired_tasks:
                del self._tasks[task_id]


# 全局任务管理器实例
_task_manager = BacktestTaskManager()


def get_task_manager() -> BacktestTaskManager:
    """获取全局任务管理器"""
    return _task_manager


class TradeRecordFilter:
    """
    交易记录筛选器
    
    支持按日期范围、基金代码、交易方向筛选交易记录
    """
    
    @staticmethod
    def filter_trades(
        trades: List[Dict[str, Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fund_code: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        筛选交易记录
        
        Args:
            trades: 交易记录列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            fund_code: 基金代码
            action: 交易方向 ('buy', 'sell', 'stop_loss', 'take_profit')
            
        Returns:
            筛选后的交易记录列表
        """
        if not trades:
            return []
        
        filtered = trades.copy()
        
        # 按日期范围筛选
        if start_date:
            filtered = [
                t for t in filtered 
                if t.get('date', '') >= start_date
            ]
        
        if end_date:
            filtered = [
                t for t in filtered 
                if t.get('date', '') <= end_date
            ]
        
        # 按基金代码筛选
        if fund_code:
            fund_code_lower = fund_code.lower()
            filtered = [
                t for t in filtered 
                if fund_code_lower in t.get('fund_code', '').lower()
            ]
        
        # 按交易方向筛选
        if action:
            action_lower = action.lower()
            filtered = [
                t for t in filtered 
                if t.get('action', '').lower() == action_lower
            ]
        
        return filtered


class CSVExporter:
    """
    CSV导出器
    
    将交易记录导出为CSV格式
    """
    
    # CSV列定义
    COLUMNS = [
        ('date', '交易日期'),
        ('fund_code', '基金代码'),
        ('fund_name', '基金名称'),
        ('action', '交易方向'),
        ('amount', '交易金额'),
        ('price', '成交价格'),
        ('shares', '交易份额'),
        ('balance', '账户余额'),
        ('holdings_value', '持仓价值'),
        ('reason', '交易原因')
    ]
    
    # 交易方向映射
    ACTION_MAP = {
        'buy': '买入',
        'sell': '卖出',
        'stop_loss': '止损',
        'take_profit': '止盈',
        'daily_stop_loss': '每日止损',
        'daily_take_profit': '每日止盈',
        'total_stop_loss': '累计止损',
        'trailing_stop': '追踪止损'
    }
    
    @classmethod
    def export_to_csv(
        cls,
        trades: List[Dict[str, Any]],
        include_header: bool = True,
        encoding: str = 'utf-8-sig'
    ) -> str:
        """
        导出交易记录为CSV字符串
        
        Args:
            trades: 交易记录列表
            include_header: 是否包含表头
            encoding: 编码格式
            
        Returns:
            CSV格式字符串
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        if include_header:
            headers = [col[1] for col in cls.COLUMNS]
            writer.writerow(headers)
        
        # 写入数据行
        for trade in trades:
            row = []
            for col_key, _ in cls.COLUMNS:
                value = trade.get(col_key, '')
                
                # 特殊处理交易方向
                if col_key == 'action':
                    value = cls.ACTION_MAP.get(value, value)
                
                # 格式化数值
                if isinstance(value, float):
                    value = round(value, 4)
                
                row.append(value)
            
            writer.writerow(row)
        
        return output.getvalue()
    
    @classmethod
    def parse_csv(
        cls,
        csv_content: str,
        has_header: bool = True
    ) -> List[Dict[str, Any]]:
        """
        解析CSV内容为交易记录列表
        
        Args:
            csv_content: CSV内容字符串
            has_header: 是否包含表头
            
        Returns:
            交易记录列表
        """
        # 反向映射
        reverse_action_map = {v: k for k, v in cls.ACTION_MAP.items()}
        
        trades = []
        reader = csv.reader(io.StringIO(csv_content))
        
        # 跳过表头
        if has_header:
            next(reader, None)
        
        for row in reader:
            if len(row) < len(cls.COLUMNS):
                continue
            
            trade = {}
            for i, (col_key, _) in enumerate(cls.COLUMNS):
                value = row[i] if i < len(row) else ''
                
                # 特殊处理交易方向
                if col_key == 'action':
                    value = reverse_action_map.get(value, value)
                
                # 尝试转换数值
                if col_key in ['amount', 'price', 'shares', 'balance', 'holdings_value']:
                    try:
                        value = float(value) if value else 0.0
                    except ValueError:
                        value = 0.0
                
                trade[col_key] = value
            
            trades.append(trade)
        
        return trades


class BacktestAPIHandler:
    """
    回测API处理器
    
    处理回测相关的API请求
    """
    
    def __init__(self, db_manager=None, fund_data_manager=None):
        """
        初始化处理器
        
        Args:
            db_manager: 数据库管理器
            fund_data_manager: 基金数据管理器
        """
        self.db_manager = db_manager
        self.fund_data_manager = fund_data_manager
        self.task_manager = get_task_manager()
    
    def run_backtest(
        self,
        strategy_id: int,
        user_id: str = 'default_user',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital: float = 100000.0,
        rebalance_freq: str = 'monthly'
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        执行回测
        
        Args:
            strategy_id: 策略ID
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            rebalance_freq: 调仓频率
            
        Returns:
            (成功标志, 结果字典)
        """
        try:
            # 获取策略配置
            strategy_data = self._get_strategy(strategy_id, user_id)
            if not strategy_data:
                return False, {'error': '策略不存在'}
            
            config_dict = strategy_data.get('config', {})
            if isinstance(config_dict, str):
                config_dict = json.loads(config_dict)
            
            strategy_config = StrategyConfig.from_dict(config_dict)
            
            # 创建任务
            task_id = self.task_manager.create_task(strategy_id)
            self.task_manager.update_task_status(
                task_id, BacktestStatus.RUNNING, progress=10.0
            )
            
            # 设置默认日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                # 默认回测1年
                start_dt = datetime.now() - pd.Timedelta(days=365)
                start_date = start_dt.strftime('%Y-%m-%d')
            
            # 获取基金数据
            self.task_manager.update_task_status(
                task_id, BacktestStatus.RUNNING, progress=30.0
            )
            
            funds_data = self._get_funds_data(start_date, end_date)
            if funds_data.empty:
                self.task_manager.update_task_status(
                    task_id, BacktestStatus.FAILED,
                    error_message='没有找到基金数据'
                )
                return False, {'error': '没有找到基金数据', 'task_id': task_id}
            
            # 执行回测
            self.task_manager.update_task_status(
                task_id, BacktestStatus.RUNNING, progress=50.0
            )
            
            result = run_custom_backtest(
                strategy_config=strategy_config,
                funds_data=funds_data,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                rebalance_freq=rebalance_freq
            )
            
            # 保存结果
            self.task_manager.set_task_result(task_id, result)
            
            # 保存到数据库
            self._save_backtest_result(strategy_id, task_id, result)
            
            return True, {
                'task_id': task_id,
                'status': 'completed',
                'result': result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"回测执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if 'task_id' in locals():
                self.task_manager.update_task_status(
                    task_id, BacktestStatus.FAILED,
                    error_message=str(e)
                )
                return False, {'error': str(e), 'task_id': task_id}
            
            return False, {'error': str(e)}
    
    def get_backtest_status(self, task_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取回测状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            (成功标志, 状态字典)
        """
        task = self.task_manager.get_task(task_id)
        
        if not task:
            return False, {'error': '任务不存在'}
        
        return True, task.to_dict()
    
    def get_backtest_result(
        self, 
        task_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fund_code: Optional[str] = None,
        action: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        获取回测结果
        
        Args:
            task_id: 任务ID
            start_date: 交易记录筛选开始日期
            end_date: 交易记录筛选结束日期
            fund_code: 交易记录筛选基金代码
            action: 交易记录筛选交易方向
            
        Returns:
            (成功标志, 结果字典)
        """
        task = self.task_manager.get_task(task_id)
        
        if not task:
            # 尝试从数据库获取
            result_data = self._get_backtest_result_from_db(task_id)
            if result_data:
                # 应用交易记录筛选
                if any([start_date, end_date, fund_code, action]):
                    trades = result_data.get('trades', [])
                    filtered_trades = TradeRecordFilter.filter_trades(
                        trades, start_date, end_date, fund_code, action
                    )
                    result_data['trades'] = filtered_trades
                    result_data['filtered_trades_count'] = len(filtered_trades)
                
                return True, result_data
            
            return False, {'error': '任务不存在'}
        
        if task.status != BacktestStatus.COMPLETED:
            return False, {
                'error': '回测尚未完成',
                'status': task.status.value,
                'progress': task.progress
            }
        
        if not task.result:
            return False, {'error': '回测结果为空'}
        
        result_dict = task.result.to_dict()
        
        # 应用交易记录筛选
        if any([start_date, end_date, fund_code, action]):
            trades = result_dict.get('trades', [])
            filtered_trades = TradeRecordFilter.filter_trades(
                trades, start_date, end_date, fund_code, action
            )
            result_dict['trades'] = filtered_trades
            result_dict['filtered_trades_count'] = len(filtered_trades)
        
        return True, result_dict
    
    def export_trades_csv(
        self,
        task_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fund_code: Optional[str] = None,
        action: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        导出交易记录为CSV
        
        Args:
            task_id: 任务ID
            start_date: 筛选开始日期
            end_date: 筛选结束日期
            fund_code: 筛选基金代码
            action: 筛选交易方向
            
        Returns:
            (成功标志, CSV内容或错误信息)
        """
        success, result = self.get_backtest_result(
            task_id, start_date, end_date, fund_code, action
        )
        
        if not success:
            return False, result.get('error', '获取结果失败')
        
        trades = result.get('trades', [])
        csv_content = CSVExporter.export_to_csv(trades)
        
        return True, csv_content
    
    def _get_strategy(self, strategy_id: int, user_id: str) -> Optional[Dict]:
        """从数据库获取策略"""
        if not self.db_manager:
            return None
        
        sql = """
        SELECT id, user_id, name, description, config
        FROM user_strategies
        WHERE id = :strategy_id AND user_id = :user_id
        """
        
        df = self.db_manager.execute_query(sql, {
            'strategy_id': strategy_id,
            'user_id': user_id
        })
        
        if df.empty:
            return None
        
        row = df.iloc[0]
        return {
            'id': int(row['id']),
            'name': row['name'],
            'description': row['description'],
            'config': row['config']
        }
    
    def _get_funds_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取基金数据"""
        if not self.db_manager:
            return pd.DataFrame()
        
        sql = """
        SELECT fund_code, fund_name, analysis_date as date,
               current_estimate as nav, today_return, yesterday_return,
               annualized_return, sharpe_ratio, max_drawdown, volatility,
               composite_score, status_label
        FROM fund_analysis_results
        WHERE analysis_date BETWEEN :start_date AND :end_date
        ORDER BY analysis_date, fund_code
        """
        
        return self.db_manager.execute_query(sql, {
            'start_date': start_date,
            'end_date': end_date
        })
    
    def _save_backtest_result(
        self, 
        strategy_id: int, 
        task_id: str, 
        result: BacktestResult
    ):
        """保存回测结果到数据库"""
        if not self.db_manager:
            return
        
        try:
            result_json = json.dumps(result.to_dict(), ensure_ascii=False)
            
            sql = """
            INSERT INTO strategy_backtest_results 
            (strategy_id, task_id, status, result, completed_at)
            VALUES (:strategy_id, :task_id, 'completed', :result, CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
            status = 'completed', result = :result, completed_at = CURRENT_TIMESTAMP
            """
            
            self.db_manager.execute_sql(sql, {
                'strategy_id': strategy_id,
                'task_id': task_id,
                'result': result_json
            })
        except Exception as e:
            logger.error(f"保存回测结果失败: {str(e)}")
    
    def _get_backtest_result_from_db(self, task_id: str) -> Optional[Dict]:
        """从数据库获取回测结果"""
        if not self.db_manager:
            return None
        
        sql = """
        SELECT result FROM strategy_backtest_results
        WHERE task_id = :task_id AND status = 'completed'
        """
        
        df = self.db_manager.execute_query(sql, {'task_id': task_id})
        
        if df.empty:
            return None
        
        result_str = df.iloc[0]['result']
        if isinstance(result_str, str):
            return json.loads(result_str)
        return result_str
