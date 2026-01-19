with open('d:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到第一个script标签应该结束的位置
# 它应该在第二个script标签（位置113384）开始之前结束
pos1 = 28292  # 第一个script开始
pos2 = 113384  # 第二个script开始

# 获取第一个script标签的内容，向前搜索找到一个合适的结束位置
section = content[pos1:pos2]

# 从后往前找，寻找合理的JavaScript结束点，比如函数结束的大括号或者注释行
lines = section.split('\n')

# 找到接近section末尾的一个合理位置来结束script标签
# 查找靠近末尾的函数定义或语句结束
found = False
for i in range(len(lines)-1, max(0, len(lines)-20), -1):  # 检查最后20行
    line = lines[i].strip()
    if '});' in line or ('}' in line and line.endswith('}')) or '});' in line or line.startswith('// ') or line.startswith('/*'):
        print(f'建议在倒数第 {len(lines)-i} 行结束script: "{line[:50]}"')
        found = True
        break

if not found:
    print("未找到明显的JavaScript结束点，考虑在第二个script标签之前结束")

# 实际上，最简单的方法是在第二个script标签之前结束第一个script标签
print(f'第一个script标签内容: {section[:100]}...')
print(f'到第二个script标签前的内容: {content[pos2-50:pos2+50]}')

# 让我们检查第二个script标签前的内容，找到合适的位置
before_second_script = content[pos2-200:pos2]
print(f'第二个script标签前的内容: {repr(before_second_script)}')