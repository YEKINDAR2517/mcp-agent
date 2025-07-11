# MCP Agent 系统

一个强大的多 MCP Server 调用的 Python Agent 系统，支持实时消息推送、多服务器并发调度和丰富的功能扩展。

## 系统架构

### 核心组件

1. **MCPAgent & MCPAgentManager**
   - `MCPAgent`: 处理单个 Server 的连接和消息
   - `MCPAgentManager`: 管理多个 Agent 实例，实现并发调度

2. **LLM 服务 (llm_service.py)**
   - 集成 OpenAI API
   - 支持流式响应
   - 智能函数调用判断
   - 文本嵌入生成

3. **MCP 功能模块 (mcp_functions.py)**
   - 搜索功能
   - 命令执行
   - 代码分析
   - 系统信息获取

4. **缓存系统 (cache.py)**
   - 双层缓存架构（内存 + 文件）
   - 支持 TTL 过期
   - 持久化存储

### 通信模式

- SSE (Server-Sent Events) 实时推送
- 标准输入输出 (stdio) 模式
- HTTP API 接口 (FastAPI)

## 工作流程

1. **消息处理流程**
   ```
   用户请求 -> FastAPI 路由
             -> LLM 服务判断是否需要调用 MCP 功能
             -> 执行相应功能
             -> 生成回复
             -> 返回结果（支持流式）
   ```

2. **缓存机制**
   ```
   请求 -> 检查内存缓存
        -> 检查文件缓存
        -> 执行操作
        -> 更新缓存
   ```

3. **并发处理**
   ```
   MCPAgentManager
   ├── Agent 1 (Server A)
   ├── Agent 2 (Server B)
   └── Agent N (Server N)
   ```

## 快速开始

### 创建并激活虚拟环境

建议使用 Python 虚拟环境隔离依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1. 创建 `.env` 文件：

```env
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1
```

2. 配置 `config.yaml`：

```yaml
mcp_servers:
  - name: server1
    url: http://localhost:8000
    api_key: your_api_key
  - name: server2
    url: http://localhost:8001
    api_key: your_api_key
```

### 启动服务

```bash
uvicorn mcp_agent.main:app --host 0.0.0.0 --port 8000
```

## API 使用

### 1. 创建对话

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "你好"}]}'
```

### 2. 流式响应

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "你好"}]}'
```

## 扩展系统

### 1. 添加新的 MCP 功能

在 `mcp_functions.py` 中添加新方法：

```python
@staticmethod
async def new_function(param: str) -> Dict[str, Any]:
    try:
        # 实现新功能
        result = {
            "param": param,
            "result": "处理结果",
            "timestamp": datetime.now().isoformat()
        }
        return result
    except Exception as e:
        logger.error(f"新功能执行失败: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### 2. 扩展缓存系统

可以通过继承 `Cache` 类来实现新的缓存后端：

```python
class RedisCache(Cache):
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
        
    async def get(self, key: str, ttl: int = 3600):
        # 实现 Redis 缓存获取
        pass
        
    async def set(self, key: str, value: Any, persist: bool = False):
        # 实现 Redis 缓存设置
        pass
```

### 3. 自定义 LLM 服务

可以修改 `llm_service.py` 来支持其他 LLM 提供商：

```python
class CustomLLMService(LLMService):
    def __init__(self, provider: str):
        self.provider = provider
        # 初始化自定义 LLM 客户端
        
    async def generate_response(self, messages: List[dict], stream: bool = False):
        # 实现自定义 LLM 调用
        pass
```

## 错误处理

系统实现了全面的错误处理机制：

- 函数调用错误捕获
- 自动重连机制
- 缓存异常处理
- API 错误响应格式化

## 注意事项

1. 确保 API 密钥安全存储
2. 监控系统资源使用
3. 定期清理缓存文件
4. 注意并发连接数限制

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

MIT License

## 启动说明

### 1. 启动 MCP Server（SSE 测试服务器）

在项目根目录下运行：

```bash
python tests/sse_test_server.py
```

默认监听端口为 3002（如有修改请以实际端口为准）。

---

### 2. 启动 Agent（如有 main.py 或其他 agent 启动脚本）

如果有专门的 agent 启动脚本（如 main.py），可用如下命令：

```bash
python mcp_agent/main.py
```

（如无 main.py，可忽略此步骤）

---

### 3. 环境变量与 .env

请确保 `.env` 文件中包含如下内容（示例）：

```
OPENAI_API_KEY=sk-xxxxxxx
OPENAI_MODEL=gpt-3.5-turbo
MONGO_URI=mongodb://admin:prHtDGq3xjbHnecU@localhost:27017/sse-agent-demo?authSource=admin
```

---

如有其他问题请参考各模块注释或联系开发者。 