#!/usr/bin/env python
# coding: utf-8

"""
手工导入工具
用于手动添加无法自动识别的基金持仓
"""

import logging
from typing import Dict, List, Optional
from ..data_retrieval.akshare_fund_lookup import lookup_fund_info
from ..data_retrieval.portfolio_importer import PortfolioImporter

logger = logging.getLogger(__name__)

class ManualImportTool:
    """手工导入工具"""
    
    def __init__(self):
        self.importer = PortfolioImporter()
    
    def validate_fund_code(self, fund_code: str, fund_name: Optional[str] = None, 
                          offline_mode: bool = False) -> Dict:
        """
        验证基金代码
        
        参数：
        fund_code: 6位基金代码
        fund_name: 基金名称（可选，离线模式下使用）
        offline_mode: 是否使用离线模式（跳过网络验证）
        
        返回：
        dict: 验证结果
        """
        if not fund_code or len(fund_code) != 6 or not fund_code.isdigit():
            return {
                'valid': False,
                'message': '基金代码必须是6位数字',
                'fund_info': None
            }
        
        # 离线模式：直接使用用户提供的基金名称，跳过网络验证
        if offline_mode:
            fund_info = {
                'fund_code': fund_code,
                'fund_name': fund_name or f'基金 {fund_code}',
                'fund_type': '',
            }
            return {
                'valid': True,
                'message': f'离线模式: 接受基金代码 {fund_code}',
                'fund_info': fund_info
            }
        
        try:
            # 通过akshare查找基金信息
            from ..data_retrieval.akshare_fund_lookup import AkshareFundLookup
            
            lookup = AkshareFundLookup()
            fund_list = lookup.get_fund_list()
            
            if fund_list.empty:
                # 网络获取失败，但如果有提供基金名称，允许离线导入
                if fund_name:
                    fund_info = {
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'fund_type': '',
                    }
                    return {
                        'valid': True,
                        'message': f'网络不可用，使用离线模式: {fund_name}',
                        'fund_info': fund_info
                    }
                return {
                    'valid': False,
                    'message': '无法获取基金列表，请检查网络连接。您也可以提供基金名称进行离线导入。',
                    'fund_info': None
                }
            
            # 查找匹配的基金代码
            matching_funds = fund_list[fund_list['基金代码'] == fund_code]
            
            if not matching_funds.empty:
                fund_row = matching_funds.iloc[0]
                fund_info = {
                    'fund_code': fund_code,
                    'fund_name': fund_row['基金简称'],
                    'fund_type': fund_row.get('基金类型', ''),
                }
                
                return {
                    'valid': True,
                    'message': f'找到基金: {fund_info["fund_name"]}',
                    'fund_info': fund_info
                }
            else:
                # 基金代码不在列表中，但如果提供了名称，允许离线导入
                if fund_name:
                    fund_info = {
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'fund_type': '',
                    }
                    return {
                        'valid': True,
                        'message': f'基金代码 {fund_code} 未在在线列表中找到，使用离线模式: {fund_name}',
                        'fund_info': fund_info
                    }
                return {
                    'valid': False,
                    'message': f'基金代码 {fund_code} 不存在',
                    'fund_info': None
                }
                
        except Exception as e:
            logger.error(f"验证基金代码时出错: {e}")
            # 发生异常时，如果提供了基金名称，允许离线导入
            if fund_name:
                fund_info = {
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'fund_type': '',
                }
                return {
                    'valid': True,
                    'message': f'验证出错，使用离线模式: {fund_name}',
                    'fund_info': fund_info
                }
            return {
                'valid': False,
                'message': f'验证失败: {e}',
                'fund_info': None
            }
    
    def manual_add_holding(self, fund_code: str, nav_value: Optional[float] = None, 
                          change_amount: Optional[float] = None, 
                          change_percent: Optional[float] = None,
                          position_value: Optional[float] = None,
                          shares: Optional[float] = None,
                          fund_name: Optional[str] = None,
                          offline_mode: bool = False,
                          user_id: str = "default") -> Dict:
        """
        手工添加持仓
        
        参数：
        fund_code: 基金代码
        nav_value: 净值
        change_amount: 涨跌金额
        change_percent: 涨跌百分比
        position_value: 持仓金额
        shares: 持有份额
        fund_name: 基金名称（可选，离线模式下使用）
        offline_mode: 是否使用离线模式（跳过网络验证）
        user_id: 用户ID
        
        返回：
        dict: 添加结果
        """
        # 验证基金代码
        validation = self.validate_fund_code(fund_code, fund_name, offline_mode)
        
        if not validation['valid']:
            return {
                'success': False,
                'message': validation['message']
            }
        
        fund_info = validation['fund_info']
        
        # 构建持仓数据
        holding_data = [{
            'fund_code': fund_code,
            'fund_name': fund_info['fund_name'],
            'fund_name_full': fund_info['fund_name'],
            'nav_value': nav_value,
            'change_amount': change_amount,
            'change_percent': change_percent,
            'position_value': position_value,
            'shares': shares,
            'confidence': 1.0,
            'source': 'manual_import'
        }]
        
        # 导入到数据库
        try:
            success = self.importer.import_to_database(holding_data, user_id)
            
            if success:
                return {
                    'success': True,
                    'message': f'成功添加持仓: {fund_code} - {fund_info["fund_name"]}',
                    'fund_info': fund_info
                }
            else:
                return {
                    'success': False,
                    'message': '导入数据库失败'
                }
                
        except Exception as e:
            logger.error(f"手工添加持仓失败: {e}")
            return {
                'success': False,
                'message': f'添加失败: {e}'
            }
    
    def batch_manual_import(self, holdings_data: List[Dict], user_id: str = "default") -> Dict:
        """
        批量手工导入
        
        参数：
        holdings_data: 持仓数据列表，每个元素包含fund_code等字段
        user_id: 用户ID
        
        返回：
        dict: 导入结果
        """
        results = []
        success_count = 0
        
        for holding in holdings_data:
            fund_code = holding.get('fund_code')
            
            if not fund_code:
                results.append({
                    'fund_code': 'N/A',
                    'success': False,
                    'message': '缺少基金代码'
                })
                continue
            
            result = self.manual_add_holding(
                fund_code=fund_code,
                nav_value=holding.get('nav_value'),
                change_amount=holding.get('change_amount'),
                change_percent=holding.get('change_percent'),
                position_value=holding.get('position_value'),
                shares=holding.get('shares'),
                user_id=user_id
            )
            
            results.append({
                'fund_code': fund_code,
                'success': result['success'],
                'message': result['message']
            })
            
            if result['success']:
                success_count += 1
        
        return {
            'success': success_count > 0,
            'total_count': len(holdings_data),
            'success_count': success_count,
            'failed_count': len(holdings_data) - success_count,
            'results': results
        }

def interactive_manual_import():
    """交互式手工导入"""
    tool = ManualImportTool()
    
    print("=== 基金持仓手工导入工具 ===")
    
    while True:
        print("\n请选择操作:")
        print("1. 添加单个基金持仓")
        print("2. 验证基金代码")
        print("3. 退出")
        print("4. 离线模式添加（无需网络验证）")
        
        choice = input("请输入选择 (1-4): ").strip()
        
        offline_mode = (choice == '4')
        
        if choice in ('1', '4'):
            # 添加单个基金持仓
            fund_code = input("请输入基金代码 (6位数字): ").strip()
            
            if not fund_code:
                print("基金代码不能为空")
                continue
            
            fund_name = None
            if offline_mode:
                fund_name = input("请输入基金名称: ").strip()
                if not fund_name:
                    print("离线模式下基金名称不能为空")
                    continue
            
            # 验证基金代码
            validation = tool.validate_fund_code(fund_code, fund_name, offline_mode)
            
            if not validation['valid']:
                print(f"验证失败: {validation['message']}")
                # 提示用户可以重试或使用离线模式
                if not offline_mode:
                    print("提示: 如果网络连接有问题，请选择选项4使用离线模式导入")
                continue
            
            print(f"找到基金: {validation['fund_info']['fund_name']}")
            
            # 输入其他信息
            try:
                nav_value = input("请输入净值 (可选，直接回车跳过): ").strip()
                nav_value = float(nav_value) if nav_value else None
                
                change_amount = input("请输入涨跌金额 (可选): ").strip()
                change_amount = float(change_amount) if change_amount else None
                
                change_percent = input("请输入涨跌百分比 (可选): ").strip()
                change_percent = float(change_percent) if change_percent else None
                
                position_value = input("请输入持仓金额 (可选): ").strip()
                position_value = float(position_value) if position_value else None
                
                shares = input("请输入持有份额 (可选): ").strip()
                shares = float(shares) if shares else None
                
                user_id = input("请输入用户ID (默认: default): ").strip()
                user_id = user_id if user_id else "default"
                
            except ValueError:
                print("输入格式错误，请输入有效的数字")
                continue
            
            # 添加持仓
            result = tool.manual_add_holding(
                fund_code=fund_code,
                nav_value=nav_value,
                change_amount=change_amount,
                change_percent=change_percent,
                position_value=position_value,
                shares=shares,
                fund_name=fund_name,
                offline_mode=offline_mode,
                user_id=user_id
            )
            
            if result['success']:
                print(f"✓ {result['message']}")
            else:
                print(f"✗ {result['message']}")
        
        elif choice == '2':
            # 验证基金代码
            fund_code = input("请输入基金代码 (6位数字): ").strip()
            
            validation = tool.validate_fund_code(fund_code)
            
            if validation['valid']:
                fund_info = validation['fund_info']
                print(f"✓ 基金代码有效")
                print(f"  代码: {fund_info['fund_code']}")
                print(f"  名称: {fund_info['fund_name']}")
                print(f"  类型: {fund_info['fund_type']}")
            else:
                print(f"✗ {validation['message']}")
        
        elif choice == '3':
            print("退出手工导入工具")
            break
        
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    interactive_manual_import()