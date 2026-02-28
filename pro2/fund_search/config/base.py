#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一配置管理 - 基础模块
提供配置加载、验证、合并的基础功能
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Union
from dataclasses import dataclass, field, asdict, fields
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseConfig')


class Environment(Enum):
    """运行环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    DOCKER = "docker"


@dataclass
class BaseConfig:
    """
    配置基类
    
    所有配置类都应继承此类，提供统一的配置管理功能：
    - 从字典加载
    - 从环境变量加载
    - 验证配置
    - 转换为字典
    """
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """从字典创建配置实例"""
        if not data:
            return cls()
        
        # 获取类定义的所有字段
        valid_fields = {f.name for f in fields(cls)}
        
        # 过滤掉无效的字段
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    @classmethod
    def from_env(cls: Type[T], prefix: str = "") -> T:
        """从环境变量创建配置实例"""
        env_data = {}
        
        for f in fields(cls):
            env_key = f"{prefix}_{f.name.upper()}" if prefix else f.name.upper()
            value = os.getenv(env_key)
            
            if value is not None:
                # 根据字段类型转换值
                if f.type == bool:
                    env_data[f.name] = value.lower() in ('true', '1', 'yes', 'on')
                elif f.type == int:
                    env_data[f.name] = int(value)
                elif f.type == float:
                    env_data[f.name] = float(value)
                else:
                    env_data[f.name] = value
        
        return cls.from_dict(env_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        验证配置有效性
        
        Returns:
            (是否有效, 错误信息列表)
        """
        return True, []
    
    def merge(self: T, other: Union[T, Dict[str, Any]]) -> T:
        """合并另一个配置"""
        if isinstance(other, BaseConfig):
            other = other.to_dict()
        
        current = self.to_dict()
        current.update(other)
        return self.__class__.from_dict(current)


class ConfigLoader:
    """配置加载器 - 支持 YAML/JSON/环境变量"""
    
    @staticmethod
    def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
        """加载 YAML 配置文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"配置文件不存在: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                logger.debug(f"成功加载 YAML 配置: {file_path}")
                return content or {}
        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误 {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            return {}
    
    @staticmethod
    def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
        """加载 JSON 配置文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"配置文件不存在: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                logger.debug(f"成功加载 JSON 配置: {file_path}")
                return content
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误 {file_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            return {}
    
    @staticmethod
    def load_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """根据文件扩展名自动选择加载器"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() in ('.yaml', '.yml'):
            return ConfigLoader.load_yaml(file_path)
        elif file_path.suffix.lower() == '.json':
            return ConfigLoader.load_json(file_path)
        else:
            logger.warning(f"不支持的配置文件格式: {file_path.suffix}")
            return {}
    
    @staticmethod
    def load_directory(dir_path: Union[str, Path]) -> Dict[str, Any]:
        """加载目录下的所有配置文件"""
        dir_path = Path(dir_path)
        
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning(f"配置目录不存在: {dir_path}")
            return {}
        
        merged_config = {}
        
        # 按文件名排序，确保加载顺序一致
        config_files = sorted(dir_path.glob("*.yaml")) + sorted(dir_path.glob("*.yml")) + sorted(dir_path.glob("*.json"))
        
        for config_file in config_files:
            config_name = config_file.stem
            config_data = ConfigLoader.load_file(config_file)
            
            if config_data:
                merged_config[config_name] = config_data
                logger.debug(f"已加载配置: {config_name}")
        
        return merged_config


def get_project_root() -> Path:
    """获取项目根目录"""
    # 从当前文件向上查找，直到找到 fund_search 目录
    current = Path(__file__).resolve().parent
    
    # 返回 fund_search 的父目录（项目根目录）
    while current.name != 'fund_search' and current.parent != current:
        current = current.parent
    
    return current


def get_config_dir() -> Path:
    """获取配置目录"""
    return Path(__file__).resolve().parent


def detect_environment() -> Environment:
    """检测当前运行环境"""
    env_str = os.getenv('FUND_ENV', 'development').lower()
    
    try:
        return Environment(env_str)
    except ValueError:
        return Environment.DEVELOPMENT


# 便捷函数
def load_config(config_name: str) -> Dict[str, Any]:
    """加载指定名称的配置文件"""
    config_dir = get_config_dir()
    
    # 尝试加载 YAML 文件
    yaml_file = config_dir / f"{config_name}.yaml"
    if yaml_file.exists():
        return ConfigLoader.load_yaml(yaml_file)
    
    # 尝试加载 JSON 文件
    json_file = config_dir / f"{config_name}.json"
    if json_file.exists():
        return ConfigLoader.load_json(json_file)
    
    logger.warning(f"未找到配置文件: {config_name}")
    return {}


__all__ = [
    'BaseConfig',
    'ConfigLoader',
    'Environment',
    'detect_environment',
    'get_project_root',
    'get_config_dir',
    'load_config',
]
