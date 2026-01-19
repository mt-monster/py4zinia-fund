import re

# 读取文件内容
file_path = 'd:/codes/py4zinia/pro2/fund_search/web/templates/my_holdings.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到所有script标签的起始和结束位置
script_starts = [(m.start(), m.group()) for m in re.finditer(r'<script[^>]*>', content)]
script_ends = [m.start() for m in re.finditer(r'</script>', content)]

print(f"Script开始位置: {[pos for pos, tag in script_starts]}")
print(f"Script结束位置: {script_ends}")

# 找到最后一个script标签的起始位置
if script_starts:
    last_script_start_pos = script_starts[-1][0]
    print(f"最后一个script标签起始位置: {last_script_start_pos}")
    
    # 检查在此之后是否有script结束标签
    after_last_start = content[last_script_start_pos:]
    if '</script>' not in after_last_start:
        # 如果最后的script标签没有闭合，在文件末尾添加
        print("发现未闭合的script标签，正在修复...")
        
        # 找到最后一个有意义的代码位置（在下一个script开始之前或文件末尾）
        next_script_start_after_last = -1
        for pos, tag in script_starts:
            if pos > last_script_start_pos:
                next_script_start_after_last = pos
                break
        
        if next_script_start_after_last != -1:
            # 在下一个script标签之前插入结束标签
            insert_pos = next_script_start_after_last
            fixed_content = content[:insert_pos] + '</script>\n' + content[insert_pos:]
        else:
            # 在文件末尾但要在body和html标签之前插入
            body_end_pos = content.rfind('</body>')
            html_end_pos = content.rfind('</html>')
            
            if body_end_pos != -1:
                insert_pos = body_end_pos
                fixed_content = content[:insert_pos] + '    </script>\n' + content[insert_pos:]
            elif html_end_pos != -1:
                insert_pos = html_end_pos
                fixed_content = content[:insert_pos] + '    </script>\n' + content[insert_pos:]
            else:
                # 如果找不到body或html标签，就在文件末尾添加
                fixed_content = content + '</script>\n'
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("文件已修复！")
    else:
        print("所有script标签均已正确闭合")
else:
    print("未找到script标签")