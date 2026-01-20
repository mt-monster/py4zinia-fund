# QDII基金特殊处理说明

## 修改时间
2026-01-19

## 背景

QDII基金由于投资海外市场，其净值更新受海外市场交易时间和时差影响，通常比国内基金晚1-2天更新。新浪财经的实时估算接口主要针对国内基金，对QDII基金的支持不完善。因此，QDII基金需要使用不同的数据获取策略。

## QDII基金列表

从京东金融表格中识别出的QDII基金（共14只）：

| 基金代码 | 基金名称 |
|---------|---------|
| 096001 | 大成标普500等权重指数(QDII)A人民币 |
| 100055 | 富国全球科技互联网股票(QDII)A |
| 012061 | 富国全球消费精选混合(QDII)美元现汇 |
| 006680 | 广发道琼斯石油指数(QDII-LOF)C美元现汇 |
| 006373 | 国富全球科技互联混合(QDII)人民币A |
| 006105 | 宏利印度股票(QDII)A |
| 021540 | 华安法国CAC40ETF发起式联接(QDII)C |
| 015016 | 华安国际龙头(DAX)ETF联接C |
| 040047 | 华安纳斯达克100ETF联接(QDII)A(美元现钞) |
| 007844 | 华宝油气C |
| 008708 | 建信富时100指数(QDII)C美元现汇 |
| 501225 | 景顺长城全球半导体芯片股票A(QDII-LOF)(人民币) |
| 162415 | 美国消费 |
| 007721 | 天弘标普500发起(QDII-FOF)A |

## 数据获取策略差异

### 普通基金
- **数据源**: 新浪财经实时估算接口
- **更新频率**: 分钟级实时更新
- **数据字段**: 
  - 当日盈亏：基于实时估算值计算
  - 昨日盈亏：从AKShare历史净值获取

### QDII基金
- **数据源**: 仅使用AKShare历史净值接口
- **更新频率**: T+1日更新（可能延迟）
- **数据字段**:
  - 当日盈亏：从最新一条数据的日增长率获取
  - 昨日盈亏：从前一条数据的日增长率获取
  - 如果当日数据没有，顺推使用前一天的数据

## 实现细节

### 1. QDII基金识别

在 `EnhancedFundData` 类中添加了QDII基金代码集合：

```python
class EnhancedFundData:
    # QDII基金代码列表
    QDII_FUND_CODES = {
        '096001', '100055', '012061', '006680', '006373',
        '006105', '021540', '015016', '040047', '007844',
        '008708', '501225', '162415', '007721',
    }
    
    @staticmethod
    def is_qdii_fund(fund_code: str) -> bool:
        """判断是否为QDII基金"""
        return fund_code in EnhancedFundData.QDII_FUND_CODES
```

### 2. 数据获取逻辑分离

`get_realtime_data()` 方法根据基金类型调用不同的处理函数：

```python
@staticmethod
def get_realtime_data(fund_code: str) -> Dict:
    # 判断是否为QDII基金
    is_qdii = EnhancedFundData.is_qdii_fund(fund_code)
    
    if is_qdii:
        # QDII基金：仅使用AKShare接口
        return EnhancedFundData._get_qdii_realtime_data(fund_code)
    else:
        # 普通基金：使用新浪接口
        return EnhancedFundData._get_normal_fund_realtime_data(fund_code)
```

### 3. QDII基金数据获取

`_get_qdii_realtime_data()` 方法实现QDII基金的特殊逻辑：

```python
@staticmethod
def _get_qdii_realtime_data(fund_code: str) -> Dict:
    # 从AKShare获取历史净值数据
    fund_nav = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
    fund_nav = fund_nav.sort_values('净值日期', ascending=True)
    
    # 获取最新数据（当日或最近一日）
    latest_data = fund_nav.iloc[-1]
    current_nav = float(latest_data.get('单位净值', 0))
    
    # 获取昨日净值
    if len(fund_nav) > 1:
        previous_data = fund_nav.iloc[-2]
        previous_nav = float(previous_data.get('单位净值', current_nav))
    
    # 获取当日盈亏率（从最新一条数据）
    daily_return = latest_data.get('日增长率', 0)
    
    # 获取昨日盈亏率（从前一条数据）
    if len(fund_nav) > 1:
        yesterday_return = previous_data.get('日增长率', 0)
    
    return {
        'fund_code': fund_code,
        'current_nav': current_nav,
        'previous_nav': previous_nav,
        'daily_return': daily_return,
        'yesterday_return': yesterday_return,
        'data_source': 'akshare_qdii',  # 标识数据来源
        ...
    }
```

## 数据顺推逻辑

QDII基金的数据获取遵循"顺推一天"的原则：

```
假设今天是 2026-01-19（周日，无数据）

历史净值数据：
  2026-01-14: 净值=1.4261, 日增长率=0.04%
  2026-01-15: 净值=1.4261, 日增长率=0.00%  ← 最新数据

数据映射：
  当日净值 = 2026-01-15的净值 = 1.4261
  昨日净值 = 2026-01-14的净值 = 1.4261
  当日盈亏 = 2026-01-15的日增长率 = 0.00%
  昨日盈亏 = 2026-01-14的日增长率 = 0.04%
```

这样确保即使在周末或节假日，系统也能获取到最新可用的数据。

## 测试验证

### 测试用例

1. **test_qdii_fund_006105.py**: 完整的QDII基金测试套件
2. **quick_test_qdii_006105.py**: 快速测试脚本
3. **test_qdii_integration.py**: 系统集成测试

### 测试结果

```bash
$ python pro2/fund_search/tests/test_qdii_integration.py

测试基金: 宏利印度股票(QDII)A (006105)
  ✅ QDII识别: 是QDII基金
  ✅ 数据来源: akshare_qdii
  ✅ 正确使用AKShare接口（不使用新浪接口）

测试基金: 国富全球科技互联混合(QDII)人民币A (006373)
  ✅ QDII识别: 是QDII基金
  ✅ 数据来源: akshare_qdii
  ✅ 正确使用AKShare接口（不使用新浪接口）

对比测试：普通基金 (001270 - 英大灵活配置A)
  ✅ QDII识别: 不是QDII基金（正确）
  ✅ 数据来源: sina_realtime
  ✅ 正确使用新浪实时接口
```

## 优势

### 1. 数据准确性
- QDII基金使用官方历史净值，避免实时估算的不准确性
- 数据来源可靠，符合基金公司公布的净值

### 2. 系统稳定性
- 不依赖新浪接口对QDII基金的支持
- 减少接口调用失败的风险

### 3. 逻辑清晰
- 明确区分QDII基金和普通基金的处理逻辑
- 代码结构清晰，易于维护

### 4. 自动识别
- 系统自动识别QDII基金
- 无需手动配置，自动应用正确的数据获取策略

## 注意事项

### 1. 数据延迟
- QDII基金净值更新通常比国内基金晚1-2天
- 这是QDII基金的固有特性，不是系统问题

### 2. 周末和节假日
- 周末和节假日无新数据时，系统会使用最近一个交易日的数据
- 这是正常现象，符合QDII基金的更新规律

### 3. 新增QDII基金
- 如果持仓中新增QDII基金，需要将基金代码添加到 `QDII_FUND_CODES` 集合中
- 位置：`pro2/fund_search/data_retrieval/enhanced_fund_data.py`

### 4. 数据来源标识
- 普通基金：`data_source = 'sina_realtime'`
- QDII基金：`data_source = 'akshare_qdii'`
- 可通过此字段区分数据来源

## 相关文档

- [QDII基金数据获取说明](./QDII基金数据获取说明.md)
- [字段计算逻辑说明](./字段计算逻辑说明.md)
- [昨日盈亏率计算逻辑修正说明](./昨日盈亏率计算逻辑修正说明.md)

## 修改文件

- ✅ `pro2/fund_search/data_retrieval/enhanced_fund_data.py`
  - 添加QDII基金代码列表
  - 添加 `is_qdii_fund()` 方法
  - 修改 `get_realtime_data()` 方法，根据基金类型分流
  - 新增 `_get_qdii_realtime_data()` 方法
  - 重构 `_get_normal_fund_realtime_data()` 方法

- ✅ `pro2/fund_search/tests/test_qdii_integration.py`
  - 新增系统集成测试用例

## 总结

通过为QDII基金实现特殊的数据获取逻辑，系统现在能够：
1. ✅ 自动识别QDII基金
2. ✅ 使用正确的数据源（AKShare而非新浪）
3. ✅ 正确处理数据延迟和顺推逻辑
4. ✅ 保持与普通基金相同的接口
5. ✅ 提供准确可靠的QDII基金数据

所有测试通过，系统运行正常！
