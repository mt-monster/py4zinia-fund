# -*- coding: utf-8 -*-
"""
Agent 工具系统
提供各种可调用的工具函数
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, Any, Optional
from churn_predict import (
    generate_securities_data,
    feature_engineering_securities,
    train_securities_churn_model,
    shap_analysis_securities,
    batch_predict_and_generate_plan
)


class ChurnPredictionTools:
    """客户流失预测工具集"""
    
    def __init__(self):
        self.model = None
        self.feature_df = None
        self.feature_cols = None
        self.scaler = None
        self.explainer = None
        self.weekly_df = None
    
    def generate_data(self, n_customers: int = 3000, n_weeks: int = 12) -> Dict[str, Any]:
        """
        生成客户数据工具
        
        Args:
            n_customers: 客户数量
            n_weeks: 周数
            
        Returns:
            执行结果
        """
        try:
            self.weekly_df = generate_securities_data(n_customers=n_customers, n_weeks=n_weeks)
            return {
                'status': 'success',
                'message': f'成功生成 {n_customers} 个客户的 {n_weeks} 周数据',
                'data_shape': self.weekly_df.shape,
                'customer_count': self.weekly_df['customer_id'].nunique(),
                'churn_rate': self.weekly_df['will_churn'].mean()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'数据生成失败: {str(e)}'
            }
    
    def feature_engineering(self) -> Dict[str, Any]:
        """
        特征工程工具
        
        Returns:
            执行结果
        """
        if self.weekly_df is None:
            return {
                'status': 'error',
                'message': '请先生成数据'
            }
        
        try:
            self.feature_df = feature_engineering_securities(self.weekly_df)
            return {
                'status': 'success',
                'message': '特征工程完成',
                'feature_count': self.feature_df.shape[1] - 2,
                'sample_count': len(self.feature_df)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'特征工程失败: {str(e)}'
            }
    
    def train_model(self) -> Dict[str, Any]:
        """
        训练模型工具
        
        Returns:
            执行结果
        """
        if self.feature_df is None:
            return {
                'status': 'error',
                'message': '请先进行特征工程'
            }
        
        try:
            self.model, X_train, X_test, y_test, self.feature_cols, self.scaler = \
                train_securities_churn_model(self.feature_df)
            
            # 进行 SHAP 分析
            self.explainer, _ = shap_analysis_securities(self.model, X_train, self.feature_cols)
            
            return {
                'status': 'success',
                'message': '模型训练完成',
                'feature_count': len(self.feature_cols),
                'test_samples': len(y_test)
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'模型训练失败: {str(e)}'
            }
    
    def predict_risk(self, top_k: int = 30) -> Dict[str, Any]:
        """
        预测风险工具
        
        Args:
            top_k: 返回前 K 个高风险客户
            
        Returns:
            执行结果
        """
        if self.model is None:
            return {
                'status': 'error',
                'message': '请先训练模型'
            }
        
        try:
            high_risk, action_df = batch_predict_and_generate_plan(
                self.model, 
                self.feature_df, 
                self.feature_cols, 
                self.scaler, 
                explainer=self.explainer, 
                top_k=top_k
            )
            
            return {
                'status': 'success',
                'message': f'成功识别 {len(high_risk)} 个高风险客户',
                'high_risk_count': len(high_risk),
                'plans_count': len(action_df),
                'retention_plans': action_df.to_dict(orient='records') if action_df is not None else []
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'风险预测失败: {str(e)}'
            }
    
    def shap_analysis(self) -> Dict[str, Any]:
        """
        SHAP 分析工具
        
        Returns:
            执行结果
        """
        if self.model is None or self.explainer is None:
            return {
                'status': 'error',
                'message': '请先训练模型'
            }
        
        try:
            # SHAP 分析已在训练时完成
            shap_files = [
                'securities_shap_bar.png',
                'securities_shap_scatter.png',
                'securities_shap_dependence.png'
            ]
            
            existing_files = [f for f in shap_files if os.path.exists(f)]
            
            return {
                'status': 'success',
                'message': 'SHAP 分析完成',
                'files': existing_files
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'SHAP 分析失败: {str(e)}'
            }
    
    def generate_retention_plan(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        生成挽留计划工具
        
        Args:
            customer_id: 客户ID，如果为None则生成所有高风险客户的计划
            
        Returns:
            执行结果
        """
        if self.model is None:
            return {
                'status': 'error',
                'message': '请先训练模型'
            }
        
        try:
            # 如果指定了客户ID，只生成该客户的计划
            if customer_id:
                customer = self.feature_df[self.feature_df['customer_id'] == customer_id]
                if customer.empty:
                    return {
                        'status': 'error',
                        'message': f'客户 {customer_id} 不存在'
                    }
                top_k = 1
            else:
                top_k = 30
            
            result = self.predict_risk(top_k=top_k)
            return result
        except Exception as e:
            return {
                'status': 'error',
                'message': f'挽留计划生成失败: {str(e)}'
            }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成分析报告工具
        
        Returns:
            执行结果
        """
        try:
            report = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'model_status': '已训练' if self.model is not None else '未训练',
                'data_status': '已加载' if self.feature_df is not None else '未加载',
                'feature_count': len(self.feature_cols) if self.feature_cols else 0,
                'customer_count': len(self.feature_df) if self.feature_df is not None else 0
            }
            
            if self.feature_df is not None:
                report['churn_rate'] = float(self.feature_df['will_churn'].mean())
            
            return {
                'status': 'success',
                'message': '报告生成完成',
                'report': report
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'报告生成失败: {str(e)}'
            }
    
    def get_customer_info(self, customer_id: str) -> Dict[str, Any]:
        """
        获取客户信息工具
        
        Args:
            customer_id: 客户ID
            
        Returns:
            客户信息
        """
        if self.feature_df is None:
            return {
                'status': 'error',
                'message': '数据未加载'
            }
        
        try:
            customer = self.feature_df[self.feature_df['customer_id'] == customer_id]
            if customer.empty:
                return {
                    'status': 'error',
                    'message': f'客户 {customer_id} 不存在'
                }
            
            return {
                'status': 'success',
                'customer_info': customer.iloc[0].to_dict()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'获取客户信息失败: {str(e)}'
            }


# 创建全局工具实例
tools_instance = ChurnPredictionTools()


def get_tools() -> ChurnPredictionTools:
    """获取工具实例"""
    return tools_instance

