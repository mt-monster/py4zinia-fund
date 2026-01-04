# -*- coding: utf-8 -*-
"""
Agent 启动示例
演示如何启动和使用客户流失预警 Agent
"""

from agent.core import ChurnPredictionAgent
from tools import get_tools
from config.settings import get_config


def main():
    """启动 Agent 并演示基本使用"""
    
    print("=" * 60)
    print("客户流失预警 Agent 启动示例")
    print("=" * 60)
    
    # 1. 初始化配置
    print("\n[1] 初始化配置...")
    config = get_config()
    print(f"   配置加载完成")
    
    # 2. 初始化 Agent
    print("\n[2] 初始化 Agent...")
    agent = ChurnPredictionAgent(config=config['llm'])
    print(f"   Agent 初始化完成")
    
    # 3. 初始化工具
    print("\n[3] 初始化工具系统...")
    tools = get_tools()
    
    # 4. 注册工具到 Agent
    print("\n[4] 注册工具...")
    agent.register_tool('generate_data', tools.generate_data, '生成客户数据')
    agent.register_tool('feature_engineering', tools.feature_engineering, '进行特征工程')
    agent.register_tool('train_model', tools.train_model, '训练流失预测模型')
    agent.register_tool('predict_risk', tools.predict_risk, '预测客户流失风险')
    agent.register_tool('shap_analysis', tools.shap_analysis, '进行模型可解释性分析')
    agent.register_tool('generate_retention_plan', tools.generate_retention_plan, '生成挽留计划')
    agent.register_tool('generate_report', tools.generate_report, '生成分析报告')
    agent.register_tool('get_customer_info', tools.get_customer_info, '获取客户信息')
    print(f"   已注册 {len(agent.tools)} 个工具")
    
    # 5. 查看 Agent 状态
    print("\n[5] Agent 状态:")
    status = agent.get_status()
    print(f"   工具数量: {status['tools_count']}")
    print(f"   记忆数量: {status['memory_count']}")
    print(f"   LLM 状态: {'已启用' if status['has_llm'] else '未启用'}")
    
    # 6. 示例对话
    print("\n" + "=" * 60)
    print("示例对话")
    print("=" * 60)
    
    # 示例 1: 训练模型
    print("\n>>> 用户: 请帮我训练一个流失预测模型")
    response1 = agent.chat("请帮我训练一个流失预测模型")
    print(f"Agent: {response1['response']}")
    print(f"状态: {response1['status']}")
    
    # 示例 2: 预测风险
    print("\n>>> 用户: 预测一下哪些客户有流失风险")
    response2 = agent.chat("预测一下哪些客户有流失风险")
    print(f"Agent: {response2['response'][:200]}...")
    print(f"状态: {response2['status']}")
    
    # 7. 查看记忆
    print("\n" + "=" * 60)
    print("Agent 记忆摘要")
    print("=" * 60)
    memory_summary = agent.get_memory_summary(limit=5)
    print(memory_summary)
    
    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
    print("\n提示：")
    print("  - 使用 agent.chat('你的指令') 与 Agent 对话")
    print("  - 使用 agent.get_status() 查看 Agent 状态")
    print("  - 使用 agent.get_memory_summary() 查看记忆")
    print("  - 使用 agent.save_memory('file.json') 保存记忆")


if __name__ == "__main__":
    main()

