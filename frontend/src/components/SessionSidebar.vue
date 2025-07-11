<template>
  <div class="session-sidebar">
    <div class="session-header">
      <el-button type="primary" @click="createNewSession" class="new-chat-btn">
        <el-icon><Plus /></el-icon>新建会话
      </el-button>
    </div>
    <div class="session-list">
      <el-scrollbar>
        <template v-if="sortedSessions.length === 0">
          <div style="color:#999;text-align:center;padding:32px 0;">暂无会话</div>
        </template>
        <div
          v-for="session in sortedSessions"
          :key="session.id"
          class="session-item"
          :class="{ active: currentSessionId === session.id }"
          @click="selectSession(session.id)"
        >
          <div class="session-info">
            <div class="session-title">{{ session.title || '新会话' }}</div>
            <div class="session-time">{{ formatTime(session.updateTime) }}</div>
          </div>
          <el-button
            v-if="currentSessionId === session.id"
            type="danger"
            size="small"
            circle
            class="delete-btn"
            @click.stop="deleteSession(session.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </el-scrollbar>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { fetchSessions, createSession, deleteSession as apiDeleteSession } from '../utils/api'

const route = useRoute()

const props = defineProps({
  currentSessionId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['session-change'])

const sessions = ref([])
let refreshInterval = null // 添加定时器引用

// 监听 route.name 和 sessions
watch(
  [() => route.name, sessions],
  ([name, list]) => {
    if (list.length === 0) return
    if (name === 'ChatDetail') {
      // 从路由参数读取 sessionId
      const sessionId = route.params.chatId
      if (sessionId) {
        emit('session-change', sessionId)
      }
    } else if (name === 'NewChat') {
      emit('session-change', list[0].id)
    }
  },
  { immediate: true }
)

// 按更新时间排序的会话列表
const sortedSessions = computed(() => {
  return [...sessions.value].sort((a, b) => b.updateTime - a.updateTime)
})

// 在组件卸载时清理定时器
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// 创建新会话
async function createNewSession() {
  try {
    const data = await createSession()
    if (!data._id) {
      throw new Error('创建会话失败：未返回会话ID')
    }
    const newSession = {
      id: data._id,
      title: data.title || '新会话',
      updateTime: Date.now()
    }
    sessions.value.push(newSession)
    emit('session-change', newSession.id)
    ElMessage.success('会话创建成功')
  } catch (error) {
    console.error('创建会话失败:', error)
    ElMessage.error(error.message || '创建会话失败，请检查服务器连接')
  }
}

// 选择会话
function selectSession(id) {
  emit('session-change', id)
}

// 删除会话
async function deleteSession(id) {
  try {
    await ElMessageBox.confirm('确定要删除这个会话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await apiDeleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (props.currentSessionId === id) {
      emit('session-change', null)
    }
    ElMessage.success('会话已删除')
  } catch (error) {
    if (error.message !== 'cancel') {
      console.error('删除会话失败:', error)
      ElMessage.error(error.message || '删除会话失败，请检查服务器连接')
    }
  }
}

// 加载会话列表
async function loadSessions() {
  try {
    const data = await fetchSessions()
    sessions.value = data.map(session => ({
      id: session._id,
      title: session.title || session.name || '新会话',
      updateTime: session.updated_at ? new Date(session.updated_at).getTime() : Date.now()
    }))
    // 首次加载后自动选中第一个会话
    // if (sessions.value.length > 0 && !props.currentSessionId) {
    //   emit('session-change', sessions.value[0].id)
    // }
  } catch (error) {
    console.error('加载会话列表失败:', error)
    ElMessage.error(error.message || '加载会话列表失败，请检查服务器连接')
  }
}

// 格式化时间
function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 在组件挂载时加载会话列表
onMounted(() => {
  loadSessions()
  // 定期刷新会话列表
  refreshInterval = setInterval(loadSessions, 30000) // 每30秒刷新一次
})
</script>

<style scoped>
.session-sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.session-header {
  flex: none;
  padding: 16px;
  border-bottom: 1px solid #eee;
  background: #fff;
}

.new-chat-btn {
  width: 100%;
}

.session-list {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.session-list :deep(.el-scrollbar__wrap) {
  overflow-x: hidden;
}

.session-list :deep(.el-scrollbar__view) {
  padding-bottom: 16px;
}

.session-item {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s;
  background: #fff;
}

.session-item:hover {
  background-color: #f5f7fa;
}

.session-item.active {
  background-color: #ecf5ff;
}

.session-info {
  flex: 1;
  min-width: 0;
  margin-right: 8px;
}

.session-title {
  font-size: 14px;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #303133;
}

.session-time {
  font-size: 12px;
  color: #909399;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .delete-btn {
  opacity: 1;
}
</style> 