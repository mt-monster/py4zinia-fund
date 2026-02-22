#!/usr/bin/env python
# coding: utf-8
"""
统一数据库访问层
提供标准化的数据库操作接口和分页查询功能
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from contextlib import contextmanager
from dataclasses import dataclass
import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class PaginationParams:
    """分页参数"""
    page: int = 1
    page_size: int = 20
    max_page_size: int = 100


@dataclass
class QueryResult:
    """查询结果"""
    data: List[Dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class DatabaseAccessException(Exception):
    """数据库访问异常"""
    pass


class DatabaseAccessor:
    """数据库访问器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = None
        try:
            conn = self.db_manager.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseAccessException(f"数据库操作失败: {str(e)}") from e
        finally:
            if conn:
                conn.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Union[Tuple, Dict]] = None,
        return_dataframe: bool = False
    ) -> Union[List[Dict], pd.DataFrame]:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            return_dataframe: 是否返回DataFrame格式
            
        Returns:
            查询结果
        """
        try:
            if return_dataframe:
                return self.db_manager.execute_query(query, params)
            else:
                df = self.db_manager.execute_query(query, params)
                return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"查询执行失败: {query}, 参数: {params}")
            raise DatabaseAccessException(f"查询执行失败: {str(e)}") from e
    
    def execute_update(self, query: str, params: Optional[Union[Tuple, Dict]] = None) -> int:
        """
        执行更新语句
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        try:
            return self.db_manager.execute_sql(query, params)
        except Exception as e:
            logger.error(f"更新执行失败: {query}, 参数: {params}")
            raise DatabaseAccessException(f"更新执行失败: {str(e)}") from e
    
    def paginated_query(
        self,
        base_query: str,
        count_query: str,
        params: Optional[Union[Tuple, Dict]] = None,
        pagination: Optional[PaginationParams] = None
    ) -> QueryResult:
        """
        分页查询
        
        Args:
            base_query: 基础查询语句
            count_query: 计数查询语句
            params: 查询参数
            pagination: 分页参数
            
        Returns:
            QueryResult: 分页查询结果
        """
        if pagination is None:
            pagination = PaginationParams()
        
        # 限制页面大小
        page_size = min(pagination.page_size, pagination.max_page_size)
        offset = (pagination.page - 1) * page_size
        
        # 构造分页查询
        paginated_query = f"{base_query} LIMIT %s OFFSET %s"
        paginated_params = list(params) if params else []
        paginated_params.extend([page_size, offset])
        
        try:
            # 执行分页查询
            data = self.execute_query(paginated_query, tuple(paginated_params))
            
            # 执行计数查询
            total_count = 0
            if count_query:
                count_result = self.execute_query(count_query, params)
                if count_result:
                    total_count = list(count_result[0].values())[0]
            
            # 计算总页数
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            
            return QueryResult(
                data=data,
                total_count=total_count,
                page=pagination.page,
                page_size=page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"分页查询失败: {base_query}")
            raise DatabaseAccessException(f"分页查询失败: {str(e)}") from e
    
    def insert_record(self, table: str, data: Dict[str, Any]) -> int:
        """
        插入记录
        
        Args:
            table: 表名
            data: 要插入的数据
            
        Returns:
            插入记录的ID
        """
        if not data:
            raise DatabaseAccessException("插入数据不能为空")
        
        columns = list(data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        params = tuple(data.values())
        
        try:
            affected_rows = self.execute_update(query, params)
            if affected_rows > 0:
                # 获取插入的ID
                last_id_result = self.execute_query("SELECT LAST_INSERT_ID() as id")
                return last_id_result[0]['id'] if last_id_result else 0
            return 0
        except Exception as e:
            logger.error(f"插入记录失败: {table}")
            raise DatabaseAccessException(f"插入记录失败: {str(e)}") from e
    
    def update_record(
        self, 
        table: str, 
        data: Dict[str, Any], 
        condition: str, 
        condition_params: Union[Tuple, Dict]
    ) -> int:
        """
        更新记录
        
        Args:
            table: 表名
            data: 要更新的数据
            condition: 更新条件
            condition_params: 条件参数
            
        Returns:
            影响的行数
        """
        if not data:
            raise DatabaseAccessException("更新数据不能为空")
        
        # 构造SET子句
        set_clause = ', '.join([f"{col} = %s" for col in data.keys()])
        set_params = list(data.values())
        
        # 合并参数
        if isinstance(condition_params, dict):
            all_params = set_params + list(condition_params.values())
        else:
            all_params = set_params + list(condition_params)
        
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        
        try:
            return self.execute_update(query, tuple(all_params))
        except Exception as e:
            logger.error(f"更新记录失败: {table}")
            raise DatabaseAccessException(f"更新记录失败: {str(e)}") from e
    
    def delete_record(self, table: str, condition: str, condition_params: Union[Tuple, Dict]) -> int:
        """
        删除记录
        
        Args:
            table: 表名
            condition: 删除条件
            condition_params: 条件参数
            
        Returns:
            影响的行数
        """
        query = f"DELETE FROM {table} WHERE {condition}"
        
        try:
            return self.execute_update(query, condition_params)
        except Exception as e:
            logger.error(f"删除记录失败: {table}")
            raise DatabaseAccessException(f"删除记录失败: {str(e)}") from e
    
    def get_record_by_id(self, table: str, record_id: int, id_column: str = 'id') -> Optional[Dict[str, Any]]:
        """
        根据ID获取记录
        
        Args:
            table: 表名
            record_id: 记录ID
            id_column: ID列名
            
        Returns:
            记录数据或None
        """
        query = f"SELECT * FROM {table} WHERE {id_column} = %s"
        
        try:
            result = self.execute_query(query, (record_id,))
            return result[0] if result else None
        except Exception as e:
            logger.error(f"根据ID获取记录失败: {table}")
            raise DatabaseAccessException(f"获取记录失败: {str(e)}") from e
    
    def bulk_insert(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """
        批量插入记录
        
        Args:
            table: 表名
            data_list: 要插入的数据列表
            
        Returns:
            插入的记录数
        """
        if not data_list:
            return 0
        
        # 获取列名（假设所有字典有相同的键）
        columns = list(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)
        
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        try:
            inserted_count = 0
            for data in data_list:
                params = tuple(data[col] for col in columns)
                affected = self.execute_update(query, params)
                inserted_count += affected
            
            return inserted_count
        except Exception as e:
            logger.error(f"批量插入失败: {table}")
            raise DatabaseAccessException(f"批量插入失败: {str(e)}") from e


class FundDataAccessor(DatabaseAccessor):
    """基金数据专用访问器"""
    
    def get_fund_analysis_results(
        self, 
        user_id: str = 'default_user',
        pagination: Optional[PaginationParams] = None
    ) -> QueryResult:
        """获取基金分析结果"""
        base_query = """
            SELECT * FROM fund_analysis_results 
            WHERE user_id = %s 
            ORDER BY analysis_date DESC
        """
        count_query = """
            SELECT COUNT(*) as total FROM fund_analysis_results 
            WHERE user_id = %s
        """
        
        return self.paginated_query(
            base_query, 
            count_query, 
            (user_id,), 
            pagination
        )
    
    def get_user_holdings(self, user_id: str = 'default_user') -> List[Dict[str, Any]]:
        """获取用户持仓"""
        query = """
            SELECT * FROM user_holdings 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """
        return self.execute_query(query, (user_id,))
    
    def get_fund_basic_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """获取基金基本信息"""
        query = "SELECT * FROM fund_basic_info WHERE fund_code = %s"
        result = self.execute_query(query, (fund_code,))
        return result[0] if result else None


# 创建全局访问器实例的工厂函数
def create_database_accessor(db_manager=None) -> DatabaseAccessor:
    """
    创建数据库访问器
    
    Args:
        db_manager: 数据库管理器实例，如果为None则自动创建
        
    Returns:
        DatabaseAccessor: 数据库访问器实例
    """
    if db_manager is None:
        # 自动创建 EnhancedDatabaseManager
        from data_access.enhanced_database import EnhancedDatabaseManager
        from shared.enhanced_config import DATABASE_CONFIG
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
    
    return DatabaseAccessor(db_manager)


def create_fund_data_accessor(db_manager=None) -> FundDataAccessor:
    """
    创建基金数据访问器
    
    Args:
        db_manager: 数据库管理器实例，如果为None则自动创建
        
    Returns:
        FundDataAccessor: 基金数据访问器实例
    """
    if db_manager is None:
        # 自动创建 EnhancedDatabaseManager
        from data_access.enhanced_database import EnhancedDatabaseManager
        from shared.enhanced_config import DATABASE_CONFIG
        db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
    
    return FundDataAccessor(db_manager)


# 便捷函数：直接执行查询
def execute_query(query: str, params=None, return_dataframe: bool = False):
    """
    直接执行查询（便捷函数）
    
    Args:
        query: SQL查询语句
        params: 查询参数
        return_dataframe: 是否返回DataFrame
        
    Returns:
        查询结果
    """
    accessor = create_database_accessor()
    return accessor.execute_query(query, params, return_dataframe)


# 便捷函数：直接执行更新
def execute_update(query: str, params=None) -> int:
    """
    直接执行更新（便捷函数）
    
    Args:
        query: SQL更新语句
        params: 更新参数
        
    Returns:
        影响的行数
    """
    accessor = create_database_accessor()
    return accessor.execute_update(query, params)