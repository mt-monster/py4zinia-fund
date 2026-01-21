# OCR功能使用说明

## 概述

基金截图OCR识别模块支持从基金截图中自动识别基金代码和名称。系统支持两种OCR引擎：

- **EasyOCR**（默认）：兼容性好，稳定可靠
- **PaddleOCR**：识别精度高，但在某些系统上可能有兼容性问题

## 配置选项

### 环境变量配置

可以通过环境变量来配置OCR行为：

```bash
# 强制使用EasyOCR
set FORCE_EASYOCR=true

# 强制使用PaddleOCR
set FORCE_PADDLEOCR=true

# 启用GPU加速
set OCR_USE_GPU=true

# 设置置信度阈值（0.0-1.0）
set OCR_CONFIDENCE_THRESHOLD=0.6
```

### 代码配置

也可以通过修改 `data_retrieval/ocr_config.py` 文件来配置：

```python
OCR_CONFIG = {
    'default_engine': 'easyocr',  # 默认引擎
    'use_gpu': False,             # GPU加速
    'confidence_threshold': 0.5,  # 置信度阈值
}
```

## 使用方法

### 基本用法

```python
from data_retrieval.fund_screenshot_ocr import recognize_fund_screenshot

# 识别基金截图
image_data = "base64编码的图片数据"
funds = recognize_fund_screenshot(image_data)

for fund in funds:
    print(f"{fund['fund_code']} - {fund['fund_name']}")
```

### 文本解析

如果已经有OCR识别的文本，可以直接使用解析功能：

```python
from data_retrieval.fund_screenshot_ocr import parse_fund_info

texts = [
    "天弘标普500发起(QDII-FOF)A",
    "007721",
    "景顺长城全球半导体芯片股票A"
]

funds = parse_fund_info(texts)
```

## 故障排除

### PaddleOCR兼容性问题

如果遇到PaddleOCR错误（如 "ConvertPirAttribute2RuntimeAttribute not support"），可以：

1. 设置环境变量强制使用EasyOCR：
   ```bash
   set FORCE_EASYOCR=true
   ```

2. 或者修改配置文件将默认引擎改为EasyOCR

### 识别精度优化

1. **调整置信度阈值**：降低阈值可以获得更多结果，但可能包含错误识别
2. **图片质量**：确保截图清晰，文字对比度高
3. **图片格式**：支持PNG、JPG等常见格式

## 支持的基金代码格式

- 6位数字基金代码（如：007721、501225）
- 自动识别基金名称和代码的对应关系
- 支持各种基金类型标识（QDII、LOF、FOF等）

## 注意事项

1. 首次使用时会下载模型文件，需要网络连接
2. EasyOCR模型较大，首次下载可能需要几分钟
3. GPU加速需要CUDA支持，否则建议使用CPU模式
4. 识别结果会自动去重，避免重复识别同一基金