from flask import Flask, request, jsonify, send_file, send_from_directory, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
import pickle
import os
from agent.core import ChurnPredictionAgent
from tools import get_tools
from config.settings import get_config

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# 启用CORS支持
CORS(app)

# 初始化 Agent 和工具
config = get_config()
agent = ChurnPredictionAgent(config=config['llm'])
tools = get_tools()

# 注册工具到 Agent
agent.register_tool('generate_data', tools.generate_data, '生成客户数据')
agent.register_tool('feature_engineering', tools.feature_engineering, '进行特征工程')
agent.register_tool('train_model', tools.train_model, '训练流失预测模型')
agent.register_tool('predict_risk', tools.predict_risk, '预测客户流失风险')
agent.register_tool('shap_analysis', tools.shap_analysis, '进行模型可解释性分析')
agent.register_tool('generate_retention_plan', tools.generate_retention_plan, '生成挽留计划')
agent.register_tool('generate_report', tools.generate_report, '生成分析报告')
agent.register_tool('get_customer_info', tools.get_customer_info, '获取客户信息')

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({'status': 'ok', 'message': 'API服务器运行正常'})

@app.route('/api/agent/status', methods=['GET'])
def agent_status():
    """获取 Agent 状态"""
    try:
        status = agent.get_status()
        return jsonify({
            'status': 'success',
            'agent_status': status
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/agent/chat', methods=['POST'])
def agent_chat():
    """Agent 对话接口"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'status': 'error', 'message': '消息不能为空'}), 400
        
        # 获取上下文（如果有）
        context = data.get('context', {})
        
        # 调用 Agent
        response = agent.chat(user_message, context)
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/agent/memory', methods=['GET'])
def get_agent_memory():
    """获取 Agent 记忆"""
    try:
        limit = request.args.get('limit', 10, type=int)
        memory_summary = agent.get_memory_summary(limit=limit)
        return jsonify({
            'status': 'success',
            'memory': memory_summary,
            'memory_count': len(agent.memory)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/agent/memory/clear', methods=['POST'])
def clear_agent_memory():
    """清空 Agent 记忆"""
    try:
        agent.clear_memory()
        return jsonify({
            'status': 'success',
            'message': '记忆已清空'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/train', methods=['POST'])
def train_model():
    """训练模型接口（兼容旧接口，内部使用 Agent）"""
    try:
        data = request.get_json() or {}
        n_customers = data.get('n_customers', config['data']['n_customers'])
        n_weeks = data.get('n_weeks', config['data']['n_weeks'])
        
        # 使用 Agent 工具
        result1 = tools.generate_data(n_customers=n_customers, n_weeks=n_weeks)
        if result1['status'] != 'success':
            return jsonify(result1), 500
        
        result2 = tools.feature_engineering()
        if result2['status'] != 'success':
            return jsonify(result2), 500
        
        result3 = tools.train_model()
        if result3['status'] != 'success':
            return jsonify(result3), 500
        
        return jsonify({
            'status': 'success',
            'message': '模型训练完成',
            'customer_count': result1.get('customer_count', 0),
            'feature_count': result2.get('feature_count', 0)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict_risk():
    """预测客户流失风险接口（兼容旧接口，内部使用 Agent）"""
    try:
        if tools.model is None:
            return jsonify({'status': 'error', 'message': '模型未训练，请先调用/train接口'}), 400
        
        # 获取请求参数
        data = request.get_json() or {}
        top_k = data.get('top_k', config['prediction']['top_k'])
        
        # 使用 Agent 工具
        result = tools.predict_risk(top_k=top_k)
        
        if result['status'] != 'success':
            return jsonify(result), 500
        
        return jsonify({
            'status': 'success',
            'high_risk_count': result.get('high_risk_count', 0),
            'plans_count': result.get('plans_count', 0),
            'retention_plans': result.get('retention_plans', [])
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/customer/<customer_id>', methods=['GET'])
def get_customer_info(customer_id):
    """获取单个客户信息接口（兼容旧接口，内部使用 Agent）"""
    try:
        result = tools.get_customer_info(customer_id)
        if result['status'] != 'success':
            status_code = 404 if '不存在' in result.get('message', '') else 400
            return jsonify(result), status_code
        return jsonify(result)
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
    return render_template('index.html')

@app.route('/agent')
@app.route('/agent.html')
def serve_agent():
    """提供 Agent 对话页面"""
    return render_template('agent.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    return send_from_directory('static', filename)

# 兼容旧路径的静态文件服务
@app.route('/<path:filename>')
def serve_legacy_static(filename):
    """提供静态文件服务（兼容旧路径）"""
    # 检查是否是图片文件
    if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.xlsx')):
        return send_from_directory('.', filename)
    return jsonify({'status': 'error', 'message': '文件不存在'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)