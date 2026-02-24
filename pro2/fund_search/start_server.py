import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# “÷÷∆æØ∏Ê
import warnings
warnings.filterwarnings('ignore')

from web.app import app

print('='*60)
print('  Fund Analysis System - Web Server')
print('='*60)
print('  URL: http://127.0.0.1:5000')
print('  API Docs: http://127.0.0.1:5000/api/')
print('='*60)
print('  Press Ctrl+C to stop')
print('='*60)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
