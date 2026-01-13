# -*- coding: utf-8 -*-
"""
Agent 使用示例
演示如何使用客户流失预警 Agent
"""

from agent.core import ChurnPredictionAgent
from tools import get_tools
from config.settings import get_config


def main():
    """Agent 使用示例"""
    
    print("=" * 60)
    print("客户流失预警 Agent 使用示例")
    print("=" * 60)
    
    # 1. 初始化 Agent 和工具
    print("\n1. 初始化 Agent...")
    config = get_config()
    agent = ChurnPredictionAgent(config=config['llm'])
    tools = get_tools()
    
    # 2. 注册工具
    print("2. 注册工具...")
    agent.register_tool('generate_data', tools.generate_data, '生成客户数据')
    agent.register_tool('feature_engineering', tools.feature_engineering, '进行特征工程')
    agent.register_tool('train_model', tools.train_model, '训练流失预测模型')
    agent.register_tool('predict_risk', tools.predict_risk, '预测客户流失风险')
    agent.register_tool('shap_analysis', tools.shap_analysis, '进行模型可解释性分析')
    agent.register_tool('generate_retention_plan', tools.generate_retention_plan, '生成挽留计划')
    agent.register_tool('generate_report', tools.generate_report, '生成分析报告')
    agent.register_tool('get_customer_info', tools.get_customer_info, '获取客户信息')
    
    print(f"   已注册 {len(agent.tools)} 个工具")
    
    # 3. 查看 Agent 状态
    print("\n3. Agent 状态:")
    status = agent.get_status()
    print(f"   能力: {list(status['capabilities'].keys())}")
    print(f"   工具数: {status['tools_count']}")
    print(f"   记忆数: {status['memory_count']}")
    print(f"   是否启用 LLM: {status['has_llm']}")
    
    # 4. 示例对话 1: 训练模型
    print("\n4. 示例对话 1: 训练模型")
    print("   用户: '请帮我训练一个流失预测模型'")
    response1 = agent.chat("请帮我训练一个流失预测模型")
    print(f"   Agent: {response1['response'][:200]}...")
    print(f"   状态: {response1['status']}")
    
    # 5. 示例对话 2: 预测风险
    print("\n5. 示例对话 2: 预测风险")
    print("   用户: '预测一下哪些客户有流失风险'")
    response2 = agent.chat("预测一下哪些客户有流失风险")
    print(f"   Agent: {response2['response'][:200]}...")
    print(f"   状态: {response2['status']}")
    
    # 6. 查看记忆
    print("\n6. Agent 记忆摘要:")
    memory_summary = agent.get_memory_summary(limit=5)
    print(memory_summary)
    
    # 7. 保存记忆
    print("\n7. 保存 Agent 记忆...")
    agent.save_memory('agent_memory_example.json')
    print("   记忆已保存到 agent_memory_example.json")
    
    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

