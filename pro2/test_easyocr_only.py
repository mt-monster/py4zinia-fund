#!/usr/bin/env python
# coding: utf-8

"""
测试仅使用EasyOCR
"""

import os
import base64
from fund_search.data_retrieval.fund_screenshot_ocr import recognize_with_easyocr

def test_easyocr_only():
    """测试仅使用EasyOCR"""
    # 设置环境变量强制使用EasyOCR
    os.environ['FORCE_EASYOCR'] = 'true'
    
    # 创建一个简单的白色图片用于测试
    from PIL import Image
    import numpy as np
    
    # 创建一个100x50的白色图片
    image = Image.new('RGB', (100, 50), color='white')
    
    # 转换为numpy数组
    image_array = np.array(image)
    
    # 转换为字节
    import io
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # 转换为base64
    image_data = base64.b64encode(img_byte_arr).decode('utf-8')
    
    try:
        # 测试EasyOCR
        result = recognize_with_easyocr(image_data, use_gpu=False)
        print(f"EasyOCR测试成功，识别结果: {result}")
        return True
    except Exception as e:
        print(f"EasyOCR测试失败: {e}")
        return False

if __name__ == "__main__":
    test_easyocr_only()