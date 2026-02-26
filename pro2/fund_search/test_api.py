#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试API端点
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.app_new import app

def test_endpoints():
    client = app.test_client()
    
    print("="*60)
    print("  API端点测试")
    print("="*60)
    
    # Test 1: Health
    print("\n[1] Health Check:")
    resp = client.get('/api/health')
    print(f"    Status: {resp.status_code}")
    print(f"    Response: {resp.get_json()}")
    
    # Test 2: Modules
    print("\n[2] Modules Status:")
    resp = client.get('/api/modules')
    data = resp.get_json()
    for name, info in data['data'].items():
        status = 'OK' if info['status'] else 'FAIL'
        print(f"    [{status}] {name}")
    
    # Test 3: Enhancements
    print("\n[3] Architecture Improvements:")
    resp = client.get('/api/enhancements')
    data = resp.get_json()
    for name, detail in data['data'].items():
        print(f"    - {detail['name']}")
        print(f"      Files: {len(detail['files'])}")
        print(f"      Features: {', '.join(detail['features'][:2])}...")
    
    # Test 4: Celery Test
    print("\n[4] Celery Test:")
    resp = client.get('/api/test/celery')
    data = resp.get_json()
    print(f"    Available: {data.get('available', False)}")
    if 'tasks' in data:
        print(f"    Tasks: {len(data['tasks'])}")
    
    # Test 5: Messaging Test
    print("\n[5] Messaging Test:")
    resp = client.get('/api/test/messaging')
    data = resp.get_json()
    print(f"    Available: {data.get('available', False)}")
    if data.get('available'):
        print(f"    Connected: {data.get('event_bus_connected', False)}")
    
    # Test 6: Microservices Test
    print("\n[6] Microservices Test:")
    resp = client.get('/api/test/microservices')
    data = resp.get_json()
    print(f"    Available: {data.get('available', False)}")
    if data.get('task_created'):
        print(f"    Task ID: {data['task_created']['task_id'][:8]}...")
    
    # Test 7: GraphQL Test
    print("\n[7] GraphQL Test:")
    resp = client.get('/api/test/graphql')
    data = resp.get_json()
    print(f"    Available: {data.get('available', False)}")
    if data.get('available'):
        print(f"    Types: {len(data.get('types', []))}")
        print(f"    Queries: {len(data.get('queries', []))}")
    
    print("\n" + "="*60)
    print("  所有端点测试完成!")
    print("="*60)

if __name__ == '__main__':
    test_endpoints()
