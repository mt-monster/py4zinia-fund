# 基金列表夏普比率计算逻辑说明文档

## 一、概述

本文档详细说明基金列表中夏普比率（Sharpe Ratio）的计算逻辑、参数配置和实现细节。

## 二、夏普比率计算公式

### 2.1 标准公式

```
夏普比率 = (年化收益率 - 无风险利率) / 年化波动率

Sharpe Ratio = (Annualized Return - Risk Free Rate) / Annualized Volatility
```

### 2.2 日收益率计算

```
日收益率 = (当日净值 - 前一日净值) / 前一日净值

Daily Return = (Nav_t - Nav_{t-1}) / Nav_{t-1}
```

### 2.3 年化处理

```
年化收益率 = (1 + 总收益率)^(交易天数/持有天数) - 1

年化波动率 = 日收益率标准差 × √交易天数
```

## 三、系统配置参数

### 3.1 配置文件位置

文件：`pro2/fund_search/shared/enhanced_config.py`

### 3.2 关键参数

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `risk_free_rate` | 0.03 (3%) | 年化无风险利率 |
| `trading_days_per_year` | 252 | 每年交易日数 |
| `historical_days` | 365 | 默认历史数据天数 |

### 3.3 代码中的配置引用

```python
from shared.enhanced_config import PERFORMANCE_CONFIG, INVESTMENT_STRATEGY_CONFIG

risk_free_rate = INVESTMENT_STRATEGY_CONFIG['risk_free_rate']  # 0.03
trading_days = PERFORMANCE_CONFIG['trading_days_per_year']    # 252
```

## 四、多期夏普比率计算

系统计算三个时间维度的夏普比率：

### 4.1 夏普比率（成立以来）- sharpe_ratio_all

- **数据范围**：基金成立至今的所有历史数据
- **用途**：评估基金长期风险调整收益
- **计算逻辑**：使用全部日收益率数据

### 4.2 夏普比率（近一年）- sharpe_ratio_1y

- **数据范围**：最近252个交易日（约1年）
- **用途**：评估基金近期表现
- **最小数据要求**：至少30个交易日

### 4.3 夏普比率（今年以来）- sharpe_ratio_ytd

- **数据范围**：当年1月1日至今
- **用途**：评估基金当年表现
- **最小数据要求**：至少10个交易日

### 4.4 默认夏普比率 - sharpe_ratio

- **取值**：默认使用 `sharpe_ratio_all`（成立以来）
- **用途**：基金列表默认展示的夏普比率

## 五、计算流程详解

### 5.1 主计算函数

位置：`pro2/fund_search/data_retrieval/multi_source_adapter.py`

```python
def get_performance_metrics(self, fund_code: str, days: int = 3650) -> Dict:
    """
    获取基金绩效指标
    
    步骤：
    1. 获取历史净值数据
    2. 提取日收益率序列
    3. 计算各期夏普比率
    4. 返回指标字典
    """
```

### 5.2 详细计算步骤

#### 步骤1：获取历史数据

```python
hist_data = self.get_historical_data(fund_code, days)
# 返回字段：date, nav, daily_return
```

#### 步骤2：处理日收益率

```python
daily_growth_col = '日增长率' if '日增长率' in hist_data.columns else 'daily_return'
daily_returns = hist_data[daily_growth_col].dropna()

# 数据格式转换
if abs(daily_returns).mean() < 1:
    daily_returns = daily_returns * 100  # 转换为百分比
```

#### 步骤3：计算年化波动率

```python
volatility = daily_returns.std() * np.sqrt(trading_days)
```

#### 步骤4：计算年化收益率

```python
# 成立以来
start_nav = hist_data['nav'].iloc[0]
end_nav = hist_data['nav'].iloc[-1]
total_return = (end_nav - start_nav) / start_nav
annualized_return = (1 + total_return) ** (trading_days / days) - 1
```

#### 步骤5：计算夏普比率

```python
sharpe_ratio = (annualized_return - risk_free_rate) / volatility
if volatility == 0:
    sharpe_ratio = 0.0
```

## 六、PerformanceCalculator 类实现

位置：`pro2/fund_search/backtesting/performance_metrics.py`

### 6.1 类初始化参数

```python
PerformanceCalculator(
    risk_free_rate: float = 0.02,  # 年化无风险利率
    trading_days: int = 252         # 每年交易日数
)
```

### 6.2 日无风险利率计算

```python
self.daily_risk_free = (1 + risk_free_rate) ** (1 / trading_days) - 1
```

### 6.3 夏普比率计算方法

```python
def calculate_sharpe_ratio(self, daily_returns: np.ndarray) -> float:
    """
    计算夏普比率
    
    公式：
    Sharpe = (mean(excess_returns) / std(excess_returns)) * sqrt(trading_days)
    
    其中：
    excess_returns = daily_returns - daily_risk_free
    """
    if len(daily_returns) < 2:
        return 0.0
    
    excess_returns = daily_returns - self.daily_risk_free
    std = np.std(excess_returns)
    
    if std == 0:
        return 0.0
    
    return float(np.mean(excess_returns) / std * np.sqrt(self.trading_days))
```

## 七、回测模块中的夏普比率

位置：`pro2/fund_search/backtesting/performance_metrics.py`

### 7.1 MetricEngine 类

```python
class MetricEngine:
    """可扩展指标引擎"""
    
    def _compute_sharpe_ratio(self, ...):
        return calculator.calculate_sharpe_ratio(context['daily_returns'])
```

### 7.2 指标定义

```python
MetricDefinition(
    metric_id='sharpe_ratio',
    name='夏普比率',
    category='风险调整',
    unit='ratio',
    description='单位风险超额收益'
)
```

## 八、综合评分中的夏普比率权重

位置：`pro2/fund_search/shared/enhanced_config.py`

```python
PERFORMANCE_CONFIG = {
    'weights': {
        'annualized_return': 0.3,   # 年化收益权重 30%
        'sharpe_ratio': 0.25,        # 夏普比率权重 25%
        'max_drawdown': 0.2,         # 最大回撤权重 20%
        'volatility': 0.15,          # 波动率权重 15%
        'win_rate': 0.1              # 胜率权重 10%
    }
}
```

## 九、数据库字段映射

### 9.1 fund_analysis_results 表

| 字段名 | 说明 | 数据类型 |
|--------|------|----------|
| `sharpe_ratio` | 夏普比率（成立以来） | FLOAT |
| `sharpe_ratio_1y` | 夏普比率（近一年） | FLOAT |
| `sharpe_ratio_ytd` | 夏普比率（今年以来） | FLOAT |
| `sharpe_ratio_all` | 夏普比率（成立以来） | FLOAT |

### 9.2 前端展示字段

位置：`pro2/fund_search/web/static/js/my-holdings/config.js`

```javascript
{ key: 'sharpe_ratio', label: '夏普比率', visible: true, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_1y', label: '夏普(近一年)', visible: false, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_ytd', label: '夏普(今年以来)', visible: false, sortable: true, type: 'number' },
{ key: 'sharpe_ratio_all', label: '夏普(成立以来)', visible: false, sortable: true, type: 'number' }
```

## 十、特殊情况处理

### 10.1 数据不足

```python
if len(daily_returns) < 2:
    return 0.0  # 数据不足返回0
```

### 10.2 波动率为0

```python
if volatility == 0:
    return 0.0  # 避免除以0
```

### 10.3 空数据返回默认值

```python
def _get_default_metrics(self) -> Dict:
    return {
        'sharpe_ratio': 0.0,
        'sharpe_ratio_ytd': 0.0,
        'sharpe_ratio_1y': 0.0,
        'sharpe_ratio_all': 0.0,
        # ... 其他指标
    }
```

## 十一、与其他风险指标的关系

### 11.1 索提诺比率 (Sortino Ratio)

```python
# 只考虑下行风险
sortino_ratio = (annual_return - risk_free_rate) / downside_volatility
```

### 11.2 卡玛比率 (Calmar Ratio)

```python
# 收益与最大回撤之比
calmar_ratio = annual_return / max_drawdown
```

### 11.3 信息比率 (Information Ratio)

```python
# 超额收益与跟踪误差
information_ratio = annual_excess / tracking_error
```

## 十二、常见问题排查

### 12.1 夏普比率为0

可能原因：
1. 历史数据不足（< 2天）
2. 日收益率波动为0（基金净值无变化）
3. 数据库中无该基金的绩效数据

### 12.2 夏普比率异常高/低

可能原因：
1. 新成立基金数据样本少
2. 基金净值长期横盘后突然大幅波动
3. 数据源问题导致净值异常

### 12.3 不同时期夏普比率差异大

可能原因：
1. 基金投资策略变化
2. 市场环境变化（牛市/熊市）
3. 基金经理变更

## 十三、调试与验证

### 13.1 手动计算验证

```python
from data_retrieval.multi_source_adapter import MultiSourceDataAdapter

adapter = MultiSourceDataAdapter()
metrics = adapter.get_performance_metrics('016667')

print(f"夏普比率: {metrics['sharpe_ratio']}")
print(f"夏普(近一年): {metrics['sharpe_ratio_1y']}")
print(f"夏普(今年以来): {metrics['sharpe_ratio_ytd']}")
```

### 13.2 日志输出

启用DEBUG级别日志可查看详细计算过程：

```python
logging.basicConfig(level=logging.DEBUG)
```

## 十四、参考资料

1. [Sharpe Ratio - Investopedia](https://www.investopedia.com/terms/s/sharperatio.asp)
2. [Sortino Ratio - Investopedia](https://www.investopedia.com/terms/s/sortinoratio.asp)
3. [Calmar Ratio - Investopedia](https://www.investopedia.com/terms/c/calmarratio.asp)

---

**文档版本**: 1.0  
**最后更新**: 2026-02-11  
**作者**: Kimi Code CLI
