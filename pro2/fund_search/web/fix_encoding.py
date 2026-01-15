#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复 HTML 文件编码"""

import codecs

# 尝试多种编码读取备份文件
encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']

for encoding in encodings:
    try:
        print(f"尝试使用 {encoding} 编码读取...")
        with codecs.open('templates/fund_index_backup.html', 'r', encoding=encoding) as f:
            content = f.read()
        
        # 写入新文件，使用 UTF-8 编码
        with codecs.open('templates/fund_index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"成功！使用 {encoding} 编码读取并转换为 UTF-8")
        print(f"文件大小: {len(content)} 字符")
        break
    except Exception as e:
        print(f"使用 {encoding} 失败: {e}")
        continue
