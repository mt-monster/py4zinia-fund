#!/usr/bin/env python
# coding: utf-8

"""
通过akshare接口反向查找基金代码
"""

import akshare as ak
import pandas as pd
import logging
import re
from typing import Optional, Dict, List
import time

logger = logging.getLogger(__name__)

class AkshareFundLookup:
    """akshare基金查找器"""
    
    def __init__(self):
        self._fund_list_cache = None
        self._cache_timestamp = None
        self._cache_duration = 3600  # 缓存1小时
    
    def get_fund_list(self) -> pd.DataFrame:
        """获取基金列表（带缓存）"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._fund_list_cache is not None and 
            self._cache_timestamp is not None and 
            current_time - self._cache_timestamp < self._cache_duration):
            return self._fund_list_cache
        
        try:
            logger.info("正在获取基金列表...")
            # 使用正确的接口获取基金基本信息
            fund_list = ak.fund_name_em()
            
            # 缓存结果
            self._fund_list_cache = fund_list
            self._cache_timestamp = current_time
            
            logger.info(f"成功获取 {len(fund_list)} 只基金信息")
            return fund_list
            
        except Exception as e:
            logger.error(f"获取基金列表失败: {e}")
            # 如果有旧缓存，返回旧缓存
            if self._fund_list_cache is not None:
                logger.warning("使用缓存的基金列表")
                return self._fund_list_cache
            return pd.DataFrame()
    
    def search_fund_by_name(self, fund_name: str, similarity_threshold: float = 0.6) -> List[Dict]:
        """
        通过基金名称搜索基金代码
        
        参数：
        fund_name: 基金名称或关键词
        similarity_threshold: 相似度阈值
        
        返回：
        list: 匹配的基金列表
        """
        fund_list = self.get_fund_list()
        
        if fund_list.empty:
            logger.warning("基金列表为空，无法进行搜索")
            return []
        
        # 清理输入的基金名称
        clean_name = self._clean_fund_name(fund_name)
        
        matches = []
        
        for _, row in fund_list.iterrows():
            try:
                db_fund_name = str(row.get('基金简称', ''))
                db_fund_code = str(row.get('基金代码', ''))
                
                # 计算相似度
                similarity = self._calculate_similarity(clean_name, db_fund_name)
                
                if similarity >= similarity_threshold:
                    matches.append({
                        'fund_code': db_fund_code,
                        'fund_name': db_fund_name,
                        'similarity': similarity,
                        'fund_type': row.get('基金类型', ''),
                        'management_company': '',  # 这个接口没有基金公司信息
                    })
            except Exception as e:
                continue
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        logger.info(f"基金名称 '{fund_name}' 找到 {len(matches)} 个匹配结果")
        return matches
    
    def find_best_match(self, fund_name: str) -> Optional[Dict]:
        """
        查找最佳匹配的基金
        
        参数：
        fund_name: 基金名称
        
        返回：
        dict: 最佳匹配的基金信息，如果没有找到返回None
        """
        matches = self.search_fund_by_name(fund_name)
        
        if matches:
            best_match = matches[0]
            logger.info(f"最佳匹配: {best_match['fund_code']} - {best_match['fund_name']} (相似度: {best_match['similarity']:.2f})")
            return best_match
        
        logger.warning(f"未找到基金: {fund_name}")
        return None
    
    def _clean_fund_name(self, name: str) -> str:
        """清理基金名称"""
        # 移除常见的后缀和标识
        name = re.sub(r'\([^)]*\)', '', name)  # 移除括号内容
        name = re.sub(r'[A-Z]$', '', name)    # 移除末尾字母
        name = re.sub(r'证券投资基金', '', name)
        name = re.sub(r'投资基金', '', name)
        name = re.sub(r'基金', '', name)
        
        # 移除多余空格
        name = ' '.join(name.split())
        return name.strip()
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个基金名称的相似度
        
        使用简单的字符串匹配算法
        """
        name1_clean = self._clean_fund_name(name1).lower()
        name2_clean = self._clean_fund_name(name2).lower()
        
        # 完全匹配
        if name1_clean == name2_clean:
            return 1.0
        
        # 包含匹配
        if name1_clean in name2_clean or name2_clean in name1_clean:
            return 0.9
        
        # 关键词匹配
        words1 = set(name1_clean.split())
        words2 = set(name2_clean.split())
        
        if not words1 or not words2:
            return 0.0
        
        # 计算交集比例
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def batch_lookup(self, fund_names: List[str]) -> Dict[str, Optional[Dict]]:
        """
        批量查找基金代码
        
        参数：
        fund_names: 基金名称列表
        
        返回：
        dict: 基金名称到基金信息的映射
        """
        results = {}
        
        for fund_name in fund_names:
            try:
                result = self.find_best_match(fund_name)
                results[fund_name] = result
                
                # 避免请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"查找基金 '{fund_name}' 时出错: {e}")
                results[fund_name] = None
        
        return results

# 全局实例
fund_lookup = AkshareFundLookup()

def lookup_fund_code(fund_name: str) -> Optional[str]:
    """
    通过基金名称查找基金代码（简化接口）
    
    参数：
    fund_name: 基金名称
    
    返回：
    str: 基金代码，如果未找到返回None
    """
    result = fund_lookup.find_best_match(fund_name)
    return result['fund_code'] if result else None

def lookup_fund_info(fund_name: str) -> Optional[Dict]:
    """
    通过基金名称查找完整基金信息（简化接口）
    
    参数：
    fund_name: 基金名称
    
    返回：
    dict: 基金信息，如果未找到返回None
    """
    return fund_lookup.find_best_match(fund_name)

if __name__ == "__main__":
    # 测试代码
    test_names = [
        "天弘标普500发起",
        "景顺长城全球半导体芯片股票",
        "广发北证50成份指数",
        "富国全球科技互联网股票",
        "易方达战略新兴产业股票"
    ]
    
    lookup = AkshareFundLookup()
    
    for name in test_names:
        result = lookup.find_best_match(name)
        if result:
            print(f"{name} -> {result['fund_code']} ({result['fund_name']})")
        else:
            print(f"{name} -> 未找到")