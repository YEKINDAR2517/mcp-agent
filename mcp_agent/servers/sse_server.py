from typing import Dict, List, Any

import abc
from typing import List, Any, Dict
import logging

from fastmcp.client import Client
from fastmcp.client.transports import SSETransport

logger = logging.getLogger(__name__)


class MCPServer(abc.ABC):
    """MCP Server 通信抽象基类"""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config

    @abc.abstractmethod
    async def initialize(self) -> None:
        pass

    @abc.abstractmethod
    async def list_tools(self) -> List[Any]:
        pass

    @abc.abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict, **kwargs) -> Any:
        pass

    @abc.abstractmethod
    async def cleanup(self) -> None:
        pass


class FastMCPServer(MCPServer):
    """FastMCP SSE服务端客户端实现"""
    def __init__(self, name: str, config: dict):
        """
        初始化FastMCP客户端
        
        参数:
        - name: 客户端名称
        - config: 配置字典，应包含:
        - base_url: FastMCP服务端的基础URL
        - group_id: 组ID(可选)
        - timeout: 请求超时时间(秒，默认30)
        """
        super().__init__(name, config)
        # logger.info(f"构建 FastMCPServer: {name}, config: {config}")
        self.sse_endpoint = config.get("sse_endpoint", "/sse")
        self.base_url = config.get("url")
        if self.base_url:
            self.base_url = self.base_url.rstrip("/")
        self.timeout = config.get("timeout", 30)
        self.headers = config.get("headers", {})
        self._initialized = False
        self.client = None
        self._client_cm = None  # 用于保存 async context manager

    async def initialize(self) -> None:
        logger.info(f"初始化 FastMCPServer: {self.name}")
        if self._initialized:
            return
        self.client = Client(
            transport=SSETransport(self.base_url),
            timeout=10,
        )
        self._client_cm = self.client.__aenter__()
        await self._client_cm
        self._initialized = True
        print(f"FastMCP客户端初始化完成")

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头，包含认证信息"""
        headers = {
            "Content-Type": "application/json",
        }

        if self.headers:
            headers.update(self.headers)

        return headers

    async def list_tools(self) -> List[Dict]:
        if not self._initialized or not self.client:
            await self.initialize()
        return await self.client.list_tools()

    async def execute_tool(self, tool_name: str, arguments: dict, **kwargs) -> Any:
        if not self._initialized or not self.client:
            await self.initialize()
        return await self.client.call_tool(tool_name, arguments)
    
    async def cleanup(self) -> None:
        if self.client:
            await self.client.__aexit__(None, None, None)
        print(f"FastMCP客户端 {self.name} 已清理资源")
