# MCP Agent 前端 (@frontend)

本项目为 MCP Agent 聊天系统的前端部分，基于 Vue3 + Element Plus 实现，支持多会话、流式对话、MCP Server 管理、路径规划可视化等功能。

## 目录结构

- @frontend
  - src/         # 前端源码
  - package.json # 依赖管理
  - vite.config.js # 构建配置
  - ...

## 主要依赖

- [Vue 3](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [Vite](https://vitejs.dev/)

## 启动方式

1. 安装依赖

```bash
cd @frontend
npm install
```

2. 启动开发服务器

```bash
npm run dev
```

3. 访问页面

浏览器打开 http://localhost:5173 （或终端输出的端口）

## 开发说明

- 主要页面入口：`src/views/ChatView.vue`
- 组件目录：`src/components/`
- API 封装：`src/utils/api.js`
- 路由配置：`src/router/`
- 支持 MCP Server 能力管理、会话管理、流式消息、路径规划可视化等。

## 其它

如需联调后端，请确保后端服务已启动并配置好 MCP Server 地址。

---
如有问题请联系开发者。 