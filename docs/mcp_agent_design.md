# Python Agent 设计文档：支持调度多个 MCP Server（SSE & stdio）与 LLM 集成

## 一、项目背景
本项目旨在实现一个智能 Python Agent，能够通过 Server-Sent Events（SSE）协议与多个已配置好的 MCP（Multi-Channel Processing）Server 进行通信，并集成 LLM（Large Language Model）服务实现智能交互。Agent 负责并发发送请求、接收并处理各服务端推送的实时数据流，适用于需要持续获取多源服务端消息的智能处理场景。

## 二、技术选型
- 语言：Python 3.x
- Web 框架：FastAPI
- 网络通信：SSE（Server-Sent Events）
- 本地通信：标准输入输出（stdio）
- HTTP 客户端库：requests、sseclient、httpx
- LLM 服务：OpenAI API
- 配置管理：YAML/JSON 配置文件 + 环境变量（.env）
- 缓存系统：双层缓存（内存 + 文件）
- 日志：logging
- 并发模型：asyncio
- 数据验证：Pydantic

## 三、系统架构

### 1. 核心组件
1. **配置模块**
   - 负责读取多个 MCP Server 的地址、认证信息、请求参数等配置
   - 支持选择工作模式（SSE 或 stdio）
   - 管理 LLM API 密钥和配置

2. **Agent 主体**
   - MCPAgent：处理单个 Server 的连接和消息
   - MCPAgentManager：管理多个 Agent 实例，实现并发调度
   - 支持 SSE 和 stdio 两种工作模式

3. **LLM 服务**
   - 集成 OpenAI API
   - 智能判断是否需要调用 MCP 功能
   - 支持流式响应
   - 文本嵌入生成
   - 缓存优化

4. **功能模块**
   - 搜索功能
   - 命令执行
   - 代码分析
   - 系统信息获取
   - 可扩展的功能接口

5. **缓存系统**
   - 内存缓存：快速访问
   - 文件缓存：持久化存储
   - TTL 过期机制
   - 线程安全

6. **API 接口**
   - RESTful API
   - WebSocket 支持
   - 认证中间件
   - 错误处理

### 2. 数据流
```
用户请求 -> FastAPI 路由
         -> 认证中间件
         -> LLM 服务（判断意图）
         -> MCPAgentManager
         -> 具体 Agent 执行
         -> 缓存处理
         -> 响应返回
```

## 四、详细设计

### 1. LLM 服务设计
```python
class LLMService:
    def __init__(self, mcp_manager: MCPAgentManager):
        self.mcp_manager = mcp_manager
        self.client = AsyncOpenAI()
        
    async def _should_call_mcp(self, messages: List[dict]) -> Optional[str]:
        # 智能判断是否需要调用 MCP 功能
        pass
        
    async def generate_response(self, messages: List[dict], stream: bool = False):
        # 生成回复（支持流式）
        pass
        
    async def get_embedding(self, text: str) -> List[float]:
        # 获取文本嵌入向量
        pass
```

### 2. 缓存系统设计
```python
class Cache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        # 获取缓存（先查内存，再查文件）
        pass
        
    def set(self, key: str, value: Any, persist: bool = False):
        # 设置缓存（支持持久化）
        pass
```

### 3. 功能模块设计
```python
class MCPFunctions:
    @staticmethod
    async def search(query: str) -> Dict[str, Any]:
        # 搜索功能
        pass
        
    @staticmethod
    async def execute(command: str) -> Dict[str, Any]:
        # 执行命令
        pass
        
    @staticmethod
    async def analyze_code(code: str) -> Dict[str, Any]:
        # 代码分析
        pass
```

## 五、配置示例

### 1. 环境变量配置 (.env)
```env
API_KEY=your_api_key
BASE_URL=https://api.openai.com/v1
```

### 2. MCP Server 配置 (config.yaml)
```yaml
mcp_servers:
  - name: server1
    mode: sse
    url: http://localhost:8000
    api_key: your_api_key
  - name: server2
    mode: stdio
```

## 六、错误处理机制

1. **异常捕获层级**
   - API 层：处理请求相关错误
   - LLM 层：处理模型调用错误
   - Agent 层：处理连接和消息错误
   - 功能层：处理具体功能执行错误

2. **自动重连机制**
   - 连接断开自动重试
   - 指数退避策略
   - 最大重试次数限制

3. **错误响应格式**
```python
{
    "error": str,
    "timestamp": datetime,
    "details": Optional[Dict]
}
```

## 七、扩展性设计

### 1. 新增功能
- 实现 `MCPFunctions` 中的新方法
- 注册到 LLM 服务的功能列表
- 添加相应的单元测试

### 2. 自定义缓存后端
- 继承 `Cache` 基类
- 实现 `get`/`set` 接口
- 可选实现持久化

### 3. 支持新的 LLM 提供商
- 继承 `LLMService` 基类
- 实现必要的接口方法
- 配置相应的认证信息

## 八、性能优化

1. **缓存策略**
   - LLM 响应缓存
   - 嵌入向量缓存
   - 功能调用结果缓存

2. **并发处理**
   - 异步 I/O
   - 连接池
   - 批量处理

3. **资源管理**
   - 定期清理过期缓存
   - 限制并发连接数
   - 内存使用监控

## 九、安全性考虑

1. **API 认证**
   - API 密钥验证
   - 请求签名
   - 访问控制

2. **数据安全**
   - 敏感信息加密
   - 安全的配置管理
   - 日志脱敏

3. **运行时安全**
   - 命令执行沙箱
   - 资源使用限制
   - 错误信息保护

## 十、测试策略

1. **单元测试**
   - 各组件独立测试
   - 模拟外部依赖
   - 边界条件测试

2. **集成测试**
   - 端到端流程测试
   - 多 Server 并发测试
   - 性能压力测试

3. **功能测试**
   - API 接口测试
   - LLM 功能测试
   - 缓存机制测试

## 十一、部署建议

1. **环境准备**
   - Python 3.8+
   - 虚拟环境
   - 依赖管理

2. **配置管理**
   - 环境变量
   - 配置文件
   - 密钥管理

3. **监控告警**
   - 日志收集
   - 性能监控
   - 异常告警

## 十二、总结
本系统通过整合 SSE、stdio、LLM 和缓存等技术，实现了一个功能强大、可扩展的智能 Agent 系统。系统架构清晰，组件解耦，易于维护和扩展，同时具备良好的性能和可靠性。 