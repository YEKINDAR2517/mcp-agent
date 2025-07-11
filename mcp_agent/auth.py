from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量获取 API 密钥
API_KEY = os.getenv("API_KEY", "your-default-api-key")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: Optional[str] = Security(api_key_header)) -> str:
    """验证 API 密钥"""
    if api_key_header and api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="无效的 API 密钥"
    ) 