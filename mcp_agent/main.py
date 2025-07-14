import sys
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import logging
from mcp_agent.llm_service import LLMService, convert_obj_id
from datetime import datetime
import json
from mcp_agent.session_manager import AsyncSessionManager
import os
import re
from pymongo import MongoClient
import httpx
from mcp_agent.mcp_server_dao import MCPServerDAO
from bson import ObjectId
import asyncio

load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 全局变量
llm_service = None
completion_tasks = {}

# 初始化异步会话管理器
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/mcp")
session_manager = AsyncSessionManager(MONGO_URI)
server_dao = MCPServerDAO()
llm_service = LLMService(server_dao)

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str
    content: str
    name: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[ChatMessage]
    stream: bool = False
    model: Optional[str] = None
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: ChatMessage
    created: int
    model: str


class CompletionRequest(BaseModel):
    message: str

app = FastAPI()


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "llm_service": "running" if llm_service else "stopped"
        }
    }


@app.get("/sessions")
async def list_sessions():
    sessions = await session_manager.list_sessions()
    return [{
        "_id": s["_id"],
        "name": s["name"],
        "title": s["name"] or "新会话"
    } for s in sessions]


@app.post("/session/create")
async def create_session():
    session = await session_manager.create_session()
    return {
        "_id": str(session._id),
        "title": session.name,
        "update_time": session.updated_at if hasattr(session, "updated_at") else None
    }


@app.post("/chat/{chat_id}/session/completion")
async def chat_session_completion(chat_id: str, req: CompletionRequest):
    """
    用户发送消息，AI直接调用工具处理
    """
    session = await session_manager.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    # 1. 追加用户消息
    await session_manager.add_message(
        session_id=chat_id,
        role="user",
        content=req.message
    )
    # 2. 获取历史消息
    messages = await session_manager.get_messages(chat_id)
    for m in messages:
        m.pop('_id', None)
    response_text = ""
    tool_results = []

    async def event_stream():
        # 标记任务为生成中
        completion_tasks[chat_id] = {"status": "generating", "content": ""}
        yield 'data: {"status": "start"}\n\n'
        nonlocal response_text, tool_results

        async for chunk in llm_service.async_generate_response(messages, stream=True):
            if isinstance(chunk, dict):
                logger.info(f"Received dict chunk: {chunk}")
                if "error" in chunk:
                    # 发生错误，返回错误信息
                    response_text = f"错误: {chunk['error']}"
                    yield f"data: {{\"error\": {json.dumps(chunk['error'], ensure_ascii=False)} }}\n\n"
                elif "function_call" in chunk:
                    msg = chunk["function_call"]
                    msg['session_id'] = chat_id
                    await session_manager.add_message_obj(msg)
                    yield f"data: {{\"function_call\": {json.dumps(convert_obj_id(msg), ensure_ascii=False)} }}\n\n"
                elif "tool_result" in chunk:
                    tool_result = chunk["tool_result"]
                    tool_result['session_id'] = chat_id
                    await session_manager.add_message_obj(tool_result)
                    yield f"data: {{\"tool_result\": {json.dumps(convert_obj_id(tool_result), ensure_ascii=False)} }}\n\n"
            elif isinstance(chunk, str):
                response_text += chunk
                # 检查 FunctionCall
                pattern_fc = r"<\|FunctionCallBegin\|>([\s\S]*?)<\|FunctionCallEnd\|>"
                for match in re.finditer(pattern_fc, chunk):
                    try:
                        fc_json = match.group(1)
                        calls = json.loads(fc_json)
                        if not isinstance(calls, list):
                            calls = [calls]
                        for call in calls:
                            await session_manager.add_message(
                                session_id=chat_id,
                                role="assistant",
                                content=match.group(0),
                                tool_call=call,
                                type="tool_call"
                            )
                    except Exception as e:
                        logger.error(f"FunctionCall解析失败: {e}, 内容: {match.group(1)}")
                # 移除 FunctionCall 片段后再保存主回复
                chunk_no_fc = re.sub(pattern_fc, '', chunk)
                completion_tasks[chat_id]["content"] = response_text
                yield f"data: {{\"response\": {json.dumps(chunk_no_fc, ensure_ascii=False)} }}\n\n"
        # 4. 追加AI消息
        # 移除 InnerThought 和 FunctionCall 片段，只保留自然语言内容
        pattern_inner = r"<InnerThoughtBegin>[\s\S]*?<InnerThoughtEnd>"
        pattern_fc = r"<\|FunctionCallBegin\|>[\s\S]*?<\|FunctionCallEnd\|>"
        clean_content = re.sub(pattern_inner, '', response_text)
        clean_content = re.sub(pattern_fc, '', clean_content)

        ai_message = {
            'session_id': chat_id,
            'role': 'assistant',
            'content': clean_content
        }
        await session_manager.add_message_obj(ai_message)
        yield f"data: {{\"update_msg\": {json.dumps(convert_obj_id(ai_message), ensure_ascii=False)} }}\n\n"
        # 任务完成
        completion_tasks.pop(chat_id, None)
        yield f"data: {{\"finish\": true}}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.delete("/chat/{chat_id}/session")
async def delete_chat_session(chat_id: str):
    """
    删除指定会话及其所有消息
    """
    ok = await session_manager.delete_session(chat_id)
    if ok:
        return {"ok": True}
    raise HTTPException(status_code=404, detail="会话不存在")


@app.post("/chat/{chat_id}/session/clear")
async def clear_chat_session(chat_id: str):
    """
    清空指定会话消息
    """
    ok = await session_manager.clear_messages(chat_id)
    if ok:
        return {"ok": True}
    raise HTTPException(status_code=404, detail="会话不存在")


@app.get("/chat/{chat_id}/completion")
async def get_chat_completion_status(chat_id: str):
    """
    刷新聊天页面时，流式返回历史消息列表（每条data: ...），以及正在生成的AI消息（如有）。
    前端只需监听此接口即可获取全部历史和生成中消息。
    """

    async def event_stream():
        # 1. 先返回历史消息
        messages = await session_manager.get_messages(chat_id)
        for m in messages:
            yield f'data: {json.dumps(convert_obj_id(m), ensure_ascii=False)}\n\n'
        # 2. 持续返回生成中的AI消息（如有）
        last_content = None
        while True:
            task = completion_tasks.get(chat_id)
            if not task:
                break  # 任务已完成，跳出循环
            content = task.get("content", "")
            if content != last_content:
                last_content = content
                yield f'data: {json.dumps({ 
                    "id": f"{chat_id}-generating",
                    "role": "assistant",
                    "content": content,
                    "timestamp": None,
                    "loading": True
                }, ensure_ascii=False)}\n\n'
            await asyncio.sleep(0.5)  # 降低频率，减少CPU占用
        # 3. 结束标记
        yield 'data: {"finish": true}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# MCP Server 管理相关接口

def get_servers_collection():
    client = MongoClient(MONGO_URI)
    db = client.get_default_database()
    return db.servers


@app.get("/servers")
async def list_mcp_servers():
    col = get_servers_collection()
    servers = list(col.find({}))
    # _id 转字符串，前端需要
    for s in servers:
        s["_id"] = str(s["_id"])
    return servers


@app.post("/server")
async def save_mcp_server(server: dict):
    col = get_servers_collection()
    name = server.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="服务器名称不能为空")

    _id = server.get("_id")

    # _id = server.pop("_id")
    logger.info(f"save_mcp_server  _id: {_id}, server: {server}")
    if _id:
        server.pop("_id")
        col.update_one({"_id": ObjectId(_id)}, {"$set": server}, upsert=True)
    else:
        args = server.get("args")
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
                if isinstance(parsed, list):
                    server["args"] = parsed
            except Exception:
                pass
        col.insert_one(server)
    return {"ok": True}


@app.delete("/server/{server_id}")
async def delete_mcp_server(server_id: str):
    col = get_servers_collection()
    result = col.delete_one({"_id": ObjectId(server_id)})
    if result.deleted_count:
        return {"ok": True}
    raise HTTPException(status_code=404, detail="未找到该服务器")


@app.get("/server/{_id}/abilities")
async def get_server_abilities(_id: str):
    """
    获取指定MCP Server的能力列表（/list_tools）
    """
    col = get_servers_collection()
    try:
        server = col.find_one({"_id": ObjectId(_id)})
    except Exception as e:
        server = col.find_one({"_id": _id})
    if not server:
        raise HTTPException(status_code=404, detail="未找到该服务器")
    mode = server.get("mode", "sse")
    # if mode == "stdio":
    mcp_server = llm_service.get_mcp_server(server["name"])
    if not mcp_server:
        raise HTTPException(status_code=404, detail="未找到该STDIO服务器实例")
    try:
        logger.info(f"{mode} 服务器配置: {mcp_server.config}")
        await mcp_server.initialize()
        tools = await mcp_server.list_tools()
        logger.info(f"{mode} 服务器能力: {tools}")
        return {"functions": tools}
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[{mode}]{server['name']} 服务器能力获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"{server['name']} 服务器能力获取失败: {e}")


@app.post("/server/{_id}/enable")
async def set_server_enabled(_id: str, data: dict = Body(...)):
    """
    启用/禁用指定id的server，支持热加载/卸载
    """
    global llm_service
    enabled = data.get("enabled")
    if enabled is None:
        raise HTTPException(status_code=400, detail="缺少enabled字段")
    col = get_servers_collection()
    try:
        result = col.update_one({"_id": ObjectId(_id)}, {"$set": {"enabled": enabled}})
    except Exception as e:
        result = col.update_one({"_id": _id}, {"$set": {"enabled": enabled}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="未找到该服务器")
    server = col.find_one({"_id": ObjectId(_id)}) if result.matched_count else col.find_one({"_id": _id})
    if server:
        server["_id"] = str(server["_id"])
        server_name = server.get("name", "未知服务器")
        if enabled:
            logger.info(f"正在启用服务器: {server_name}")
            llm_service.add_mcp_server(server)
            # llm_service.update_mcp_servers()
            logger.info(f"服务器 {server_name} 已启用并完成热加载")
        else:
            logger.info(f"正在禁用服务器: {server_name}")
            llm_service.remove_mcp_server(server["name"])
            # llm_service.update_mcp_servers()
            logger.info(f"服务器 {server_name} 已禁用并完成热卸载")
        return server
    raise HTTPException(status_code=500, detail="服务器状态更新失败")


def main():
    """主函数"""
    global llm_service
    from mcp_agent.mcp_server_dao import MCPServerDAO
    server_dao = MCPServerDAO()
    try:
        llm_service = LLMService(server_dao)
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logger.info("收到退出信号")


if __name__ == "__main__":
    main()
