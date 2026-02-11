# 数据源优先级配置说明

## 实时数据计算优先级

**RealtimeDataFetcher 获取日涨跌幅等实时数据时的优先级：**

1. **天天基金**（第一优先级）
   - 最实时，提供估算涨跌幅
   - 估值接口：`http://fundgz.1234567.com.cn/js/{code}.js`

2. **新浪**（第二优先级）
   - 实时性好
   - 接口：`https://hq.sinajs.cn/list=f_{code}`

3. **东方财富**（第三优先级）
   - AKShare 的 fund_em_valuation 接口
   - 备用数据源

4. **Tushare**（第四优先级）
   - 稳定性高
   - 需要 `.OF` 后缀格式
   - 用于实时数据计算的备选

5. **AKShare**（降级）
   - 数据全面
   - 作为最后备选

## 历史数据获取优先级

**MultiSourceFundData 获取历史净值数据时的优先级：**

1. **Tushare**（PRIMARY - 主要数据源）
   - 稳定性高
   - 成功率监控，失败率过高时自动降级

2. **AKShare**（BACKUP_1 - 第一备用）
   - 数据全面
   - 格式兼容性好

## 昨日盈亏率获取优先级

**HoldingRealtimeService 获取昨日盈亏率时的优先级：**

1. **内存缓存**（15分钟有效）

2. **数据库缓存**（fund_nav_cache 表）
   - 昨日的净值和涨跌幅

3. **数据库缓存**（fund_analysis_results 表）
   - prev_day_return 字段

4. **MultiSourceDataAdapter**
   - 使用历史数据计算昨日收益率
   - QDII基金会进行前向追溯

## 关键区别

| 数据类型 | 第一优先级 | 说明 |
|---------|-----------|------|
| 实时日涨跌幅 | 天天基金 | 需要最实时的估算数据 |
| 历史净值数据 | Tushare | 需要稳定的历史数据 |
| 昨日盈亏率 | 数据库缓存 | 优先使用已缓存的计算结果 |
| 绩效指标计算 | Tushare | 使用历史数据计算夏普比率等 |

## 配置文件

### Tushare Token 配置（shared/enhanced_config.py）

```python
DATA_SOURCE_CONFIG = {
    'tushare': {
        'token': 'your_token_here',
        'timeout': 30,
        'max_retries': 3
    }
}
```

## 验证数据源

查看日志确认数据源：
```
# 实时数据
DEBUG - 天天基金获取成功 {code}
DEBUG - 新浪获取成功 {code}
...

# 历史数据
INFO - 使用 PRIMARY 数据源 Tushare 获取 {code}
INFO - 使用 BACKUP_1 数据源 Akshare 获取 {code}
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `services/holding_realtime_service.py` | RealtimeDataFetcher 类，实时数据计算优先级 |
| `data_retrieval/multi_source_fund_data.py` | MultiSourceFundData 类，历史数据获取优先级 |
| `data_retrieval/multi_source_adapter.py` | 昨日收益率计算 |
| `shared/enhanced_config.py` | 数据源配置 |
