#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery工作进程启动脚本

用于启动Celery Worker和Beat调度器。

使用方法:
    # 启动Worker
    python -m celery_tasks.runner worker
    
    # 启动Beat（定时任务调度器）
    python -m celery_tasks.runner beat
    
    # 同时启动Worker和Beat
    python -m celery_tasks.runner both
    
    # 监控Flower
    python -m celery_tasks.runner flower
"""

import os
import sys
import argparse
import subprocess


def run_worker():
    """启动Celery Worker"""
    cmd = [
        'celery', '-A', 'celery_tasks.celery_app', 'worker',
        '--loglevel=info',
        '-Q', 'default,high_priority,low_priority',
        '-n', 'fund_platform_worker@%h',
        '--concurrency=4'
    ]
    print(f"启动Celery Worker: {' '.join(cmd)}")
    subprocess.run(cmd)


def run_beat():
    """启动Celery Beat调度器"""
    cmd = [
        'celery', '-A', 'celery_tasks.celery_app', 'beat',
        '--loglevel=info',
        '--scheduler', 'celery.beat.PersistentScheduler',
        '--schedule', 'celerybeat-schedule.db'
    ]
    print(f"启动Celery Beat: {' '.join(cmd)}")
    subprocess.run(cmd)


def run_flower():
    """启动Flower监控"""
    cmd = [
        'celery', '-A', 'celery_tasks.celery_app', 'flower',
        '--port=5555',
        '--broker=redis://localhost:6379/0'
    ]
    print(f"启动Flower监控: {' '.join(cmd)}")
    subprocess.run(cmd)


def run_both():
    """同时启动Worker和Beat"""
    import multiprocessing
    
    worker_process = multiprocessing.Process(target=run_worker)
    beat_process = multiprocessing.Process(target=run_beat)
    
    worker_process.start()
    beat_process.start()
    
    try:
        worker_process.join()
        beat_process.join()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        worker_process.terminate()
        beat_process.terminate()


def main():
    parser = argparse.ArgumentParser(description='Celery任务管理')
    parser.add_argument(
        'command',
        choices=['worker', 'beat', 'flower', 'both'],
        help='要执行的命令'
    )
    
    args = parser.parse_args()
    
    # 确保在项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    sys.path.insert(0, project_root)
    
    if args.command == 'worker':
        run_worker()
    elif args.command == 'beat':
        run_beat()
    elif args.command == 'flower':
        run_flower()
    elif args.command == 'both':
        run_both()


if __name__ == '__main__':
    main()
