#!/usr/bin/env python
# coding: utf-8

"""
基金截图OCR识别模块
使用OCR技术识别基金截图中的基金名称和代码
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from PIL import Image
import io

logger = logging.getLogger(__name__)


def recognize_fund_screenshot(image_data: str, use_gpu: bool = False, import_to_portfolio: bool = False, user_id: str = "default", ocr_engine: str = None) -> List[Dict]:
    """
    识别基金截图中的基金信息

    参数：
    image_data: Base64编码的图片数据或图片二进制数据
    use_gpu: 是否使用GPU加速
    import_to_portfolio: 是否导入到持仓列表
    user_id: 用户ID（用于持仓导入）
    ocr_engine: 指定OCR引擎 ('baidu', 'easyocr', 'paddleocr')，None则使用配置

    返回：
    list: 识别到的基金列表，每个元素包含 fund_code、fund_name、confidence
    """
    from data_retrieval.utils.ocr_config import get_ocr_engine, validate_engine_config

    # 根据配置选择OCR引擎
    if ocr_engine is None:
        ocr_engine = get_ocr_engine()

    # 验证引擎配置
    is_valid, error_msg = validate_engine_config(ocr_engine)
    if not is_valid:
        logger.error(f"OCR引擎 {ocr_engine} 配置无效: {error_msg}")
        # 尝试使用其他可用引擎
        for fallback_engine in ['baidu', 'easyocr', 'paddleocr']:
            if fallback_engine != ocr_engine:
                is_valid, _ = validate_engine_config(fallback_engine)
                if is_valid:
                    logger.info(f"切换到备用引擎: {fallback_engine}")
                    ocr_engine = fallback_engine
                    break
        else:
            logger.error("没有可用的OCR引擎")
            return []

    ocr_texts = []

    if ocr_engine == 'baidu':
        logger.info("使用百度OCR进行识别")
        result, ocr_texts = recognize_with_baidu(image_data)
    elif ocr_engine == 'easyocr':
        logger.info("使用EasyOCR进行识别")
        result, ocr_texts = recognize_with_easyocr(image_data, use_gpu)
    else:
        logger.info("使用PaddleOCR进行识别")
        result = recognize_with_paddleocr(image_data, use_gpu)
        # 保存OCR识别的文本，避免重复识别
        ocr_texts = _get_ocr_texts_paddleocr(image_data, use_gpu)
    
    # 如果需要导入到持仓列表
    if import_to_portfolio and result:
        try:
            from .portfolio_importer import PortfolioImporter
            
            if ocr_texts:
                importer = PortfolioImporter()
                holdings = importer.extract_portfolio_from_ocr(ocr_texts)
                
                if holdings:
                    success = importer.import_to_database(holdings, user_id)
                    if success:
                        logger.info(f"成功导入 {len(holdings)} 个持仓到用户 {user_id}")
                    else:
                        logger.warning("持仓导入失败")
                else:
                    logger.warning("未能从截图中提取持仓信息")
        except Exception as e:
            logger.error(f"持仓导入过程中出错: {e}")
    
    return result


def recognize_with_paddleocr(image_data: str, use_gpu: bool = False) -> List[Dict]:
    """
    使用 PaddleOCR 进行识别
    
    参数：
    image_data: Base64编码的图片数据或图片二进制数据
    use_gpu: 是否使用GPU加速
    
    返回：
    list: 识别到的基金列表
    """
    try:
        # 处理Base64编码的图片数据
        if isinstance(image_data, str):
            import base64
            # 移除data:image/xxx;base64,前缀
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # 使用 PaddleOCR 进行识别
        from paddleocr import PaddleOCR
        
        # 初始化 OCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='ch')
        
        # 将字节数据转换为图片
        image = Image.open(io.BytesIO(image_bytes))
        
        # 执行 OCR 识别 - 新版本需要传入PIL Image或numpy array
        import numpy as np
        image_array = np.array(image)
        result = ocr.ocr(image_array)
        
        if not result or not result[0]:
            logger.warning("OCR识别结果为空")
            return []
        
        # 提取文本
        texts = []
        for line in result[0]:
            text = line[1][0]  # 获取识别的文本
            confidence = line[1][1]  # 获取置信度
            
            from data_retrieval.utils.ocr_config import get_confidence_threshold
            threshold = get_confidence_threshold()
            
            if confidence > threshold:  # 使用配置的置信度阈值
                texts.append(text)
        
        logger.info(f"OCR识别到 {len(texts)} 行文本")
        
        # 使用智能解析器进行解析
        from .smart_fund_parser import parse_fund_info_with_manual_fallback
        parse_result = parse_fund_info_with_manual_fallback(texts)
        
        funds = parse_result['funds']
        
        # 如果有手工导入建议，记录到日志
        if parse_result['manual_import_needed']:
            logger.warning(f"有 {len(parse_result['manual_items'])} 项需要手工导入")
            logger.info(parse_result['manual_prompt'])
        
        # 如果智能解析器没有结果，尝试原始解析器
        if not funds:
            from .enhanced_fund_parser import parse_fund_info_enhanced
            funds = parse_fund_info_enhanced(texts)
            
            # 如果还是没有结果，尝试基础解析器
            if not funds:
                funds = parse_fund_info(texts)
        
        return funds
        
    except ImportError:
        logger.error("PaddleOCR 未安装，请运行: pip install paddleocr")
        # 尝试使用备用方案：easyocr
        funds, _ = recognize_with_easyocr(image_data, use_gpu)
        return funds
    except Exception as e:
        logger.error(f"PaddleOCR识别失败: {e}")
        # 如果PaddleOCR失败，尝试使用EasyOCR作为备用方案
        logger.info("PaddleOCR失败，尝试使用EasyOCR作为备用方案")
        funds, _ = recognize_with_easyocr(image_data, use_gpu)
        return funds


def recognize_with_easyocr(image_data: str, use_gpu: bool = False) -> Tuple[List[Dict], List[str]]:
    """
    使用 EasyOCR 作为备用方案
    
    参数：
    image_data: Base64编码的图片数据或图片二进制数据
    use_gpu: 是否使用GPU加速
    
    返回：
    tuple: (识别到的基金列表, 识别到的文本列表)
    """
    try:
        import easyocr
        
        # 处理Base64编码的图片数据
        if isinstance(image_data, str):
            import base64
            # 移除data:image/xxx;base64,前缀
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # 初始化 EasyOCR
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=use_gpu)
        
        # 将字节数据转换为图片
        image = Image.open(io.BytesIO(image_bytes))
        
        # 执行 OCR 识别 - EasyOCR可以接受numpy array
        import numpy as np
        image_array = np.array(image)
        result = reader.readtext(image_array)
        
        # 提取文本
        texts = []
        for detection in result:
            text = detection[1]  # 获取识别的文本
            confidence = detection[2]  # 获取置信度
            
            from data_retrieval.utils.ocr_config import get_confidence_threshold
            threshold = get_confidence_threshold()
            
            if confidence > threshold:
                texts.append(text)
        
        logger.info(f"EasyOCR识别到 {len(texts)} 行文本")
        
        # 使用智能解析器进行解析
        from .smart_fund_parser import parse_fund_info_with_manual_fallback
        parse_result = parse_fund_info_with_manual_fallback(texts)
        
        funds = parse_result['funds']
        
        # 如果有手工导入建议，记录到日志
        if parse_result['manual_import_needed']:
            logger.warning(f"有 {len(parse_result['manual_items'])} 项需要手工导入")
            logger.info(parse_result['manual_prompt'])
        
        # 如果智能解析器没有结果，尝试原始解析器
        if not funds:
            from .enhanced_fund_parser import parse_fund_info_enhanced
            funds = parse_fund_info_enhanced(texts)
            
            # 如果还是没有结果，尝试基础解析器
            if not funds:
                funds = parse_fund_info(texts)
        
        return funds, texts
        
    except ImportError:
        logger.error("EasyOCR 未安装，请运行: pip install easyocr")
        # 提供手动输入提示
        logger.info("所有OCR库都无法使用，建议手动输入基金信息或检查PyTorch安装")
        return []
    except Exception as e:
        logger.error(f"EasyOCR识别失败: {e}")
        # 提供手动输入提示
        logger.info("OCR识别失败，请考虑手动输入基金代码和名称")
        return []


def _get_ocr_texts_easyocr(image_data: str, use_gpu: bool = False) -> List[str]:
    """获取EasyOCR识别的原始文本列表"""
    try:
        import easyocr
        
        # 处理Base64编码的图片数据
        if isinstance(image_data, str):
            import base64
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # 初始化 EasyOCR
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=use_gpu)
        
        # 将字节数据转换为图片
        image = Image.open(io.BytesIO(image_bytes))
        
        # 执行 OCR 识别
        import numpy as np
        image_array = np.array(image)
        result = reader.readtext(image_array)
        
        # 提取文本
        texts = []
        for detection in result:
            text = detection[1]  # 获取识别的文本
            confidence = detection[2]  # 获取置信度
            
            from data_retrieval.utils.ocr_config import get_confidence_threshold
            threshold = get_confidence_threshold()
            
            if confidence > threshold:
                texts.append(text)
        
        return texts
        
    except Exception as e:
        logger.error(f"获取EasyOCR文本失败: {e}")
        return []


def recognize_with_baidu(image_data: str, use_accurate: bool = True) -> Tuple[List[Dict], List[str]]:
    """
    使用百度OCR识别基金截图

    参数：
    image_data: Base64编码的图片数据或图片二进制数据
    use_accurate: 是否使用高精度识别

    返回：
    (识别到的基金列表, 识别到的文本列表)
    """
    try:
        from .baidu_ocr import BaiduOCR

        ocr = BaiduOCR(use_accurate=use_accurate)
        funds = ocr.recognize_fund_screenshot(image_data)

        # 获取原始文本
        texts, _ = ocr.recognize(image_data)

        return funds, texts

    except Exception as e:
        logger.error(f"百度OCR识别失败: {e}")
        return [], []


def _get_ocr_texts_paddleocr(image_data: str, use_gpu: bool = False) -> List[str]:
    """获取PaddleOCR识别的原始文本列表"""
    try:
        # 处理Base64编码的图片数据
        if isinstance(image_data, str):
            import base64
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data

        # 使用 PaddleOCR 进行识别
        from paddleocr import PaddleOCR

        # 初始化 OCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='ch')

        # 将字节数据转换为图片
        image = Image.open(io.BytesIO(image_bytes))

        # 执行 OCR 识别
        import numpy as np
        image_array = np.array(image)
        result = ocr.ocr(image_array)

        if not result or not result[0]:
            return []

        # 提取文本
        texts = []
        for line in result[0]:
            text = line[1][0]  # 获取识别的文本
            confidence = line[1][1]  # 获取置信度
            
            from data_retrieval.utils.ocr_config import get_confidence_threshold
            threshold = get_confidence_threshold()
            
            if confidence > threshold:
                texts.append(text)
        
        return texts
        
    except Exception as e:
        logger.error(f"获取PaddleOCR文本失败: {e}")
        return []


def parse_fund_info(texts: List[str]) -> List[Dict]:
    """
    从OCR识别的文本中解析基金信息
    
    参数：
    texts: OCR识别的文本列表
    
    返回：
    list: 解析出的基金列表，包含 fund_code、fund_name、confidence
    """
    funds = []
    
    # 基金代码的正则表达式（6位数字）
    code_pattern = re.compile(r'\b(\d{6})\b')
    
    # 判断是否为纯数字（包括小数、百分号等）
    def is_numeric_text(text):
        """判断文本是否主要是数字"""
        # 移除常见的数字符号
        cleaned = text.replace('.', '').replace('-', '').replace('+', '').replace('%', '').replace(',', '').strip()
        # 如果移除后全是数字，或者为空，则认为是数字文本
        return cleaned.isdigit() or len(cleaned) == 0
    
    # 判断是否包含中文或英文字母
    def has_text_content(text):
        """判断文本是否包含中文或英文字母"""
        return bool(re.search(r'[\u4e00-\u9fa5a-zA-Z]', text))
    
    # 遍历文本，查找基金代码和名称
    i = 0
    while i < len(texts):
        text = texts[i]
        
        # 查找基金代码
        code_match = code_pattern.search(text)
        
        if code_match:
            fund_code = code_match.group(1)
            
            # 尝试从当前行或前一行提取基金名称
            fund_name = None
            
            # 方案1：基金名称在代码前面（同一行）
            name_before = text[:code_match.start()].strip()
            if name_before and len(name_before) > 2 and has_text_content(name_before):
                fund_name = clean_fund_name(name_before)
            
            # 方案2：基金名称在代码后面（同一行）
            if not fund_name:
                name_after = text[code_match.end():].strip()
                if name_after and len(name_after) > 2 and has_text_content(name_after):
                    fund_name = clean_fund_name(name_after)
            
            # 方案3：基金名称在上一行
            if not fund_name and i > 0:
                prev_text = texts[i - 1].strip()
                # 确保上一行不是基金代码，也不是纯数字，且包含文字内容
                if (prev_text and len(prev_text) > 2 and 
                    not code_pattern.search(prev_text) and 
                    has_text_content(prev_text) and
                    not is_numeric_text(prev_text)):
                    fund_name = clean_fund_name(prev_text)
            
            # 方案4：基金名称在下一行
            if not fund_name and i < len(texts) - 1:
                next_text = texts[i + 1].strip()
                # 确保下一行不是基金代码，也不是纯数字，且包含文字内容
                if (next_text and len(next_text) > 2 and 
                    not code_pattern.search(next_text) and 
                    has_text_content(next_text) and
                    not is_numeric_text(next_text)):
                    fund_name = clean_fund_name(next_text)
            
            # 如果找到了基金名称，添加到结果中
            if fund_name:
                funds.append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'confidence': 0.85  # 默认置信度
                })
                logger.info(f"识别到基金: {fund_code} - {fund_name}")
        
        i += 1
    
    # 去重
    unique_funds = []
    seen_codes = set()
    for fund in funds:
        if fund['fund_code'] not in seen_codes:
            unique_funds.append(fund)
            seen_codes.add(fund['fund_code'])
    
    return unique_funds


def clean_fund_name(name: str) -> str:
    """
    清理基金名称，移除特殊字符和多余空格
    
    参数：
    name: 原始基金名称
    
    返回：
    str: 清理后的基金名称
    """
    # 移除常见的后缀标识
    name = re.sub(r'\(QDII[^)]*\)', '', name)
    name = re.sub(r'\(LOF\)', '', name)
    name = re.sub(r'\(FOF\)', '', name)
    
    # 移除多余的空格
    name = ' '.join(name.split())
    
    # 移除特殊字符（保留中文、英文、数字、括号）
    name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9()（）\-]', '', name)
    
    return name.strip()


def validate_recognized_fund(fund: Dict) -> Tuple[bool, str]:
    """
    验证识别的基金信息是否有效
    
    参数：
    fund: 基金信息字典，包含 fund_code 和 fund_name
    
    返回：
    tuple: (是否有效, 错误信息或真实基金名称)
    """
    fund_code = fund.get('fund_code', '')
    fund_name = fund.get('fund_name', '')
    
    # 验证基金代码格式
    if not re.match(r'^\d{6}$', fund_code):
        return False, "基金代码格式错误，应为6位数字"
    
    # 验证基金名称长度
    if not fund_name or len(fund_name) < 2:
        return False, "基金名称过短"
    
    if len(fund_name) > 50:
        return False, "基金名称过长"
    
    # 尝试从数据源验证基金是否存在
    try:
        from data_retrieval.adapters.multi_source_adapter import MultiSourceDataAdapter
        
        # 获取基金基本信息
        basic_info = MultiSourceDataAdapter.get_fund_basic_info(fund_code)
        
        if basic_info and basic_info.get('fund_name'):
            real_name = basic_info['fund_name']
            # 只有当获取到的名称不是默认格式时，才更新基金名称
            if not real_name.startswith(f'基金{fund_code}'):
                # 更新基金名称为真实名称
                fund['fund_name'] = real_name
                return True, real_name
            else:
                # 如果获取到的是默认格式，保留原有的基金名称
                return True, fund_name
        else:
            return False, f"基金代码 {fund_code} 不存在"
            
    except Exception as e:
        logger.warning(f"验证基金信息时出错: {e}")
        # 如果验证失败，仍然返回True，允许用户手动确认
        return True, fund_name


def extract_fund_from_text(text: str) -> Optional[Dict]:
    """
    从单行文本中提取基金信息（用于简单场景）
    
    参数：
    text: 文本内容
    
    返回：
    dict: 基金信息，包含 fund_code 和 fund_name
    """
    # 基金代码的正则表达式
    code_pattern = re.compile(r'\b(\d{6})\b')
    
    code_match = code_pattern.search(text)
    if not code_match:
        return None
    
    fund_code = code_match.group(1)
    
    # 提取基金名称（代码前面的文本）
    name_before = text[:code_match.start()].strip()
    if name_before and len(name_before) > 2:
        fund_name = clean_fund_name(name_before)
        return {
            'fund_code': fund_code,
            'fund_name': fund_name
        }
    
    # 提取基金名称（代码后面的文本）
    name_after = text[code_match.end():].strip()
    if name_after and len(name_after) > 2:
        fund_name = clean_fund_name(name_after)
        return {
            'fund_code': fund_code,
            'fund_name': fund_name
        }
    
    return None


if __name__ == "__main__":
    # 测试代码
    test_text = """
    天弘标普500发起(QDII-FOF)A 681.30
    007721
    景顺长城全球半导体芯片股票A(QDII-LOF)(人民币) 664.00
    501225
    广发北证50成份指数A 568.11
    """
    
    texts = test_text.strip().split('\n')
    funds = parse_fund_info(texts)
    
    print(f"识别到 {len(funds)} 只基金:")
    for fund in funds:
        print(f"  {fund['fund_code']} - {fund['fund_name']}")
