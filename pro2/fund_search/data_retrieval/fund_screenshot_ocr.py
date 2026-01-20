#!/usr/bin/env python
# coding: utf-8

"""
基金持仓截图识别模块
通过OCR识别上传的基金持仓截图，自动提取基金代码、名称、份额、成本价等信息
"""

import os
import re
import base64
import uuid
import tempfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

OCR_AVAILABLE = False
easyocr = None

try:
    import easyocr
    OCR_AVAILABLE = True
    logger.info("EasyOCR 库已加载，GPU模式: 可用")
except ImportError:
    logger.warning("EasyOCR 未安装，尝试使用其他OCR方案...")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    logger.warning("PIL 未安装")
    PIL_AVAILABLE = False


@dataclass
class RecognizedFund:
    """识别到的基金信息"""
    fund_code: str = ""
    fund_name: str = ""
    holding_shares: float = 0.0
    cost_price: float = 0.0
    buy_date: str = ""
    confidence: float = 0.0
    raw_text: str = ""


class FundScreenshotRecognizer:
    """基金持仓截图识别器"""
    
    def __init__(self, use_gpu: bool = True):
        self.reader = None
        self.use_gpu = use_gpu
        self._init_reader()
    
    def _init_reader(self):
        """初始化OCR阅读器"""
        if not OCR_AVAILABLE or not easyocr:
            logger.warning("OCR库不可用")
            return
        
        try:
            self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=self.use_gpu)
            logger.info("EasyOCR 初始化成功")
        except Exception as e:
            logger.error(f"EasyOCR 初始化失败: {e}")
            self.reader = None
    
    def _save_base64_image(self, base64_data: str) -> Optional[str]:
        """保存Base64图片到临时文件"""
        if not PIL_AVAILABLE:
            return None
        
        try:
            header, encoded = base64_data.split(',') if ',' in base64_data else ('', base64_data)
            image_data = base64.b64decode(encoded)
            
            temp_dir = tempfile.gettempdir()
            filename = f"fund_screenshot_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(temp_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            return filepath
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """清理识别文本"""
        if not text:
            return ""
        return text.strip().replace(' ', '').replace('\n', '')
    
    def _extract_fund_code(self, text: str) -> Optional[str]:
        """从文本中提取基金代码（6位数字）"""
        pattern = r'[0-9]{6}'
        matches = re.findall(pattern, text)
        for match in matches:
            if 100000 <= int(match) <= 999999:
                return match
        return None
    
    def _extract_money_amount(self, text: str) -> Optional[float]:
        """从文本中提取金额"""
        pattern = r'([0-9]+\.?[0-9]*)'
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                value = float(match)
                if 0.01 <= value <= 10000000:
                    return value
            except ValueError:
                continue
        return None
    
    def _extract_shares(self, text: str) -> Optional[float]:
        """从文本中提取份额"""
        pattern = r'([0-9]+\.?[0-9]*)'
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                value = float(match)
                if 0.01 <= value <= 100000000:
                    return value
            except ValueError:
                continue
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """从文本中提取日期"""
        patterns = [
            r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{1,2}[-/.]\d{1,2}[-/.]\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                date_str = date_str.replace('/', '-').replace('.', '-')
                try:
                    datetime.strptime(date_str[:10], '%Y-%m-%d')
                    return date_str[:10]
                except ValueError:
                    continue
        return None
    
    def _find_fund_name_line(self, texts: List[Tuple]) -> Optional[str]:
        """查找基金名称行"""
        keywords = ['基金', '混合', '股票', '债券', '指数', 'ETF', 'QDII', 'LOF', 'FOF']
        
        for text, bbox, confidence in texts:
            cleaned = self._clean_text(text)
            for keyword in keywords:
                if keyword in cleaned and len(cleaned) >= 4 and len(cleaned) <= 30:
                    return cleaned
        return None
    
    def _calculate_confidence(self, texts: List[Tuple]) -> float:
        """计算整体识别置信度"""
        if not texts:
            return 0.0
        
        total_conf = sum(conf for _, _, conf in texts)
        avg_conf = total_conf / len(texts)
        return round(avg_conf, 2)
    
    def recognize(self, image_path: str) -> List[RecognizedFund]:
        """识别图片中的基金信息"""
        if not self.reader:
            logger.error("OCR阅读器未初始化")
            return []
        
        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return []
        
        try:
            results = self.reader.readtext(image_path)
            logger.info(f"OCR识别到 {len(results)} 个文本区域")
            
            full_text = ' '.join([text for text, _, _ in results])
            confidence = self._calculate_confidence(results)
            
            fund_code = self._extract_fund_code(full_text)
            fund_name = self._find_fund_name_line(results)
            
            recognized = RecognizedFund(
                fund_code=fund_code or "",
                fund_name=fund_name or "",
                confidence=confidence,
                raw_text=full_text[:500]
            )
            
            return [recognized]
            
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return []
    
    def recognize_base64(self, base64_data: str) -> List[RecognizedFund]:
        """识别Base64格式的图片"""
        image_path = self._save_base64_image(base64_data)
        if not image_path:
            return []
        
        try:
            results = self.recognize(image_path)
            return results
        finally:
            self._cleanup_image(image_path)
    
    def _cleanup_image(self, image_path: str):
        """清理临时图片文件"""
        try:
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            logger.warning(f"清理临时图片失败: {e}")


def recognize_fund_screenshot(base64_image: str, use_gpu: bool = True) -> List[Dict]:
    """
    识别基金持仓截图
    
    参数：
    base64_image: Base64编码的图片数据
    use_gpu: 是否使用GPU加速
    
    返回：
    List[Dict]: 识别到的基金信息列表
    """
    recognizer = FundScreenshotRecognizer(use_gpu=use_gpu)
    results = recognizer.recognize_base64(base64_image)
    
    return [
        {
            'fund_code': r.fund_code,
            'fund_name': r.fund_name,
            'holding_shares': r.holding_shares,
            'cost_price': r.cost_price,
            'buy_date': r.buy_date,
            'confidence': r.confidence,
        }
        for r in results
    ]


def validate_recognized_fund(fund_info: Dict) -> Tuple[bool, str]:
    """
    验证识别结果的基金信息
    
    返回：
    (是否有效, 错误信息)
    """
    if not fund_info.get('fund_code'):
        return False, "未能识别到基金代码"
    
    if len(fund_info['fund_code']) != 6:
        return False, f"基金代码长度不正确: {fund_info['fund_code']}"
    
    if not fund_info['fund_code'].isdigit():
        return False, f"基金代码包含非数字字符: {fund_info['fund_code']}"
    
    if not (100000 <= int(fund_info['fund_code']) <= 999999):
        return False, f"基金代码范围无效: {fund_info['fund_code']}"
    
    return True, ""


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("基金截图识别模块测试")
    print("=" * 50)
    
    recognizer = FundScreenshotRecognizer(use_gpu=False)
    
    if not OCR_AVAILABLE:
        print("⚠️  EasyOCR 未安装")
        print("请运行: pip install easyocr")
    elif not recognizer.reader:
        print("⚠️  OCR阅读器初始化失败")
    else:
        print("✅ OCR识别器准备就绪")
        
    print("\n使用方法:")
    print("1. 调用 recognize_fund_screenshot(base64_image) 识别图片")
    print("2. 调用 validate_recognized_fund(fund_info) 验证结果")
