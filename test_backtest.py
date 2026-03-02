import sys
sys.path.insert(0, '.')
from pro2.fund_search.web.routes.strategies import execute_backtest
import json

# 直接调用回测函数测试
result = execute_backtest('010052', 'default', 10000, 1000, '2024-01-01', '2024-12-31', 90, '000300')
print('Result keys:', result.keys() if isinstance(result, dict) else 'not dict')
print('total_return:', result.get('total_return') if isinstance(result, dict) else 'N/A')
print('equity_curve length:', len(result.get('equity_curve', [])) if isinstance(result, dict) else 'N/A')
print('equity_curve[:5]:', result.get('equity_curve', [])[:5] if isinstance(result, dict) else 'N/A')
print('dates length:', len(result.get('dates', [])) if isinstance(result, dict) else 'N/A')
print('benchmark_curve length:', len(result.get('benchmark_curve', [])) if isinstance(result, dict) else 'N/A')
