# 基金类型分类标准说明

## 概述

本项目采用**中国证监会官方基金分类标准**对基金进行分类。分类逻辑完全由后端服务处理，前端仅负责展示。

## 证监会标准分类体系

根据《公开募集证券投资基金运作管理办法》及相关监管指引：

| 类型代码 | 中文名称 | 定义标准 | 颜色标识 |
|---------|---------|---------|---------|
| `stock` | 股票型 | 股票资产占基金资产比例不低于80% | 绿色(#28a745) |
| `bond` | 债券型 | 债券资产占基金资产比例不低于80% | 青色(#17a2b8) |
| `hybrid` | 混合型 | 投资于股票、债券和货币市场工具，但不符合股票型、债券型基金要求 | 黄色(#ffc107) |
| `money` | 货币型 | 仅投资于货币市场工具的基金 | 灰色(#6c757d) |
| `index` | 指数型 | 采用被动投资策略跟踪某一标的指数的基金 | 蓝色(#007bff) |
| `qdii` | QDII | 合格境内机构投资者基金，投资于境外证券市场 | 紫色(#9b59b6) |
| `etf` | ETF | 交易型开放式指数基金，可在交易所上市交易 | 红色(#e74c3c) |
| `fof` | FOF | 基金中基金，投资于其他基金份额不低于80% | 橙色(#fd7e14) |
| `unknown` | 未知 | 无法识别分类的基金 | 浅灰(#adb5bd) |

## 分类逻辑优先级

系统按以下优先级判断基金类型：

1. **官方类型**（最高优先级）
   - 从 `fund_basic_info` 表获取基金官方类型
   - 支持解析：股票型、债券型、混合型、货币型、指数型、QDII、ETF、FOF等

2. **基金名称关键词**（次优先级）
   - ETF: 包含"ETF"、"交易型开放式"
   - QDII: 包含"QDII"、"全球"、"海外"、"美国"、"香港"等
   - FOF: 包含"FOF"、"基金中基金"
   - 指数型: 包含"指数"、"INDEX"、"沪深300"、"联接"等
   - 货币型: 包含"货币"、"现金"、"余额宝"等
   - 债券型: 包含"债券"、"纯债"、"信用债"、"短债"等
   - 股票型: 包含"股票"、"EQUITY"、"GROWTH"等
   - 混合型: 包含"混合"、"MIX"、"灵活配置"等

3. **基金代码特征**（最低优先级）
   - ETF: 代码以51/56/15/16开头（6位数字）
   - LOF: 代码以16/50开头

## 技术实现

### 后端服务

**核心文件**: `pro2/fund_search/services/fund_type_service.py`

#### 主要类和方法

```python
from fund_search.services.fund_type_service import (
    FundType, FundTypeService, classify_fund,
    get_fund_type_display, get_fund_type_css_class
)

# 分类单个基金
fund_type = FundTypeService.classify_fund(
    fund_name="易方达沪深300ETF",
    fund_code="510300",
    official_type="ETF"
)
# 返回: FundType.ETF

# 便捷函数 - 返回类型代码
type_code = classify_fund("易方达沪深300ETF")
# 返回: "etf"

# 获取中文显示名称
display_name = get_fund_type_display("etf")
# 返回: "ETF"

# 获取CSS类名
css_class = get_fund_type_css_class("etf")
# 返回: "fund-type-etf"

# 批量分类
funds = [
    {'fund_code': '000001', 'fund_name': '华夏大盘精选混合'},
    {'fund_code': '510300', 'fund_name': '华泰柏瑞沪深300ETF'},
]
results = FundTypeService.batch_classify(funds)
# 返回包含 fund_type_code, fund_type_cn, fund_type_class 的基金列表
```

#### API响应格式

`/api/holdings` 返回的数据现在包含基金类型信息：

```json
{
  "success": true,
  "data": [
    {
      "fund_code": "510300",
      "fund_name": "华泰柏瑞沪深300ETF",
      "fund_type": "etf",           // 类型代码
      "fund_type_cn": "ETF",        // 中文名称
      "fund_type_class": "fund-type-etf",  // CSS类名
      // ... 其他字段
    }
  ]
}
```

### 前端展示

**相关文件**:
- `pro2/fund_search/web/static/js/my-holdings/table.js` - 表格展示
- `pro2/fund_search/web/static/js/my-holdings/detail.js` - 详情面板
- `pro2/fund_search/web/static/css/my-holdings-refactored.css` - 样式定义

#### 使用方式

前端不再进行基金类型判断，直接使用后端返回的数据：

```javascript
// 获取基金类型信息
getFundTypeInfo(fund) {
    return {
        code: fund.fund_type || 'unknown',
        label: fund.fund_type_cn || '其他',
        className: fund.fund_type_class || 'fund-type-unknown'
    };
}

// 渲染类型标签
const typeInfo = this.getFundTypeInfo(fund);
const html = `<span class="fund-type-tag ${typeInfo.className}">${typeInfo.label}</span>`;
```

## 样式类名

CSS类名与类型代码对应关系：

| 类型代码 | CSS类名 |
|---------|---------|
| stock | fund-type-stock |
| bond | fund-type-bond |
| hybrid | fund-type-hybrid |
| money | fund-type-money |
| index | fund-type-index |
| qdii | fund-type-qdii |
| etf | fund-type-etf |
| fof | fund-type-fof |
| unknown | fund-type-unknown |

## 资产配置功能

资产配置功能已同步更新使用新的基金类型分类：

- `/api/dashboard/allocation` - 获取资产配置分布
- `get_real_holding_distribution()` - 获取持仓分布数据

返回数据中的 `type_code` 字段使用新的类型代码（stock, bond, hybrid等）。

## 向后兼容

为了向后兼容，保留了以下旧函数但不再主动使用：
- `infer_fund_type_from_name()` - 旧的前端分类函数
- `normalize_fund_type()` - 旧的类型标准化函数

## 测试

运行测试脚本验证分类逻辑：

```bash
cd pro2
python tests/test_fund_type_service.py
```

## 更新日志

### 2026-02-09
- 初始实现证监会标准基金分类
- 创建基金类型服务模块
- 更新后端API返回基金类型信息
- 修改前端代码使用后端返回的类型数据
- 添加新基金类型样式（债券型、货币型、ETF、FOF）
