#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库表结构优化工具
- 添加表和字段注释
- 清理冗余字段
- 生成结构文档
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """数据库优化器"""
    
    # 表注释定义
    TABLE_COMMENTS = {
        'fund_analysis_results': '基金分析结果表 - 存储基金实时分析数据、策略信号、绩效指标',
        'fund_basic_info': '基金基本信息表 - 存储基金基础档案信息',
        'fund_performance': '基金绩效数据表 - 存储历史净值和绩效指标（按日期汇总）',
        'user_holdings': '用户持仓表 - 存储用户基金持仓信息',
        'analysis_summary': '分析汇总表 - 存储每日分析汇总统计',
        'user_strategies': '用户策略表 - 存储用户自定义投资策略',
        'strategy_backtest_results': '策略回测结果表 - 存储策略回测执行结果',
        'fund_heavyweight_stocks': '基金重仓股表 - 存储基金重仓持股信息',
        'user_operations': '用户操作记录表 - 存储用户操作历史',
        'fund_nav_cache': '基金净值缓存表 - 缓存基金历史净值数据',
        'fund_cache_metadata': '缓存元数据表 - 记录基金数据缓存状态',
    }
    
    # 字段注释定义（补充其他表）
    COLUMN_COMMENTS = {
        'analysis_summary': {
            'analysis_date': '分析日期',
            'total_funds': '分析基金总数',
            'buy_signals': '买入信号数量',
            'sell_signals': '卖出信号数量',
            'hold_signals': '持有信号数量',
            'avg_buy_multiplier': '平均买入倍率',
            'total_redeem_amount': '总建议赎回金额',
            'best_performing_fund': '表现最佳基金代码',
            'worst_performing_fund': '表现最差基金代码',
            'highest_sharpe_fund': '夏普比率最高基金',
            'lowest_volatility_fund': '波动率最低基金',
            'report_files': '报告文件路径（JSON格式）',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'user_strategies': {
            'id': '策略ID，自增主键',
            'user_id': '用户ID',
            'name': '策略名称',
            'description': '策略描述',
            'config': '策略配置（JSON格式）',
            'created_at': '创建时间',
            'updated_at': '更新时间',
        },
        'strategy_backtest_results': {
            'id': '回测记录ID',
            'strategy_id': '关联的策略ID',
            'task_id': '任务唯一标识',
            'status': '回测状态：pending/running/success/failed',
            'result': '回测结果数据（JSON格式）',
            'created_at': '创建时间',
            'completed_at': '完成时间',
        },
        'fund_heavyweight_stocks': {
            'id': '记录ID',
            'fund_code': '基金代码',
            'stock_code': '股票代码',
            'stock_name': '股票名称',
            'holding_ratio': '持仓比例(%)',
            'market_value': '持仓市值',
            'change_percent': '持仓变动比例(%)',
            'report_period': '报告期，如：2024Q1',
            'ranking': '重仓排名',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'fund_nav_cache': {
            'id': '记录ID',
            'fund_code': '基金代码',
            'nav_date': '净值日期',
            'nav_value': '单位净值',
            'accum_nav': '累计净值',
            'daily_return': '日涨跌幅(%)',
            'data_source': '数据来源：akshare/tushare/eastmoney',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'fund_cache_metadata': {
            'id': '记录ID',
            'fund_code': '基金代码',
            'earliest_date': '最早数据日期',
            'latest_date': '最新数据日期',
            'total_records': '总记录数',
            'last_sync_at': '最后同步时间',
            'next_sync_at': '下次预定同步时间',
            'sync_status': '同步状态：pending/syncing/completed/failed',
            'sync_fail_count': '连续失败次数',
            'data_source': '主要数据来源',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'fund_analysis_results': {
            'fund_code': '基金代码，如：000001',
            'fund_name': '基金名称',
            'analysis_date': '分析日期',
            'yesterday_nav': '昨日净值',
            'current_estimate': '当前估算净值/最新净值',
            'today_return': '当日收益率(%)',
            'prev_day_return': '昨日收益率(%) - 主要使用的昨日盈亏字段',
            'status_label': '策略状态标签，如：强烈买入、观望等',
            'is_buy': '是否为买入信号：1=买入，0=非买入',
            'buy_multiplier': '买入倍率，建议加仓倍数',
            'redeem_amount': '赎回金额建议',
            'comparison_value': '对比值（今日-昨日收益率差值）',
            'operation_suggestion': '操作建议描述',
            'execution_amount': '执行金额建议',
            'annualized_return': '年化收益率(%)',
            'sharpe_ratio': '夏普比率-默认周期',
            'sharpe_ratio_ytd': '夏普比率-今年以来',
            'sharpe_ratio_1y': '夏普比率-近一年',
            'sharpe_ratio_all': '夏普比率-成立以来',
            'max_drawdown': '最大回撤(%)',
            'volatility': '波动率(%)',
            'calmar_ratio': '卡玛比率',
            'sortino_ratio': '索提诺比率',
            'var_95': 'VaR风险价值(95%置信度)',
            'win_rate': '胜率(%)',
            'profit_loss_ratio': '盈亏比',
            'total_return': '累计收益率(%)',
            'composite_score': '综合评分',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'fund_basic_info': {
            'fund_code': '基金代码，唯一标识',
            'fund_name': '基金全称',
            'fund_type': '基金类型：股票型/债券型/混合型/指数型等',
            'fund_company': '基金公司/管理人',
            'fund_manager': '基金经理',
            'establish_date': '基金成立日期',
            'management_fee': '管理费率(%)',
            'custody_fee': '托管费率(%)',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'fund_performance': {
            'fund_code': '基金代码',
            'analysis_date': '分析日期',
            'current_nav': '当日单位净值',
            'previous_nav': '前一日单位净值',
            'daily_return': '日涨跌幅(%)',
            'nav_date': '净值日期',
            'annualized_return': '年化收益率(%)',
            'sharpe_ratio': '夏普比率',
            'max_drawdown': '最大回撤(%)',
            'volatility': '波动率(%)',
            'calmar_ratio': '卡玛比率',
            'sortino_ratio': '索提诺比率',
            'var_95': 'VaR风险价值(95%置信度)',
            'win_rate': '胜率(%)',
            'profit_loss_ratio': '盈亏比',
            'composite_score': '综合评分',
            'total_return': '累计收益率(%)',
            'data_days': '数据天数/样本量',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
        'user_holdings': {
            'id': '自增主键ID',
            'user_id': '用户ID，默认default_user',
            'fund_code': '基金代码',
            'fund_name': '基金名称',
            'holding_shares': '持仓份额',
            'cost_price': '成本价',
            'holding_amount': '持有金额（份额×成本价）',
            'buy_date': '买入日期',
            'notes': '备注信息',
            'created_at': '记录创建时间',
            'updated_at': '记录更新时间',
        },
    }
    
    # 冗余字段定义（需要删除的）
    REDUNDANT_COLUMNS = {
        'fund_analysis_results': ['yesterday_return'],  # 与 prev_day_return 重复，从未使用
    }
    
    def __init__(self):
        self.conn = None
        self.db_config = self._load_db_config()
        
    def _load_db_config(self):
        """加载数据库配置"""
        try:
            from shared.enhanced_config import DATABASE_CONFIG
            return DATABASE_CONFIG
        except ImportError:
            # 默认配置
            return {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': 'fund_analysis',
                'charset': 'utf8mb4'
            }
    
    def connect(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                charset=self.db_config['charset'],
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"✓ 数据库连接成功: {self.db_config['database']}")
            return True
        except Exception as e:
            logger.error(f"✗ 数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            logger.info("✓ 数据库连接已关闭")
    
    def execute(self, sql, params=None):
        """执行SQL"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                self.conn.commit()
                return True
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def query(self, sql, params=None):
        """查询数据"""
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def table_exists(self, table_name):
        """检查表是否存在"""
        sql = """
        SELECT COUNT(*) as count FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = self.query(sql, (self.db_config['database'], table_name))
        return result[0]['count'] > 0
    
    def column_exists(self, table_name, column_name):
        """检查字段是否存在"""
        sql = """
        SELECT COUNT(*) as count FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """
        result = self.query(sql, (self.db_config['database'], table_name, column_name))
        return result[0]['count'] > 0
    
    def get_column_info(self, table_name, column_name):
        """获取字段信息"""
        sql = """
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
               NUMERIC_PRECISION, NUMERIC_SCALE, COLUMN_DEFAULT, IS_NULLABLE, EXTRA
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """
        result = self.query(sql, (self.db_config['database'], table_name, column_name))
        return result[0] if result else None
    
    def add_table_comment(self, table_name, comment):
        """添加表注释"""
        try:
            sql = f"ALTER TABLE {table_name} COMMENT = %s"
            self.execute(sql, (comment,))
            logger.info(f"  ✓ 表注释已添加: {table_name}")
            return True
        except Exception as e:
            logger.warning(f"  ✗ 表注释添加失败: {table_name} - {e}")
            return False
    
    def add_column_comment(self, table_name, column_name, comment):
        """添加字段注释"""
        try:
            # 获取当前字段定义
            col_info = self.get_column_info(table_name, column_name)
            if not col_info:
                logger.warning(f"  ! 字段不存在: {table_name}.{column_name}")
                return False
            
            # 构建字段类型字符串
            data_type = col_info['DATA_TYPE'].upper()
            if data_type == 'VARCHAR' and col_info['CHARACTER_MAXIMUM_LENGTH']:
                type_str = f"VARCHAR({col_info['CHARACTER_MAXIMUM_LENGTH']})"
            elif data_type == 'DECIMAL' and col_info['NUMERIC_PRECISION']:
                scale = col_info['NUMERIC_SCALE'] or 0
                type_str = f"DECIMAL({col_info['NUMERIC_PRECISION']},{scale})"
            elif data_type == 'FLOAT':
                type_str = "FLOAT"
            elif data_type == 'DOUBLE':
                type_str = "DOUBLE"
            elif data_type == 'INT':
                type_str = "INT"
            elif data_type == 'TINYINT':
                type_str = "TINYINT(1)" if col_info['NUMERIC_PRECISION'] == 1 else "TINYINT"
            elif data_type == 'DATE':
                type_str = "DATE"
            elif data_type == 'TIMESTAMP':
                type_str = "TIMESTAMP"
            elif data_type == 'DATETIME':
                type_str = "DATETIME"
            elif data_type == 'TEXT':
                type_str = "TEXT"
            elif data_type == 'JSON':
                type_str = "JSON"
            else:
                type_str = data_type
            
            # 添加默认值和NULL属性
            default_str = ""
            if col_info['COLUMN_DEFAULT'] is not None:
                default_val = col_info['COLUMN_DEFAULT']
                if isinstance(default_val, str):
                    default_str = f" DEFAULT '{default_val}'"
                else:
                    default_str = f" DEFAULT {default_val}"
            elif col_info['IS_NULLABLE'] == 'YES':
                default_str = " DEFAULT NULL"
            
            null_str = "" if col_info['IS_NULLABLE'] == 'YES' else " NOT NULL"
            
            # 添加自增属性
            extra_str = ""
            if col_info.get('EXTRA'):
                # 处理 MySQL 8.0 的特殊属性
                extra = col_info['EXTRA']
                if 'auto_increment' in extra:
                    extra_str = " AUTO_INCREMENT"
                # DEFAULT_GENERATED 是内部属性，不需要在 MODIFY 中指定
            
            # 构建完整SQL
            sql = f"""
            ALTER TABLE {table_name} 
            MODIFY COLUMN {column_name} {type_str}{null_str}{default_str}{extra_str} 
            COMMENT %s
            """
            self.execute(sql, (comment,))
            logger.info(f"  ✓ 字段注释已添加: {table_name}.{column_name}")
            return True
            
        except Exception as e:
            logger.warning(f"  ✗ 字段注释添加失败: {table_name}.{column_name} - {e}")
            return False
    
    def drop_column(self, table_name, column_name):
        """删除字段"""
        try:
            sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            self.execute(sql)
            logger.info(f"  ✓ 冗余字段已删除: {table_name}.{column_name}")
            return True
        except Exception as e:
            logger.warning(f"  ✗ 字段删除失败: {table_name}.{column_name} - {e}")
            return False
    
    def optimize_table(self, table_name):
        """优化单个表"""
        logger.info(f"\n{'='*50}")
        logger.info(f"优化表: {table_name}")
        logger.info('='*50)
        
        if not self.table_exists(table_name):
            logger.warning(f"  ! 表不存在，跳过: {table_name}")
            return
        
        # 1. 添加表注释
        if table_name in self.TABLE_COMMENTS:
            self.add_table_comment(table_name, self.TABLE_COMMENTS[table_name])
        
        # 2. 添加字段注释
        if table_name in self.COLUMN_COMMENTS:
            for column, comment in self.COLUMN_COMMENTS[table_name].items():
                if self.column_exists(table_name, column):
                    self.add_column_comment(table_name, column, comment)
                else:
                    logger.debug(f"  ! 字段不存在，跳过: {table_name}.{column}")
        
        # 3. 清理冗余字段
        if table_name in self.REDUNDANT_COLUMNS:
            for column in self.REDUNDANT_COLUMNS[table_name]:
                if self.column_exists(table_name, column):
                    self.drop_column(table_name, column)
                else:
                    logger.info(f"  ✓ 冗余字段已不存在: {table_name}.{column}")
    
    def generate_documentation(self):
        """生成数据库结构文档"""
        logger.info("\n" + "="*50)
        logger.info("生成数据库结构文档")
        logger.info("="*50)
        
        tables = [
            'fund_analysis_results', 'fund_basic_info', 'fund_performance',
            'user_holdings', 'analysis_summary', 'user_strategies',
            'strategy_backtest_results', 'fund_heavyweight_stocks',
            'fund_nav_cache', 'fund_cache_metadata'
        ]
        
        doc_lines = ["# 基金分析系统 - 数据库表结构文档\n"]
        doc_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        doc_lines.append("=" * 60 + "\n")
        
        for table in tables:
            if not self.table_exists(table):
                continue
                
            # 获取表注释
            sql = """
            SELECT TABLE_COMMENT FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
            """
            result = self.query(sql, (self.db_config['database'], table))
            table_comment = result[0]['TABLE_COMMENT'] if result and result[0]['TABLE_COMMENT'] else ''
            
            doc_lines.append(f"\n## {table}")
            doc_lines.append(f"{table_comment}\n")
            doc_lines.append("| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |")
            doc_lines.append("|--------|----------|------|--------|------|")
            
            # 获取字段信息
            sql = """
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                   NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE,
                   COLUMN_DEFAULT, COLUMN_COMMENT, EXTRA
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ORDINAL_POSITION
            """
            columns = self.query(sql, (self.db_config['database'], table))
            
            for col in columns:
                col_name = col['COLUMN_NAME']
                data_type = col['DATA_TYPE'].upper()
                
                # 构建类型字符串
                if data_type == 'VARCHAR' and col['CHARACTER_MAXIMUM_LENGTH']:
                    type_str = f"VARCHAR({col['CHARACTER_MAXIMUM_LENGTH']})"
                elif data_type == 'DECIMAL' and col['NUMERIC_PRECISION']:
                    scale = col['NUMERIC_SCALE'] or 0
                    type_str = f"DECIMAL({col['NUMERIC_PRECISION']},{scale})"
                else:
                    type_str = data_type
                
                nullable = '是' if col['IS_NULLABLE'] == 'YES' else '否'
                default = str(col['COLUMN_DEFAULT']) if col['COLUMN_DEFAULT'] is not None else '-'
                comment = col['COLUMN_COMMENT'] or '-'
                
                # 标记自增字段
                if col.get('EXTRA') and 'auto_increment' in col['EXTRA']:
                    extra = ' [自增]'
                else:
                    extra = ''
                
                doc_lines.append(f"| {col_name} | {type_str} | {nullable} | {default} | {comment}{extra} |")
            
            doc_lines.append("")
        
        # 保存文档
        doc_content = "\n".join(doc_lines)
        docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
        os.makedirs(docs_dir, exist_ok=True)
        doc_path = os.path.join(docs_dir, 'DATABASE_SCHEMA.md')
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        logger.info(f"✓ 文档已保存: {doc_path}")
        return doc_content
    
    def run(self):
        """执行所有优化"""
        logger.info("\n" + "="*60)
        logger.info("基金分析系统 - 数据库结构优化")
        logger.info("="*60)
        
        # 连接数据库
        if not self.connect():
            return False
        
        try:
            # 优化各个表
            tables_to_optimize = [
                'fund_analysis_results',
                'fund_basic_info',
                'fund_performance',
                'user_holdings',
                'analysis_summary',
                'user_strategies',
                'strategy_backtest_results',
                'fund_heavyweight_stocks',
            ]
            
            for table in tables_to_optimize:
                self.optimize_table(table)
            
            # 生成文档
            self.generate_documentation()
            
            logger.info("\n" + "="*60)
            logger.info("✅ 数据库优化完成！")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"优化过程出错: {e}")
            return False
        finally:
            self.close()


def main():
    """主函数"""
    optimizer = DatabaseOptimizer()
    optimizer.run()


if __name__ == '__main__':
    main()
