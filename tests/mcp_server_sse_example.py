import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
import json
import logging
import time

logger = logging.getLogger(__name__)

app = FastAPI()

# 工具列表
TOOLS = [
    {
        "name": "add",
        "description": "两个数字相加",
        "params": [
            {"name": "a", "type": "number", "desc": "加数1"},
            {"name": "b", "type": "number", "desc": "加数2"}
        ]
    }
]

@app.get("/list_tools")
async def list_tools():
    return {"functions": TOOLS}

def format_sse(data: str, event=None) -> str:
    """格式化 SSE 消息"""
    msg = f'data: {data}\n'
    if event is not None:
        msg = f'event: {event}\n{msg}'
    return msg + '\n'

@app.get("/sse")
async def sse(request: Request):
    """
    SSE接口，支持function=add&params={...}
    """
    function = request.query_params.get("function")
    params = request.query_params.get("params")
    try:
        params = json.loads(params) if params else {}
    except Exception:
        params = {}
    async def event_stream():
        if function == "add":
            a = params.get("a", 0)
            b = params.get("b", 0)
            try:
                result = float(a) + float(b)
                data = json.dumps({"result": result})
            except Exception as e:
                data = json.dumps({"error": str(e)})
            yield f"data: {data}\n\n"
        else:
            logger.info(f"未知功能，进入长连接心跳: {function}")
            try:
                while True:
                    yield format_sse(json.dumps({"pong": True}))
                    time.sleep(5)
            except GeneratorExit:
                logger.info("SSE连接关闭，心跳循环退出")
            return
    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3010)