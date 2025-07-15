# MCP Agent 系统

一个强大的多 MCP Server 调用的 Python Agent 系统，支持实时消息推送、多服务器并发调度和丰富的功能扩展。

## 目录
- [项目简介](#项目简介)
- [快速开始](#快速开始)
- [前端说明](#前端说明)
- [系统架构](#系统架构)
- [工作流程](#工作流程)
- [API 使用](#api-使用)
- [扩展系统](#扩展系统)
- [错误处理](#错误处理)
- [注意事项](#注意事项)
- [贡献指南](#贡献指南)

## 项目简介

MCP Agent 是一个支持多服务器并发、流式消息推送、能力扩展的智能代理系统，适用于多场景智能对话和自动化任务。前端基于 Vue3 + Element Plus，后端基于 Python FastAPI。

---

## 快速开始

### 1. 克隆项目
```bash
git clone https://your.repo.url/mcp-agent.git
cd mcp-agent
```

### 2. 启动后端
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn mcp_agent.main:app --host 0.0.0.0 --port 8000
```

### 3. 启动前端
```bash
cd frontend
npm install
npm run dev
```
浏览器访问 http://localhost:5173

---

## 前端说明

本项目前端基于 Vue3 + Element Plus 实现，支持多会话、流式对话、MCP Server 管理、路径规划可视化等功能。

### 目录结构
- frontend/
  - src/         # 前端源码
  - package.json # 依赖管理
  - vite.config.js # 构建配置
  - ...

### 主要依赖
- [Vue 3](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [Vite](https://vitejs.dev/)

### 开发说明
- 主要页面入口：`src/views/ChatView.vue`
- 组件目录：`src/components/`
- API 封装：`src/utils/api.js`
- 路由配置：`src/router/`
- 支持 MCP Server 能力管理、会话管理、流式消息、路径规划可视化等。

如需联调后端，请确保后端服务已启动并配置好 MCP Server 地址。

---

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

---

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

---

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

---

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

---

## 错误处理

系统实现了全面的错误处理机制：
- 函数调用错误捕获
- 自动重连机制
- 缓存异常处理
- API 错误响应格式化

---

## 注意事项

1. 确保 API 密钥安全存储
2. 监控系统资源使用
3. 定期清理缓存文件
4. 注意并发连接数限制

---

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

---

## 启动说明

### 1. 启动 MCP Server（SSE 测试服务器）
在项目根目录下运行：
```bash
python tests/sse_test_server.py
```
默认监听端口为 3002（如有修改请以实际端口为准）。

### 2. 启动 Agent（如有 main.py 或其他 agent 启动脚本）
如果有专门的 agent 启动脚本（如 main.py），可用如下命令：
```bash
python mcp_agent/main.py
```
（如无 main.py，可忽略此步骤）

### 3. 环境变量与 .env
请确保 `.env` 文件中包含如下内容（示例）：
```
API_KEY=sk-xxxxxxx
MODEL=gpt-3.5-turbo
MONGO_URI=mongodb://admin:prHtDGq3xjbHnecU@localhost:27017/sse-agent-demo?authSource=admin
```

---

## 常见问题

- **Q: 前端无法连接后端？**  
  A: 请检查后端服务是否已启动，端口和地址是否正确配置。
- **Q: 如何添加新功能？**  
  A: 参考 `mcp_functions.py`，按模板添加静态方法即可。
- **Q: 如何扩展缓存系统？**  
  A: 继承 `Cache` 类实现新后端，参考 `cache.py`。
