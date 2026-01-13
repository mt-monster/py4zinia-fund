import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 设置非交互式后端，解决Flask多线程问题
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import shap
import json
import os
from openai import OpenAI

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# ==================== 1. 数据生成 ====================
def generate_securities_data(n_customers=3000, n_weeks=12):
    """
    生成证券客户周度行为数据
    """
    np.random.seed(42)
    
    # 客户基础信息
    customer_ids = [f'CUST_{i:06d}' for i in range(n_customers)]
    customer_types = np.random.choice(['retail', 'vip', 'institution'], n_customers, p=[0.7, 0.2, 0.1])
    risk_tolerances = np.random.choice(['conservative', 'moderate', 'aggressive'], n_customers, p=[0.4, 0.4, 0.2])
    base_assets = np.random.lognormal(10, 2, n_customers)
    base_assets[customer_types == 'institution'] = np.random.lognormal(14, 1.5, sum(customer_types == 'institution'))
    
    # 生成周度数据
    weekly_data = []
    for i in range(n_weeks):
        week_data = {
            'customer_id': customer_ids,
            'customer_type': customer_types,
            'risk_tolerance': risk_tolerances,
            'week': i + 1,
            'base_assets': base_assets * (1 + np.random.normal(0, 0.05, n_customers)),
            'stock_market_value_mean': base_assets * np.random.uniform(0.3, 0.8, n_customers) * (1 + np.random.normal(0, 0.08, n_customers)),
            'stock_market_value_std': base_assets * np.random.uniform(0.05, 0.2, n_customers) * (1 + np.random.normal(0, 0.1, n_customers)),
            'stock_market_value_cv': np.random.uniform(0.1, 0.8, n_customers),
            'a_stock_volume_mean': np.random.lognormal(8, 2, n_customers),
            'a_stock_volume_std': np.random.lognormal(6, 2, n_customers),
            'a_stock_volume_cv': np.random.uniform(0.1, 0.5, n_customers),
            'transaction_frequency': np.random.poisson(3, n_customers),
            'commission_fee_mean': np.random.lognormal(4, 1, n_customers),
            'commission_fee_std': np.random.lognormal(2, 1, n_customers),
            'commission_cv': np.random.uniform(0.1, 0.6, n_customers),
            'daily_pnl_mean': np.random.normal(0, 1000, n_customers),
            'daily_pnl_std': np.random.uniform(500, 5000, n_customers),
            'daily_pnl_cv': np.random.uniform(0.2, 1.0, n_customers),
            'liquid_assets_mean': base_assets * np.random.uniform(0.2, 0.5, n_customers),
            'liquid_assets_std': base_assets * np.random.uniform(0.05, 0.15, n_customers),
            'liquid_assets_cv': np.random.uniform(0.1, 0.5, n_customers),
            'total_guarantee_mean': base_assets * np.random.uniform(0, 0.3, n_customers),
            'total_guarantee_std': base_assets * np.random.uniform(0, 0.1, n_customers),
            'total_guarantee_cv': np.random.uniform(0.1, 1.0, n_customers),
            'login_days_mean': np.random.poisson(15, n_customers),
            'login_days_std': np.random.uniform(1, 10, n_customers),
            'fund_flow_mean': np.random.normal(0, 10000, n_customers),
            'fund_flow_std': np.random.uniform(5000, 50000, n_customers),
            'fund_flow_cv': np.random.uniform(0.2, 1.0, n_customers),
            'fund_flow_negative_weeks': np.random.poisson(1, n_customers),
            'will_churn': 0  # 初始化流失标签为0
        }
        weekly_data.append(pd.DataFrame(week_data))
    
    # 合并所有周数据
    df = pd.concat(weekly_data, ignore_index=True)
    
    # 为30%的客户添加流失行为模式
    churn_customers = np.random.choice(customer_ids, int(n_customers * 0.3), replace=False)
    
    for customer in churn_customers:
        customer_data = df[df['customer_id'] == customer]
        if len(customer_data) < 3:
            continue
            
        # 在最后几周设置流失标签
        churn_week = np.random.randint(3, n_weeks)
        df.loc[(df['customer_id'] == customer) & (df['week'] >= churn_week), 'will_churn'] = 1
        
        # 模拟流失前的资产和登录行为变化
        df.loc[(df['customer_id'] == customer) & (df['week'] >= churn_week - 2), 'base_assets'] *= 0.8
        df.loc[(df['customer_id'] == customer) & (df['week'] >= churn_week - 2), 'login_days_mean'] *= 0.5
        df.loc[(df['customer_id'] == customer) & (df['week'] >= churn_week - 2), 'fund_flow_negative_weeks'] += 1
    
    # 计算股票市值趋势（最后几周资产下降比例）
    for customer in df['customer_id'].unique():
        customer_data = df[df['customer_id'] == customer].sort_values('week')
        if len(customer_data) >= 3:
            recent_assets = customer_data['base_assets'].tail(3).values
            if recent_assets[0] > 0:
                trend = (recent_assets[-1] - recent_assets[0]) / recent_assets[0]
                df.loc[df['customer_id'] == customer, 'stock_market_value_trend'] = trend
            else:
                df.loc[df['customer_id'] == customer, 'stock_market_value_trend'] = -1.0
        else:
            df.loc[df['customer_id'] == customer, 'stock_market_value_trend'] = 0.0
    
    return df

# ==================== 2. 特征工程 ====================
def feature_engineering_securities(df):
    """
    证券行业特征工程
    """
    # 聚合周度数据到客户级别
    customer_level = df.groupby('customer_id').agg({
        'customer_type': 'first',
        'risk_tolerance': 'first',
        'base_assets': 'mean',
        'stock_market_value_mean': 'mean',
        'stock_market_value_std': 'mean',
        'stock_market_value_cv': 'mean',
        'a_stock_volume_mean': 'mean',
        'a_stock_volume_std': 'mean',
        'a_stock_volume_cv': 'mean',
        'transaction_frequency': 'sum',
        'commission_fee_mean': 'mean',
        'commission_fee_std': 'mean',
        'commission_cv': 'mean',
        'daily_pnl_mean': 'mean',
        'daily_pnl_std': 'mean',
        'daily_pnl_cv': 'mean',
        'liquid_assets_mean': 'mean',
        'liquid_assets_std': 'mean',
        'liquid_assets_cv': 'mean',
        'total_guarantee_mean': 'mean',
        'total_guarantee_std': 'mean',
        'total_guarantee_cv': 'mean',
        'login_days_mean': 'mean',
        'login_days_std': 'mean',
        'fund_flow_mean': 'mean',
        'fund_flow_std': 'mean',
        'fund_flow_cv': 'mean',
        'fund_flow_negative_weeks': 'max',
        'stock_market_value_trend': 'mean',
        'will_churn': 'max'  # 只要有一周标记为流失，则标记为流失客户
    }).reset_index()
    
    feature_df = customer_level.copy()
    
    # 编码类别变量
    feature_df['customer_type'] = feature_df['customer_type'].map({
        'retail': 0, 'vip': 1, 'institution': 2
    })
    feature_df['risk_tolerance'] = feature_df['risk_tolerance'].map({
        'conservative': 0, 'moderate': 1, 'aggressive': 2
    })
    
    return feature_df

# ==================== 3. 模型训练与评估 ====================
def train_securities_churn_model(df):
    """
    训练证券行业流失预警模型
    """
    # 准备特征
    feature_cols = [col for col in df.columns if col not in ['customer_id', 'will_churn']]
    X = df[feature_cols]
    y = df['will_churn']
    
    print(f"特征数量: {len(feature_cols)}")
    print(f"样本数量: {len(df)}")
    print(f"流失率: {y.mean():.2%}")
    
    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # 标准化数值特征
    scaler = StandardScaler()
    numeric_cols = X_train.select_dtypes(include=['float64', 'int64']).columns
    X_train[numeric_cols] = scaler.fit_transform(X_train[numeric_cols])
    X_test[numeric_cols] = scaler.transform(X_test[numeric_cols])
    
    # 训练XGBoost
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=3.5,  # 处理样本不平衡
        random_state=42,
        eval_metric='auc',
        tree_method='hist'
    )
    
    model.fit(X_train, y_train)
    
    # 预测与评估
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    print("\n" + "="*60)
    print("证券客户流失预警模型评估")
    print("="*60)
    print(f"测试集AUC: {roc_auc_score(y_test, y_proba):.4f}")
    print("\n分类报告:")
    print(classification_report(y_test, y_pred, 
                               target_names=['留存', '流失']))
    
    return model, X_train, X_test, y_test, feature_cols, scaler

# ==================== 4. SHAP特征重要性分析 ====================
def shap_analysis_securities(model, X_train, feature_cols):
    """
    证券行业SHAP分析
    识别关键流失驱动因素
    """
    print("\n进行SHAP可解释性分析...")
    
    # 采样加速分析
    X_sample = X_train.sample(n=1000, random_state=42)
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # 为特征创建中文映射字典
    feature_name_mapping = {
        'stock_market_value_cv': '股票市值波动率',
        'fund_flow_negative_weeks': '资金净流出周数',
        'login_days_mean': '平均登录天数',
        'stock_market_value_trend': '股票市值趋势',
        'a_stock_volume_cv': 'A股交易量波动率',
        'commission_cv': '佣金波动率',
        'daily_pnl_cv': '日盈亏波动率',
        'liquid_assets_cv': '流动资产波动率',
        'total_guarantee_cv': '总担保金波动率',
        'liquid_assets_trend': '流动资产趋势',
        'risk_tolerance': '风险承受能力',
        'customer_type': '客户类型',
        'guarantee_to_volume': '担保金周转率',
        'pnl_to_guarantee': '盈亏担保比',
        'last_login_max': '最后登录间隔',
        'fund_flow_total': '资金流总额',
        'age': '年龄',
        'has_financial_product': '是否有金融产品',
        'has_visited': '是否访问过',
        'daily_pnl_trend': '日盈亏趋势',
        'login_days_trend': '登录天数趋势',
        'commission_trend': '佣金趋势',
        'commission_max': '最大佣金'
    }
    
    # 创建中文特征名列表
    chinese_feature_names = [feature_name_mapping.get(col, col) for col in feature_cols]
    
    # 保存路径设置
    save_path = 'D:/codes/py4zinia/customer_churn_predict/'
    
    # 1. 特征重要性柱状图
    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False, 
                     feature_names=chinese_feature_names)
    plt.title("证券客户流失关键特征排名", fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{save_path}securities_shap_bar.png', dpi=300, bbox_inches='tight')
    print(f"✅ SHAP特征重要性柱状图已保存: {save_path}securities_shap_bar.png")
    plt.close()
    
    # 2. SHAP值散点图
    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X_sample, show=False, 
                     feature_names=chinese_feature_names)
    plt.title("证券客户流失特征SHAP值散点图", fontsize=14)
    plt.tight_layout()
    plt.savefig(f'{save_path}securities_shap_scatter.png', dpi=300, bbox_inches='tight')
    print(f"✅ SHAP特征重要性散点图已保存: {save_path}securities_shap_scatter.png")
    plt.close()
    
    # 3. 综合依赖图
    plt.figure(figsize=(15, 12))
    
    # 选择前4个最重要的特征进行可视化（使用索引）
    for i in range(4):
        plt.subplot(2, 2, i+1)
        shap.dependence_plot(i, shap_values, X_sample, 
                            feature_names=chinese_feature_names,
                            show=False)
        plt.title(f"{chinese_feature_names[i]}影响", fontsize=14)
    
    plt.tight_layout()
    plt.savefig(f'{save_path}securities_shap_dependence.png', dpi=300, bbox_inches='tight')
    print(f"✅ SHAP特征依赖图已保存: {save_path}securities_shap_dependence.png")
    plt.close()
    
    return explainer, shap_values

# ==================== 5. 大模型生成挽留策略 ====================
def generate_retention_strategy(customer_profile, risk_score, shap_contrib):
    """
    调用字节跳动方舟大模型生成个性化挽留策略
    
    如果没有API密钥或调用失败，会返回模拟的策略文本
    """
    prompt = f"""
    你是一位经验丰富的证券客户关系管理专家。请根据以下客户信息，生成3条具体、可执行的挽留策略。
    
    客户情况：
    - 流失风险：{risk_score:.1%}
    - 客户类型：{'零售客户' if customer_profile.get('customer_type') == 'retail' else 'VIP客户' if customer_profile.get('customer_type') == 'vip' else '机构客户'}
    - 总资产：¥{customer_profile.get('base_assets', 0):.2f}
    - 主要风险因素：{', '.join([f"{k}({v:.2f})" for k,v in list(shap_contrib.items())[:3]])}
    
    要求：
    1. 策略必须具体明确，包含优惠力度和沟通话术
    2. 考虑客户生命周期价值
    3. 区分高/中/低不同风险等级
    4. 输出格式：JSON格式，包含"风险等级"、"策略"、"预期效果"、"执行优先级"
    """
    
    # 调用字节跳动方舟大模型
    try:
        # 请确保您已将 API Key 存储在环境变量 ARK_API_KEY 中
        # 初始化Openai客户端，从环境变量中读取您的API Key
        client = OpenAI(
            # 此为默认路径，您可根据业务所在地域进行配置
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key="7301bcd7-0207-4bc1-8bd7-8f64182fa1bb",
        )
        
        # Non-streaming request
        response = client.chat.completions.create(
            # 指定您创建的方舟推理接入点 ID
            model="kimi-k2-thinking-251104",
            messages=[
                {"role": "system", "content": "你是一位经验丰富的证券客户关系管理专家"},
                {"role": "user", "content": prompt},
            ],
        )
        
        # 获取响应内容
        content = response.choices[0].message.content
        
        # 打印响应内容以便调试
        print(f"API响应内容: {content[:200]}...")
        
        # 如果响应包含JSON格式，提取纯JSON部分
        if '{' in content:
            # 找到第一个'{'和最后一个'}'的位置
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                content = content[start_idx:end_idx]
        
        return content
    except Exception as e:
        print(f"字节跳动方舟API调用异常：{str(e)}")
        # 返回模拟的策略JSON
        return json.dumps({
            "风险等级": "高" if risk_score > 0.7 else "中" if risk_score > 0.4 else "低",
            "策略": ["客户经理电话回访", "提供个性化投资建议", "赠送服务优惠券"],
            "预期效果": "降低客户流失风险",
            "执行优先级": 1 if risk_score > 0.7 else 2 if risk_score > 0.4 else 3
        })

def batch_predict_and_generate_plan(model, df, feature_cols, scaler, explainer=None, top_k=30):
    """
    批量预测证券高流失风险客户并生成挽留计划
    
    参数:
    - model: 训练好的模型
    - df: 包含客户特征的数据框
    - feature_cols: 特征列名列表
    - scaler: 用于特征标准化的缩放器
    - explainer: SHAP解释器对象，用于计算特征重要性
    - top_k: 生成计划的前k个高风险客户
    
    返回:
    - high_risk: 高风险客户数据框
    - action_df: 挽留计划数据框
    """
    print("\n" + "="*60)
    print("开始批量预测与挽留计划生成")
    print("="*60)
    
    # 准备特征
    X = df[feature_cols].copy()
    numeric_cols = X.select_dtypes(include=['float64', 'int64']).columns
    X[numeric_cols] = scaler.transform(X[numeric_cols])
    
    # 预测
    df['churn_prob'] = model.predict_proba(X)[:, 1]
    
    # 识别高风险客户
    high_risk = df[df['churn_prob'] > 0.6].copy()
    high_risk = high_risk.sort_values('churn_prob', ascending=False).head(top_k)
    
    print(f"\n识别出 {len(high_risk)} 个高危客户（流失概率>60%）")
    
    # 生成挽留计划
    action_plans = []
    
    # 计算SHAP值（如果提供了解释器）
    shap_values = None
    if explainer is not None:
        shap_values = explainer.shap_values(X)
    
    for idx, customer in high_risk[:2].iterrows():
        # 提取客户信息
        customer_info = customer.to_dict()
        risk_score = customer['churn_prob']
        
        # 提取SHAP贡献（如果有）
        shap_contrib = {}
        if shap_values is not None:
            # 找到客户在原始数据中的索引
            customer_idx = df.index.get_loc(idx)
            # 提取该客户的SHAP值
            customer_shap = shap_values[customer_idx]
            # 构建特征与SHAP值的映射
            shap_contrib = {col: customer_shap[i] for i, col in enumerate(feature_cols)}
        
        # 调用大模型生成挽留策略
        strategy_response = generate_retention_strategy(customer_info, risk_score, shap_contrib)
        
        # 解析策略JSON
        strategy_data = {}
        
        try:
            # 复制响应内容以便处理
            response_content = strategy_response
            
            # 清理markdown代码块标记
            if response_content.strip().startswith('```json'):
                response_content = response_content[response_content.find('\n')+1:]
            if response_content.strip().endswith('```'):
                response_content = response_content[:response_content.rfind('```')]
            response_content = response_content.strip()
            
            # 尝试解析整个内容
            try:
                strategy_data = json.loads(response_content)
            except json.JSONDecodeError:
                # 如果整个内容解析失败，尝试提取JSON部分
                print("尝试提取JSON部分...")
                # 找到所有可能的JSON开始位置
                json_starts = [i for i, char in enumerate(response_content) if char == '{']
                json_ends = [i for i, char in enumerate(response_content) if char == '}']
                
                # 找到最长的有效JSON
                for start in reversed(json_starts):
                    for end in json_ends:
                        if end > start:
                            try:
                                json_part = response_content[start:end+1]
                                strategy_data = json.loads(json_part)
                                print("已提取有效的JSON部分")
                                break
                            except json.JSONDecodeError:
                                continue
                    if strategy_data:
                        break
        except Exception as e:
            # 如果解析失败，使用默认策略
            print(f"警告：策略JSON解析失败 - {str(e)}，已使用默认策略")
            strategy_data = {}
        
        
        # 如果strategy_data为空或缺少关键信息，使用默认值
        if not strategy_data:
            risk_level = "高" if risk_score > 0.7 else "中" if risk_score > 0.4 else "低"
            strategy_data = {
                "风险等级": risk_level,
                "策略": ["客户经理电话回访", "提供个性化投资建议", "赠送服务优惠券"],
                "预期效果": "降低客户流失风险",
                "执行优先级": 1 if risk_score > 0.7 else 2 if risk_score > 0.4 else 3
            }
        
        # 构建完整的挽留计划
        # 根据risk_score计算正确的风险等级
        calculated_risk_level = "高" if risk_score > 0.7 else "中" if risk_score > 0.4 else "低"
        
        # 如果大模型返回了风险等级，则使用大模型的结果，否则使用计算的风险等级
        if "风险等级" not in strategy_data:
            strategy_data["风险等级"] = calculated_risk_level
        
        # 更新执行优先级，确保与风险等级匹配
        if "执行优先级" not in strategy_data: 
            strategy_data["执行优先级"] = 1 if calculated_risk_level == "高" else 2 if calculated_risk_level == "中" else 3
        
        # 处理挽留策略（适配大模型返回的字典格式）
        if "策略" in strategy_data:
            # 如果有"策略"字段，使用该字段
            strategy = strategy_data["策略"]
            if isinstance(strategy, dict):
                # 如果是字典格式，转换为列表以便展示
                strategy_list = [f"{k}: {v}" for k, v in strategy.items()]
            else:
                strategy_list = strategy
        else:
            # 否则，将整个strategy_data作为策略内容，但排除非策略字段
            strategy_list = []
            for k, v in strategy_data.items():
                if k not in ["风险等级", "执行优先级", "预期效果", "备注"]:
                    if isinstance(v, list):
                        # 如果是列表，转换为字符串
                        items = []
                        for item in v:
                            if isinstance(item, dict):
                                # 如果列表项是字典，转换为键值对字符串
                                item_str = "; ".join([f"{ik}: {iv}" for ik, iv in item.items()])
                                items.append(item_str)
                            elif isinstance(item, str):
                                # 如果是字符串，直接使用
                                items.append(item)
                            else:
                                # 其他类型，转换为字符串
                                items.append(str(item))
                        v_str = ", ".join(items)
                        strategy_list.append(f"{k}: {v_str}")
                    else:
                        strategy_list.append(f"{k}: {v}")
        
        # 处理预期效果（适配大模型返回的字典格式）
        expected_effect = strategy_data.get("预期效果", "降低客户流失风险")
        if isinstance(expected_effect, dict):
            # 如果是字典格式，转换为字符串以便展示
            expected_effect_str = ", ".join([f"{k}: {v}" for k, v in expected_effect.items()])
        else:
            expected_effect_str = expected_effect
        
        # 获取最终的风险等级（优先使用大模型返回的，否则使用计算的）
        final_risk_level = strategy_data["风险等级"]
        
        # 构建挽留计划
        plan = {
            "客户ID": customer_info['customer_id'],
            "风险等级": final_risk_level,
            "流失概率": f"{risk_score:.1%}",
            "关键预警信号": f"资产波动率: {customer_info.get('stock_market_value_cv', 0):.2f}, "
                           f"资金净流出周数: {customer_info.get('fund_flow_negative_weeks', 0)}",
            "挽留策略": strategy_list,
            "预期效果": expected_effect_str,
            "执行优先级": strategy_data.get("执行优先级", 1 if calculated_risk_level == "高" else 2 if calculated_risk_level == "中" else 3),
            "执行期限": "3个工作日" if calculated_risk_level == "高" else "7个工作日",
            "备注": strategy_data.get("备注", "")
        }
        
        action_plans.append(plan)
        
        # 打印Top5详情
        if len(action_plans) <= 1:
            print(f"\n【{plan['客户ID']}】风险等级: {plan['风险等级']} | 流失概率: {plan['流失概率']}")
            print(f"关键信号: {plan['关键预警信号']}")
            print("挽留策略:")
            for idx, strategy in enumerate(plan['挽留策略'], 1):
                print(f"  {idx}. {strategy}")
            print(f"预期效果: {plan['预期效果']}")
            print(f"执行优先级: {plan['执行优先级']}")
            print(f"执行期限: {plan['执行期限']}")
            if plan['备注']:
                print(f"备注: {plan['备注']}")
    
    # 保存计划
    action_df = pd.DataFrame(action_plans)
    action_df.to_excel('securities_retention_plan.xlsx', index=False)
    print(f"\n✅ 挽留计划已保存至: securities_retention_plan.xlsx")
    
    return high_risk, action_df

# ==================== 6. 主流程 ====================
def main():
    """证券客户流失预警主流程"""
    print("🚀 启动证券行业客户流失预警系统...")
    
    # 1. 生成模拟数据
    print("\n1. 生成证券客户周度数据...")
    weekly_df = generate_securities_data(n_customers=3000, n_weeks=12)
    print(f"   数据规模: {weekly_df.shape}")
    print(f"   客户数: {weekly_df['customer_id'].nunique()}")
    print(f"   流失率: {weekly_df['will_churn'].mean():.2%}")
    
    # 2. 特征工程
    print("\n2. 构建证券行业特征...")
    feature_df = feature_engineering_securities(weekly_df)
    print(f"   特征数量: {feature_df.shape[1] - 2}")  # 排除id和label
    
    # 3. 训练模型
    print("\n3. 训练流失预警模型...")
    model, X_train, X_test, y_test, feature_cols, scaler = train_securities_churn_model(feature_df)
    
    # 4. SHAP分析
    print("\n4. 进行模型可解释性分析...")
    explainer, shap_values = shap_analysis_securities(model, X_train, feature_cols)
    
    # 5. 批量预测与挽留计划
    print("\n5. 生成高危客户挽留计划...")
    high_risk_customers, action_df = batch_predict_and_generate_plan(
        model, feature_df, feature_cols, scaler, explainer=explainer, top_k=30
    )
    
    print("\n✅ 证券客户流失预警分析完成！")
    print("   生成文件:")
    print("   - securities_shap_bar.png (特征重要性柱状图)")
    print("   - securities_shap_scatter.png (特征重要性散点图)")
    print("   - securities_shap_dependence.png (特征依赖图)")
    print("   - securities_retention_plan.xlsx (挽留计划)")

if __name__ == "__main__":
    main()