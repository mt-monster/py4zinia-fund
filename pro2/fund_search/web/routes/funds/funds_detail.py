#!/usr/bin/env python
# coding: utf-8

"""
基金详情 API 路由
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from flask import jsonify

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.json_utils import safe_jsonify
from shared.exceptions import FundNotFoundError

logger = logging.getLogger(__name__)

db_manager = None
fund_data_manager = None


def init_components(**kwargs):
    """初始化组件"""
    global db_manager, fund_data_manager
    db_manager = kwargs.get('db_manager')
    fund_data_manager = kwargs.get('fund_data_manager')


def register_funds_detail_routes(app, **kwargs):
    """注册基金详情路由"""
    init_components(**kwargs)
    
    @app.route('/api/fund/<fund_code>', methods=['GET'])
    def get_fund_detail(fund_code):
        """获取单个基金详情（实时数据）"""
        try:
            try:
                fund_data = fund_data_manager.get_realtime_data(fund_code)
                if fund_data:
                    real_fund_name = fund_code
                    try:
                        import akshare as ak
                        fund_list = ak.fund_name_em()
                        fund_info = fund_list[fund_list['基金代码'] == fund_code]
                        if not fund_info.empty:
                            real_fund_name = fund_info.iloc[0]['基金简称']
                    except Exception as e:
                        logger.warning(f"获取基金 {fund_code} 真实名称失败: {e}")
                    
                    hist_data = fund_data_manager.get_historical_data(fund_code, days=10)
                    if hist_data is not None and not hist_data.empty:
                        if len(hist_data) >= 2:
                            prev_return = 0.0
                            try:
                                return_result = fund_data_manager._get_yesterday_return(fund_code)
                                prev_return = return_result.get('value', 0.0) if isinstance(return_result, dict) else return_result
                            except Exception as e:
                                logger.warning(f"基金 {fund_code} 内置方法获取prev_day_return失败: {e}")
                            
                            for i in range(len(hist_data) - 2, -1, -1):
                                data_row = hist_data.iloc[i]
                                return_raw = data_row.get('daily_growth_rate', None)
                                
                                if pd.notna(return_raw):
                                    return_value = float(return_raw)
                                    if abs(return_value) < 0.1:
                                        return_value = return_value * 100
                                    return_value = round(return_value, 2)
                                    
                                    if return_value != 0.0:
                                        prev_return = return_value
                                        break
                            
                            fund_data['prev_day_return'] = prev_return
                        
                        fund = {
                            'fund_code': fund_code,
                            'fund_name': real_fund_name,
                            'today_return': round(float(fund_data.get('today_return', 0)), 2),
                            'prev_day_return': round(float(fund_data.get('prev_day_return', 0)), 2),
                            'current_estimate': fund_data.get('current_nav'),
                            'yesterday_nav': fund_data.get('previous_nav'),
                            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                            'data_source': fund_data.get('data_source', 'unknown')
                        }
                        
                        return safe_jsonify({'success': True, 'data': fund})
            except Exception as e:
                logger.warning(f"获取实时数据失败: {str(e)}, 使用缓存数据")
            
            sql = "SELECT * FROM fund_analysis_results WHERE fund_code = :fund_code ORDER BY analysis_date DESC LIMIT 1"
            df = db_manager.execute_query(sql, {'fund_code': fund_code})
            
            if df.empty:
                raise FundNotFoundError(fund_code)
            
            fund = df.iloc[0].to_dict()
            
            for key in fund:
                if pd.isna(fund[key]):
                    fund[key] = None
            
            for key in ['annualized_return', 'max_drawdown', 'volatility', 'win_rate']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]) * 100, 2)
            
            for key in ['today_return', 'prev_day_return']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 2)
            
            for key in ['sharpe_ratio', 'calmar_ratio', 'sortino_ratio', 'var_95', 'profit_loss_ratio', 'composite_score']:
                if fund.get(key) is not None:
                    fund[key] = round(float(fund[key]), 4)
            
            return safe_jsonify({'success': True, 'data': fund})
            
        except FundNotFoundError as e:
            return jsonify(e.to_dict()), e.http_status
        except Exception as e:
            logger.error(f"获取基金详情失败: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    logger.info("基金详情路由已注册")
