from typing import List, Dict, Any, AsyncGenerator
import logging
import json
import os
import openai
from .cache import cache
from .mcp_server_dao import MCPServerDAO
import re
from .server import StdioMCPServer, SSEMCPServer
import asyncio
import traceback
import uuid

logger = logging.getLogger(__name__)


def convert_obj_id(obj):
    if isinstance(obj, dict):
        return {k: convert_obj_id(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_obj_id(i) for i in obj]
    elif 'bson' in str(type(obj)) and hasattr(obj, '__str__'):
        # 兼容 ObjectId 及其他 bson 类型
        return str(obj)
    else:
        return obj


def filter_llm_message(msg):
    msg = convert_obj_id(msg)
    return {k: v for k, v in msg.items() if k not in ("session_id", "tools", "updated_at", "timestamp", 'call')}


def _serialize_tool_result(result):
    """将工具调用结果转换为可序列化的格式"""
    if hasattr(result, 'meta'):
        result_dict = {}
        if hasattr(result, 'content'):
            content = []
            for item in result.content:
                if hasattr(item, '__dict__'):
                    content.append({
                        'type': getattr(item, 'type', None),
                        'text': getattr(item, 'text', None),
                        'annotations': getattr(item, 'annotations', None)
                    })
                else:
                    content.append(item)
            result_dict['content'] = content
        if hasattr(result, 'isError'):
            result_dict['isError'] = result.isError
        if result.meta:
            result_dict['meta'] = result.meta
        return result_dict
    return result


def extract_function_call(text):
    # logger.info(f"[FunctionCall] 检查内容: {text}")
    match = re.search(r"<\|FunctionCallBegin\|>([\s\S]*?)<\|FunctionCallEnd\|>", text)
    if not match:
        logger.info("[FunctionCall] 正则未匹配")
        return None
    try:
        parsed = json.loads(match.group(1))
        # logger.info(f"[FunctionCall] 解析成功: {parsed}")
        return parsed
    except Exception as e:
        logger.error(f"[FunctionCall] JSON 解析失败: {e}, 内容: {match.group(1)}")
        return None


class LLMService:
    def __init__(self, server_dao: MCPServerDAO):
        self.server_dao = server_dao
        self.client = openai.OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("BASE_URL", "https://api.openai.com/v1")
        )
        self._function_prompt = None
        self.mcp_servers: Dict[str, SSEMCPServer | StdioMCPServer] = {}
        self.server_dao = MCPServerDAO()
        self.update_mcp_servers()

    def get_mcp_server(self, name: str) -> SSEMCPServer | StdioMCPServer:
        return self.mcp_servers.get(name)

    def update_mcp_servers(self):
        """更新 MCP Server 列表（支持多协议）"""
        logger.info(f"更新 MCP Server 列表（支持多协议）")
        self.mcp_servers.clear()
        servers = self.server_dao.list_servers()
        for server in servers:
            mode = server.get("mode", "sse")
            name = server["name"]
            if mode == "stdio":
                self.mcp_servers[name] = StdioMCPServer(name, server)
            else:
                self.mcp_servers[name] = SSEMCPServer(name, server)

    async def list_all_tools(self) -> List[Dict[str, Any]]:
        """汇总所有 MCP Server 的工具列表"""
        all_tools = []
        for name, server in self.mcp_servers.items():
            try:
                logger.info(f"[list_all_tools] 开始获取服务器 {name} 的工具列表...")
                await server.initialize()
                tools = await server.list_tools()
                logger.info(
                    f"[list_all_tools] 服务器 {name} 返回的原始工具列表: {json.dumps(tools, ensure_ascii=False, indent=2)}")

                for tool in tools:
                    all_tools.append({
                        "name": tool["name"] if isinstance(tool, dict) else getattr(tool, "name", None),
                        "server": name,
                        "description": tool.get("description", "") if isinstance(tool, dict) else getattr(tool,
                                                                                                            "description",
                                                                                                            ""),
                        "params": tool.get("inputSchema", {}) if isinstance(tool, dict) else getattr(tool,
                                                                                                        "input_schema", {})
                    })
                logger.info(
                    f"[list_all_tools] 服务器 {name} 处理后的工具列表: {json.dumps(all_tools, ensure_ascii=False, indent=2)}")
            except Exception as e:
                logger.error(f"获取 {name} 工具列表失败: {e}")
                traceback.print_exc()
        return all_tools

    async def call_mcp_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        logger.info(
            f"[call_mcp_tool] 调用工具: server={server_name}, tool={tool_name}, arguments={json.dumps(arguments, ensure_ascii=False)}")
        server = self.mcp_servers.get(server_name)
        if not server:
            return {"error": f"未找到服务器: {server_name}"}
        try:
            await server.initialize()
            result = await server.execute_tool(tool_name, arguments)
            await server.cleanup()
            return _serialize_tool_result(result)
        except Exception as e:
            logger.error(f"调用 MCP 工具失败: {e}")
            return {"error": str(e)}

    async def _fetch_functions(self):
        """从 MCP Server 获取功能列表并返回 JSON"""
        all_functions = []
        try:
            if not self.mcp_servers:
                logger.info("无 MCP Server，返回空功能列表")
                return []
            for name, server in self.mcp_servers.items():
                try:
                    logger.info(f"[_fetch_functions] 开始获取服务器 {name} 的工具列表...")
                    tools = await server.list_tools()
                    logger.info(
                        f"[_fetch_functions] 服务器 {name} 返回的原始工具列表: {json.dumps(tools, ensure_ascii=False, indent=2)}")

                    for tool in tools:
                        try:
                            if isinstance(tool, dict) and 'name' in tool:
                                param_schema = tool.get("params") or tool.get("inputSchema") or {}
                                properties = param_schema.get("properties", {})
                                required = param_schema.get("required", list(properties.keys()))
                                tool_copy = {
                                    "name": tool["name"],
                                    "server": name,
                                    "description": tool.get("description", ""),
                                    "params": param_schema
                                }
                                all_functions.append(tool_copy)
                            elif hasattr(tool, 'name'):
                                param_schema = getattr(tool, "input_schema", {})
                                properties = param_schema.get("properties", {})
                                required = param_schema.get("required", list(properties.keys()))
                                tool_copy = {
                                    "name": getattr(tool, 'name', 'unknown'),
                                    "server": name,
                                    "description": getattr(tool, "description", ""),
                                    "params": param_schema
                                }
                                all_functions.append(tool_copy)
                            else:
                                logger.warning(f"tool对象无name字段: {tool}")
                                continue
                        except Exception as e:
                            logger.error(f"tools处理异常: {e}, tool内容: {tool}")
                            raise
                    logger.info(
                        f"[_fetch_functions] 服务器 {name} 处理后的工具列表: {json.dumps(all_functions, ensure_ascii=False, indent=2)}")
                except Exception as e:
                    logger.error(f"获取 {name} 工具列表失败: {e}")
                    traceback.print_exc()
                    continue  # 跳过出错的服务器，继续处理其他服务器
            return all_functions
        except Exception as e:
            logger.error(f"自动获取 MCP 功能列表失败: {e}")
            return []

    async def async_generate_response(self, messages: List[dict], stream: bool = True) -> AsyncGenerator[
        str | dict, None]:
        """
        直接让 LLM 调用已注册的 MCP Server 处理消息
        """
        # 构建系统提示词，包含所有可用的工具信息
        tools = []
        available_servers = []  # 记录所有可用的服务器

        for name, server in self.mcp_servers.items():
            try:
                # 确保 server 已初始化
                if not getattr(server, '_initialized', False):
                    await server.initialize()
                server_tools = await server.list_tools()
                if isinstance(server_tools, dict) and "functions" in server_tools:
                    server_tools = server_tools["functions"]
                # 如果成功获取工具列表，将服务器标记为可用
                available_servers.append(server)
                for tool in server_tools:
                    try:
                        if isinstance(tool, dict) and 'name' in tool:
                            param_schema = tool.get("params") or tool.get("inputSchema") or {}
                            properties = param_schema.get("properties", {})
                            required = param_schema.get("required", list(properties.keys()))
                            tool_copy = {
                                "type": "function",
                                "function": {
                                    "name": f"{name}.{tool['name']}",
                                    "description": tool.get("description", ""),
                                    "parameters": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required
                                    }
                                }
                            }
                            tools.append(tool_copy)
                        elif hasattr(tool, 'name'):
                            param_schema = getattr(tool, "input_schema", {})
                            properties = param_schema.get("properties", {})
                            required = param_schema.get("required", list(properties.keys()))
                            tool_copy = {
                                "type": "function",
                                "function": {
                                    "name": f"{name}.{getattr(tool, 'name', 'unknown')}",
                                    "description": getattr(tool, "description", ""),
                                    "parameters": {
                                        "type": "object",
                                        "properties": properties,
                                        "required": required
                                    }
                                }
                            }
                            tools.append(tool_copy)
                        else:
                            logger.warning(f"tool对象无name字段: {tool}")
                            continue
                    except Exception as e:
                        logger.error(f"tools处理异常: {e}, tool内容: {tool}")
                        traceback.print_exc()
                        continue
            except Exception as e:
                logger.error(f"获取服务器 {name} 的工具列表失败: {e}")
                traceback.print_exc()
                continue  # 跳过出错的服务器，继续处理其他服务器

        # 如果没有可用工具，直接用 LLM 聊天
        if not tools:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=messages,
                stream=True
            )
            for chunk in response:
                delta = getattr(chunk.choices[0], 'delta', None)
                if delta and getattr(delta, 'content', None):
                    yield delta.content
            return

        # 构建系统消息
        tool_names = [tool['function']['name'] for tool in tools]
        tool_names_str = '\n'.join(f'- {n}' for n in tool_names)
        system_message = {
            "role": "system",
            "content": f"""你是一个强大的 AI 助手。你只能调用以下工具（名称区分大小写）：
                {tool_names_str}
                禁止调用未注册的工具，否则会报错。
                调用工具时，请使用完整的工具名称（包含 server_name 前缀）。
                调用工具时，参数必须严格按照 schema 格式传递。例如 sqlite.create_table 只接受 query 字符串参数，内容为完整的 SQL 语句。
                每次调用需要严格按照参数数量给入，如果需要多次调用，则发起多次调用；
                如果遇到错误，尝试其他可用的工具或向用户说明情况。"""
        }

        logger.info(f"系统消息: {system_message['content']}")

        # 添加工具列表到系统消息
        messages = [system_message] + [filter_llm_message(m) for m in messages]
        # logger.log(logging.INFO, f"messages: {messages}")
        # 1. 首先检查是否有可用的服务器, 理论上不太可能走到这儿
        if not available_servers:
            yield {"error": "没有可用的服务器"}
            return

        try:
            # 统一 tools 结构为 OpenAI function-calling 格式
            def convert_to_openai_functions(tools_in):
                openai_functions = []
                for fn in tools_in:
                    fn = fn.get('function')
                    # 兼容不同字段
                    schema = fn.get('params') or fn.get('inputSchema') or {}
                    openai_functions.append({
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "parameters": schema
                    })
                return openai_functions

            openai_tools = convert_to_openai_functions(tools)
            max_chain_steps = 10
            chain_count = 0
            while chain_count < max_chain_steps:
                logger.info(f"当前轮数 {chain_count} / {max_chain_steps}")
                # logger.info(f"当前messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
                has_tool_calls = False
                response = self.client.chat.completions.create(
                    model=os.getenv("MODEL"),
                    messages=messages,
                    functions=openai_tools,
                    stream=True
                )
                current_content = ""
                tool_calls = {}
                for chunk in response:
                    # logger.info(f"收到chunk: {chunk}")
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # logger.info(f"收到delta: {delta}")
                    if hasattr(delta, 'content') and delta.content is not None:
                        current_content += delta.content
                        # 检查是否有完整的 FunctionCall
                        yield delta.content
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        logger.info(f"[FunctionCall]2  call: delta.tool_calls={delta.tool_calls}")
                        for call in delta.tool_calls:
                            index = call.index

                            # 初始化或更新工具调用信息
                            if index not in tool_calls:
                                tool_calls[index] = {
                                    "name": "",
                                    "id": call.id,
                                    "parameters": {},
                                    "arguments_buffer": ""  # 用于累积参数的JSON字符串
                                }

                            # 处理函数名称
                            if call.function.name:
                                tool_calls[index]["name"] += call.function.name

                            # 处理参数
                            if call.function.arguments:
                                tool_calls[index]["arguments_buffer"] += call.function.arguments

                # 解析累积的参数JSON字符串
                for index, tool_call in tool_calls.items():
                    try:
                        # 尝试解析完整的JSON
                        tool_call["parameters"] = json.loads(tool_call["arguments_buffer"])
                    except json.JSONDecodeError:
                        # 如果解析失败，可能是JSON不完整（虽然流式响应应该会返回完整的JSON）
                        logger.warning(f"警告: 工具调用参数JSON不完整: {tool_call['arguments_buffer']}")
                        continue

                    # 调用对应的工具函数
                    async for item in self.handle_function_calling(tool_call, messages):  # 异步遍历子生成器
                        has_tool_calls = True
                        yield item

                while True:
                    match = re.search(r"<\|FunctionCallBegin\|>([\s\S]*?)<\|FunctionCallEnd\|>", current_content)
                    if not match:
                        break
                    function_call_str = match.group(0)
                    logger.info(f"[FunctionCall] 检测到 FunctionCall 字符串: {function_call_str}")
                    calls = extract_function_call(function_call_str)
                    if calls:
                        if not isinstance(calls, list):
                            calls = [calls]
                        for call in calls:
                            # yield {"tool_call": call}
                            async for item in self.handle_function_calling(call, messages):  # 异步遍历子生成器
                                if 'function_call' in item:
                                    item['content'] = function_call_str
                                yield item
                            has_tool_calls = True
                    # 移除已处理部分
                    current_content = current_content.replace(function_call_str, "", 1)
                if not has_tool_calls:
                    logger.info(f"没有方法调用了，可以返回")
                    break
                else:
                    chain_count += 1
                    logger.info(f"有方法调用，且当前轮数 {chain_count} / {max_chain_steps}")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"生成响应失败: {e}")
            yield {"error": f"生成响应失败: {e}"}

    def generate_response(self, messages: List[dict], stream: bool = False):
        raise NotImplementedError("请使用 async_generate_response 以支持异步链式工具调用！")

    async def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        try:
            # 检查缓存
            cache_key = f"embedding_{hash(text)}"
            cached_embedding = cache.get(cache_key)
            if cached_embedding:
                return cached_embedding

            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = response.data[0].embedding

            # 缓存结果
            cache.set(cache_key, embedding, persist=True)

            return embedding
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            raise

    async def handle_function_calling(self, call: dict, messages: list):
        name = call.get('name')
        params = call.get('parameters')
        # logger.info(f"[FunctionCall] 解析到调用2: name={name}, params={params}")
        if name and params is not None and '.' in name:
            server_name, tool_name = name.split('.', 1)
            logger.info(
                f"[FunctionCall] 自动执行: server={server_name}, "
                f"tool={tool_name}, params={params}")

            tool_call_id = call.get('id') or call.get('tool_call_id')
            if not tool_call_id:
                tool_call_id = f"fc_{uuid.uuid4().hex[:16]}"
                call['id'] = tool_call_id
                logger.warning(f"FunctionCall缺少id，已自动生成: {tool_call_id}")

            function_call_msg = {
                "role": 'assistant',
                'tool_calls': [{
                    'id': call['id'],
                    'type': 'function',
                    'function': {
                        'name': name,
                        'arguments': json.dumps(params)
                    }
                }]
            }
            yield {'function_call': function_call_msg}
            messages.append(filter_llm_message(function_call_msg))

            result = await self.call_mcp_tool(server_name, tool_name, params)
            logger.info(f"[FunctionCall] call: {call} 执行结果: {result}")

            def convert_text_content(obj):
                if isinstance(obj, dict):
                    return {k: convert_text_content(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_text_content(item) for item in obj]
                elif hasattr(obj, 'text') or hasattr(obj, '__str__'):
                    # 假设 TextContent 对象有 text 属性或者可以直接转换为字符串
                    return str(obj)
                else:
                    return obj

            # 在序列化之前使用这个函数处理数据
            data_to_serialize = convert_text_content(result)
            json_result = json.dumps(data_to_serialize, ensure_ascii=False)

            tool_result = {
                "role": "tool",
                'name': name,
                "content": json_result,
                'call': call,
                "tool_call_id": tool_call_id
            }
            messages.append(filter_llm_message(tool_result))
            # 用于保存到数组中
            yield {"tool_result": tool_result}
            # has_tool_calls = True
        else:
            logger.warning(f"find no tool call for {call}")

    def add_mcp_server(self, server: dict) -> None:
        """添加一个 MCP Server 到服务列表

        Args:
            server: 服务器配置字典
        """
        if not server.get("enabled", True):
            return
        name = server["name"]
        mode = server.get("mode", "sse")
        if mode == "stdio":
            self.mcp_servers[name] = StdioMCPServer(name, server)
        else:
            self.mcp_servers[name] = FastMCPServer(name, server)
        logger.info(f"添加 MCP Server: {name}")

    def remove_mcp_server(self, server_name: str) -> None:
        """从服务列表中移除一个 MCP Server

        Args:
            server_name: 服务器名称
        """
        if server_name in self.mcp_servers:
            server = self.mcp_servers[server_name]
            # 确保清理资源
            if hasattr(server, "cleanup"):
                asyncio.create_task(server.cleanup())
            del self.mcp_servers[server_name]
            logger.info(f"移除 MCP Server: {server_name}")
