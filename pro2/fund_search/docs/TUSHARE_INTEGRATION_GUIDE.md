# Tushare Token 集成使用说明

## 📋 概述

本文档介绍如何在基金分析系统中正确配置和使用 Tushare Token。

## 🔧 配置方式

### 1. 环境变量配置（推荐）

创建 `.env` 文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的 Tushare Token：
```env
TUSHARE_TOKEN=5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b
```

### 2. 配置文件方式

Token 已经集成到 `shared/enhanced_config.py` 中：
```python
DATA_SOURCE_CONFIG = {
    'tushare': {
        'token': os.environ.get('TUSHARE_TOKEN', '5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b'),
        # ... 其他配置
    }
}
```

### 3. 代码中直接传入

```python
from fund_search.data_retrieval.multi_source_data_fetcher import MultiSourceFundDataFetcher

# 方式1: 使用环境变量中的token
fetcher = MultiSourceFundDataFetcher()

# 方式2: 直接传入token
fetcher = MultiSourceFundDataFetcher(tushare_token="your_token_here")
```

## 🚀 使用示例

### 基本使用
```python
from fund_search.data_retrieval.multi_source_data_fetcher import MultiSourceFundDataFetcher

# 初始化获取器
fetcher = MultiSourceFundDataFetcher()

# 获取基金基本信息
basic_info = fetcher.get_fund_basic_info("021539")
print(f"基金名称: {basic_info['fund_name']}")

# 获取历史净值数据
nav_history = fetcher.get_fund_nav_history("021539", days=30)
print(f"获取到 {len(nav_history)} 条历史数据")

# 获取实时估算数据
realtime_data = fetcher.get_fund_realtime_estimate("021539")
print(f"实时估算净值: {realtime_data['current_estimate']}")
```

### 高级配置
```python
# 自定义配置
fetcher = MultiSourceFundDataFetcher(
    tushare_token="your_custom_token"
)

# 使用配置文件中的参数
print(f"Tushare 超时时间: {fetcher.tushare_config['timeout']}秒")
print(f"Akshare 重试次数: {fetcher.akshare_config['max_retries']}次")
```

## 📊 数据源优先级

系统采用多数据源自动切换机制：

1. **主数据源**: Akshare (免费、QDII处理成熟)
2. **备用数据源**: Tushare (稳定性高、响应快)
3. **应急数据源**: 新浪财经、天天基金网

## 🔍 验证配置

运行测试脚本验证配置：
```bash
cd pro2
python tests/test_improved_data_sources.py
```

预期输出应该显示：
```
2026-02-09 11:24:07,737 - INFO - Tushare 初始化成功
```

## ⚠️ 注意事项

### 安全性
- ❌ 不要在代码中硬编码 Token
- ✅ 使用环境变量或配置文件
- ✅ 将 `.env` 文件加入 `.gitignore`

### 权限说明
当前 Token 的权限级别：
- ✅ 基本基金信息查询
- ✅ 历史净值数据获取
- ⚠️ 部分高级功能可能需要更高权限

### 性能优化
```python
# 配置合理的超时和重试参数
export TUSHARE_TIMEOUT=30
export TUSHARE_RETRIES=3
export AKSHARE_DELAY=1.0
```

## 🛠️ 故障排除

### 1. Tushare 初始化失败
```bash
# 检查 Token 是否正确
echo $TUSHARE_TOKEN

# 检查网络连接
ping api.tushare.pro
```

### 2. 权限不足
- 登录 Tushare 官网检查账户权限
- 考虑升级到更高权限套餐

### 3. 数据获取失败
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 监控和维护

### 健康检查
```python
# 检查各数据源状态
fetcher = MultiSourceFundDataFetcher()
# 实现健康检查方法...
```

### 日志监控
```python
# 配置日志记录
logger = logging.getLogger('data_fetcher')
logger.setLevel(logging.INFO)
```

## 🔄 更新 Token

当需要更新 Token 时：

1. 更新 `.env` 文件中的 `TUSHARE_TOKEN`
2. 重启应用服务
3. 验证新 Token 是否生效

```bash
# 重新加载环境变量
source .env
# 或者重启服务
```

## 💡 最佳实践

1. **安全性**: 始终使用环境变量存储敏感信息
2. **可靠性**: 配置多个备用数据源
3. **可维护性**: 使用配置文件管理参数
4. **监控性**: 启用详细的日志记录
5. **测试性**: 定期运行测试验证配置

---

**当前配置状态**: ✅ 已集成
**Token**: 5ff19facae0e5b26a407d491d33707a9884a39a714a0d76b6495725b
**最后更新**: 2026-02-09