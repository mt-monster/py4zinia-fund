#!/usr/bin/env python
# coding: utf-8

"""
Pydantic models for backtest service request/response schemas
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class BacktestStatus(str, Enum):
    """回测状态枚举"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class BacktestType(str, Enum):
    """回测类型枚举"""
    SINGLE_FUND = 'single_fund'
    PORTFOLIO = 'portfolio'
    STRATEGY = 'strategy'


class FilterCondition(BaseModel):
    """筛选条件模型"""
    field: str = Field(..., description="筛选字段名")
    operator: str = Field(..., description="操作符 (>, <, >=, <=, ==, !=)")
    value: Union[float, str, bool] = Field(..., description="比较值")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "list_days",
                "operator": ">",
                "value": 365
            }
        }


class StrategyConfig(BaseModel):
    """策略配置模型"""
    name: Optional[str] = Field(default="", description="策略名称")
    description: Optional[str] = Field(default="", description="策略描述")
    strategy_type: str = Field(default="momentum", description="策略类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    filter_conditions: List[FilterCondition] = Field(default_factory=list, description="筛选条件")
    filter_logic: str = Field(default="AND", description="筛选逻辑 (AND/OR)")
    sort_field: str = Field(default="composite_score", description="排序字段")
    sort_order: str = Field(default="DESC", description="排序方向 (ASC/DESC)")
    select_count: int = Field(default=10, ge=1, le=100, description="选股数量")
    weight_mode: str = Field(default="equal", description="权重模式 (equal/custom)")
    custom_weights: List[float] = Field(default_factory=list, description="自定义权重")
    max_positions: int = Field(default=10, ge=1, le=100, description="最大持仓数")
    daily_stop_loss: float = Field(default=-0.05, description="每日止损阈值")
    daily_take_profit: float = Field(default=0.10, description="每日止盈阈值")
    total_stop_loss: float = Field(default=-0.15, description="累计止损阈值")


class RunBacktestRequest(BaseModel):
    """执行回测请求模型"""
    backtest_type: BacktestType = Field(default=BacktestType.SINGLE_FUND, description="回测类型")
    
    # 单基金回测参数
    fund_code: Optional[str] = Field(default=None, description="基金代码（单基金回测）")
    
    # 组合回测参数
    fund_codes: Optional[List[str]] = Field(default=None, description="基金代码列表（组合回测）")
    weights: Optional[List[float]] = Field(default=None, description="基金权重列表")
    
    # 策略回测参数
    strategy_id: Optional[int] = Field(default=None, description="策略ID")
    strategy_config: Optional[StrategyConfig] = Field(default=None, description="策略配置")
    
    # 通用参数
    start_date: Optional[str] = Field(default=None, description="回测开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="回测结束日期 (YYYY-MM-DD)")
    base_amount: float = Field(default=100.0, gt=0, description="基准定投金额")
    initial_cash: Optional[float] = Field(default=None, description="初始现金")
    initial_capital: float = Field(default=100000.0, gt=0, description="初始资金")
    rebalance_freq: str = Field(default="monthly", description="调仓频率")
    use_unified_strategy: bool = Field(default=True, description="是否使用统一策略引擎")
    
    # 用户标识
    user_id: str = Field(default="default_user", description="用户ID")
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and values.get('start_date') and v < values['start_date']:
            raise ValueError('结束日期不能早于开始日期')
        return v


class BacktestMetrics(BaseModel):
    """回测绩效指标模型"""
    total_return_strategy: float = Field(..., description="策略总收益率")
    total_return_benchmark: float = Field(..., description="基准总收益率")
    annual_return_strategy: float = Field(..., description="策略年化收益率")
    annual_return_benchmark: float = Field(..., description="基准年化收益率")
    max_drawdown_strategy: float = Field(..., description="策略最大回撤")
    max_drawdown_benchmark: float = Field(..., description="基准最大回撤")
    sharpe_ratio_strategy: float = Field(..., description="策略夏普比率")
    sharpe_ratio_benchmark: float = Field(..., description="基准夏普比率")
    win_rate_strategy: float = Field(..., description="策略胜率")
    win_rate_benchmark: float = Field(..., description="基准胜率")
    annual_volatility_strategy: float = Field(..., description="策略年化波动率")
    annual_volatility_benchmark: float = Field(..., description="基准年化波动率")
    alpha_strategy: float = Field(..., description="策略Alpha")
    beta_strategy: float = Field(..., description="策略Beta")
    sortino_ratio_strategy: float = Field(..., description="策略索提诺比率")
    sortino_ratio_benchmark: float = Field(..., description="基准索提诺比率")
    calmar_ratio_strategy: float = Field(..., description="策略卡玛比率")
    calmar_ratio_benchmark: float = Field(..., description="基准卡玛比率")


class TradeRecord(BaseModel):
    """交易记录模型"""
    date: str = Field(..., description="交易日期")
    fund_code: str = Field(..., description="基金代码")
    fund_name: Optional[str] = Field(default=None, description="基金名称")
    action: str = Field(..., description="交易方向")
    amount: float = Field(..., description="交易金额")
    price: float = Field(..., description="成交价格")
    shares: float = Field(..., description="交易份额")
    balance: float = Field(..., description="账户余额")
    holdings_value: float = Field(..., description="持仓价值")
    reason: Optional[str] = Field(default=None, description="交易原因")


class BacktestResultData(BaseModel):
    """回测结果数据模型"""
    task_id: str = Field(..., description="任务ID")
    strategy_name: Optional[str] = Field(default=None, description="策略名称")
    start_date: str = Field(..., description="回测开始日期")
    end_date: str = Field(..., description="回测结束日期")
    total_return: float = Field(..., description="总收益率")
    annualized_return: float = Field(..., description="年化收益率")
    max_drawdown: float = Field(..., description="最大回撤")
    sharpe_ratio: float = Field(..., description="夏普比率")
    metrics: BacktestMetrics = Field(..., description="完整绩效指标")
    trades: List[TradeRecord] = Field(default_factory=list, description="交易记录")
    daily_values: List[Dict[str, Any]] = Field(default_factory=list, description="每日资产价值")


class RunBacktestResponse(BaseModel):
    """执行回测响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(default="", description="状态消息")
    result: Optional[BacktestResultData] = Field(default=None, description="回测结果（如已完成）")


class BacktestStatusResponse(BaseModel):
    """获取回测状态响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    status: BacktestStatus = Field(..., description="任务状态")
    progress: float = Field(..., ge=0, le=100, description="进度百分比")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: str = Field(..., description="创建时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")


class BacktestResultResponse(BaseModel):
    """获取回测结果响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    status: BacktestStatus = Field(..., description="任务状态")
    result: Optional[BacktestResultData] = Field(default=None, description="回测结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class CancelBacktestResponse(BaseModel):
    """取消回测响应模型"""
    success: bool = Field(..., description="是否成功")
    task_id: str = Field(..., description="任务ID")
    message: str = Field(..., description="状态消息")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    timestamp: str = Field(..., description="当前时间戳")
    active_tasks: int = Field(..., description="活跃任务数")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = Field(default=False, description="是否成功")
    error: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(default=None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细错误信息")
