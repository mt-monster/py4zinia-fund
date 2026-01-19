#!/usr/bin/env python
# coding: utf-8

"""
增强版数据库管理模块
提供基金数据的存储、查询和管理功能
"""

import pandas as pd
import numpy as np
import pymysql
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedDatabaseManager:
    """增强版数据库管理类"""
    
    def __init__(self, db_config: Dict):
        """
        初始化数据库管理器
        
        参数：
        db_config: 数据库配置字典
        """
        self.db_config = db_config
        self.engine = self._create_engine()
        self._init_database()
    
    def _create_engine(self) -> object:
        """
        创建数据库引擎
        
        返回：
        数据库引擎对象
        """
        try:
            # 先连接到MySQL服务器（不指定数据库）
            connection_string_no_db = (
                f"mysql+pymysql://{self.db_config['user']}:{self.db_config['password']}"
                f"@{self.db_config['host']}:{self.db_config['port']}"
                f"?charset={self.db_config['charset']}"
            )
            
            # 创建临时引擎连接到服务器
            temp_engine = create_engine(connection_string_no_db, echo=False)
            
            # 检查并创建数据库
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']} DEFAULT CHARACTER SET {self.db_config['charset']}"))
                conn.commit()
                logger.info(f"数据库 {self.db_config['database']} 检查/创建成功")
            
            # 关闭临时引擎
            temp_engine.dispose()
            
            # 创建最终引擎（指定数据库）
            connection_string = (
                f"mysql+pymysql://{self.db_config['user']}:{self.db_config['password']}"
                f"@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
                f"?charset={self.db_config['charset']}"
            )
            
            engine = create_engine(connection_string, echo=False)
            logger.info("数据库引擎创建成功")
            return engine
        except Exception as e:
            logger.error(f"创建数据库引擎失败: {str(e)}")
            raise
    
    def _init_database(self):
        """
        初始化数据库表结构
        """
        try:
            # 创建基金基本信息表
            self._create_fund_basic_info_table()
            
            # 创建基金绩效数据表
            self._create_fund_performance_table()
            
            # 创建基金分析结果表
            self._create_fund_analysis_results_table()
            
            # 创建基金分析汇总表
            self._create_analysis_summary_table()
            
            # 创建用户持仓表
            self._create_user_holdings_table()
            
            # 创建用户策略表
            self._create_user_strategies_table()
            
            # 创建策略回测结果表
            self._create_strategy_backtest_results_table()
            
            logger.info("数据库表结构初始化完成")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def _create_fund_basic_info_table(self):
        """创建基金基本信息表"""
        sql = """
        CREATE TABLE IF NOT EXISTS fund_basic_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fund_code VARCHAR(10) NOT NULL UNIQUE,
            fund_name VARCHAR(100) NOT NULL,
            fund_type VARCHAR(50),
            fund_company VARCHAR(100),
            fund_manager VARCHAR(100),
            establish_date DATE,
            management_fee DECIMAL(5,4),
            custody_fee DECIMAL(5,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_fund_code (fund_code),
            INDEX idx_fund_type (fund_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)
    
    def _create_fund_performance_table(self):
        """创建基金绩效数据表"""
        sql = """
        CREATE TABLE IF NOT EXISTS fund_performance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fund_code VARCHAR(10) NOT NULL,
            analysis_date DATE NOT NULL,
            current_nav DECIMAL(10,4),
            previous_nav DECIMAL(10,4),
            daily_return DECIMAL(8,4),
            nav_date DATE,
            annualized_return DECIMAL(8,4),
            sharpe_ratio DECIMAL(8,4),
            max_drawdown DECIMAL(8,4),
            volatility DECIMAL(8,4),
            calmar_ratio DECIMAL(8,4),
            sortino_ratio DECIMAL(8,4),
            var_95 DECIMAL(8,4),
            win_rate DECIMAL(5,4),
            profit_loss_ratio DECIMAL(8,4),
            composite_score DECIMAL(5,4),
            total_return DECIMAL(8,4),
            data_days INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_fund_code (fund_code),
            INDEX idx_analysis_date (analysis_date),
            UNIQUE KEY uk_fund_date (fund_code, analysis_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)
    

    
    def _create_analysis_summary_table(self):
        """创建分析汇总表"""
        sql = """
        CREATE TABLE IF NOT EXISTS analysis_summary (
            id INT AUTO_INCREMENT PRIMARY KEY,
            analysis_date DATE NOT NULL UNIQUE,
            total_funds INT,
            buy_signals INT,
            sell_signals INT,
            hold_signals INT,
            avg_buy_multiplier DECIMAL(5,2),
            total_redeem_amount INT,
            best_performing_fund VARCHAR(10),
            worst_performing_fund VARCHAR(10),
            highest_sharpe_fund VARCHAR(10),
            lowest_volatility_fund VARCHAR(10),
            report_files JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_analysis_date (analysis_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)
    

    def _create_fund_analysis_results_table(self):
        """创建基金分析结果表"""
        sql = """
        CREATE TABLE IF NOT EXISTS fund_analysis_results (
            fund_code VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
            fund_name VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
            yesterday_nav FLOAT DEFAULT NULL,
            current_estimate FLOAT DEFAULT NULL,
            today_return FLOAT DEFAULT NULL,
            yesterday_return FLOAT DEFAULT NULL,
            prev_day_return FLOAT DEFAULT NULL,
            status_label VARCHAR(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
            is_buy TINYINT(1) DEFAULT NULL,
            redeem_amount DECIMAL(10,2) DEFAULT NULL,
            comparison_value FLOAT DEFAULT NULL,
            operation_suggestion VARCHAR(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
            execution_amount VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
            analysis_date DATE DEFAULT NULL,
            buy_multiplier FLOAT DEFAULT NULL,
            annualized_return FLOAT DEFAULT NULL,
            sharpe_ratio FLOAT DEFAULT NULL,
            sharpe_ratio_ytd FLOAT DEFAULT NULL,
            sharpe_ratio_1y FLOAT DEFAULT NULL,
            sharpe_ratio_all FLOAT DEFAULT NULL,
            max_drawdown FLOAT DEFAULT NULL,
            volatility FLOAT DEFAULT NULL,
            calmar_ratio FLOAT DEFAULT NULL,
            sortino_ratio FLOAT DEFAULT NULL,
            var_95 FLOAT DEFAULT NULL,
            win_rate FLOAT DEFAULT NULL,
            profit_loss_ratio FLOAT DEFAULT NULL,
            daily_return FLOAT DEFAULT NULL,
            total_return FLOAT DEFAULT NULL,
            composite_score FLOAT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fund_date (fund_code, analysis_date),
            INDEX idx_fund_code (fund_code),
            INDEX idx_analysis_date (analysis_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)
        
        # 添加新的夏普比率字段（如果表已存在）
        self._add_sharpe_ratio_columns()
    
    def _add_sharpe_ratio_columns(self):
        """添加新的夏普比率字段到fund_analysis_results表"""
        try:
            # 先检查表结构，确定哪些字段需要添加
            check_sql = """
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'fund_analysis_results'
            """
            existing_columns = set()
            try:
                result = self.execute_query_raw(check_sql)
                if result:
                    existing_columns = {row[0] for row in result}
            except Exception as e:
                logger.warning(f"检查表结构时出现错误: {str(e)}")
            
            # 定义需要添加的字段
            columns_to_add = [
                ('sharpe_ratio_ytd', 'FLOAT DEFAULT NULL AFTER sharpe_ratio'),
                ('sharpe_ratio_1y', 'FLOAT DEFAULT NULL AFTER sharpe_ratio_ytd'),
                ('sharpe_ratio_all', 'FLOAT DEFAULT NULL AFTER sharpe_ratio_1y')
            ]
            
            # 只添加不存在的字段
            for column_name, column_def in columns_to_add:
                if column_name not in existing_columns:
                    alter_sql = f"ALTER TABLE fund_analysis_results ADD COLUMN {column_name} {column_def}"
                    try:
                        self.execute_sql(alter_sql)
                        logger.info(f"成功添加字段: {column_name}")
                    except Exception as e:
                        logger.warning(f"添加字段 {column_name} 时出现错误: {str(e)}")
                else:
                    logger.info(f"字段 {column_name} 已存在，跳过")
            
            logger.info("夏普比率字段检查完成")
        except Exception as e:
            logger.warning(f"添加夏普比率字段时出现错误: {str(e)}")
    
    def _create_user_holdings_table(self):
        """
        创建用户持仓表
        """
        sql = """
        CREATE TABLE IF NOT EXISTS user_holdings (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id VARCHAR(50) NOT NULL DEFAULT 'default_user',
            fund_code VARCHAR(20) NOT NULL,
            fund_name VARCHAR(100) NOT NULL,
            holding_shares FLOAT DEFAULT 0,
            cost_price FLOAT DEFAULT 0,
            holding_amount FLOAT DEFAULT 0,
            buy_date DATE DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_fund (user_id, fund_code),
            INDEX idx_user_id (user_id),
            INDEX idx_fund_code (fund_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)

    def _create_user_strategies_table(self):
        """
        创建用户策略表
        存储用户自定义的投资策略配置
        """
        sql = """
        CREATE TABLE IF NOT EXISTS user_strategies (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL DEFAULT 'default_user',
            name VARCHAR(100) NOT NULL,
            description TEXT,
            config JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)
        logger.info("用户策略表 user_strategies 创建/检查完成")

    def _create_strategy_backtest_results_table(self):
        """
        创建策略回测结果表
        存储策略回测的执行状态和结果数据
        """
        sql = """
        CREATE TABLE IF NOT EXISTS strategy_backtest_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            strategy_id INT NOT NULL,
            task_id VARCHAR(50) NOT NULL UNIQUE,
            status VARCHAR(20) DEFAULT 'pending',
            result JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP NULL,
            FOREIGN KEY (strategy_id) REFERENCES user_strategies(id) ON DELETE CASCADE,
            INDEX idx_task_id (task_id),
            INDEX idx_strategy_id (strategy_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        self.execute_sql(sql)
        logger.info("策略回测结果表 strategy_backtest_results 创建/检查完成")


    def execute_query_raw(self, sql: str, params: Optional[Tuple] = None) -> Optional[List]:
        """
        执行原始查询并返回结果
        
        参数：
        sql: SQL查询语句
        params: 查询参数元组
        
        返回：
        查询结果列表或None
        """
        try:
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                return result.fetchall()
        except Exception as e:
            logger.error(f"执行原始查询失败: {str(e)}")
            return None
    
    def execute_sql(self, sql: str, params: Optional[Dict] = None) -> bool:
        """
        执行SQL语句
        
        参数：
        sql: SQL语句
        params: 参数字典（用于命名参数）或None
        
        返回：
        bool: 执行是否成功
        """
        try:
            # 转换numpy类型为Python原生类型
            if params:
                import numpy as np
                converted_params = {}
                for key, value in params.items():
                    if isinstance(value, np.floating):
                        converted_params[key] = float(value)
                    elif isinstance(value, np.integer):
                        converted_params[key] = int(value)
                    elif isinstance(value, np.bool_):
                        converted_params[key] = bool(value)
                    else:
                        converted_params[key] = value
                params = converted_params
            
            with self.engine.connect() as conn:
                if params:
                    conn.execute(text(sql), params)
                else:
                    conn.execute(text(sql))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"执行SQL失败: {str(e)}")
            return False
    

    def execute_query(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        执行查询SQL并返回DataFrame
        
        参数：
        sql: 查询SQL语句
        params: 参数字典（用于命名参数）或None
        
        返回：
        pd.DataFrame: 查询结果
        """
        try:
            if params:
                df = pd.read_sql(text(sql), self.engine, params=params)
            else:
                df = pd.read_sql(sql, self.engine)
            return df
        except Exception as e:
            logger.error(f"执行查询失败: {str(e)}")
            return pd.DataFrame()
    


    def insert_fund_basic_info(self, fund_info: Dict) -> bool:
        """
        插入基金基本信息
        
        参数：
        fund_info: 基金基本信息字典
        
        返回：
        bool: 插入是否成功
        """
        try:
            sql = """
            INSERT INTO fund_basic_info (
                fund_code, fund_name, fund_type, fund_company, fund_manager, 
                establish_date, management_fee, custody_fee
            ) VALUES (
                :fund_code, :fund_name, :fund_type, :fund_company, :fund_manager,
                :establish_date, :management_fee, :custody_fee
            ) ON DUPLICATE KEY UPDATE
                fund_name = VALUES(fund_name),
                fund_type = VALUES(fund_type),
                fund_company = VALUES(fund_company),
                fund_manager = VALUES(fund_manager),
                establish_date = VALUES(establish_date),
                management_fee = VALUES(management_fee),
                custody_fee = VALUES(custody_fee),
                updated_at = CURRENT_TIMESTAMP
            """
            
            self.execute_sql(sql, fund_info)
            
            logger.info(f"基金 {fund_info.get('fund_code', '')} 基本信息已保存")
            return True
            
        except Exception as e:
            logger.error(f"插入基金基本信息失败: {str(e)}")
            return False
    
    def insert_fund_performance(self, performance_data: Dict) -> bool:
        """
        插入基金绩效数据
        
        参数：
        performance_data: 基金绩效数据字典
        
        返回：
        bool: 插入是否成功
        """
        try:
            sql = """
            INSERT INTO fund_performance (
                fund_code, analysis_date, current_nav, previous_nav, daily_return, nav_date,
                annualized_return, sharpe_ratio, max_drawdown, volatility, calmar_ratio,
                sortino_ratio, var_95, win_rate, profit_loss_ratio, composite_score,
                total_return, data_days
            ) VALUES (
                :fund_code, :analysis_date, :current_nav, :previous_nav, :daily_return, :nav_date,
                :annualized_return, :sharpe_ratio, :max_drawdown, :volatility, :calmar_ratio,
                :sortino_ratio, :var_95, :win_rate, :profit_loss_ratio, :composite_score,
                :total_return, :data_days
            ) ON DUPLICATE KEY UPDATE
                current_nav = VALUES(current_nav),
                previous_nav = VALUES(previous_nav),
                daily_return = VALUES(daily_return),
                nav_date = VALUES(nav_date),
                annualized_return = VALUES(annualized_return),
                sharpe_ratio = VALUES(sharpe_ratio),
                max_drawdown = VALUES(max_drawdown),
                volatility = VALUES(volatility),
                calmar_ratio = VALUES(calmar_ratio),
                sortino_ratio = VALUES(sortino_ratio),
                var_95 = VALUES(var_95),
                win_rate = VALUES(win_rate),
                profit_loss_ratio = VALUES(profit_loss_ratio),
                composite_score = VALUES(composite_score),
                total_return = VALUES(total_return),
                data_days = VALUES(data_days),
                updated_at = CURRENT_TIMESTAMP
            """
            
            self.execute_sql(sql, performance_data)
            
            logger.info(f"基金 {performance_data.get('fund_code', '')} 绩效数据已保存")
            return True
            
        except Exception as e:
            logger.error(f"插入基金绩效数据失败: {str(e)}")
            return False
    

    
    def insert_analysis_summary(self, summary_data: Dict) -> bool:
        """
        插入分析汇总数据
        
        参数：
        summary_data: 分析汇总数据字典
        
        返回：
        bool: 插入是否成功
        """
        try:
            sql = """
            INSERT INTO analysis_summary (
                analysis_date, total_funds, buy_signals, sell_signals, hold_signals,
                avg_buy_multiplier, total_redeem_amount, best_performing_fund,
                worst_performing_fund, highest_sharpe_fund, lowest_volatility_fund,
                report_files
            ) VALUES (
                :analysis_date, :total_funds, :buy_signals, :sell_signals, :hold_signals,
                :avg_buy_multiplier, :total_redeem_amount, :best_performing_fund,
                :worst_performing_fund, :highest_sharpe_fund, :lowest_volatility_fund,
                :report_files
            ) ON DUPLICATE KEY UPDATE
                total_funds = VALUES(total_funds),
                buy_signals = VALUES(buy_signals),
                sell_signals = VALUES(sell_signals),
                hold_signals = VALUES(hold_signals),
                avg_buy_multiplier = VALUES(avg_buy_multiplier),
                total_redeem_amount = VALUES(total_redeem_amount),
                best_performing_fund = VALUES(best_performing_fund),
                worst_performing_fund = VALUES(worst_performing_fund),
                highest_sharpe_fund = VALUES(highest_sharpe_fund),
                lowest_volatility_fund = VALUES(lowest_volatility_fund),
                report_files = VALUES(report_files),
                updated_at = CURRENT_TIMESTAMP
            """
            
            import json
            
            # 确保所有必填字段都有默认值
            safe_summary_data = {
                'analysis_date': summary_data.get('analysis_date', datetime.now().date()),
                'total_funds': summary_data.get('total_funds', 0),
                'buy_signals': summary_data.get('buy_signals', 0),
                'sell_signals': summary_data.get('sell_signals', 0),
                'hold_signals': summary_data.get('hold_signals', 0),
                'avg_buy_multiplier': summary_data.get('avg_buy_multiplier', 0.0),
                'total_redeem_amount': summary_data.get('total_redeem_amount', 0),
                'best_performing_fund': summary_data.get('best_performing_fund', ''),
                'worst_performing_fund': summary_data.get('worst_performing_fund', ''),
                'highest_sharpe_fund': summary_data.get('highest_sharpe_fund', ''),
                'lowest_volatility_fund': summary_data.get('lowest_volatility_fund', ''),
                'report_files': json.dumps(summary_data.get('report_files', {}))
            }
            
            self.execute_sql(sql, safe_summary_data)
            
            logger.info(f"分析汇总数据已保存，日期: {summary_data.get('analysis_date', datetime.now().date())}")
            return True
            
        except Exception as e:
            logger.error(f"插入分析汇总数据失败: {str(e)}")
            return False
    
    def batch_insert_data(self, fund_data_list: List[Dict], 
                         summary_data: Dict) -> bool:
        """
        批量插入所有数据
        
        参数：
        fund_data_list: 基金数据列表
        summary_data: 汇总数据
        
        返回：
        bool: 批量插入是否成功
        """
        try:
            logger.info("开始批量插入数据...")
            
            # 插入基金基本信息
            for fund_data in fund_data_list:
                basic_info = {
                    'fund_code': fund_data.get('fund_code', ''),
                    'fund_name': fund_data.get('fund_name', ''),
                    'fund_type': fund_data.get('fund_type', ''),
                    'fund_company': fund_data.get('fund_company', ''),
                    'fund_manager': fund_data.get('fund_manager', ''),
                    'establish_date': fund_data.get('establish_date', None),
                    'management_fee': fund_data.get('management_fee', 0.0),
                    'custody_fee': fund_data.get('custody_fee', 0.0)
                }
                self.insert_fund_basic_info(basic_info)
            
            # 插入基金绩效数据
            for fund_data in fund_data_list:
                performance_data = {
                    'fund_code': fund_data.get('fund_code', ''),
                    'analysis_date': fund_data.get('analysis_date', datetime.now().date()),
                    'current_nav': fund_data.get('current_nav', 0.0),
                    'previous_nav': fund_data.get('previous_nav', 0.0),
                    'daily_return': fund_data.get('daily_return', 0.0),
                    'nav_date': fund_data.get('nav_date', datetime.now().date()),
                    'annualized_return': fund_data.get('annualized_return', 0.0),
                    'sharpe_ratio': fund_data.get('sharpe_ratio', 0.0),
                    'max_drawdown': fund_data.get('max_drawdown', 0.0),
                    'volatility': fund_data.get('volatility', 0.0),
                    'calmar_ratio': fund_data.get('calmar_ratio', 0.0),
                    'sortino_ratio': fund_data.get('sortino_ratio', 0.0),
                    'var_95': fund_data.get('var_95', 0.0),
                    'win_rate': fund_data.get('win_rate', 0.0),
                    'profit_loss_ratio': fund_data.get('profit_loss_ratio', 0.0),
                    'composite_score': fund_data.get('composite_score', 0.0),
                    'total_return': fund_data.get('total_return', 0.0),
                    'data_days': fund_data.get('data_days', 0)
                }
                self.insert_fund_performance(performance_data)
            
            # 插入综合分析结果数据到fund_analysis_results表
            for fund_data in fund_data_list:
                fund_analysis_data = {
                    'fund_code': fund_data.get('fund_code', ''),
                    'fund_name': fund_data.get('fund_name', ''),
                    'analysis_date': fund_data.get('analysis_date', datetime.now().date()),
                    'today_return': fund_data.get('today_return', 0.0),
                    'prev_day_return': fund_data.get('prev_day_return', 0.0),
                    'daily_return': fund_data.get('daily_return', 0.0),
                    'status_label': fund_data.get('status_label', ''),
                    'operation_suggestion': fund_data.get('operation_suggestion', ''),
                    'execution_amount': fund_data.get('execution_amount', ''),
                    'annualized_return': fund_data.get('annualized_return', 0.0),
                    'sharpe_ratio': fund_data.get('sharpe_ratio', 0.0),
                    'sharpe_ratio_ytd': fund_data.get('sharpe_ratio_ytd', 0.0),
                    'sharpe_ratio_1y': fund_data.get('sharpe_ratio_1y', 0.0),
                    'sharpe_ratio_all': fund_data.get('sharpe_ratio_all', 0.0),
                    'max_drawdown': fund_data.get('max_drawdown', 0.0),
                    'volatility': fund_data.get('volatility', 0.0),
                    'calmar_ratio': fund_data.get('calmar_ratio', 0.0),
                    'sortino_ratio': fund_data.get('sortino_ratio', 0.0),
                    'var_95': fund_data.get('var_95', 0.0),
                    'win_rate': fund_data.get('win_rate', 0.0),
                    'profit_loss_ratio': fund_data.get('profit_loss_ratio', 0.0),
                    'composite_score': fund_data.get('composite_score', 0.0),
                    'total_return': fund_data.get('total_return', 0.0),
                    'yesterday_nav': fund_data.get('previous_nav', 0.0),
                    'current_estimate': fund_data.get('estimate_nav', 0.0),
                    'is_buy': 1 if fund_data.get('is_buy', False) else 0,
                    'redeem_amount': fund_data.get('redeem_amount', 0.0),
                    'comparison_value': fund_data.get('comparison_value', 0.0),
                    'buy_multiplier': fund_data.get('buy_multiplier', 0.0)
                }
                self.insert_fund_analysis_results(fund_analysis_data)
            
            # 插入分析汇总数据
            self.insert_analysis_summary(summary_data)
            
            logger.info("批量插入数据完成")
            return True
            
        except Exception as e:
            logger.error(f"批量插入数据失败: {str(e)}")
            return False
    
    def get_fund_performance_history(self, fund_code: str, days: int = 30) -> pd.DataFrame:
        """
        获取基金绩效历史数据
        
        参数：
        fund_code: 基金代码
        days: 历史天数
        
        返回：
        DataFrame: 历史绩效数据
        """
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            sql = """
            SELECT 
                fp.analysis_date,
                fp.annualized_return,
                fp.sharpe_ratio,
                fp.max_drawdown,
                fp.volatility,
                fp.composite_score,
                far.status_label
            FROM fund_performance fp
            LEFT JOIN fund_analysis_results far ON fp.fund_code = far.fund_code AND fp.analysis_date = far.analysis_date
            WHERE fp.fund_code = %(fund_code)s AND fp.analysis_date >= %(start_date)s
            ORDER BY fp.analysis_date DESC
            """
            
            df = pd.read_sql(sql, self.engine, params={'fund_code': fund_code, 'start_date': start_date})
            return df
            
        except Exception as e:
            logger.error(f"获取基金绩效历史数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_top_performing_funds(self, metric: str = 'composite_score', limit: int = 10) -> pd.DataFrame:
        """
        获取表现最佳的基金
        
        参数：
        metric: 排序指标
        limit: 返回数量限制
        
        返回：
        DataFrame: 最佳基金数据
        """
        try:
            sql = f"""
            SELECT 
                fbi.fund_code,
                fbi.fund_name,
                fbi.fund_type,
                fp.annualized_return,
                fp.sharpe_ratio,
                fp.max_drawdown,
                fp.volatility,
                fp.composite_score,
                fp.analysis_date
            FROM fund_basic_info fbi
            JOIN fund_performance fp ON fbi.fund_code = fp.fund_code
            WHERE fp.analysis_date = (
                SELECT MAX(analysis_date) FROM fund_performance WHERE fund_code = fbi.fund_code
            )
            ORDER BY fp.{metric} DESC
            LIMIT :limit
            """
            
            df = pd.read_sql(sql, self.engine, params={'limit': limit})
            return df
            
        except Exception as e:
            logger.error(f"获取最佳基金数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_strategy_distribution(self, analysis_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取策略分布统计
        
        参数：
        analysis_date: 分析日期（可选，默认最新日期）
        
        返回：
        DataFrame: 策略分布数据
        """
        try:
            if not analysis_date:
                analysis_date = datetime.now().date()
            
            sql = """
            SELECT 
                status_label,
                COUNT(*) as fund_count,
                AVG(buy_multiplier) as avg_buy_multiplier,
                SUM(redeem_amount) as total_redeem_amount
            FROM fund_analysis_results
            WHERE analysis_date = %(analysis_date)s
            GROUP BY status_label
            ORDER BY fund_count DESC
            """
            
            df = pd.read_sql(sql, self.engine, params={'analysis_date': analysis_date})
            return df
            
        except Exception as e:
            logger.error(f"获取策略分布统计失败: {str(e)}")
            return pd.DataFrame()
    
    def get_analysis_summary(self, days: int = 7) -> pd.DataFrame:
        """
        获取分析汇总数据
        
        参数：
        days: 最近天数
        
        返回：
        DataFrame: 分析汇总数据
        """
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            sql = """
            SELECT 
                analysis_date,
                total_funds,
                buy_signals,
                sell_signals,
                hold_signals,
                avg_buy_multiplier,
                total_redeem_amount
            FROM analysis_summary
            WHERE analysis_date >= %(start_date)s
            ORDER BY analysis_date DESC
            """
            
            df = pd.read_sql(sql, self.engine, params={'start_date': start_date})
            return df
            
        except Exception as e:
            logger.error(f"获取分析汇总数据失败: {str(e)}")
            return pd.DataFrame()
    

    def save_fund_analysis(self, analysis_data: Dict) -> bool:
        """
        保存基金分析数据（兼容性方法）
        
        参数：
        analysis_data: 基金分析数据字典
        
        返回：
        bool: 保存是否成功
        """
        try:
            # 同时保存到fund_analysis_results表（如果包含必要的字段）
            if ('fund_code' in analysis_data and 'fund_name' in analysis_data) or \
               ('today_return' in analysis_data or 'status_label' in analysis_data or 'operation_suggestion' in analysis_data):
                # 准备fund_analysis_results表的数据
                fund_analysis_data = {
                    'fund_code': analysis_data.get('fund_code', ''),
                    'fund_name': analysis_data.get('fund_name', ''),
                    'analysis_date': analysis_data.get('analysis_date', datetime.now().date()),
                    'today_return': analysis_data.get('today_return', 0.0),
                    'prev_day_return': analysis_data.get('prev_day_return', 0.0),
                    'status_label': analysis_data.get('status_label', ''),
                    'operation_suggestion': analysis_data.get('operation_suggestion', ''),
                    'annualized_return': analysis_data.get('annualized_return', 0.0),
                    'sharpe_ratio': analysis_data.get('sharpe_ratio', 0.0),
                    'max_drawdown': analysis_data.get('max_drawdown', 0.0),
                    'volatility': analysis_data.get('volatility', 0.0),
                    'calmar_ratio': analysis_data.get('calmar_ratio', 0.0),
                    'sortino_ratio': analysis_data.get('sortino_ratio', 0.0),
                    'var_95': analysis_data.get('var_95', 0.0),
                    'win_rate': analysis_data.get('win_rate', 0.0),
                    'profit_loss_ratio': analysis_data.get('profit_loss_ratio', 0.0),
                    'composite_score': analysis_data.get('composite_score', 0.0),
                    'daily_return': analysis_data.get('daily_return', 0.0),
                    'total_return': analysis_data.get('total_return', 0.0),
                    # 修复字段名不匹配的问题
                    'yesterday_nav': analysis_data.get('previous_nav', 0.0),
                    'current_estimate': analysis_data.get('estimate_nav', 0.0),
                    'is_buy': analysis_data.get('is_buy', 0),
                    'redeem_amount': analysis_data.get('redeem_amount', 0.0),
                    'comparison_value': analysis_data.get('comparison_value', 0.0),
                    'execution_amount': analysis_data.get('execution_amount', ''),
                    'buy_multiplier': analysis_data.get('buy_multiplier', 0.0)
                }
                
                # 插入到fund_analysis_results表
                self.insert_fund_analysis_results(fund_analysis_data)
            
            # 根据数据内容决定使用哪种插入方式（保持原有逻辑）
            if 'annualized_return' in analysis_data or 'sharpe_ratio' in analysis_data:
                # 包含绩效指标，使用绩效数据表
                performance_data = {
                    'fund_code': analysis_data.get('fund_code', ''),
                    'analysis_date': analysis_data.get('analysis_date', datetime.now().date()),
                    'current_nav': analysis_data.get('current_nav', 0.0),
                    'previous_nav': analysis_data.get('previous_nav', 0.0),
                    'daily_return': analysis_data.get('daily_return', 0.0),
                    'nav_date': analysis_data.get('nav_date', datetime.now().date()),
                    'annualized_return': analysis_data.get('annualized_return', 0.0),
                    'sharpe_ratio': analysis_data.get('sharpe_ratio', 0.0),
                    'max_drawdown': analysis_data.get('max_drawdown', 0.0),
                    'volatility': analysis_data.get('volatility', 0.0),
                    'calmar_ratio': analysis_data.get('calmar_ratio', 0.0),
                    'sortino_ratio': analysis_data.get('sortino_ratio', 0.0),
                    'var_95': analysis_data.get('var_95', 0.0),
                    'win_rate': analysis_data.get('win_rate', 0.0),
                    'profit_loss_ratio': analysis_data.get('profit_loss_ratio', 0.0),
                    'composite_score': analysis_data.get('composite_score', 0.0),
                    'total_return': analysis_data.get('total_return', 0.0),
                    'data_days': analysis_data.get('data_days', 0)
                }
                return self.insert_fund_performance(performance_data)
            else:
                # 默认使用绩效数据表
                return self.insert_fund_performance(analysis_data)
                
        except Exception as e:
            logger.error(f"保存基金分析数据失败: {str(e)}")
            return False
    
    def save_strategy_summary(self, summary_data: Dict) -> bool:
        """
        保存策略汇总数据
        
        参数：
        summary_data: 策略汇总数据字典
        
        返回：
        bool: 保存是否成功
        """
        try:
            # 准备汇总数据
            summary_record = {
                'analysis_date': summary_data.get('analysis_date', datetime.now().date()),
                'total_funds': summary_data.get('total_funds', 0),
                'buy_signals': summary_data.get('buy_signals', 0),
                'sell_signals': summary_data.get('sell_signals', 0),
                'hold_signals': summary_data.get('hold_signals', 0),
                'avg_buy_multiplier': summary_data.get('avg_buy_multiplier', 0.0),
                'total_redeem_amount': summary_data.get('total_redeem_amount', 0),
                'best_performing_fund': summary_data.get('best_performing_fund', ''),
                'worst_performing_fund': summary_data.get('worst_performing_fund', ''),
                'avg_today_return': summary_data.get('avg_today_return', 0.0)
            }
            
            # 插入到analysis_summary表
            return self.insert_analysis_summary(summary_record)
            
        except Exception as e:
            logger.error(f"保存策略汇总数据失败: {str(e)}")
            return False
    
    def get_latest_performance_analysis(self, limit: int = 100) -> pd.DataFrame:
        """
        获取最新的基金绩效分析结果
        
        参数：
        limit: 返回结果的最大数量
        
        返回：
        pd.DataFrame: 包含基金绩效分析结果的DataFrame
        """
        try:
            # 查询最新的分析结果
            sql = """
            SELECT * 
            FROM fund_analysis_results 
            WHERE fund_code IS NOT NULL AND fund_code != '' 
            ORDER BY analysis_date DESC, fund_code ASC 
            LIMIT :limit
            """
            
            with self.engine.connect() as connection:
                df = pd.read_sql(text(sql), connection, params={'limit': limit})
            
            logger.info(f"获取最新绩效分析结果成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取绩效分析结果失败: {str(e)}")
            return pd.DataFrame()
    
    def get_performance_analysis_by_date(self, analysis_date: datetime.date, limit: int = 100) -> pd.DataFrame:
        """
        根据日期获取基金绩效分析结果
        
        参数：
        analysis_date: 分析日期
        limit: 返回结果的最大数量
        
        返回：
        pd.DataFrame: 包含基金绩效分析结果的DataFrame
        """
        try:
            # 查询指定日期的分析结果
            sql = """
            SELECT * 
            FROM fund_analysis_results 
            WHERE analysis_date = :analysis_date 
            AND fund_code IS NOT NULL AND fund_code != '' 
            ORDER BY fund_code ASC 
            LIMIT :limit
            """
            
            with self.engine.connect() as connection:
                df = pd.read_sql(text(sql), connection, params={'analysis_date': analysis_date, 'limit': limit})
            
            logger.info(f"获取 {analysis_date} 绩效分析结果成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取指定日期绩效分析结果失败: {str(e)}")
            return pd.DataFrame()
    
    def get_performance_analysis_by_fund(self, fund_code: str, days_limit: int = 30) -> pd.DataFrame:
        """
        根据基金代码获取历史绩效分析结果
        
        参数：
        fund_code: 基金代码
        days_limit: 查询天数限制
        
        返回：
        pd.DataFrame: 包含基金历史绩效分析结果的DataFrame
        """
        try:
            # 计算起始日期
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_limit)
            
            # 查询指定基金的历史分析结果
            sql = """
            SELECT * 
            FROM fund_analysis_results 
            WHERE fund_code = :fund_code 
            AND analysis_date BETWEEN :start_date AND :end_date 
            ORDER BY analysis_date DESC
            """
            
            with self.engine.connect() as connection:
                df = pd.read_sql(text(sql), connection, params={'fund_code': fund_code, 'start_date': start_date, 'end_date': end_date})
            
            logger.info(f"获取基金 {fund_code} 历史绩效分析结果成功，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取基金历史绩效分析结果失败: {str(e)}")
            return pd.DataFrame()
    
    def save_report_info(self, report_file: str, report_type: str = 'general') -> bool:
        """
        保存报告文件信息
        
        参数：
        report_file: 报告文件路径
        report_type: 报告类型
        
        返回：
        bool: 保存是否成功
        """
        try:
            # 这里可以创建一个专门的表来存储报告信息，或者将信息附加到分析汇总中
            # 为简化实现，我们先记录日志
            logger.info(f"报告文件已记录: {report_file}, 类型: {report_type}")
            return True
            
        except Exception as e:
            logger.error(f"保存报告文件信息失败: {str(e)}")
            return False
    
    def insert_fund_analysis_results(self, analysis_data: Dict) -> bool:
        """
        插入基金分析结果数据到fund_analysis_results表
        
        参数：
        analysis_data: 基金分析结果数据字典
        
        返回：
        bool: 插入是否成功
        """
        try:
            sql = """
            INSERT INTO fund_analysis_results (
                fund_code, fund_name, yesterday_nav, current_estimate, today_return, 
                prev_day_return, status_label, is_buy, redeem_amount, comparison_value, 
                operation_suggestion, execution_amount, analysis_date, buy_multiplier, 
                annualized_return, sharpe_ratio, sharpe_ratio_ytd, sharpe_ratio_1y, sharpe_ratio_all,
                max_drawdown, volatility, calmar_ratio, 
                sortino_ratio, var_95, win_rate, profit_loss_ratio, daily_return, 
                total_return, composite_score
            ) VALUES (
                :fund_code, :fund_name, :yesterday_nav, :current_estimate, :today_return,
                :prev_day_return, :status_label, :is_buy, :redeem_amount, :comparison_value,
                :operation_suggestion, :execution_amount, :analysis_date, :buy_multiplier,
                :annualized_return, :sharpe_ratio, :sharpe_ratio_ytd, :sharpe_ratio_1y, :sharpe_ratio_all,
                :max_drawdown, :volatility, :calmar_ratio,
                :sortino_ratio, :var_95, :win_rate, :profit_loss_ratio, :daily_return, 
                :total_return, :composite_score
            ) ON DUPLICATE KEY UPDATE
                fund_name = VALUES(fund_name),
                yesterday_nav = VALUES(yesterday_nav),
                current_estimate = VALUES(current_estimate),
                today_return = VALUES(today_return),
                prev_day_return = VALUES(prev_day_return),
                status_label = VALUES(status_label),
                is_buy = VALUES(is_buy),
                redeem_amount = VALUES(redeem_amount),
                comparison_value = VALUES(comparison_value),
                operation_suggestion = VALUES(operation_suggestion),
                execution_amount = VALUES(execution_amount),
                buy_multiplier = VALUES(buy_multiplier),
                annualized_return = VALUES(annualized_return),
                sharpe_ratio = VALUES(sharpe_ratio),
                sharpe_ratio_ytd = VALUES(sharpe_ratio_ytd),
                sharpe_ratio_1y = VALUES(sharpe_ratio_1y),
                sharpe_ratio_all = VALUES(sharpe_ratio_all),
                max_drawdown = VALUES(max_drawdown),
                volatility = VALUES(volatility),
                calmar_ratio = VALUES(calmar_ratio),
                sortino_ratio = VALUES(sortino_ratio),
                var_95 = VALUES(var_95),
                win_rate = VALUES(win_rate),
                profit_loss_ratio = VALUES(profit_loss_ratio),
                daily_return = VALUES(daily_return),
                total_return = VALUES(total_return),
                composite_score = VALUES(composite_score)
            """
            
            # 准备插入的数据，映射到实际表的列
            prepared_data = {
                'fund_code': str(analysis_data.get('fund_code', '')),
                'fund_name': str(analysis_data.get('fund_name', '')),
                'yesterday_nav': float(analysis_data.get('yesterday_nav', 0.0)),
                'current_estimate': float(analysis_data.get('current_estimate', 0.0)),
                'today_return': float(analysis_data.get('today_return', 0.0)),
                'prev_day_return': float(analysis_data.get('prev_day_return', 0.0)),
                'status_label': str(analysis_data.get('status_label', '')),
                'is_buy': int(analysis_data.get('is_buy', 0)),
                'redeem_amount': float(analysis_data.get('redeem_amount', 0.0)),
                'comparison_value': float(analysis_data.get('comparison_value', 0.0)),
                'operation_suggestion': str(analysis_data.get('operation_suggestion', '')),
                'execution_amount': str(analysis_data.get('execution_amount', '')),
                'analysis_date': analysis_data.get('analysis_date', datetime.now().date()),
                'buy_multiplier': float(analysis_data.get('buy_multiplier', 0.0)),
                'annualized_return': float(analysis_data.get('annualized_return', 0.0)),
                'sharpe_ratio': float(analysis_data.get('sharpe_ratio', 0.0)),
                'sharpe_ratio_ytd': float(analysis_data.get('sharpe_ratio_ytd', 0.0)),
                'sharpe_ratio_1y': float(analysis_data.get('sharpe_ratio_1y', 0.0)),
                'sharpe_ratio_all': float(analysis_data.get('sharpe_ratio_all', 0.0)),
                'max_drawdown': float(analysis_data.get('max_drawdown', 0.0)),
                'volatility': float(analysis_data.get('volatility', 0.0)),
                'calmar_ratio': float(analysis_data.get('calmar_ratio', 0.0)),
                'sortino_ratio': float(analysis_data.get('sortino_ratio', 0.0)),
                'var_95': float(analysis_data.get('var_95', 0.0)),
                'win_rate': float(analysis_data.get('win_rate', 0.0)),
                'profit_loss_ratio': float(analysis_data.get('profit_loss_ratio', 0.0)),
                'daily_return': float(analysis_data.get('daily_return', 0.0)),
                'total_return': float(analysis_data.get('total_return', 0.0)),
                'composite_score': float(analysis_data.get('composite_score', 0.0))
            }
            
            self.execute_sql(sql, prepared_data)
            
            logger.info(f"基金 {analysis_data.get('fund_code', '')} 分析结果已保存到fund_analysis_results表")
            return True
            
        except Exception as e:
            logger.error(f"插入基金分析结果数据失败: {str(e)}")
            return False



    def close_connection(self):
        """关闭数据库连接"""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {str(e)}")


if __name__ == "__main__":
    # 测试代码
    from shared.enhanced_config import DATABASE_CONFIG
    
    # 创建数据库管理器
    db_manager = EnhancedDatabaseManager(DATABASE_CONFIG)
    
    # 测试数据
    test_fund_info = {
        'fund_code': '000001',
        'fund_name': '测试基金',
        'fund_type': '股票型',
        'fund_company': '测试公司',
        'fund_manager': '测试经理',
        'establish_date': '2020-01-01',
        'management_fee': 0.015,
        'custody_fee': 0.005
    }
    
    test_performance = {
        'fund_code': '000001',
        'analysis_date': datetime.now().date(),
        'current_nav': 1.5,
        'previous_nav': 1.4,
        'daily_return': 0.0714,
        'nav_date': datetime.now().date(),
        'annualized_return': 0.15,
        'sharpe_ratio': 1.2,
        'max_drawdown': -0.08,
        'volatility': 0.12,
        'calmar_ratio': 1.875,
        'sortino_ratio': 1.5,
        'var_95': -0.015,
        'win_rate': 0.65,
        'profit_loss_ratio': 1.8,
        'composite_score': 0.75,
        'total_return': 0.5,
        'data_days': 365
    }
    
    test_summary = {
        'analysis_date': datetime.now().date(),
        'total_funds': 5,
        'buy_signals': 3,
        'sell_signals': 1,
        'hold_signals': 1,
        'avg_buy_multiplier': 1.2,
        'total_redeem_amount': 30,
        'best_performing_fund': '000001',
        'worst_performing_fund': '000002',
        'highest_sharpe_fund': '000001',
        'lowest_volatility_fund': '000003',
        'report_files': {'test': 'test.png'}
    }
    
    # 测试插入功能
    print("测试插入基金基本信息:")
    result = db_manager.insert_fund_basic_info(test_fund_info)
    print(f"结果: {result}")
    
    print("\n测试插入基金绩效数据:")
    result = db_manager.insert_fund_performance(test_performance)
    print(f"结果: {result}")
    
    print("\n测试插入分析汇总:")
    result = db_manager.insert_analysis_summary(test_summary)
    print(f"结果: {result}")
    
    # 测试查询功能
    print("\n测试查询基金绩效历史:")
    history = db_manager.get_fund_performance_history('000001', 30)
    print(f"历史数据: {len(history)} 条记录")
    
    print("\n测试查询最佳基金:")
    top_funds = db_manager.get_top_performing_funds('composite_score', 5)
    print(f"最佳基金: {top_funds}")
    
    print("\n测试查询策略分布:")
    strategy_dist = db_manager.get_strategy_distribution()
    print(f"策略分布: {strategy_dist}")
    
    print("\n测试查询分析汇总:")
    summary = db_manager.get_analysis_summary(7)
    print(f"分析汇总: {summary}")
    
    # 关闭连接
    db_manager.close_connection()