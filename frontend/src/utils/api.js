import axios from 'axios'

// 创建axios实例，统一baseURL（走vite代理，实际为''）
const http = axios.create({
  // baseURL: 'http://localhost:8000',
  baseURL: '/api',
  timeout: 15000
})

// 会话相关API
export async function fetchSessions() {
  const res = await http.get('/sessions')
  return res.data || []
}

export async function createSession() {
  const response = await fetch(`/api/session/create`, {
    method: 'POST'
  })
  const data = await response.json()
  return data
}

export async function deleteSession(sessionId) {
  const res = await http.delete(`/chat/${sessionId}/session`)
  return res.data
}

export async function loadMessages(sessionId) {
  const res = await http.get(`/chat/${sessionId}/messages`)
  return res.data || []
}

// MCP Server 管理相关API
export async function loadServers() {
  const res = await http.get('/servers')
  return res.data || []
}

export async function saveServer(server) {
  const res = await http.post('/server', server)
  return res.data
}

export async function removeServer(server_id) {
  const res = await http.delete(`/server/${server_id}`)
  return res.data
}

// 获取会话completion状态（AI回复生成中/完成）
export async function getSessionCompletion(sessionId, message = '') {
  if (message) {
    // 发送新消息
    const response = await fetch(`/api/chat/${sessionId}/session/completion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    })
    return response
  } else {
    // 加载历史消息
    const response = await fetch(`/api/chat/${sessionId}/completion`)
    return response
  }
}

// 获取指定MCP Server能力列表
export async function getServerAbilities(id) {
  const res = await http.get(`/server/${encodeURIComponent(id)}/abilities`)
  return res.data
}

export async function setServerEnabled(id, enabled) {
  const res = await http.post(`/server/${encodeURIComponent(id)}/enable`, { enabled })
  return res.data
}

export async function clearSessionMessages(sessionId) {
  const res = await http.post(`/chat/${sessionId}/session/clear`)
  return res.data
} 