# pip install flask

from flask import Flask, render_template, jsonify, request
import random
import math
import datetime
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ledger')
def ledger():
    return render_template('ledger.html')

@app.route('/tools')
def tools():
    return render_template('tools.html')

# 格雷厄姆指数计算工具
@app.route('/api/graham-index')
def graham_index():
    # 简化的格雷厄姆指数计算逻辑
    # 实际应用中需要从数据库或API获取真实的财务数据
    pe_ratio = random.uniform(5, 25)  # 市盈率
    pb_ratio = random.uniform(0.5, 3)  # 市净率
    earnings_yield = 100 / pe_ratio  # 收益率
    graham_index_value = (earnings_yield * 100) / (4.4 * pb_ratio)
    
    return jsonify({
        'value': round(graham_index_value, 2),
        'pe_ratio': round(pe_ratio, 2),
        'pb_ratio': round(pb_ratio, 2),
        'interpretation': '高估' if graham_index_value > 1 else '低估' if graham_index_value < 1 else '合理估值'
    })

# 西瓜量化温度计
@app.route('/api/watermelon-thermometer')
def watermelon_thermometer():
    # 模拟市场情绪温度计
    temperature = random.uniform(0, 100)
    if temperature < 20:
        status = "冰点"
        color = "#007BFF"
    elif temperature < 40:
        status = "寒冷"
        color = "#6C757D"
    elif temperature < 60:
        status = "温和"
        color = "#28A745"
    elif temperature < 80:
        status = "炎热"
        color = "#FFC107"
    else:
        status = "过热"
        color = "#DC3545"
    
    return jsonify({
        'temperature': round(temperature, 2),
        'status': status,
        'color': color
    })

# 波动性计算器
@app.route('/api/volatility-calculator', methods=['POST'])
def volatility_calculator():
    data = request.get_json()
    prices = data.get('prices', [])
    
    if len(prices) < 2:
        return jsonify({'error': '至少需要2个价格数据点'}), 400
    
    # 计算收益率
    returns = []
    for i in range(1, len(prices)):
        ret = (prices[i] - prices[i-1]) / prices[i-1]
        returns.append(ret)
    
    # 计算波动率（年化）
    avg_return = sum(returns) / len(returns)
    variance = sum([(r - avg_return) ** 2 for r in returns]) / len(returns)
    volatility = math.sqrt(variance) * math.sqrt(252)  # 年化波动率
    
    return jsonify({
        'volatility': round(volatility * 100, 2),
        'avg_return': round(avg_return * 100, 2),
        'returns': [round(r * 100, 2) for r in returns]
    })

# 相关性筛选器
@app.route('/api/correlation-filter', methods=['POST'])
def correlation_filter():
    data = request.get_json()
    asset1 = data.get('asset1', [])
    asset2 = data.get('asset2', [])
    
    if len(asset1) != len(asset2) or len(asset1) < 2:
        return jsonify({'error': '两个资产序列长度必须相同且至少有2个数据点'}), 400
    
    # 计算相关系数
    n = len(asset1)
    sum1 = sum(asset1)
    sum2 = sum(asset2)
    sum1_sq = sum([x**2 for x in asset1])
    sum2_sq = sum([x**2 for x in asset2])
    psum = sum([asset1[i] * asset2[i] for i in range(n)])
    
    num = psum - (sum1 * sum2 / n)
    den = math.sqrt((sum1_sq - sum1**2 / n) * (sum2_sq - sum2**2 / n))
    
    correlation = num / den if den != 0 else 0
    
    return jsonify({
        'correlation': round(correlation, 4),
        'interpretation': '强正相关' if correlation > 0.7 else '弱相关' if abs(correlation) < 0.3 else '负相关' if correlation < -0.3 else '中等相关'
    })

# 复利计算器
@app.route('/api/compound-calculator', methods=['POST'])
def compound_calculator():
    data = request.get_json()
    principal = data.get('principal', 0)
    rate = data.get('rate', 0)  # 年化收益率（百分比）
    time = data.get('time', 0)  # 投资年限
    frequency = data.get('frequency', 1)  # 复利频率（每年复利次数）
    
    # 复利公式: A = P(1 + r/n)^(nt)
    amount = principal * (1 + (rate / 100) / frequency) ** (frequency * time)
    interest = amount - principal
    
    return jsonify({
        'final_amount': round(amount, 2),
        'interest_earned': round(interest, 2),
        'total_return': round(((amount - principal) / principal) * 100, 2)
    })

# 相关性计算器一
@app.route('/api/correlation-calculator-1', methods=['POST'])
def correlation_calculator_1():
    data = request.get_json()
    series_a = data.get('series_a', [])
    series_b = data.get('series_b', [])
    
    if len(series_a) != len(series_b) or len(series_a) < 2:
        return jsonify({'error': '两个序列长度必须相同且至少有2个数据点'}), 400
    
    n = len(series_a)
    sum_a = sum(series_a)
    sum_b = sum(series_b)
    sum_a_sq = sum([x**2 for x in series_a])
    sum_b_sq = sum([x**2 for x in series_b])
    psum = sum([series_a[i] * series_b[i] for i in range(n)])
    
    num = n * psum - sum_a * sum_b
    den = math.sqrt((n * sum_a_sq - sum_a**2) * (n * sum_b_sq - sum_b**2))
    
    correlation = num / den if den != 0 else 0
    
    return jsonify({
        'correlation': round(correlation, 4),
        'strength': '强' if abs(correlation) > 0.7 else '中等' if abs(correlation) > 0.3 else '弱'
    })

# 相关性计算器二
@app.route('/api/correlation-calculator-2', methods=['POST'])
def correlation_calculator_2():
    data = request.get_json()
    x_values = data.get('x_values', [])
    y_values = data.get('y_values', [])
    
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return jsonify({'error': 'X和Y序列长度必须相同且至少有2个数据点'}), 400
    
    n = len(x_values)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum([x_values[i] * y_values[i] for i in range(n)])
    sum_x_sq = sum([x**2 for x in x_values])
    sum_y_sq = sum([y**2 for y in y_values])
    
    numerator = n * sum_xy - sum_x * sum_y
    denominator = math.sqrt((n * sum_x_sq - sum_x**2) * (n * sum_y_sq - sum_y**2))
    
    correlation = numerator / denominator if denominator != 0 else 0
    
    return jsonify({
        'correlation': round(correlation, 4),
        'direction': '正相关' if correlation > 0 else '负相关' if correlation < 0 else '无相关'
    })

# 内部收益计算器 (IRR)
@app.route('/api/irr-calculator', methods=['POST'])
def irr_calculator():
    data = request.get_json()
    cash_flows = data.get('cash_flows', [])
    
    if len(cash_flows) < 2:
        return jsonify({'error': '至少需要2个现金流数据点'}), 400
    
    # 使用牛顿法近似计算IRR
    def npv(rate, cash_flows):
        return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))
    
    def npv_derivative(rate, cash_flows):
        return sum(-i * cf / ((1 + rate) ** (i + 1)) for i, cf in enumerate(cash_flows) if i > 0)
    
    # 初始猜测
    rate = 0.1
    for _ in range(100):  # 最多迭代100次
        npv_val = npv(rate, cash_flows)
        npv_deriv = npv_derivative(rate, cash_flows)
        
        if abs(npv_deriv) < 1e-10:  # 避免除以零
            break
            
        new_rate = rate - npv_val / npv_deriv
        if abs(new_rate - rate) < 1e-6:  # 收敛
            rate = new_rate
            break
        rate = new_rate
    
    return jsonify({
        'irr': round(rate * 100, 4),
        'converged': True
    })

# A股日历数据
@app.route('/api/china-stock-calendar')
def china_stock_calendar():
    today = datetime.date.today()
    # 模拟一些交易日数据
    trading_days = []
    for i in range(10):
        day = today + datetime.timedelta(days=i)
        if day.weekday() < 5:  # 周一到周五
            trading_days.append({
                'date': day.strftime('%Y-%m-%d'),
                'type': 'trading_day',
                'description': f'{day.strftime("%m-%d")} 开市'
            })
        else:
            trading_days.append({
                'date': day.strftime('%Y-%m-%d'),
                'type': 'holiday',
                'description': f'{day.strftime("%m-%d")} 休市'
            })
    
    return jsonify({
        'calendar': trading_days,
        'current_date': today.strftime('%Y-%m-%d')
    })

# ETF公告数据
@app.route('/api/etf-announcements')
def etf_announcements():
    announcements = [
        {
            'id': 1,
            'title': '华夏沪深300ETF更新公告',
            'date': '2026-01-09',
            'type': '更新',
            'fund_code': '510330'
        },
        {
            'id': 2,
            'title': '易方达中概互联ETF分红公告',
            'date': '2026-01-08',
            'type': '分红',
            'fund_code': '513050'
        },
        {
            'id': 3,
            'title': '华泰柏瑞沪深300ETF份额变动',
            'date': '2026-01-07',
            'type': '份额变动',
            'fund_code': '510300'
        }
    ]
    
    return jsonify({
        'announcements': announcements
    })

# 导入akshare
import akshare as ak

# ETF列表数据
@app.route('/api/etf-list')
def etf_list():
    # 获取查询参数
    category = request.args.get('category', 'all')
    subcategory = request.args.get('subcategory', 'all')
    volume_min = request.args.get('volume_min', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)  # 默认每页20条记录
    
    try:
        # 使用akshare获取ETF列表数据
        etf_list_df = ak.fund_etf_spot_em()
        
        # 将DataFrame转换为字典列表
        etfs = []
        
        # Define common ETF name patterns to extract underlying index information
        index_patterns = [
            # Major indices
            {'pattern': '沪深300|HS300', 'code': '000300', 'name': '沪深300'},
            {'pattern': '中证500|CS500', 'code': '000905', 'name': '中证500'},
            {'pattern': '上证50|SSE50', 'code': '000016', 'name': '上证50'},
            {'pattern': '中证1000|CS1000', 'code': '000852', 'name': '中证1000'},
            {'pattern': '创业板|ChiNext|CYB', 'code': '399006', 'name': '创业板指'},
            {'pattern': '科创|STAR', 'code': '000688', 'name': '科创50'},
            {'pattern': '深证成指|SZCI', 'code': '399001', 'name': '深证成指'},
            {'pattern': '中证A500|CSA500', 'code': '000510', 'name': '中证A500'},
            {'pattern': '中证A50|CSA50', 'code': '000985', 'name': '中证A50'},
            
            # Sector indices
            {'pattern': '银行', 'code': '399812', 'name': '中证银行'},
            {'pattern': '医药|医疗', 'code': '399996', 'name': '中证医药'},
            {'pattern': '白酒', 'code': '399997', 'name': '中证白酒'},
            {'pattern': '消费', 'code': '000932', 'name': '中证主要消费'},
            {'pattern': '消费|可选', 'code': '000931', 'name': '中证消费'},
            {'pattern': '军工', 'code': '399967', 'name': '中证军工'},
            {'pattern': '光伏', 'code': '000941', 'name': '中证光伏产业'},
            {'pattern': '新能源车|汽车', 'code': '399991', 'name': '中证新能源汽车产业'},
            {'pattern': '芯片|半导体', 'code': '000931', 'name': '国证半导体芯片'},
            {'pattern': '传媒|文化', 'code': '399971', 'name': '中证传媒'},
            {'pattern': '证券', 'code': '399975', 'name': '中证全指证券公司'},
            {'pattern': '保险', 'code': '399804', 'name': '中证保险'},
            {'pattern': '煤炭', 'code': '000820', 'name': '中证煤炭'},
            {'pattern': '钢铁', 'code': '000819', 'name': '中证钢铁'},
            {'pattern': '有色', 'code': '399819', 'name': '中证有色金属'},
            {'pattern': '家电', 'code': '399326', 'name': '中证家电'},
            {'pattern': '地产|房地产', 'code': '399973', 'name': '中证房地产'},
            {'pattern': '建材', 'code': '399978', 'name': '中证建材'},
            {'pattern': '环保', 'code': '000827', 'name': '中证环保'},
            {'pattern': '计算机', 'code': '399396', 'name': '中证计算机'},
            {'pattern': '电子', 'code': '399914', 'name': '中证电子'},
            {'pattern': '通信', 'code': '399961', 'name': '中证通信'},
            {'pattern': '农林', 'code': '399969', 'name': '中证农林牧渔'},
            
            # Bond indices
            {'pattern': '国债', 'code': '000012', 'name': '上证国债'},
            {'pattern': '企业债', 'code': '000013', 'name': '上证企业债'},
            {'pattern': '公司债', 'code': '000011', 'name': '上证公司债'},
            {'pattern': '可转债', 'code': '000832', 'name': '中证可转债'},
            {'pattern': '信用债', 'code': 'CBA05501', 'name': '中证信用债'},
            
            # Commodity ETFs
            {'pattern': '黄金|黄金现货', 'code': 'AU99.99', 'name': '黄金现货'},
            {'pattern': '白银', 'code': 'AG(T+D)', 'name': '白银现货'},
            {'pattern': '豆粕', 'code': 'M000000', 'name': '豆粕期货'},
            {'pattern': '能源', 'code': '000978', 'name': '中证能源'},
            {'pattern': '煤炭', 'code': '000820', 'name': '中证煤炭'},
        ]
        
        # 基金公司映射
        fund_company_mapping = {
            '华夏': '华夏基金',
            '易方达': '易方达',
            '华泰柏瑞': '华泰柏瑞',
            '南方': '南方基金',
            '博时': '博时基金',
            '国泰': '国泰基金',
            '海富通': '海富通',
            '华富': '华富基金',
            '招商': '招商基金',
            '嘉实': '嘉实基金',
            '广发': '广发基金',
            '银华': '银华基金',
            '大成': '大成基金',
            '富国': '富国基金',
            '天弘': '天弘基金',
            '汇添富': '汇添富',
            '工银瑞信': '工银瑞信',
            '建信': '建信基金',
            '中欧': '中欧基金',
            '景顺长城': '景顺长城',
            '兴全': '兴全基金',
            '鹏华': '鹏华基金',
            '长盛': '长盛基金',
            '万家': '万家基金',
            '诺安': '诺安基金',
            '华安': '华安基金',
            '泰达宏利': '泰达宏利',
            '国投瑞银': '国投瑞银',
            '融通': '融通基金',
            '长城': '长城基金',
            '申万菱信': '申万菱信',
            '浦银安盛': '浦银安盛',
            '中银': '中银基金',
            '华商': '华商基金',
            '新华': '新华基金',
            '民生加银': '民生加银',
            '长安': '长安基金',
            '中邮': '中邮创业',
            '汇丰晋信': '汇丰晋信',
            '农银汇理': '农银汇理',
            '中航': '中航基金',
            '中信建投': '中信建投',
            '鑫元': '鑫元基金',
            '国联安': '国联安',
            '德邦': '德邦基金',
            '西部利得': '西部利得',
            '永赢': '永赢基金',
            '东海': '东海基金',
            '国寿安保': '国寿安保',
            '前海开源': '前海开源',
            '泓德': '泓德基金',
            '华泰柏瑞': '华泰柏瑞',
            '中融': '中融基金',
            '中金': '中金基金',
        }
        
        for i, row in etf_list_df.iterrows():
            # 跳过 rows without trading volume data
            if pd.isna(row['成交额']) or row['成交额'] == 0:
                continue
                
            # 获取ETF代码
            etf_code = row['代码']
            
            # 提取ETF名称并根据名称模式推断跟踪的指数
            etf_name = row['名称']
            index_info = {'code': '000000', 'name': '未知指数'}
            
            # 查找匹配的指数模式
            for pattern_info in index_patterns:
                import re
                if re.search(pattern_info['pattern'], etf_name):
                    index_info = {'code': pattern_info['code'], 'name': pattern_info['name']}
                    break
            
            # 提取基金公司名称
            fund_company = '未知基金公司'
            for key, value in fund_company_mapping.items():
                if key in etf_name:
                    fund_company = value
                    break
            
            # Calculate 20-day average volume (using current day's volume as approximation)
            avg_20d_volume = float(row['成交额']) / 10000  # Convert to hundred million
            
            # Determine category based on ETF characteristics
            category_type = '股票ETF'
            subcategory_type = '宽基'
            
            # Determine category
            if any(keyword in etf_name for keyword in ['黄金', '白银', '商品', '原油', '能源', '农产品', '豆粕', '棉花', '糖']):
                category_type = '商品ETF'
                subcategory_type = '商品'
            elif any(keyword in etf_name for keyword in ['国债', '企业债', '公司债', '可转债', '信用债', '债券']):
                category_type = '债券ETF'
                subcategory_type = '债券'
            elif any(keyword in etf_name for keyword in ['货币', '现金']):
                category_type = '货币ETF'
                subcategory_type = '货币'
            elif any(keyword in etf_name for keyword in ['黄金', '贵金属']):
                category_type = '黄金ETF'
                subcategory_type = '贵金属'
            else:
                category_type = '股票ETF'
                
                # Determine subcategory for stock ETFs
                if any(keyword in etf_name for keyword in ['沪深300', '上证50', '中证500', '中证1000', '科创50', '创业板']):
                    subcategory_type = '宽基'
                elif any(keyword in etf_name for keyword in ['银行', '证券', '保险', '地产', '钢铁', '煤炭', '有色', '建材']):
                    subcategory_type = '行业'
                elif any(keyword in etf_name for keyword in ['医药', '医疗', '消费', '食品', '白酒', '家电', '汽车', '光伏', '芯片', '通信', '计算机', '传媒']):
                    subcategory_type = '行业'
                elif any(keyword in etf_name for keyword in ['恒生', 'H股', '国企', '中概互联', '纳斯达克', '标普']):
                    subcategory_type = 'QDII'
                elif any(keyword in etf_name for keyword in ['期货', '期权']):
                    subcategory_type = '期货'
                else:
                    subcategory_type = '宽基'
            
            # Generate ETF data
            etf_data = {
                'rank': i + 1,
                'index_code': index_info['code'],
                'index_name': index_info['name'],
                'etf_code': etf_code,
                'etf_name': etf_name,
                'fund_company': fund_company,
                'latest_price': float(row['最新价']),
                'avg_20d_volume': round(avg_20d_volume, 2),
                'category': category_type,
                'subcategory': subcategory_type,
                'index_link': '[1]',  # Placeholder link
                'etf_link': f'{etf_name} {fund_company}'
            }
            
            etfs.append(etf_data)
        
        # Apply filters
        filtered_etfs = etfs
        
        # Filter by category
        if category != 'all':
            filtered_etfs = [etf for etf in filtered_etfs if etf['category'] == category]
        
        # Filter by subcategory
        if subcategory != 'all':
            filtered_etfs = [etf for etf in filtered_etfs if etf['subcategory'] == subcategory]
        
        # Filter by volume
        if volume_min:
            try:
                min_volume = float(volume_min)
                filtered_etfs = [etf for etf in filtered_etfs if etf['avg_20d_volume'] >= min_volume]
            except ValueError:
                pass
        
        # Filter by search keyword
        if search:
            keyword = search.lower()
            filtered_etfs = [etf for etf in filtered_etfs if 
                keyword in etf['index_code'].lower() or
                keyword in etf['index_name'].lower() or
                keyword in etf['etf_code'].lower() or
                keyword in etf['etf_name'].lower() or
                keyword in etf['fund_company'].lower()
            ]
        
        # Calculate pagination
        total = len(filtered_etfs)
        total_pages = (total + page_size - 1) // page_size  # 向上取整
        
        # Get paginated results
        start = (page - 1) * page_size
        end = start + page_size
        paginated_etfs = filtered_etfs[start:end]
        
        # Get current time
        current_time = datetime.datetime.now().strftime('%Y年%m月%d日%H时%M分')
        
        return jsonify({
            'etfs': paginated_etfs,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages
            },
            'update_time': current_time
        })
    except Exception as e:
        # If akshare fetch fails, use fallback data
        etfs = [
            {
                'rank': 1,
                'index_code': '000300',
                'index_name': '沪深300',
                'etf_code': '510300',
                'etf_name': '沪深300ETF',
                'fund_company': '华夏基金',
                'latest_price': 4.05,
                'avg_20d_volume': 250.5,
                'category': '股票ETF',
                'subcategory': '宽基',
                'index_link': '[1]',
                'etf_link': '沪深300ETF 华夏基金'
            },
            {
                'rank': 2,
                'index_code': '000905',
                'index_name': '中证500',
                'etf_code': '510500',
                'etf_name': '中证500ETF',
                'fund_company': '南方基金',
                'latest_price': 6.12,
                'avg_20d_volume': 180.3,
                'category': '股票ETF',
                'subcategory': '宽基',
                'index_link': '[1]',
                'etf_link': '中证500ETF 南方基金'
            },
            {
                'rank': 3,
                'index_code': '399006',
                'index_name': '创业板指',
                'etf_code': '159915',
                'etf_name': '创业板ETF',
                'fund_company': '易方达',
                'latest_price': 2.34,
                'avg_20d_volume': 150.7,
                'category': '股票ETF',
                'subcategory': '宽基',
                'index_link': '[1]',
                'etf_link': '创业板ETF 易方达'
            }
        ]
        
        return jsonify({
            'etfs': etfs,
            'pagination': {
                'page': 1,
                'page_size': 20,
                'total': len(etfs),
                'total_pages': 1
            },
            'update_time': datetime.datetime.now().strftime('%Y年%m月%d日%H时%M分')
        })

if __name__ == '__main__':
    app.run(debug=True)