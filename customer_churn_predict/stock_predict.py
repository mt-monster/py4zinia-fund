# -*- coding: utf-8 -*-
"""
证券行业客户流失预警完整案例
运行环境: Python 3.8+, 依赖包见文末 requirements.txt
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import shap
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# ==================== 1. 证券行业数据模拟 ====================
def generate_securities_data(n_customers=3000, n_weeks=12):
    """
    模拟证券客户周度数据
    包含资产、交易、行为等证券行业核心特征
    """
    np.random.seed(42)
    
    # 客户基础信息
    customers = []
    for i in range(1, n_customers + 1):
        customer_id = f"CUST_{i:06d}"
        
        # 根据客户类型设置基础参数
        customer_type = np.random.choice(['retail', 'vip', 'institution'], p=[0.7, 0.25, 0.05])
        base_assets = {
            'retail': np.random.uniform(5, 100),
            'vip': np.random.uniform(100, 1000),
            'institution': np.random.uniform(500, 5000)
        }[customer_type]
        
        customers.append({
            'customer_id': customer_id,
            'customer_type': customer_type,
            'age': np.random.randint(25, 70),
            'risk_tolerance': np.random.choice(['conservative', 'moderate', 'aggressive'], 
                                               p=[0.3, 0.5, 0.2]),
            'has_financial_product': np.random.choice([0, 1], p=[0.7, 0.3]),
            'has_visited': np.random.choice([0, 1], p=[0.6, 0.4]),  # 是否当面拜访
            'base_assets': base_assets
        })
    
    customer_df = pd.DataFrame(customers)
    
    # 生成周度数据
    weekly_records = []
    start_date = datetime(2023, 1, 1)
    
    for _, customer in customer_df.iterrows():
        # 为流失客户设置资产下降趋势
        will_churn = np.random.choice([0, 1], p=[0.78, 0.22])  # 22%流失率
        
        for week in range(n_weeks):
            week_date = start_date + timedelta(weeks=week)
            
            # 资产类特征（带趋势和噪声）
            if will_churn and week >= 8:  # 流失前4周开始资产下降
                asset_decay = 1 - (week - 7) * np.random.uniform(0.08, 0.15)
                asset_decay = max(asset_decay, 0.3)
            else:
                asset_decay = 1.0
            
            # 核心资产指标
            stock_market_value = customer['base_assets'] * asset_decay * np.random.uniform(0.9, 1.1)
            total_guarantee = stock_market_value * np.random.uniform(0.95, 1.05)
            liquid_assets = total_guarantee * np.random.uniform(0.8, 0.95)
            
            # 交易行为
            if will_churn and week >= 8:
                trade_multiplier = 1 - (week - 7) * 0.2
            else:
                trade_multiplier = 1.0
            
            a_stock_volume = max(0, total_guarantee * np.random.uniform(0.05, 0.3) * trade_multiplier)
            commission = a_stock_volume * np.random.uniform(0.0003, 0.0005)
            
            # 盈亏
            daily_pnl = stock_market_value * np.random.uniform(-0.03, 0.03)
            
            # 资金流动（流失前会大额转出）
            if will_churn and week >= 10:
                fund_flow = -total_guarantee * np.random.uniform(0.2, 0.6)
            else:
                fund_flow = np.random.uniform(-5, 5)
            
            # 行为特征
            login_days = np.random.randint(0, 5) if will_churn and week >= 8 else np.random.randint(2, 6)
            last_login_days_ago = np.random.randint(0, 3) if login_days > 0 else np.random.randint(5, 15)
            
            weekly_records.append({
                'customer_id': customer['customer_id'],
                'week': week,
                'week_date': week_date,
                'stock_market_value': stock_market_value,
                'total_guarantee': total_guarantee,
                'liquid_assets': liquid_assets,
                'a_stock_volume': a_stock_volume,
                'commission': commission,
                'daily_pnl': daily_pnl,
                'fund_flow': fund_flow,
                'login_days': login_days,
                'last_login_days_ago': last_login_days_ago,
                'will_churn': will_churn
            })
    
    weekly_df = pd.DataFrame(weekly_records)
    
    # 合并客户信息
    df = weekly_df.merge(customer_df, on='customer_id', how='left')
    
    return df

# ==================== 2. 证券行业特征工程 ====================
def feature_engineering_securities(df):
    """
    构建证券行业流失预警特征
    实现周统计量、复合因子等核心特征
    """
    features = []
    
    for cust_id, group in df.groupby('customer_id'):
        group = group.sort_values('week')
        base_info = group.iloc[0]
        
        # 计算周统计量（均值、标准差、变异系数、最大值等）
        asset_features = {}
        
        # 资产类因子（5个统计量）
        for col in ['stock_market_value', 'total_guarantee', 'liquid_assets', 
                   'a_stock_volume', 'commission', 'daily_pnl']:
            values = group[col].values
            
            asset_features[f'{col}_mean'] = np.mean(values)
            asset_features[f'{col}_std'] = np.std(values)
            asset_features[f'{col}_cv'] = np.std(values) / (np.mean(values) + 1e-6)
            asset_features[f'{col}_max'] = np.max(values)
            asset_features[f'{col}_trend'] = np.polyfit(range(len(values)), values, 1)[0]
        
        # 非资产类因子
        behavior_features = {
            'login_days_mean': np.mean(group['login_days']),
            'login_days_trend': np.polyfit(range(len(group)), group['login_days'], 1)[0],
            'last_login_max': np.max(group['last_login_days_ago']),
            'fund_flow_total': np.sum(group['fund_flow']),
            'fund_flow_negative_weeks': np.sum(group['fund_flow'] < -10),
            
            # 基础信息
            'age': base_info['age'],
            'has_financial_product': base_info['has_financial_product'],
            'has_visited': base_info['has_visited'],
            
            # 编码类特征
            'customer_type': base_info['customer_type'],
            'risk_tolerance': base_info['risk_tolerance']
        }
        
        # 复合因子
        composite_features = {
            'pnl_to_guarantee': asset_features['daily_pnl_mean'] / (asset_features['total_guarantee_mean'] + 1e-6),
            'guarantee_to_volume': asset_features['total_guarantee_mean'] / (asset_features['a_stock_volume_mean'] + 1e-6)
        }
        
        # 合并所有特征
        feature_dict = {
            'customer_id': cust_id,
            'will_churn': base_info['will_churn'],
            **asset_features,
            **behavior_features,
            **composite_features
        }
        
        features.append(feature_dict)
    
    feature_df = pd.DataFrame(features)
    
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
    
    # 可视化
    plt.figure(figsize=(15, 10))
    
    # 特征重要性
    plt.subplot(2, 2, 1)
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.title("证券客户流失关键特征排名", fontsize=14)
    
    # 在网时长影响
    plt.subplot(2, 2, 2)
    shap.dependence_plot("tenure", shap_values, X_sample, show=False)
    plt.title("在网时长(tenure)影响", fontsize=14)
    
    # 资产波动影响
    plt.subplot(2, 2, 3)
    shap.dependence_plot("stock_market_value_cv", shap_values, X_sample, show=False)
    plt.title("资产波动率影响", fontsize=14)
    
    # 资金流出影响
    plt.subplot(2, 2, 4)
    shap.dependence_plot("fund_flow_negative_weeks", shap_values, X_sample, show=False)
    plt.title("资金净流出周数影响", fontsize=14)
    
    plt.tight_layout()
    plt.savefig('securities_shap_analysis.png', dpi=300, bbox_inches='tight')
    print("✅ SHAP分析图表已保存: securities_shap_analysis.png")
    plt.show()
    
    return explainer, shap_values

# ==================== 5. 批量预测与挽留策略 ====================
def generate_securities_retention_plan(customer_info, risk_score):
    """
    生成证券行业专属挽留方案
    """
    risk_level = "高" if risk_score > 0.7 else "中" if risk_score > 0.4 else "低"
    
    strategies = {
        "高": [
            "客户经理48小时内电话回访，提供投资组合诊断",
            "赠送3个月Level2行情+专属投顾服务",
            "根据持仓提供定制化调仓建议"
        ],
        "中": [
            "推送近期热门研报和市场分析",
            "邀请参加线下投资策略会",
            "提供佣金优惠方案"
        ],
        "低": [
            "短信关怀提醒市场机会",
            "推送APP新功能引导",
            "积分商城优惠券激励"
        ]
    }
    
    plan = {
        "客户ID": customer_info['customer_id'],
        "风险等级": risk_level,
        "流失概率": f"{risk_score:.1%}",
        "关键预警信号": f"资产波动率: {customer_info.get('stock_market_value_cv', 0):.2f}, "
                       f"资金净流出周数: {customer_info.get('fund_flow_negative_weeks', 0)}",
        "挽留策略": strategies[risk_level],
        "执行期限": "3个工作日" if risk_level == "高" else "7个工作日"
    }
    
    return plan

def batch_predict_and_generate_plan(model, df, feature_cols, scaler, top_k=30):
    """
    批量预测证券高流失风险客户并生成挽留计划
    """
    print("\n" + "="*60)
    print("开始批量预测与挽留计划生成")
    print("="*60)
    
    # 准备特征
    X = df[feature_cols]
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
    for _, customer in high_risk.iterrows():
        plan = generate_securities_retention_plan(customer.to_dict(), customer['churn_prob'])
        action_plans.append(plan)
        
        # 打印Top5详情
        if len(action_plans) <= 5:
            print(f"\n【{plan['客户ID']}】风险等级: {plan['风险等级']} | 流失概率: {plan['流失概率']}")
            print(f"关键信号: {plan['关键预警信号']}")
            print("挽留策略:")
            for idx, strategy in enumerate(plan['挽留策略'], 1):
                print(f"  {idx}. {strategy}")
            print(f"执行期限: {plan['执行期限']}")
    
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
        model, feature_df, feature_cols, scaler, top_k=30
    )
    
    print("\n✅ 证券客户流失预警分析完成！")
    print("   生成文件:")
    print("   - securities_shap_analysis.png (特征重要性)")
    print("   - securities_retention_plan.xlsx (挽留计划)")

if __name__ == "__main__":
    main()

# ==================== 7. 依赖包说明 ====================
"""
requirements_securities.txt 内容:

# 核心数据处理
pandas>=2.0.0
numpy>=1.24.0

# 机器学习
scikit-learn>=1.3.0
xgboost>=2.0.0

# 模型解释
shap>=0.43.0

# 可视化
matplotlib>=3.7.0
seaborn>=0.12.0

# Excel输出
openpyxl>=3.1.0

# 可选：接入真实LLM生成策略
# dashscope>=1.19.0  # 阿里云通义千问SDK

安装命令:
pip install -r requirements_securities.txt
"""
