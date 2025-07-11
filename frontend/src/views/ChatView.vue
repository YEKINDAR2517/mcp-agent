<template>
  <el-container class="app-container">
    <el-main class="content-area">
      <template v-if="chatId">
        <ChatBox
          :session-id="chatId"
          :mcp-server="mcpServer"
          @create-session="onCreateSession"
        />
      </template>
      <template v-else>
        <div style="color:#888;text-align:center;margin-top:80px;">请选择或新建一个会话</div>
      </template>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ChatBox from '../components/ChatBox.vue'

const router = useRouter()
const route = useRoute()
const mcpServer = ref(localStorage.getItem('mcp_server') || '')

// 响应式chatId
const chatId = ref(route.params.chatId || null)

// 自动跳转到第一个会话
onMounted(() => {
  // 刷新或首次进入时，始终用route.params.chatId初始化chatId
  chatId.value = route.params.chatId || null;
  // 打印当前路由
  console.log('当前路由:', route.fullPath)
  console.log('onMounted chatId:', chatId.value)
  if (route.path === '/chat') {
    // 尝试从 sessionStorage 获取最近会话
    const lastSessionId = sessionStorage.getItem('lastSessionId')
    if (lastSessionId) {
      router.replace(`/chat/${lastSessionId}`)
    } else {
      // 动态获取会话列表
      fetch('/api/sessions').then(res => res.json()).then(list => {
        if (Array.isArray(list) && list.length > 0 && list[0]._id) {
          router.replace(`/chat/${list[0]._id}`)
        }
      })
    }
  }
})

watch(() => route.params.chatId, (val) => {
  chatId.value = val || null
  if (val) sessionStorage.setItem('lastSessionId', val)
})

function onCreateSession(sessionId) {
  console.log('onCreateSession:', sessionId)
  router.push(`/chat/${sessionId}`)
}
</script>

<style scoped>
.app-container {
  height: 100vh;
}
.content-area {
  position: relative;
  padding: 24px 32px 0 0;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
}
</style> 