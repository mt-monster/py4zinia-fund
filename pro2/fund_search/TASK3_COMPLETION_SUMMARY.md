# Task 3: 添加两列到基金分析报告HTML - 完成总结

## 任务描述
在基金分析报告HTML表格中添加两个新列：
1. **持有金额** (holding_amount) - 用户持有该基金的成本金额
2. **累计盈亏** (cumulative_profit_loss) - 当前市值与持有金额的差额

## 实现方案

### 1. 数据源
- **持有金额**: 来自 `user_holdings` 表的 `holding_amount` 字段
- **累计盈亏**: 通过计算得出 = `current_estimate` (当前净值) - `holding_amount` (持有金额)

### 2. 修改的文件

#### 文件1: `pro2/fund_search/data_retrieval/enhanced_notification.py`

**修改1**: 更新 `_format_fund_data_to_table` 方法的列定义
```python
# 原来的列定义
display_columns = [
    'fund_code', 'fund_name', 'today_return', 'yesterday_return', 
    'status_label', 'operation_suggestion', 'execution_amount'
]

# 新的列定义（添加了两列）
display_columns = [
    'fund_code', 'fund_name', 'today_return', 'yesterday_return', 
    'status_label', 'operation_suggestion', 'execution_amount',
    'holding_amount', 'cumulative_profit_loss'
]
```

**修改2**: 更新 `_get_column_display_name` 方法，添加新列的显示名称
```python
# 持仓相关字段
'holding_amount': '持有金额',
'cumulative_profit_loss': '累计盈亏'
```

**修改3**: 在表格数据行处理中添加新列的格式化逻辑
```python
elif col == 'holding_amount':
    # 格式化为货币形式，右对齐
    if pd.notna(value):
        try:
            holding_val = float(value)
            formatted_value = f"¥{holding_val:.2f}"
            html_table += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: right;'>{formatted_value}</td>"
        except (ValueError, TypeError):
            html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{value}</td>"
    else:
        html_table += "<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>"

elif col == 'cumulative_profit_loss':
    # 格式化为货币形式，根据正负值显示不同颜色
    if pd.notna(value):
        try:
            profit_val = float(value)
            formatted_value = f"¥{profit_val:.2f}"
            color = '#e74c3c' if profit_val > 0 else '#27ae60' if profit_val < 0 else 'black'
            html_table += f"<td style='padding: 8px; border: 1px solid #ddd; text-align: right; color: {color}; font-weight: 500;'>{formatted_value}</td>"
        except (ValueError, TypeError):
            html_table += f"<td style='padding: 8px; border: 1px solid #ddd;'>{value}</td>"
    else:
        html_table += "<td style='padding: 8px; border: 1px solid #ddd;'>N/A</td>"
```

**修改4**: 更新表头宽度设置
```python
elif col in ['holding_amount', 'cumulative_profit_loss']:
    width_style = "min-width: 100px;"
```

#### 文件2: `pro2/fund_search/enhanced_main.py`

**修改**: 更新 `send_notification_reports` 方法，在生成报告前从数据库获取持仓数据
```python
def send_notification_reports(self, results_df: pd.DataFrame, strategy_summary: Dict, report_files: Dict) -> bool:
    """
    发送通知报告
    """
    try:
        logger.info("开始生成和发送通知报告")
        
        analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        # 从数据库获取持仓数据并合并到results_df
        try:
            # 查询user_holdings表获取持仓金额
            holdings_sql = """
            SELECT fund_code, holding_amount 
            FROM user_holdings 
            WHERE user_id = 'default_user'
            """
            holdings_df = self.db_manager.execute_query(holdings_sql)
            
            if not holdings_df.empty:
                # 与results_df合并
                results_df = results_df.merge(holdings_df, on='fund_code', how='left')
                logger.info(f"成功合并持仓数据，共 {len(holdings_df)} 条记录")
            
            # 计算累计盈亏 = 当前市值 - 持仓金额
            if 'holding_amount' in results_df.columns and 'current_estimate' in results_df.columns:
                results_df['cumulative_profit_loss'] = results_df.apply(
                    lambda row: (row['current_estimate'] - row['holding_amount']) if pd.notna(row['holding_amount']) and pd.notna(row['current_estimate']) else None,
                    axis=1
                )
                logger.info("成功计算累计盈亏")
        
        except Exception as e:
            logger.warning(f"获取持仓数据失败: {str(e)}，将继续生成报告但不包含持仓信息")
        
        # 生成综合报告
        report_data = self.notification_manager.generate_comprehensive_report(
            results_df, strategy_summary, report_files, analysis_date
        )
        
        # 发送通知
        success = self.notification_manager.send_comprehensive_notification(report_data, report_files)
        
        if success:
            logger.info("通知报告发送成功")
        else:
            logger.error("通知报告发送失败")
        
        return success
        
    except Exception as e:
        logger.error(f"发送通知报告失败: {str(e)}")
        return False
```

## 功能特性

### 1. 持有金额列
- **显示格式**: `¥XXXX.XX` (货币格式，保留两位小数)
- **对齐方式**: 右对齐
- **数据来源**: `user_holdings` 表的 `holding_amount` 字段
- **缺失处理**: 如果没有持仓数据，显示 `N/A`

### 2. 累计盈亏列
- **显示格式**: `¥XXXX.XX` (货币格式，保留两位小数)
- **对齐方式**: 右对齐
- **颜色编码**:
  - 红色 (#e74c3c): 盈利 (正数)
  - 绿色 (#27ae60): 亏损 (负数)
  - 黑色: 无盈亏 (0)
- **计算公式**: `current_estimate - holding_amount`
- **缺失处理**: 如果缺少必要数据，显示 `N/A`

## 测试结果

已创建测试脚本 `test_new_columns.py` 验证功能：

✅ **测试通过**
- 新列成功添加到HTML表格
- 持有金额正确格式化为货币形式
- 累计盈亏正确计算并显示
- 颜色编码正确应用

### 测试数据示例
```
基金代码: 001614
持有金额: ¥1000.50
累计盈亏: ¥50.25 (红色，表示盈利)

基金代码: 006105
持有金额: ¥1500.75
累计盈亏: ¥-75.50 (绿色，表示亏损)
```

## 集成说明

### 工作流程
1. 用户运行基金分析系统
2. 系统分析所有基金并生成 `results_df`
3. 在发送通知前，从 `user_holdings` 表获取持仓数据
4. 将持仓数据与分析结果合并
5. 计算累计盈亏
6. 生成包含新列的HTML报告
7. 发送通知或保存本地HTML文件

### 错误处理
- 如果获取持仓数据失败，系统会记录警告但继续生成报告
- 如果某个基金没有持仓数据，该行的新列显示 `N/A`
- 如果数据格式不正确，系统会尝试转换或显示原始值

## 向后兼容性
- 修改完全向后兼容
- 如果 DataFrame 中不包含新列，表格仍能正常生成（只是不显示新列）
- 现有的报告生成逻辑不受影响

## 文件清单
- ✅ `pro2/fund_search/data_retrieval/enhanced_notification.py` - 已修改
- ✅ `pro2/fund_search/enhanced_main.py` - 已修改
- ✅ `pro2/fund_search/test_new_columns.py` - 新建测试文件
- ✅ `reports/test_new_columns.html` - 测试输出文件

## 下一步建议
1. 在实际系统中运行完整的基金分析流程进行集成测试
2. 验证与微信/邮件通知的兼容性
3. 检查在大量基金数据下的性能表现
4. 考虑添加更多财务指标列（如持仓占比、收益率等）
