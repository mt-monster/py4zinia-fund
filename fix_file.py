import re

# 读取文件内容
file_path = 'd:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到所有script标签的开始和结束位置
script_start_pattern = r'<script[^>]*>'
script_end_pattern = r'</script>'

# 查找所有script标签的开始和结束位置
starts = [(m.start(), m.end()) for m in re.finditer(script_start_pattern, content)]
ends = [(m.start(), m.end()) for m in re.finditer(script_end_pattern, content)]

print(f"找到 {len(starts)} 个开始的script标签")
print(f"找到 {len(ends)} 个结束的script标签")

# 检查是否有不匹配的情况
if len(starts) != len(ends):
    print("警告：script标签数量不匹配！")
else:
    print("script标签数量匹配")

# 修复HTML结构：确保JavaScript代码在script标签内部
# 搜索位于script标签外但在应该在script内的JavaScript代码模式
js_outside_script_pattern = r'(?<!<script.*?)(\s*\w+\s*=.*?function\s+\w+\s*\(|async\s+function\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=)'
js_functions_pattern = r'(renderSidebarNavHistory|loadSidebarStageReturns|renderStageReturns)'

# 找到有问题的部分并修复
# 首先定位到我们之前发现的问题区域
problem_area_start = content.find('业绩走势</div>')
problem_area_end = content.find('async function loadSidebarStageReturns')

if problem_area_start != -1 and problem_area_end != -1:
    # 提取问题区域
    before_problem = content[:problem_area_start]
    problem_section = content[problem_area_start:problem_area_end]
    after_problem = content[problem_area_end:]
    
    # 修复问题区域：添加缺失的HTML结束标签和script标签
    fixed_section = '''
                        <div class="sidebar-chart-tab" data-type="analysis" style="padding: 12px 16px; font-size: 0.9rem; color: #7f8c8d; cursor: pointer;">持仓分析</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
'''
    
    # 重新组合文件
    fixed_content = before_problem + fixed_section + after_problem
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("文件已修复！")
else:
    print("未找到预期的问题区域")
