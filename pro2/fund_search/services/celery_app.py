#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
services/celery_app.py — 兼容转发层

Celery 应用实例已统一到顶层 celery_tasks/celery_app.py。
此文件保留 celery_app 变量引用，防止旧代码 from services.celery_app import celery_app 报错。
"""

from celery_tasks.celery_app import celery_app, init_celery, get_celery_app, create_celery_app

__all__ = ['celery_app', 'init_celery', 'get_celery_app', 'create_celery_app']
