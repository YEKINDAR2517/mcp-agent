<template>
  <el-container class="app-container">
    <el-header height="56px" class="top-bar">
      <div class="title">MCP Agent Demo</div>
      <div class="top-actions">
        <SettingsMenu @update-mcp-server="onUpdateMcpServer" />
      </div>
    </el-header>
    <el-container class="main-content">
      <SideBar />
      <el-main class="content-area">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
<script setup>
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'
import SettingsMenu from './components/SettingsMenu.vue'
import SideBar from './components/SideBar.vue'
import { Setting } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

// 当前会话id（仅在 chat 路由下有效）
const currentSessionId = computed(() => {
  if (route.name === 'ChatDetail' && route.params.chatId) {
    return route.params.chatId
  }
  return null
})

function onUpdateMcpServer(server) {}
function gotoServerManager() {
  router.push('/servers')
}
</script>
<style>
html, body, #app {
  height: 100%;
  overflow: hidden;
}
.app-container {
  height: 100vh;
  min-height: 0;
}
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0 24px;
  box-sizing: border-box;
}
.title {
  font-size: 1.3em;
  font-weight: bold;
}
.top-actions {
  display: flex;
  align-items: center;
}
.main-content {
  height: calc(100vh - 56px);
  min-height: 0;
  min-width: 0;
}
.content-area, .el-main.content-area {
  position: relative;
  padding: 0 !important;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
}
.sidebar-aside {
  background: #f5f5f5;
  border-right: 1px solid #eee;
  padding: 0;
  position: relative;
  width: 220px;
}
.sidebar-bottom-btn {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  padding: 16px 0 12px 0;
  background: linear-gradient(to top, #f5f5f5 90%, transparent);
  text-align: center;
}
.server-btn {
  background: #e6eaf0 !important;
  color: #6b7685 !important;
  border: none !important;
  box-shadow: none !important;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  transition: background 0.2s, color 0.2s;
}
.server-btn:hover {
  background: #e3f0ff !important;
  color: #3576f5 !important;
}
</style> 