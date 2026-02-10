#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Repository 基类
提供通用的数据访问接口
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Union, Tuple
import pandas as pd
import logging

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """
    仓储基类
    
    提供标准化的 CRUD 操作接口
    所有具体的 Repository 应继承此类
    """
    
    def __init__(self, db_manager):
        """
        初始化 Repository
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.table_name = self._get_table_name()
    
    @abstractmethod
    def _get_table_name(self) -> str:
        """获取表名（子类必须实现）"""
        pass
    
    @abstractmethod
    def _to_entity(self, row: Dict[str, Any]) -> T:
        """将数据库行转换为实体（子类必须实现）"""
        pass
    
    def get_by_id(self, id: int) -> Optional[T]:
        """根据 ID 获取实体"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = %s"
            df = self.db.execute_query(query, (id,))
            
            if df.empty:
                return None
            
            return self._to_entity(df.iloc[0].to_dict())
            
        except Exception as e:
            self.logger.error(f"根据ID获取失败: {e}")
            return None
    
    def get_all(
        self, 
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """获取所有实体"""
        try:
            query = f"SELECT * FROM {self.table_name}"
            
            if order_by:
                query += f" ORDER BY {order_by}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            if offset:
                query += f" OFFSET {offset}"
            
            df = self.db.execute_query(query)
            
            return [self._to_entity(row.to_dict()) for _, row in df.iterrows()]
            
        except Exception as e:
            self.logger.error(f"获取所有记录失败: {e}")
            return []
    
    def create(self, data: Dict[str, Any]) -> Optional[int]:
        """
        创建记录
        
        Args:
            data: 记录数据
            
        Returns:
            新记录的 ID，失败返回 None
        """
        try:
            columns = list(data.keys())
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(columns)
            
            query = f"INSERT INTO {self.table_name} ({columns_str}) VALUES ({placeholders})"
            
            affected = self.db.execute_sql(query, tuple(data.values()))
            
            if affected > 0:
                # 获取插入的 ID
                result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
                return int(result.iloc[0]['id']) if not result.empty else None
            
            return None
            
        except Exception as e:
            self.logger.error(f"创建记录失败: {e}")
            return None
    
    def update(
        self, 
        id: int, 
        data: Dict[str, Any]
    ) -> bool:
        """
        更新记录
        
        Args:
            id: 记录 ID
            data: 更新的数据
            
        Returns:
            是否更新成功
        """
        try:
            if not data:
                return False
            
            set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
            query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = %s"
            
            params = list(data.values()) + [id]
            
            affected = self.db.execute_sql(query, tuple(params))
            
            return affected > 0
            
        except Exception as e:
            self.logger.error(f"更新记录失败: {e}")
            return False
    
    def delete(self, id: int) -> bool:
        """删除记录"""
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = %s"
            affected = self.db.execute_sql(query, (id,))
            return affected > 0
            
        except Exception as e:
            self.logger.error(f"删除记录失败: {e}")
            return False
    
    def count(self, where: Optional[str] = None, params: Optional[Tuple] = None) -> int:
        """统计记录数"""
        try:
            query = f"SELECT COUNT(*) as count FROM {self.table_name}"
            
            if where:
                query += f" WHERE {where}"
            
            df = self.db.execute_query(query, params)
            
            return int(df.iloc[0]['count']) if not df.empty else 0
            
        except Exception as e:
            self.logger.error(f"统计记录数失败: {e}")
            return 0
    
    def exists(self, id: int) -> bool:
        """检查记录是否存在"""
        return self.count("id = %s", (id,)) > 0
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> pd.DataFrame:
        """
        执行原始查询
        
        Args:
            query: SQL 查询
            params: 查询参数
            
        Returns:
            DataFrame 结果
        """
        return self.db.execute_query(query, params)
    
    def execute_sql(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        执行 SQL 语句
        
        Returns:
            影响的行数
        """
        return self.db.execute_sql(sql, params)
