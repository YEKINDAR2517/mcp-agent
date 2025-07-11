import json
import logging
from typing import Any, Dict, List, Optional
import re

logger = logging.getLogger(__name__)

def extract_json_from_string(s: str) -> Optional[Dict]:
    """从字符串中提取 JSON 对象"""
    try:
        # 查找字符串中的 JSON 部分
        match = re.search(r'\{.*\}', s, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return None
    except Exception as e:
        logger.error(f"解析 JSON 失败: {e}")
        return None

def parse_function_call(message: str) -> Optional[Dict[str, Any]]:
    """解析消息中的函数调用，支持 xxx@server 格式"""
    logger.info(f"parse_function_call 解析函数调用: message: {message}")
    try:
        # 支持：调用函数 search@test2 参数 {"query": "用户数据"}
        pattern = r'调用函数\s+([\w]+)(?:@([\w\-]+))?\s+参数\s+(\{.*\})'
        match = re.search(pattern, message)
        logger.info(f"解析函数调用: message: {message}, match: {match}")
        if match:
            function_name = match.group(1)
            server_name = match.group(2) if match.group(2) else None
            args = json.loads(match.group(3))
            logger.info(f"解析函数调用成功: {function_name}, server: {server_name}, args: {args}")
            return {
                "name": function_name if not server_name else f"{function_name}@{server_name}",
                "function": function_name,
                "server": server_name,
                "arguments": args
            }
        return None
    except Exception as e:
        logger.error(f"解析函数调用失败: {e}")
        return None

def format_chat_context(messages: List[Dict]) -> str:
    """格式化聊天上下文"""
    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)

def is_json_response(text: str) -> bool:
    """检查文本是否为 JSON 格式"""
    try:
        json.loads(text)
        return True
    except:
        return False

def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全地解析 JSON"""
    try:
        return json.loads(text)
    except:
        return default

def format_error_response(error: Exception) -> Dict[str, Any]:
    """格式化错误响应"""
    return {
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "details": getattr(error, "details", None)
        }
    } 