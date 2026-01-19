import re

def check_html_structure(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 使用更精确的正则表达式来查找div标签
    tokens = []
    
    # 查找所有<div>和</div>标签及其位置
    for match in re.finditer(r'</?div\b', content):
        is_closing = match.group()[1] == '/'  # 检查是否是闭合标签
        tokens.append((match.start(), is_closing))
    
    # 检查标签匹配
    stack = []
    unmatched_closing = []
    
    for pos, is_closing in tokens:
        if is_closing:
            if stack:
                stack.pop()  # 匹配成功
            else:
                unmatched_closing.append(pos)  # 多余的闭合标签
        else:
            stack.append(pos)  # 开始标签入栈
    
    print(f"未匹配的开始<div>标签数量: {len(stack)}")
    print(f"未匹配的结束</div>标签数量: {len(unmatched_closing)}")
    
    if stack:
        print("开始<div>标签位置（前10个）:")
        for i, pos in enumerate(stack[:10]):
            # 获取该位置附近的上下文
            start = max(0, pos - 20)
            end = min(len(content), pos + 50)
            context = content[start:end]
            print(f"  位置 {pos}: '{context}'")
    
    if unmatched_closing:
        print("结束</div>标签位置（前10个）:")
        for i, pos in enumerate(unmatched_closing[:10]):
            # 获取该位置附近的上下文
            start = max(0, pos - 20)
            end = min(len(content), pos + 50)
            context = content[start:end]
            print(f"  位置 {pos}: '{context}'")
    
    return len(stack), len(unmatched_closing)

# 检查文件
stack_count, closing_count = check_html_structure('d:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html')

if stack_count == 0 and closing_count == 0:
    print("\n✓ 所有div标签都已正确匹配！")
else:
    print(f"\n✗ 还存在 {stack_count} 个未闭合的<div>标签和 {closing_count} 个多余的</div>标签")