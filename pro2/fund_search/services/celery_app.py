#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery 应用初始化
异步任务处理入口
"""

import os
import sys
import logging
from celery import Celery

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.celery_config import CeleryConfig

logger = logging.getLogger(__name__)

celery_app = Celery('fund_analysis')
celery_app.config_from_object(CeleryConfig)

celery_app.autodiscover_tasks(['services.celery_tasks'])

logger.info("Celery 应用初始化完成")

if __name__ == '__main__':
    celery_app.start()

