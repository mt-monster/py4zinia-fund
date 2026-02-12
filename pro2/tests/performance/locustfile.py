#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能测试脚本 - Locust

使用方法:
    locust -f locustfile.py --host=http://localhost:5001

命令行参数:
    --users: 并发用户数
    --spawn-rate: 用户生成速率
    --run-time: 测试运行时间
"""

from locust import HttpUser, task, between, events
import random
import json


# 测试基金代码列表
FUND_CODES = [
    '000001', '000002', '000003',   # 华夏基金
    '006373', '007721', '008706',   # 其他常见基金
    '016667', '020422', '022714',   # QDII基金
    '519196', '005550', '001270'    # 混合基金
]


class FundSearchUser(HttpUser):
    """
    基金搜索系统用户行为模拟
    
    权重分配基于实际用户使用频率:
    - Dashboard 查看: 最高频
    - 基金详情查看: 高频
    - 持仓管理: 中频
    - 回测功能: 低频
    """
    
    wait_time = between(1, 5)  # 用户操作间隔1-5秒
    
    def on_start(self):
        """用户启动时执行 - 模拟登录"""
        # 可以在这里设置用户token等
        import uuid
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    @task(10)
    def get_dashboard_stats(self):
        """获取Dashboard统计 - 最高频操作"""
        with self.client.get(
            '/api/dashboard/stats',
            catch_response=True,
            name='/api/dashboard/stats'
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    response.success()
                else:
                    response.failure("API返回失败状态")
            else:
                response.failure(f"状态码: {response.status_code}")
    
    @task(8)
    def get_profit_trend(self):
        """获取收益趋势"""
        days = random.choice([30, 90, 180])
        self.client.get(
            f'/api/dashboard/profit-trend?days={days}',
            name='/api/dashboard/profit-trend'
        )
    
    @task(8)
    def get_allocation(self):
        """获取基金类型分布"""
        self.client.get(
            '/api/dashboard/allocation',
            name='/api/dashboard/allocation'
        )
    
    @task(6)
    def get_holding_stocks(self):
        """获取持仓股票"""
        self.client.get(
            '/api/dashboard/holding-stocks',
            name='/api/dashboard/holding-stocks'
        )
    
    @task(5)
    def get_fund_detail(self):
        """获取基金详情"""
        fund_code = random.choice(FUND_CODES)
        with self.client.get(
            f'/api/fund/{fund_code}',
            catch_response=True,
            name='/api/fund/[code]'
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    response.success()
                else:
                    response.failure("基金数据获取失败")
    
    @task(3)
    def get_fund_performance(self):
        """获取基金绩效"""
        fund_code = random.choice(FUND_CODES)
        self.client.get(
            f'/api/fund/{fund_code}/performance',
            name='/api/fund/[code]/performance'
        )
    
    @task(3)
    def get_fund_history(self):
        """获取基金历史数据"""
        fund_code = random.choice(FUND_CODES)
        days = random.choice([30, 90, 180, 365])
        self.client.get(
            f'/api/fund/{fund_code}/history?days={days}',
            name='/api/fund/[code]/history'
        )
    
    @task(2)
    def get_market_index(self):
        """获取市场指数"""
        self.client.get(
            '/api/market/index',
            name='/api/market/index'
        )
    
    @task(2)
    def get_recent_activities(self):
        """获取最近活动"""
        self.client.get(
            '/api/dashboard/recent-activities',
            name='/api/dashboard/recent-activities'
        )
    
    @task(1)
    def add_and_delete_holding(self):
        """模拟添加和删除持仓（低频操作）"""
        fund_code = random.choice(FUND_CODES)
        
        # 添加持仓
        holding_data = {
            'user_id': 'default_user',
            'fund_code': fund_code,
            'fund_name': f'测试基金{fund_code}',
            'holding_shares': 1000,
            'cost_price': round(random.uniform(1.0, 2.0), 2)
        }
        
        add_response = self.client.post(
            '/api/holdings',
            json=holding_data,
            name='/api/holdings (POST)'
        )
        
        if add_response.status_code == 200:
            # 删除刚添加的持仓
            self.client.delete(
                f'/api/holdings/{fund_code}?user_id=default_user',
                name='/api/holdings/[code] (DELETE)'
            )


class HeavyLoadUser(HttpUser):
    """
    高负载测试用户
    用于压力测试，短时间内发起大量请求
    """
    
    wait_time = between(0.1, 0.5)  # 更短的间隔
    
    @task(1)
    def rapid_dashboard_requests(self):
        """快速请求Dashboard"""
        self.client.get('/api/dashboard/stats')


# 事件监听
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """
    请求事件监听
    可用于记录详细日志或发送到监控系统
    """
    # 记录慢请求（超过1秒）
    if response_time > 1000:
        print(f"[SLOW REQUEST] {name}: {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行"""
    print("=" * 60)
    print("性能测试开始")
    print(f"目标主机: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时执行"""
    print("=" * 60)
    print("性能测试结束")
    print("=" * 60)
