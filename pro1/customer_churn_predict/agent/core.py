# -*- coding: utf-8 -*-
"""
客户流失预警 Agent 核心模块
实现自主决策、规划、记忆等 AI Agent 能力
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from openai import OpenAI


@dataclass
class AgentMemory:
    """Agent 记忆单元"""
    timestamp: str
    action: str
    result: Any
    context: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)


class ChurnPredictionAgent:
    """
    客户流失预警 Agent
    
    具备以下能力：
    1. 自主决策：根据用户意图自动选择执行工具
    2. 规划能力：将复杂任务分解为多个步骤
    3. 记忆能力：记录历史操作和结果
    4. 工具调用：使用各种工具完成任务
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Agent
        
        Args:
            config: 配置字典，包含 API 密钥等
        """
        self.config = config or {}
        self.memory: List[AgentMemory] = []
        self.tools = {}
        self.llm_client = None
        
        # 初始化 LLM 客户端（如果配置了 API）
        if self.config.get('api_key'):
            self.llm_client = OpenAI(
                base_url=self.config.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3'),
                api_key=self.config.get('api_key')
            )
        
        # Agent 能力描述
        self.capabilities = {
            'data_generation': '生成模拟客户数据',
            'model_training': '训练流失预测模型',
            'risk_prediction': '预测客户流失风险',
            'shap_analysis': '进行模型可解释性分析',
            'retention_planning': '生成个性化挽留计划',
            'report_generation': '生成分析报告'
        }
    
    def register_tool(self, tool_name: str, tool_func, description: str):
        """
        注册工具
        
        Args:
            tool_name: 工具名称
            tool_func: 工具函数
            description: 工具描述
        """
        self.tools[tool_name] = {
            'func': tool_func,
            'description': description
        }
    
    def add_memory(self, action: str, result: Any, context: Dict[str, Any] = None):
        """
        添加记忆
        
        Args:
            action: 执行的动作
            result: 执行结果
            context: 上下文信息
        """
        memory = AgentMemory(
            timestamp=datetime.now().isoformat(),
            action=action,
            result=result,
            context=context or {}
        )
        self.memory.append(memory)
    
    def get_memory_summary(self, limit: int = 10) -> str:
        """
        获取记忆摘要
        
        Args:
            limit: 返回最近 N 条记忆
            
        Returns:
            记忆摘要文本
        """
        recent_memories = self.memory[-limit:] if len(self.memory) > limit else self.memory
        summary = []
        for mem in recent_memories:
            summary.append(f"[{mem.timestamp}] {mem.action}: {str(mem.result)[:100]}")
        return "\n".join(summary)
    
    def plan(self, user_intent: str) -> List[Dict[str, Any]]:
        """
        根据用户意图制定执行计划
        
        Args:
            user_intent: 用户意图描述
            
        Returns:
            执行计划列表
        """
        plan = []
        
        # 意图识别和任务分解
        intent_lower = user_intent.lower()
        
        if '训练' in intent_lower or 'train' in intent_lower:
            plan.append({
                'step': 1,
                'action': 'data_generation',
                'description': '生成客户数据',
                'tool': 'generate_data'
            })
            plan.append({
                'step': 2,
                'action': 'feature_engineering',
                'description': '进行特征工程',
                'tool': 'feature_engineering'
            })
            plan.append({
                'step': 3,
                'action': 'model_training',
                'description': '训练流失预测模型',
                'tool': 'train_model'
            })
            plan.append({
                'step': 4,
                'action': 'shap_analysis',
                'description': '进行模型可解释性分析',
                'tool': 'shap_analysis'
            })
        
        elif '预测' in intent_lower or 'predict' in intent_lower:
            plan.append({
                'step': 1,
                'action': 'risk_prediction',
                'description': '预测客户流失风险',
                'tool': 'predict_risk'
            })
            plan.append({
                'step': 2,
                'action': 'retention_planning',
                'description': '生成挽留计划',
                'tool': 'generate_retention_plan'
            })
        
        elif '分析' in intent_lower or 'analyze' in intent_lower:
            plan.append({
                'step': 1,
                'action': 'shap_analysis',
                'description': '进行模型可解释性分析',
                'tool': 'shap_analysis'
            })
        
        elif '报告' in intent_lower or 'report' in intent_lower:
            plan.append({
                'step': 1,
                'action': 'report_generation',
                'description': '生成分析报告',
                'tool': 'generate_report'
            })
        
        else:
            # 默认完整流程
            plan.append({
                'step': 1,
                'action': 'data_generation',
                'description': '生成客户数据',
                'tool': 'generate_data'
            })
            plan.append({
                'step': 2,
                'action': 'model_training',
                'description': '训练流失预测模型',
                'tool': 'train_model'
            })
            plan.append({
                'step': 3,
                'action': 'risk_prediction',
                'description': '预测客户流失风险',
                'tool': 'predict_risk'
            })
        
        return plan
    
    def execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行计划
        
        Args:
            plan: 执行计划
            context: 上下文信息
            
        Returns:
            执行结果
        """
        import inspect
        context = context or {}
        results = {}
        
        for step in plan:
            tool_name = step.get('tool')
            if tool_name and tool_name in self.tools:
                try:
                    # 执行工具
                    tool_func = self.tools[tool_name]['func']
                    
                    # 获取工具函数的参数签名
                    sig = inspect.signature(tool_func)
                    params = sig.parameters
                    
                    # 只传递函数实际需要的参数（排除 self）
                    func_kwargs = {}
                    for param_name, param in params.items():
                        if param_name == 'self':
                            continue
                        if param_name in context:
                            func_kwargs[param_name] = context[param_name]
                        elif param.default != inspect.Parameter.empty:
                            # 有默认值，不需要传递
                            pass
                    
                    # 调用工具函数
                    if func_kwargs:
                        step_result = tool_func(**func_kwargs)
                    else:
                        step_result = tool_func()
                    
                    # 记录记忆
                    self.add_memory(
                        action=step['action'],
                        result=step_result,
                        context=context
                    )
                    
                    # 更新上下文（只更新字典类型的结果）
                    if isinstance(step_result, dict):
                        context.update(step_result)
                    else:
                        context['result'] = step_result
                    results[step['action']] = step_result
                    
                except Exception as e:
                    error_msg = f"执行步骤 {step['step']} ({step['action']}) 时出错: {str(e)}"
                    self.add_memory(
                        action=step['action'],
                        result={'error': error_msg},
                        context=context
                    )
                    results[step['action']] = {'error': error_msg}
            else:
                error_msg = f"工具 {tool_name} 未注册"
                results[step['action']] = {'error': error_msg}
        
        return results
    
    def chat(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Agent 对话接口
        
        Args:
            user_message: 用户消息
            context: 上下文信息
            
        Returns:
            Agent 响应
        """
        context = context or {}
        
        # 制定计划
        plan = self.plan(user_message)
        
        if not plan:
            return {
                'response': '抱歉，我无法理解您的意图。请尝试使用以下命令：\n- 训练模型\n- 预测风险\n- 生成报告',
                'plan': [],
                'status': 'error'
            }
        
        # 执行计划
        results = self.execute_plan(plan, context)
        
        # 生成响应
        response = self._generate_response(user_message, plan, results)
        
        return {
            'response': response,
            'plan': plan,
            'results': results,
            'status': 'success'
        }
    
    def _generate_response(self, user_message: str, plan: List[Dict], results: Dict) -> str:
        """
        生成自然语言响应
        
        Args:
            user_message: 用户消息
            plan: 执行计划
            results: 执行结果
            
        Returns:
            响应文本
        """
        response_parts = []
        
        # 总结执行计划
        response_parts.append(f"我已经为您制定了执行计划，包含 {len(plan)} 个步骤：")
        for step in plan:
            response_parts.append(f"  {step['step']}. {step['description']}")
        
        # 总结执行结果
        response_parts.append("\n执行结果：")
        for action, result in results.items():
            if isinstance(result, dict) and 'error' in result:
                response_parts.append(f"  ❌ {action}: {result['error']}")
            else:
                response_parts.append(f"  ✅ {action}: 执行成功")
        
        return "\n".join(response_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取 Agent 状态
        
        Returns:
            Agent 状态信息
        """
        return {
            'capabilities': self.capabilities,
            'tools_count': len(self.tools),
            'memory_count': len(self.memory),
            'has_llm': self.llm_client is not None,
            'recent_memories': self.get_memory_summary(5)
        }
    
    def clear_memory(self):
        """清空记忆"""
        self.memory = []
    
    def save_memory(self, filepath: str):
        """
        保存记忆到文件
        
        Args:
            filepath: 文件路径
        """
        memory_data = [mem.to_dict() for mem in self.memory]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
    
    def load_memory(self, filepath: str):
        """
        从文件加载记忆
        
        Args:
            filepath: 文件路径
        """
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
            self.memory = [AgentMemory(**mem) for mem in memory_data]

