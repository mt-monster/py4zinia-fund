#!/usr/bin/env python
# coding: utf-8

"""
基金映射管理工具
用于管理基金名称到代码的映射关系
"""

import json
import os
from typing import Dict

class FundMappingManager:
    """基金映射管理器"""
    
    def __init__(self, mapping_file="fund_mappings.json"):
        self.mapping_file = mapping_file
        self.mappings = self.load_mappings()
    
    def load_mappings(self) -> Dict[str, str]:
        """加载映射文件"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载映射文件失败: {e}")
        
        # 返回默认映射
        return {
            "天弘标普500": "007721",
            "天弘标普500发起": "007721", 
            "景顺长城全球半导体": "501225",
            "景顺长城全球半导体芯片": "501225",
            "广发北证50": "159673",
            "广发北证50成份": "159673",
            "富国全球科技": "100055",
            "富国全球科技互联网": "100055",
            "易方达战略新兴": "010391",
            "易方达战略新兴产业": "010391",
        }
    
    def save_mappings(self):
        """保存映射到文件"""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)
            print(f"映射已保存到 {self.mapping_file}")
        except Exception as e:
            print(f"保存映射文件失败: {e}")
    
    def add_mapping(self, fund_name: str, fund_code: str):
        """添加新的映射"""
        self.mappings[fund_name] = fund_code
        print(f"添加映射: {fund_name} -> {fund_code}")
    
    def remove_mapping(self, fund_name: str):
        """删除映射"""
        if fund_name in self.mappings:
            del self.mappings[fund_name]
            print(f"删除映射: {fund_name}")
        else:
            print(f"映射不存在: {fund_name}")
    
    def search_mapping(self, keyword: str):
        """搜索映射"""
        results = []
        for name, code in self.mappings.items():
            if keyword in name or keyword in code:
                results.append((name, code))
        return results
    
    def list_all_mappings(self):
        """列出所有映射"""
        print("当前基金映射:")
        for name, code in sorted(self.mappings.items()):
            print(f"  {code} - {name}")
    
    def get_mappings(self) -> Dict[str, str]:
        """获取所有映射"""
        return self.mappings.copy()

def interactive_mapping_manager():
    """交互式映射管理"""
    manager = FundMappingManager()
    
    while True:
        print("\n=== 基金映射管理器 ===")
        print("1. 查看所有映射")
        print("2. 添加新映射")
        print("3. 删除映射")
        print("4. 搜索映射")
        print("5. 保存并退出")
        print("6. 退出不保存")
        
        choice = input("请选择操作 (1-6): ").strip()
        
        if choice == '1':
            manager.list_all_mappings()
        
        elif choice == '2':
            fund_name = input("请输入基金名称关键词: ").strip()
            fund_code = input("请输入基金代码 (6位数字): ").strip()
            
            if len(fund_code) == 6 and fund_code.isdigit():
                manager.add_mapping(fund_name, fund_code)
            else:
                print("基金代码必须是6位数字")
        
        elif choice == '3':
            fund_name = input("请输入要删除的基金名称: ").strip()
            manager.remove_mapping(fund_name)
        
        elif choice == '4':
            keyword = input("请输入搜索关键词: ").strip()
            results = manager.search_mapping(keyword)
            if results:
                print("搜索结果:")
                for name, code in results:
                    print(f"  {code} - {name}")
            else:
                print("未找到匹配的映射")
        
        elif choice == '5':
            manager.save_mappings()
            print("已保存并退出")
            break
        
        elif choice == '6':
            print("退出不保存")
            break
        
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    interactive_mapping_manager()