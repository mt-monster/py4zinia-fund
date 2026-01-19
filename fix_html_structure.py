# 修复HTML结构：将错误地包含在script标签内的HTML内容移出
with open('d:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 定位第一个script标签的内容
script_start = 28292
script_end = 113384  # 这里是第二个<script>的开始

script_content = content[script_start:script_end]

# 找到JavaScript代码的真正结束位置
# 查找JavaScript函数或代码块的结束，然后是HTML内容的开始
lines = script_content.split('\n')

# 从后往前找，寻找JavaScript代码的结束点
js_end_line_idx = len(lines) - 1
for i in range(len(lines) - 1, -1, -1):
    line = lines[i].strip()
    # 寻找JavaScript代码的结束标志，如函数结尾、注释等
    if line.endswith('}'):  # 函数或对象的结束
        js_end_line_idx = i
        break
    elif line.startswith('//') or line.startswith('/*'):  # 注释
        js_end_line_idx = i
        break
    elif line == '':  # 空行
        continue
    elif line.startswith('</div'):  # 如果遇到HTML标签，说明找到了分界点
        js_end_line_idx = i - 1  # 在HTML标签之前结束JS
        break

# 构造修复后的内容
if js_end_line_idx >= 0:
    # 分离JavaScript代码和HTML代码
    js_lines = lines[:js_end_line_idx + 1]
    html_lines = lines[js_end_line_idx + 1:]
    
    # 重新构造内容
    new_content = (
        content[:script_start] +  # 文件开始到第一个script标签
        '<script>\n' +            # script开始标签
        '\n'.join(js_lines) +     # JavaScript代码
        '\n</script>\n' +         # script结束标签
        '\n'.join(html_lines) +   # HTML内容（移出script标签）
        content[script_end:]      # 文件其余部分
    )
    
    # 写回文件
    with open('d:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"修复完成！JavaScript代码在第{js_end_line_idx+1}行结束")
    print(f"移出了 {len(html_lines)} 行HTML内容")
    
    # 验证修复
    import re
    starts = len(re.findall(r'<script[^>]*>', new_content))
    ends = len(re.findall(r'</script>', new_content))
    open_divs = len(re.findall(r'<div\b', new_content))
    close_divs = len(re.findall(r'</div>', new_content))
    
    print(f'Script标签: {starts} 开始, {ends} 结束, 匹配: {starts==ends}')
    print(f'Div标签: {open_divs} 开始, {close_divs} 结束, 匹配: {open_divs==close_divs}')
else:
    print("未能找到合适的JavaScript/HTML分界点")