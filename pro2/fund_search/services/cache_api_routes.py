#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存相关API路由

提供缓存管理、实时持仓数据获取等接口
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
cache_bp = Blueprint('cache_api', __name__, url_prefix='/api')

# 全局服务实例（在init时注入）
cache_manager = None
holding_service = None
sync_service = None


def init_cache_routes(app, cache_mgr, holding_svc, sync_svc):
    """初始化缓存路由"""
    global cache_manager, holding_service, sync_service
    cache_manager = cache_mgr
    holding_service = holding_svc
    sync_service = sync_svc
    
    app.register_blueprint(cache_bp)
    logger.info("缓存API路由已注册")


# ==================== 新的持仓数据API（使用缓存）====================

@cache_bp.route('/my-holdings/combined', methods=['GET'])
def get_my_holdings_combined():
    """
    获取持仓组合数据（分层缓存版）
    
    数据分级：
    - 实时数据（日涨跌幅）：每次请求实时获取
    - 准实时数据（昨日数据）：内存缓存15分钟
    - 低频指标（年化收益、夏普等）：数据库缓存1天
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        if not holding_service:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500
        
        # 使用分层服务获取数据
        holdings = holding_service.get_holdings_data(user_id)
        
        return jsonify({
            'success': True,
            'data': holdings,
            'meta': {
                'fetch_time': datetime.now().strftime('%H:%M:%S'),
                'count': len(holdings),
                'data_freshness': {
                    'realtime': '实时获取',
                    'yesterday_data': '内存缓存15分钟',
                    'performance': '数据库缓存1天'
                }
            }
        })
        
    except Exception as e:
        logger.error(f"获取持仓数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/my-holdings/realtime', methods=['GET'])
def get_my_holdings_realtime():
    """
    仅获取实时数据（用于定时刷新）
    
    只返回实时字段，减少数据传输量
    """
    try:
        user_id = request.args.get('user_id', 'default_user')
        fund_codes_param = request.args.get('codes', '')
        
        if not holding_service:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500
        
        fund_codes = [c.strip() for c in fund_codes_param.split(',') if c.strip()]
        
        if not fund_codes:
            return jsonify({'success': True, 'data': []})
        
        # 只获取实时数据
        realtime_data = holding_service.refresh_realtime_only(user_id, fund_codes)
        
        return jsonify({
            'success': True,
            'data': realtime_data,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"获取实时数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 缓存管理API ====================

@cache_bp.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """获取缓存统计信息"""
    try:
        if not cache_manager:
            return jsonify({'success': False, 'error': '缓存管理器未初始化'}), 500
        
        stats = cache_manager.get_cache_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/cache/invalidate', methods=['POST'])
def invalidate_cache():
    """使缓存失效"""
    try:
        if not cache_manager:
            return jsonify({'success': False, 'error': '缓存管理器未初始化'}), 500
        
        data = request.get_json() or {}
        fund_code = data.get('fund_code')
        cache_type = data.get('type', 'all')  # all, memory, performance
        
        if cache_type == 'all' or cache_type == 'memory':
            if fund_code:
                # 清除特定基金的内存缓存
                cache_manager.invalidate_memory_cache(fund_code)
            else:
                # 清除所有内存缓存
                cache_manager.invalidate_memory_cache()
        
        if cache_type == 'performance' and fund_code:
            # 使绩效缓存失效（通过重新计算）
            cache_manager.get_performance_metrics(fund_code, force_refresh=True)
        
        return jsonify({
            'success': True,
            'message': f'缓存已清除: {fund_code or "全部"} ({cache_type})'
        })
        
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/cache/fund/<fund_code>/sync', methods=['POST'])
def manual_sync_fund(fund_code):
    """手动同步单只基金数据"""
    try:
        if not sync_service:
            return jsonify({'success': False, 'error': '同步服务未初始化'}), 500
        
        success = sync_service.manual_sync_fund(fund_code)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'基金 {fund_code} 同步成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'基金 {fund_code} 同步失败'
            }), 500
            
    except Exception as e:
        logger.error(f"手动同步失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@cache_bp.route('/cache/sync/status', methods=['GET'])
def get_sync_status():
    """获取同步任务状态"""
    try:
        if not cache_manager or not cache_manager.db:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500
        
        # 获取最近的同步任务
        sql = """
            SELECT job_name, job_type, status, start_time, end_time,
                   total_count, success_count, fail_count
            FROM fund_sync_job_log
            WHERE start_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ORDER BY start_time DESC
            LIMIT 10
        """
        
        df = cache_manager.db.execute_query(sql)
        
        jobs = []
        if not df.empty:
            for _, row in df.iterrows():
                jobs.append({
                    'job_name': row['job_name'],
                    'job_type': row['job_type'],
                    'status': row['status'],
                    'start_time': row['start_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['start_time'], 'strftime') else str(row['start_time']),
                    'end_time': row['end_time'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['end_time'], 'strftime') else str(row['end_time']),
                    'total_count': int(row['total_count']),
                    'success_count': int(row['success_count']),
                    'fail_count': int(row['fail_count'])
                })
        
        # 获取待同步的基金数量
        pending_sql = """
            SELECT COUNT(*) as pending_count
            FROM fund_cache_metadata
            WHERE sync_status = 'pending'
               OR (next_sync_at <= NOW() AND sync_status != 'syncing')
        """
        
        pending_df = cache_manager.db.execute_query(pending_sql)
        pending_count = int(pending_df.iloc[0]['pending_count']) if not pending_df.empty else 0
        
        return jsonify({
            'success': True,
            'data': {
                'recent_jobs': jobs,
                'pending_count': pending_count,
                'service_running': sync_service is not None and getattr(sync_service, 'running', False)
            }
        })
        
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 数据一致性检查API ====================

@cache_bp.route('/cache/health-check', methods=['GET'])
def cache_health_check():
    """缓存健康检查"""
    try:
        if not cache_manager or not cache_manager.db:
            return jsonify({'success': False, 'error': '服务未初始化'}), 500
        
        issues = []
        
        # 检查过期数据
        stale_sql = """
            SELECT fund_code, latest_date, last_sync_at
            FROM fund_cache_metadata
            WHERE latest_date < DATE_SUB(CURDATE(), INTERVAL 3 DAY)
              AND sync_status != 'syncing'
            LIMIT 10
        """
        
        stale_df = cache_manager.db.execute_query(stale_sql)
        if not stale_df.empty:
            issues.append({
                'type': 'stale_data',
                'message': f'发现{len(stale_df)}只基金数据过期',
                'funds': stale_df['fund_code'].tolist()
            })
        
        # 检查连续失败
        failed_sql = """
            SELECT fund_code, sync_fail_count
            FROM fund_cache_metadata
            WHERE sync_fail_count >= 3
            LIMIT 10
        """
        
        failed_df = cache_manager.db.execute_query(failed_sql)
        if not failed_df.empty:
            issues.append({
                'type': 'sync_failures',
                'message': f'发现{len(failed_df)}只基金同步连续失败',
                'funds': failed_df.to_dict('records')
            })
        
        # 获取总体统计
        stats_sql = """
            SELECT 
                COUNT(*) as total_funds,
                SUM(CASE WHEN sync_status = 'completed' THEN 1 ELSE 0 END) as synced,
                SUM(CASE WHEN sync_status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN sync_status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM fund_cache_metadata
        """
        
        stats_df = cache_manager.db.execute_query(stats_sql)
        stats = {
            'total_funds': int(stats_df.iloc[0]['total_funds']) if not stats_df.empty else 0,
            'synced': int(stats_df.iloc[0]['synced']) if not stats_df.empty else 0,
            'failed': int(stats_df.iloc[0]['failed']) if not stats_df.empty else 0,
            'pending': int(stats_df.iloc[0]['pending']) if not stats_df.empty else 0
        } if not stats_df.empty else {}
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy' if not issues else 'warning',
                'issues': issues,
                'stats': stats,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
