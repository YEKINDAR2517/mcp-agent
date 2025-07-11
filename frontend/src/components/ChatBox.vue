<template>
  <div class="chat-container">
    <div class="message-list" ref="messageList">
      <el-scrollbar>
        <div v-for="(msg, idx) in messagesWithoutToolResults()" :key="msg.id" class="message-item" :class="msg.role">
          <div class="message-avatar">
            <el-avatar :size="36">
              <template v-if="msg.role === 'user'">
                <el-icon><UserFilled /></el-icon>
              </template>
              <template v-else>
                <el-icon><Service /></el-icon>
              </template>
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-role">{{ msg.role === 'user' ? '用户' : 'AI助手' }}</div>
            <template v-if="msg.loading && !msg.content">
              <div class="message-text loading">
                <span class="loading-dots">
                  <i></i><i></i><i></i>
                </span>
              </div>
            </template>
            <template v-else-if="msg.type === 'inner_thought'">
              <el-card class="inner-thought-card" shadow="hover">
                <div class="inner-thought-title">AI思考</div>
                <div class="inner-thought-content">{{ msg.content }}</div>
              </el-card>
            </template>
            <template v-else-if="msg.tool_calls && msg.tool_calls.length">
              <el-card class="function-call-card" shadow="hover">
                <template v-if="Array.isArray(msg.tool_calls)" v-for="(item, idx) in msg.tool_calls" :key="idx" >
                  <div class="fc-block">
                    <div class="fc-title">
                      <el-icon><Tools /></el-icon>
                      <span class="fc-func-name">工具调用：</span>
                      <span class="fc-func-main">{{ item.function?.name }}</span>
                    </div>
                    <div v-if="item.function?.arguments" class="fc-params">
                      <div class="fc-param-title">参数：</div>
                      <div class="fc-param-text">{{ JSON.stringify(JSON.parse(item.function.arguments), null, 2) }}</div>
                    </div>
                  </div>
                  <div class="fc-params" v-for="(result, r_idx) in findToolCallResult(item.id)" :key="r_idx">
                    <div class="fc-param-title">执行结果：</div>
                    <div class="fc-param-text" :class="{ 'fc-result-error': result.isError, 'fc-result-success': !result.isError }">
                      {{ result.isError?'执行失败':'执行成功' }}
                      <el-tooltip placement="top" effect="dark">
                        <template #content>
                          <pre style="max-width:400px;white-space:pre-wrap;">{{ formatResultDetail(result) }}</pre>
                        </template>
                        <el-button size="small" type="primary" text style="margin-left:8px;vertical-align:middle;">查看详情</el-button>
                      </el-tooltip>
                    </div>
                  </div>
                </template>
              </el-card>
            </template>
            <template v-else-if="msg.content && (msg.content.includes('<|InnerThoughtBegin|>') || msg.content.includes('<|FunctionCallBegin|>'))">
              <template v-for="(block, bidx) in parseSpecialBlocks(msg)" :key="bidx">
                <el-card v-if="block.type === 'inner_thought'" class="inner-thought-card" shadow="hover">
                  <div class="inner-thought-title">AI思考</div>
                  <div class="inner-thought-content">{{ block.content }}</div>
                </el-card>
                <el-card v-else-if="block.type === 'tool_call'" class="function-call-card" shadow="hover">
                  <div class="fc-title">
                    <el-icon><Tools /></el-icon>
                    <span class="fc-func-name">工具调用：</span>
                    <span class="fc-func-main">{{ block.tool_call.name }}</span>
                    <el-tag v-if="block.loading" size="small" type="info" style="margin-left:8px;">执行中</el-tag>
                    <el-tag v-else-if="block.tool_result && block.tool_result.isError" size="small" type="danger" style="margin-left:8px;">失败</el-tag>
                    <el-tag v-else-if="block.tool_result" size="small" type="success" style="margin-left:8px;">成功</el-tag>
                  </div>
                  <div v-if="block.tool_call.parameters && typeof block.tool_call.parameters === 'object' && Object.keys(block.tool_call.parameters).length" class="fc-params">
                    <div class="fc-param-title">参数：</div>
                    <div class="fc-param-text">
                      <pre>{{ formatToolArguments(block.tool_call.parameters) }}</pre>
                    </div>
                  </div>
                  <div v-if="block.tool_result" class="fc-params">
                    <div class="fc-param-title">执行结果：</div>
                    <div class="fc-param-text" :class="{ error: block.tool_result?.isError }">
                      <template v-if="Array.isArray(block.tool_result.content)">
                        <div v-for="(item, idx) in block.tool_result.content" :key="idx">
                          <div v-if="item.type === 'text'">{{ item.text }}</div>
                        </div>
                      </template>
                      <template v-else>
                        {{ block.tool_result.content }}
                      </template>
                    </div>
                  </div>
                </el-card>
                <div v-else-if="block.type === 'text'" class="message-text" v-html="formatMessage(block.content)"></div>
              </template>
            </template>
            <template v-else>
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
            </template>
          </div>
        </div>
      </el-scrollbar>
    </div>
    
    <div class="clear-btn-area">
      <el-button
        type="danger"
        :disabled="!props.sessionId"
        @click="clearSessionMessages"
        icon="Delete"
        plain
        size="small"
        style="margin-bottom: 8px;"
      >清空消息</el-button>
    </div>
    <div class="input-area">
      <div class="input-wrap">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          placeholder="输入消息..."
          resize="none"
          @keydown.enter.exact.prevent="sendMessage"
        />
      </div>
      <el-button
        type="primary"
        :icon="Position"
        circle
        class="send-btn"
        :disabled="!inputMessage.trim()"
        @click="sendMessage"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, reactive, onMounted } from 'vue'
import { UserFilled, Service, Position, Tools, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSessionCompletion, createSession, clearSessionMessages as apiClearSessionMessages } from '../utils/api'

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['create-session'])

const inputMessage = ref('')
const messages = ref([])
const messageList = ref(null)

// 处理流式响应
async function handleStreamResponse(response, onMessage) {
  if (!response.body) throw new Error('无流式响应')
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let done = false
  let buffer = ''

  while (!done) {
    const { value, done: doneReading } = await reader.read()
    done = doneReading
    if (value) {
      buffer += decoder.decode(value, { stream: true })
      let lines = buffer.split('\n\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (line.startsWith('data:')) {
          try {
            const data = JSON.parse(line.replace('data:', '').trim())
            // console.log('recv data', data)

            // 1. 普通AI回复
            if (data.response) {
              let aiMsg = messages.value.findLast(msg => msg.role === 'assistant' && msg.loading)
              if (!aiMsg) {
                aiMsg = {
                  id: Date.now().toString() + '-ai',
                  role: 'assistant',
                  content: '',
                  timestamp: new Date(),
                  loading: true
                }
                messages.value.push(aiMsg)
              }
              aiMsg.content += data.response
              await scrollToBottom()
              continue
            }

            // 2. function_call 消息
            if (data.function_call) {
              // 这里需要把function_all消息插入到aiMsg前面
              messages.value.splice(messages.value.findIndex(msg => msg.role === 'assistant' && msg.loading), 0, data.function_call)

              let aiMsg = messages.value.findLast(msg => msg.role === 'assistant' && msg.loading)
              if (aiMsg) {
                aiMsg.content = ''
                aiMsg.loading = true
              }

              await scrollToBottom()
              continue
            }

            // 3. tool_result 消息
            if (data.tool_result) {
              messages.value.push(data.tool_result)
              await scrollToBottom()
              continue
            }

            // 4. update_message 消息
            if (data.update_message) {
              let aiMsg = messages.value.findLast(msg => msg.role === 'assistant' && msg.loading)
              if (aiMsg) {
                aiMsg.content = data.update_message.content
                aiMsg.loading = false
                aiMsg.timestamp = new Date()
              await scrollToBottom()
              }
              continue
            }

            // 其他类型，交给 onMessage
            await onMessage(data)
          } catch (e) {
            console.error('解析消息失败:', e)
            throw e
          }
        }
      }
    }
  }

  // 处理最后剩余的buffer
  if (buffer && buffer.startsWith('data:')) {
    try {
      const data = JSON.parse(buffer.replace('data:', '').trim())
      // 1. 普通AI回复
      if (data.response) {
        let aiMsg = messages.value.findLast(msg => msg.role === 'assistant' && msg.loading)
        if (!aiMsg) {
          aiMsg = {
          id: Date.now().toString() + '-ai',
          role: 'assistant',
            content: '',
          timestamp: new Date(),
            loading: true
        }
          messages.value.push(aiMsg)
        }
        aiMsg.content += data.response
        await scrollToBottom()
        return
      }
      // 2. function_call 消息
      if (data.function_call) {
        const card = {
          id: data.function_call.tool_calls?.[0]?.id || Date.now().toString() + '-fc',
          role: 'assistant',
          type: 'function_call',
          tool_call: data.function_call.tool_calls?.[0],
          tool_result: null,
          loading: false,
          timestamp: data.function_call.timestamp ? new Date(data.function_call.timestamp) : new Date()
        }
        messages.value.push(card)
        await scrollToBottom()
        return
      }
      // 3. tool_result 消息
      if (data.tool_result) {
        const toolCallId = data.tool_result.tool_call_id
        const card = messages.value.find(msg =>
          msg.type === 'function_call' &&
          msg.tool_call &&
          msg.tool_call.id === toolCallId
        )
        if (card) {
          let contentObj = data.tool_result.content
          if (typeof contentObj === 'string') {
            try {
              contentObj = JSON.parse(contentObj)
            } catch {}
          }
          card.tool_result = {
            ...contentObj,
            isError: contentObj?.isError
          }
          card.loading = false
          await scrollToBottom()
        }
        return
      }
      // 4. update_message 消息
      if (data.update_message) {
        let aiMsg = messages.value.findLast(msg => msg.role === 'assistant' && msg.loading)
        if (aiMsg) {
          aiMsg.content = data.update_message.content
          aiMsg.loading = false
          aiMsg.timestamp = new Date()
          await scrollToBottom()
        }
        return
      }
      await onMessage(data)
    } catch (e) {
      console.error('解析最后消息失败:', e)
      throw e
    }
  }
}

let maxMsgCount = 0
// 监听消息列表变化（深度监听，内容变化也触发）, 如何知道是新增消息还是更新消息
watch(messages, () => {
  scrollToBottom(maxMsgCount>0)
  maxMsgCount = Math.max(maxMsgCount, messages.value.length)
}, { deep: true })

// 滚动到底部
async function scrollToBottom(animate = true) {
  await nextTick()
  const scrollbar = messageList.value?.querySelector('.el-scrollbar__wrap')
  if (scrollbar) {
    scrollbar.scrollTo({
      top: scrollbar.scrollHeight,
      behavior: animate ? 'smooth' : 'auto'
    })
  }
}

// 加载历史消息
async function loadHistory(sessionId) {
  messages.value = []
  try {
    const resp = await getSessionCompletion(sessionId)
    const dataList = []
    await handleStreamResponse(resp, async (data) => {
      if (data.finish) return
      console.log('data', data)
      // loading为true的为生成中AI消息，替换最后一条assistant
      if (data.loading) {
        const idx = messages.value.findIndex(m => m.loading)
        if (idx !== -1) messages.value.splice(idx, 1)
        dataList.push(data)
      } else {
        // 补全卡片字段，防止 undefined
        dataList.push({
          ...data,
          type: data.type || null
        })
      }
    })
    messages.value.push(...dataList)
  } catch (error) {
    console.error('加载消息失败:', error)
    ElMessage.error('加载历史消息失败')
  }
}

// 监听会话ID变化
watch(() => props.sessionId, async (newId) => {
  maxMsgCount = 0
  if (newId) {
    await loadHistory(newId)
  } else {
    messages.value = []
  }
})

// 发送消息（流式处理AI回复，带loading）
async function sendMessage() {
  const cleanInput = inputMessage.value.replace(/\s+$/g, '')
  if (!cleanInput) return

  const message = {
    id: Date.now().toString(),
    role: 'user',
    content: cleanInput,
    timestamp: new Date()
  }

  const currentInput = cleanInput
  inputMessage.value = ''
  messages.value.push(message)

  let aiMsg = null
  try {
    let sessionId = props.sessionId
    // 没有会话先创建
    if (!sessionId) {
      const data = await createSession()
      if (!data._id) throw new Error('会话创建失败')
      sessionId = data._id
      emit('create-session', sessionId)
    }

    // 创建AI消息占位
    aiMsg = reactive({
      id: Date.now().toString() + '-ai',
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      loading: true,
    })
    messages.value.push(aiMsg)

    // 流式请求
    const response = await getSessionCompletion(sessionId, currentInput)
    await handleStreamResponse(response, async (data) => {
      // 处理AI回复内容
      if (data.response) {
        aiMsg.content += data.response
        aiMsg.loading = false
      }
      // 处理流式开始
      if (data.status === 'start') {
        aiMsg.loading = true
      }
      // 处理流式结束
      if (data.finish) {
        aiMsg.timestamp = new Date()
        aiMsg.loading = false
      }
    })
  } catch (error) {
    ElMessage.error(error.message || '发送消息失败')
    // 回滚用户消息
    messages.value = messages.value.filter(msg => msg.content !== currentInput)
    // 退出AI loading
    if (aiMsg && aiMsg.loading) aiMsg.loading = false
  }
}

// 格式化时间
function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function toArray(obj) {
  if (!obj) return []
  if (Array.isArray(obj)) return obj.map((v, i) => ({ key: i, value: v }))
  if (typeof obj === 'object') {
    return Object.entries(obj).map(([key, value]) => ({ key, value }))
  }
  return [{ key: '值', value: obj }]
}

function formatMessage(content) {
  if (!content) return ''
  return content.replace(/\n/g, '<br/>')
}

function messagesWithoutToolResults() {
  return messages.value.filter(msg => msg.role !== 'tool')
}

function findToolCallResult(call_id) {
  const results = messages.value.filter(msg => msg.role === 'tool' && msg.tool_call_id === call_id).map(msg => {
    try{
      if(typeof msg.content === 'string'){
        msg.content = JSON.parse(msg.content)
      }
    }catch(e){
      console.error('parse tool result failed', e, "msg.content:", msg.content)
    }
    return msg
  })
  return results
}

function parseSpecialBlocks(msg) {
  const { content } = msg
  if (!content) return []

  const blocks = []

  let lastIdx = 0
  const regex = /(<\|InnerThoughtBegin\|>[\s\S]*?<\|InnerThoughtEnd\|>)|(<\|FunctionCallBegin\|>[\s\S]*?<\|FunctionCallEnd\|>)/g
  let match
  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIdx) {
      blocks.push({ type: 'text', content: content.slice(lastIdx, match.index) })
    }
    if (match[0].startsWith('<|InnerThoughtBegin|>')) {
      const inner = match[0].replace('<|InnerThoughtBegin|>', '').replace('<|InnerThoughtEnd|>', '').trim()
      blocks.push({ type: 'inner_thought', content: inner })
    } else if (match[0].startsWith('<|FunctionCallBegin|>')) {
      let fcJson = match[0].replace('<|FunctionCallBegin|>', '').replace('<|FunctionCallEnd|>', '').trim()
      let parsed = null
      try {
        parsed = JSON.parse(fcJson)
      } catch (e1) {
        try {
          let fcJson2 = fcJson.replace(/[\n\r\t]/g, '')
          parsed = JSON.parse(fcJson2)
        } catch (e2) {
          try {
            let fcJson3 = fcJson.replace(/，/g, ',').replace(/[\n\r\t]/g, '')
            parsed = JSON.parse(fcJson3)
          } catch (e3) {
            console.warn('FunctionCall JSON解析失败', fcJson, e1, e2, e3)
            blocks.push({ type: 'text', content: match[0] })
          }
        }
      }
      if (parsed) {
        (Array.isArray(parsed) ? parsed : [parsed]).forEach(call => {
          blocks.push({ type: 'tool_call', tool_call: call })
        })
      }
    }
    lastIdx = regex.lastIndex
  }
  // // 检查是否有未闭合的 <|InnerThoughtBegin|>
  // const lastBegin = content.lastIndexOf('<|InnerThoughtBegin|>')
  // const lastEnd = content.lastIndexOf('<|InnerThoughtEnd|>')
  // if (lastBegin > lastEnd) {
  //   // 没有找到结束标记，把后面内容都当作 inner_thought
  //   const inner = content.slice(lastBegin + 19).trim()
  //   blocks.push({ type: 'inner_thought', content: inner })
  //   lastIdx = content.length
  // }
  if (lastIdx < content.length) {
    blocks.push({ type: 'text', content: content.slice(lastIdx) })
  }
  return blocks
}

function findToolResult(msg) {
  // 1. 直接取当前消息的 tool_result 字段
  if (msg.tools) return msg.tools
  // 2. 可选：查找上一条消息是否为 tool_result，可扩展
  return []
}

function tryParseTable(text) {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    try {
      // eslint-disable-next-line no-eval
      return eval(text)
    } catch {
      return null
    }
  }
}

function formatToolArguments(args) {
  if (!args) return ''
  if (typeof args === 'string') {
    try {
      const obj = JSON.parse(args)
      return JSON.stringify(obj, null, 2)
    } catch {
      return args
    }
  }
  if (typeof args === 'object') {
    return JSON.stringify(args, null, 2)
  }
  return String(args)
}

function formatResultDetail(result) {
  let obj = result
  if (typeof result === 'object' && result.content) {
    obj = result.content
  }
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}

// 清空当前会话消息
async function clearSessionMessages() {
  if (!props.sessionId) return
  try {
    await apiClearSessionMessages(props.sessionId)
    messages.value = []
    ElMessage.success('消息已清空')
    await scrollToBottom(false)
  } catch (e) {
    ElMessage.error('清空消息失败')
  }
}

onMounted(() => {
  if (props.sessionId) {
    loadHistory(props.sessionId)
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  max-width: 800px;
  margin: 0 auto;
  height: 100%;
  width: 100%;
  position: relative;
  min-height: 0;
  /* background: #f7f9fb; */
}

.message-list {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  padding: 32px 0 16px 16px;
  /* el-scrollbar高度100%保证内容区撑满 */
}
.el-scrollbar {
  height: 100%;
  max-height: 100%;
}

.message-item {
  display: flex;
  margin-bottom: 28px;
  align-items: flex-end;
}

.message-item.user {
  flex-direction: row-reverse;
  justify-content: flex-end;
  align-items: flex-start;
}

.message-item.user .message-content {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
}

.message-item.user .message-text {
  background: linear-gradient(135deg, #4f8cff 0%, #3576f5 100%);
  color: #fff;
  border-radius: 20px 8px 20px 20px;
  margin-left: 0;
  margin-right: 12px;
  box-shadow: 0 2px 8px #3576f522;
}

.message-item.assistant {
  flex-direction: row;
  justify-content: flex-start;
  align-items: flex-start;
}

.message-item.assistant .message-content {
  align-items: flex-start;
  display: flex;
  flex-direction: column;
}

.message-item.assistant .message-text {
  background: #fff;
  color: #333;
  border-radius: 8px 20px 20px 20px;
  margin-left: 12px;
  margin-right: 0;
  box-shadow: 0 2px 8px #0001;
}

.message-avatar {
  margin: 0 12px 0 12px;
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-role {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #3576f5;
}

.message-text {
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  display: flex;
  align-items: center;
  padding: 12px 20px;
  min-width: 40px;
  max-width: 70%;
  box-sizing: border-box;
  margin-bottom: 4px;
  transition: box-shadow 0.2s;
}

.thinking-text {
  color: #409eff;
  margin-left: 8px;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.loading-spin {
  animation: spin 1s linear infinite;
  font-size: 16px;
}
@keyframes spin {
  100% { transform: rotate(360deg); }
}

.message-time {
  font-size: 12px;
  color: #b0b8c7;
  margin-top: 4px;
}

.input-area {
  position: sticky;
  bottom: 0;
  left: 0;
  width: 100%;
  background: #fff;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px 10px 16px;
  margin: 0 16px 24px 0;
  border-radius: 16px;
  box-sizing: border-box;
}
.input-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

.send-btn {
  margin-left: 8px;
  background: linear-gradient(135deg, #4f8cff 0%, #3576f5 100%);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  font-size: 22px;
  box-shadow: 0 2px 8px #3576f522;
  transition: background 0.2s, box-shadow 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.send-btn:active, .send-btn:focus {
  background: #3576f5;
  box-shadow: 0 2px 12px #3576f544;
}
:deep(.el-textarea__inner) {
  resize: none !important;
  border-radius: 12px !important;
  font-size: 15px;
  background: #f7f9fb;
  border: 1.5px solid #e6eaf0;
  box-shadow: 0 1px 4px #3576f508;
  padding: 10px 16px;
  transition: border 0.2s, box-shadow 0.2s;
}
:deep(.el-textarea__inner:focus) {
  border: 1.5px solid #4f8cff;
  box-shadow: 0 2px 8px #4f8cff22;
  background: #fff;
}

.function-call-card {
  background: #f8fafc;
  border: 1.5px solid #e0e7ef;
  margin-bottom: 8px;
  padding: 12px 16px;
}
.fc-title {
  font-weight: bold;
  font-size: 1.1em;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.fc-func-name {
  color: #409eff;
}
.fc-func-main {
  color: #222;
  font-family: monospace;
  margin-left: 4px;
}
.fc-params {
  margin-top: 8px;
}
.fc-param-title {
  font-weight: 500;
  margin-bottom: 4px;
}
.fc-param-text {
  font-family: monospace;
  background: #f3f4f6;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
.fc-block {
  margin-bottom: 16px;
}
.fc-block:last-child {
  margin-bottom: 0;
}

.inner-thought-card {
  margin-bottom: 8px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
}
.inner-thought-title {
  font-weight: bold;
  color: #faad14;
  margin-bottom: 4px;
}
.inner-thought-content {
  color: #ad8b00;
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.tool-result-text.error {
  color: #f56c6c;
  font-weight: bold;
}

.loading-dots {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
}

.loading-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3576f5;
  display: inline-block;
  animation: loading 1.4s infinite;
}

.loading-dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes loading {
  0% {
    transform: scale(0.2);
    opacity: 0.2;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(0.2);
    opacity: 0.2;
  }
}

.message-text.loading {
  background: #f0f7ff;
  min-width: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
}

.fc-param-text.error {
  color: #f56c6c;
  font-weight: bold;
}
.fc-param-text pre {
  margin: 0;
  font-family: monospace;
  background: #f3f4f6;
  padding: 8px 12px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}

.clear-btn-area {
  display: flex;
  justify-content: flex-end;
  margin: 0 16px 0 0;
}

.fc-result-success {
  color: #21ba45;
  font-weight: bold;
}
.fc-result-error {
  color: #f56c6c;
  font-weight: bold;
}
</style> 