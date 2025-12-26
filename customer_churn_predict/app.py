from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
import pickle
import os
from churn_predict import (generate_securities_data, 
                           feature_engineering_securities, 
                           train_securities_churn_model, 
                           batch_predict_and_generate_plan,
                           shap_analysis_securities)

app = Flask(__name__, static_folder='.')

# 启用CORS支持
CORS(app)

# 全局变量，用于存储训练好的模型和数据
model = None
feature_df = None
feature_cols = None
scaler = None
explainer = None

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': 'API服务器运行正常'})

@app.route('/api/train', methods=['POST'])
def train_model():
    """训练模型接口"""
    global model, feature_df, feature_cols, scaler, explainer
    
    try:
        # 生成模拟数据
        weekly_df = generate_securities_data(n_customers=3000, n_weeks=12)
        
        # 特征工程
        feature_df = feature_engineering_securities(weekly_df)
        
        # 训练模型
        model, X_train, X_test, y_test, feature_cols, scaler = train_securities_churn_model(feature_df)
        
        # 进行SHAP分析
        explainer, _ = shap_analysis_securities(model, X_train, feature_cols)
        
        return jsonify({
            'status': 'success',
            'message': '模型训练完成',
            'customer_count': feature_df['customer_id'].nunique(),
            'feature_count': len(feature_cols)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict_risk():
    """预测客户流失风险接口"""
    global model, feature_df, feature_cols, scaler, explainer
    
    if model is None:
        return jsonify({'status': 'error', 'message': '模型未训练，请先调用/train接口'}), 400
    
    try:
        # 获取请求参数
        data = request.get_json()
        top_k = data.get('top_k', 30)
        
        # 批量预测并生成挽留计划
        high_risk, action_df = batch_predict_and_generate_plan(
            model, feature_df, feature_cols, scaler, explainer=explainer, top_k=top_k
        )
        
        # 转换为JSON可序列化格式
        retention_plans = action_df.to_dict(orient='records')
        
        return jsonify({
            'status': 'success',
            'high_risk_count': len(high_risk),
            'plans_count': len(retention_plans),
            'retention_plans': retention_plans
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/customer/<customer_id>', methods=['GET'])
def get_customer_info(customer_id):
    """获取单个客户信息接口"""
    global feature_df
    
    if feature_df is None:
        return jsonify({'status': 'error', 'message': '数据未加载，请先调用/train接口'}), 400
    
    try:
        customer = feature_df[feature_df['customer_id'] == customer_id]
        if customer.empty:
            return jsonify({'status': 'error', 'message': '客户不存在'}), 404
        
        customer_info = customer.iloc[0].to_dict()
        return jsonify({
            'status': 'success',
            'customer_info': customer_info
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/plans/download', methods=['GET'])
def download_plans():
    """下载挽留计划Excel文件接口"""
    try:
        if not os.path.exists('securities_retention_plan.xlsx'):
            return jsonify({'status': 'error', 'message': '挽留计划文件不存在，请先调用/predict接口'}), 404
        
        # 读取Excel文件内容
        df = pd.read_excel('securities_retention_plan.xlsx')
        plans = df.to_dict(orient='records')
        
        return jsonify({
            'status': 'success',
            'plans': plans
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
@app.route('/index.html')
def serve_index():
    """提供前端页面"""
    return send_file('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)