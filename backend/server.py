import asyncio
import os
import shutil
from typing import Any, Dict, List
from contextlib import AsyncExitStack
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp_agent.servers.sse_server import MCPServer, FastMCPServer
import shlex
import json

logger = logging.getLogger(__name__)


        
class StdioMCPServer(MCPServer):
    """基于 stdio 协议的 MCP Server 通信实现"""
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.stdio_context = None
        self._cleanup_lock = asyncio.Lock()
        self.exit_stack = AsyncExitStack()
        self.session = None

    async def initialize(self) -> None:
        command = (
            shutil.which("npx")
            if self.config.get("command") == "npx"
            else self.config.get("command")
        )
        if command is None:
            raise ValueError("The command must be a valid string and cannot be None.")
        
        args = self.config.get("args", [])
        if isinstance(args, str):
            args = shlex.split(args)
        logger.info(f"[stdio] args: {args}")
        
        env = self.config.get("env", {})
        if isinstance(env, str):
            try:
                env = json.loads(env)
            except json.JSONDecodeError:
                env = {}

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env={**os.environ, **env} if self.config.get("env") else None,
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
        except Exception as e:
            logger.error(f"Error initializing stdio server {self.name}: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> List[Any]:
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")
        tools_response = await self.session.list_tools()
        # logger.info(f"[list_tools] tools_response: {tools_response}")
        tools = []
        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                for tool in item[1]:
                    if isinstance(tool, dict):
                        # logger.info(f"[list_tools] tool(dict): name={tool.get('name')}, params={tool.get('params')}, inputSchema={tool.get('inputSchema')}")
                        tools.append(tool)
                    else:
                        # 尝试多种属性名获取 schema
                        schema = (
                            getattr(tool, "inputSchema", None) or 
                            getattr(tool, "input_schema", None) or 
                            getattr(tool, "schema", {})
                        )
                        # logger.info(f"[list_tools] tool(obj): name={getattr(tool, 'name', None)}, input_schema={schema}")
                        tool_dict = {
                            "name": getattr(tool, "name", None),
                            "description": getattr(tool, "description", ""),
                            "params": schema,
                            "inputSchema": schema
                        }
                        tools.append(tool_dict)
        return tools

    async def execute_tool(self, tool_name: str, arguments: dict, **kwargs) -> Any:
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")
        retries = 3
        delay = 1
        attempt = 0
        while attempt < retries:
            try:
                logger.info(f"[stdio] Executing {tool_name} on {self.name}...")
                result = await self.session.call_tool(tool_name, arguments)
                return result
            except Exception as e:
                attempt += 1
                logger.warning(f"Error executing tool: {e}. Attempt {attempt} of {retries}.")
                if attempt < retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached. Failing.")
                    raise

    async def cleanup(self) -> None:
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
                self.stdio_context = None
            except Exception as e:
                logger.error(f"Error during cleanup of server {self.name}: {e}")


class SSEMCPServer(FastMCPServer):
    """基于 SSE/HTTP 协议的 MCP Server 通信实现"""
    def __init__(self, name: str, config: dict):
        logger.info(f"初始化 SSEMCPServer: {name}")
        super(SSEMCPServer, self).__init__(name, config)