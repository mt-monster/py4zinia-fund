# 微信登录配置文件

import os
import time

class WeChatConfig:
    """微信登录配置类"""
    
    # 登录配置
    MAX_LOGIN_RETRIES = 3
    LOGIN_RETRY_DELAY = 2  # 秒
    LOGIN_TIMEOUT = 30  # 秒
    
    # 好友列表配置
    FRIENDS_PAGE_SIZE = 20  # 每页显示的好友数量
    
    # 网络配置
    REQUEST_TIMEOUT = 10  # 秒
    NETWORK_RETRY_DELAY = 5  # 秒
    
    # 日志配置
    ENABLE_DEBUG = False
    LOG_LEVEL = "INFO"
    
    # 二维码配置
    QR_CODE_ENABLE_CMD = True
    QR_CODE_PATH = os.path.join(os.path.dirname(__file__), "qrcode.png")
    
    @classmethod
    def get_retry_delay(cls, attempt: int) -> int:
        """获取重试延迟时间（指数退避）"""
        return cls.LOGIN_RETRY_DELAY * (2 ** attempt)
    
    @classmethod
    def should_retry(cls, attempt: int, max_retries: int = None) -> bool:
        """判断是否应该重试"""
        max_retries = max_retries or cls.MAX_LOGIN_RETRIES
        return attempt < max_retries

# 常见错误消息和处理建议
ERROR_MESSAGES = {
    "xml.parsers.expat.ExpatError": {
        "message": "XML解析错误，可能是网络问题或微信接口变更",
        "solution": "请检查网络连接，稍后重试",
        "retry": True
    },
    "ConnectionError": {
        "message": "网络连接失败",
        "solution": "请检查网络连接状态",
        "retry": True
    },
    "TimeoutError": {
        "message": "请求超时",
        "solution": "网络较慢，请稍后重试",
        "retry": True
    },
    "KeyError": {
        "message": "数据格式异常",
        "solution": "可能是微信接口变更，请联系开发者",
        "retry": False
    }
}

def get_error_info(error: Exception) -> dict:
    """根据异常类型获取错误信息"""
    error_type = type(error).__name__
    error_class = error.__class__.__name__
    
    # 优先匹配完整类名
    if error_class in ERROR_MESSAGES:
        return ERROR_MESSAGES[error_class]
    
    # 其次匹配异常类型
    if error_type in ERROR_MESSAGES:
        return ERROR_MESSAGES[error_type]
    
    # 默认处理
    return {
        "message": f"未知错误: {str(error)}",
        "solution": "请检查错误信息，稍后重试或联系开发者",
        "retry": True
    }