#!/usr/bin/env python
# coding: utf-8

"""
百度OCR本地识别模块
支持通用文字识别和高精度识别
"""

import requests
import base64
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from PIL import Image
import io

logger = logging.getLogger(__name__)


class BaiduOCR:
    """百度OCR识别类"""
    
    # 百度OCR API地址
    API_URLS = {
        'general': 'https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic',  # 通用文字识别
        'accurate': 'https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic',  # 通用文字识别(高精度版)
        'general_enhanced': 'https://aip.baidubce.com/rest/2.0/ocr/v1/general',  # 通用文字识别(含位置信息)
    }
    
    def __init__(self, api_key: str = None, secret_key: str = None, 
                 use_accurate: bool = True, timeout: int = 30):
        """
        初始化百度OCR
        
        Args:
            api_key: 百度API Key
            secret_key: 百度Secret Key
            use_accurate: 是否使用高精度识别
            timeout: 请求超时时间(秒)
        """
        self.api_key = api_key or self._get_api_key_from_config()
        self.secret_key = secret_key or self._get_secret_key_from_config()
        self.use_accurate = use_accurate
        self.timeout = timeout
        self.access_token = None
        self.token_expire_time = 0
        
        if not self.api_key or not self.secret_key:
            raise ValueError("百度OCR需要提供API Key和Secret Key")
    
    def _get_api_key_from_config(self) -> str:
        """从配置获取API Key"""
        try:
            from .ocr_config import get_baidu_api_key
            return get_baidu_api_key()
        except:
            return None
    
    def _get_secret_key_from_config(self) -> str:
        """从配置获取Secret Key"""
        try:
            from .ocr_config import get_baidu_secret_key
            return get_baidu_secret_key()
        except:
            return None
    
    def _get_access_token(self) -> str:
        """获取百度访问令牌"""
        # 检查令牌是否过期
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token
        
        # 请求新令牌
        url = f"https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params, timeout=10)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                # 令牌有效期通常为30天，这里设置为29天后过期
                self.token_expire_time = time.time() + 29 * 24 * 3600
                logger.info("百度OCR访问令牌获取成功")
                return self.access_token
            else:
                error_msg = result.get('error_description', '未知错误')
                raise Exception(f"获取访问令牌失败: {error_msg}")
                
        except Exception as e:
            logger.error(f"获取百度OCR访问令牌失败: {e}")
            raise
    
    def recognize(self, image_data, recognize_type: str = 'accurate') -> Tuple[List[str], float]:
        """
        识别图片中的文字
        
        Args:
            image_data: 图片数据(Base64字符串或二进制)
            recognize_type: 识别类型 ('general', 'accurate', 'general_enhanced')
        
        Returns:
            (识别文本列表, 平均置信度)
        """
        try:
            # 处理图片数据
            if isinstance(image_data, str):
                # 如果是Base64字符串，移除前缀
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            # 图片压缩和优化
            optimized_image = self._optimize_image(image_bytes)
            image_base64 = base64.b64encode(optimized_image).decode('utf-8')
            
            # 获取访问令牌
            access_token = self._get_access_token()
            
            # 选择API地址
            api_type = 'accurate' if self.use_accurate else 'general'
            if recognize_type in self.API_URLS:
                api_type = recognize_type
            
            url = f"{self.API_URLS[api_type]}?access_token={access_token}"
            
            # 准备请求数据
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                'image': image_base64,
                'language_type': 'CHN_ENG',  # 中英文混合
                'detect_direction': 'true',   # 检测方向
                'paragraph': 'false',         # 不输出段落信息
                'probability': 'true'         # 返回置信度
            }
            
            # 发送请求
            start_time = time.time()
            response = requests.post(url, data=data, headers=headers, timeout=self.timeout)
            elapsed_time = time.time() - start_time
            
            result = response.json()
            
            if 'words_result' in result:
                texts = []
                total_confidence = 0
                
                for item in result['words_result']:
                    text = item.get('words', '')
                    # 获取置信度
                    probability = item.get('probability', {})
                    if isinstance(probability, dict):
                        confidence = probability.get('average', 0.9)
                    else:
                        confidence = 0.9
                    
                    texts.append(text)
                    total_confidence += confidence
                
                avg_confidence = total_confidence / len(texts) if texts else 0
                logger.info(f"百度OCR识别成功: {len(texts)}行文字, 平均置信度: {avg_confidence:.2%}, 耗时: {elapsed_time:.2f}s")
                
                return texts, avg_confidence
            else:
                error_msg = result.get('error_msg', '未知错误')
                logger.error(f"百度OCR识别失败: {error_msg}")
                return [], 0
                
        except requests.exceptions.Timeout:
            logger.error("百度OCR请求超时")
            return [], 0
        except Exception as e:
            logger.error(f"百度OCR识别异常: {e}")
            return [], 0
    
    def _optimize_image(self, image_bytes: bytes, max_size: int = 4 * 1024 * 1024) -> bytes:
        """
        优化图片以满足百度OCR要求并提升识别精度
        - 最大4MB
        - 最短边至少15px，最长边最大4096px
        - 支持jpg/png/bmp格式
        - 增强对比度和清晰度以提升识别率
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 检查尺寸并调整
            width, height = image.size
            max_dimension = 4096
            min_dimension = 15
            
            # 如果尺寸过大，按比例缩小
            if max(width, height) > max_dimension:
                ratio = max_dimension / max(width, height)
                new_size = (int(width * ratio), int(height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"图片尺寸调整: {width}x{height} -> {new_size[0]}x{new_size[1]}")
            
            # 如果尺寸过小，放大以提升识别率
            if min(width, height) < 800:
                # 对于小图片，放大2倍以提升文字识别率
                scale_factor = max(2, 800 / min(width, height))
                new_size = (int(width * scale_factor), int(height * scale_factor))
                if max(new_size) <= max_dimension:
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"图片放大以提升识别率: {width}x{height} -> {new_size[0]}x{new_size[1]}")
            
            # 图像增强处理（针对基金截图优化）
            image = self._enhance_image_for_ocr(image)
            
            # 压缩图片以满足大小限制
            quality = 95
            output = io.BytesIO()
            
            while True:
                output.seek(0)
                output.truncate()
                image.save(output, format='JPEG', quality=quality)
                
                if output.tell() <= max_size or quality <= 30:
                    break
                
                quality -= 5
                logger.debug(f"降低图片质量至 {quality}")
            
            optimized_bytes = output.getvalue()
            logger.info(f"图片优化完成: {len(image_bytes)/1024:.1f}KB -> {len(optimized_bytes)/1024:.1f}KB")
            
            return optimized_bytes
            
        except Exception as e:
            logger.warning(f"图片优化失败，使用原图: {e}")
            return image_bytes
    
    def _enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        针对OCR识别增强图像质量
        - 增强对比度
        - 锐化处理
        - 去除噪点
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # 1. 对比度增强（提升文字与背景的区分度）
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)  # 增强20%对比度
            
            # 2. 亮度微调（确保文字清晰可见）
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.05)  # 微调亮度
            
            # 3. 锐化处理（使文字边缘更清晰）
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)  # 增强锐度
            
            # 4. 颜色饱和度微调（使文字颜色更鲜明）
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.1)
            
            logger.debug("图像增强处理完成")
            return image
            
        except Exception as e:
            logger.warning(f"图像增强处理失败: {e}")
            return image
    
    def recognize_fund_screenshot(self, image_data) -> List[Dict]:
        """
        识别基金截图并解析基金信息
        
        Args:
            image_data: 图片数据
        
        Returns:
            基金信息列表
        """
        # 执行OCR识别
        texts, confidence = self.recognize(image_data)
        
        if not texts:
            logger.warning("百度OCR未识别到文字")
            return []
        
        # 使用智能解析器解析基金信息
        from .smart_fund_parser import parse_fund_info_with_manual_fallback
        parse_result = parse_fund_info_with_manual_fallback(texts)
        
        funds = parse_result['funds']
        
        # 添加置信度信息
        for fund in funds:
            fund['ocr_confidence'] = confidence
            fund['ocr_engine'] = 'baidu'
        
        # 如果有手工导入建议，记录到日志
        if parse_result['manual_import_needed']:
            logger.warning(f"有 {len(parse_result['manual_items'])} 项需要手工导入")
            logger.info(parse_result['manual_prompt'])
        
        # 如果智能解析器没有结果，尝试其他解析器
        if not funds:
            from .enhanced_fund_parser import parse_fund_info_enhanced
            funds = parse_fund_info_enhanced(texts)
            
            if not funds:
                from .fund_screenshot_ocr import parse_fund_info
                funds = parse_fund_info(texts)
        
        return funds


def recognize_with_baidu(image_data: str, use_accurate: bool = True) -> Tuple[List[Dict], List[str]]:
    """
    使用百度OCR识别基金截图
    
    Args:
        image_data: Base64编码的图片数据或图片二进制数据
        use_accurate: 是否使用高精度识别
    
    Returns:
        (识别到的基金列表, 识别到的文本列表)
    """
    try:
        ocr = BaiduOCR(use_accurate=use_accurate)
        funds = ocr.recognize_fund_screenshot(image_data)
        
        # 获取原始文本
        texts, _ = ocr.recognize(image_data)
        
        return funds, texts
        
    except Exception as e:
        logger.error(f"百度OCR识别失败: {e}")
        return [], []


# 测试代码
if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 测试百度OCR
    # 注意：需要提供有效的API Key和Secret Key
    try:
        ocr = BaiduOCR()
        print("百度OCR初始化成功")
        print(f"使用高精度识别: {ocr.use_accurate}")
    except Exception as e:
        print(f"百度OCR初始化失败: {e}")
