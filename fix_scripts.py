# 修复HTML文件结构
with open('d:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找关键位置
first_script_start = 28292  # 第一个<script>标签开始
second_script_start = 113384  # 第二个<script>标签开始

# 我们需要在第二个<script>标签之前结束第一个<script>标签
# 这意味着我们需要在content[second_script_start:]之前插入</script>

# 找到第二个<script>标签的开始位置
insert_pos = second_script_start

# 在这个位置前插入</script>
new_content = content[:insert_pos] + '</script>\n' + content[insert_pos:]

# 写回文件
with open('d:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("已添加缺失的</script>标签")
print(f"插入位置: {insert_pos}")

# 验证修复结果
import re
starts = len(re.findall(r'<script[^>]*>', new_content))
ends = len(re.findall(r'</script>', new_content))

print(f'开始的script标签数量: {starts}')
print(f'结束的script标签数量: {ends}')
print(f'是否匹配: {starts == ends}')