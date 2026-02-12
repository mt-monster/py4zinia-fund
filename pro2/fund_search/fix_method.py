#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

with open('services/fund_data_preloader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 新的方法代码
new_method = '''    def _get_user_holdings_fund_codes(self) -> List[str]:
        """
        获取用户持仓中的基金代码
        
        从数据库读取用户的持仓基金列表，优先预加载这些基金
        
        Returns:
            List[str]: 用户持仓的基金代码列表
        """
        # 尝试从数据库获取用户持仓
        try:
            from data_retrieval.enhanced_database import EnhancedDatabaseManager
            
            # 尝试连接数据库
            db_config = self._get_db_config()
            if db_config:
                db = EnhancedDatabaseManager(db_config)
                
                try:
                    # 查询 holdings 表
                    sql = """
                    SELECT DISTINCT fund_code 
                    FROM holdings 
                    WHERE user_id = 'default_user' OR user_id IS NULL
                    ORDER BY fund_code
                    """
                    
                    try:
                        result = db.execute_query(sql)
                        if not result.empty and 'fund_code' in result.columns:
                            codes = result['fund_code'].tolist()
                            # 过滤有效的基金代码
                            valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                            if valid_codes:
                                logger.info(f"从数据库获取到 {len(valid_codes)} 只用户持仓基金")
                                return valid_codes
                    except Exception as e:
                        logger.debug(f"查询 holdings 表失败: {e}")
                    
                    # 尝试 user_holdings 表
                    sql2 = """
                    SELECT DISTINCT fund_code 
                    FROM user_holdings 
                    WHERE user_id = 'default_user' OR user_id IS NULL
                    ORDER BY fund_code
                    """
                    
                    try:
                        result = db.execute_query(sql2)
                        if not result.empty and 'fund_code' in result.columns:
                            codes = result['fund_code'].tolist()
                            valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                            if valid_codes:
                                logger.info(f"从数据库获取到 {len(valid_codes)} 只用户持仓基金")
                                return valid_codes
                    except Exception as e:
                        logger.debug(f"查询 user_holdings 表失败: {e}")
                    
                finally:
                    # 确保关闭数据库连接
                    try:
                        db.close()
                    except Exception:
                        pass
                    
        except Exception as e:
            logger.debug(f"数据库查询失败: {e}")
        
        # 尝试从本地存储读取（如JSON文件）
        try:
            import json
            holdings_file = 'user_holdings.json'
            if os.path.exists(holdings_file):
                with open(holdings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        codes = [h.get('fund_code') for h in data if h.get('fund_code')]
                        valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
                        if valid_codes:
                            logger.info(f"从本地文件获取到 {len(valid_codes)} 只用户持仓基金")
                            return valid_codes
        except Exception as e:
            logger.debug(f"读取本地持仓文件失败: {e}")
        
        logger.info("未发现用户持仓基金")
        return []
'''

# 替换方法
pattern = r'def _get_user_holdings_fund_codes.*?(?=\n    def _get_db_config)'
content_new = re.sub(pattern, new_method.rstrip(), content, flags=re.DOTALL)

with open('services/fund_data_preloader.py', 'w', encoding='utf-8') as f:
    f.write(content_new)

print('Method replaced successfully')
