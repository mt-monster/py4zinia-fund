#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查看基金列表"""

import sys
sys.path.insert(0, '.')

from fund_search.core.db import get_connection

def get_fund_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT fund_code, fund_name FROM user_holdings WHERE is_deleted = 0 ORDER BY fund_code')
    funds = cursor.fetchall()
    cursor.close()
    conn.close()
    return funds

if __name__ == '__main__':
    funds = get_fund_list()
    print('基金列表：')
    for f in funds:
        print(f'  {f[0]} - {f[1]}')
    print(f'\n共 {len(funds)} 只基金')
