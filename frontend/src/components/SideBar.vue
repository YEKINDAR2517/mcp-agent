<template>
  <div class="side-bar" :class="{ collapsed }">
    <button class="sidebar-toggle" :class="{ 'sidebar-toggle-collapsed': collapsed }" @click="toggleSidebar">
      <el-tooltip :content="collapsed ? '展开侧边栏' : '收起侧边栏'" placement="right">
        <el-icon v-if="!collapsed" style="font-size: 22px;"><ArrowLeft /></el-icon>
        <el-icon v-else style="font-size: 22px;"><Menu /></el-icon>
      </el-tooltip>
    </button>
    <div v-if="!collapsed" class="side-bar-content">
      <SessionSidebar :current-session-id="currentSessionId" @session-change="onSessionChange" />
    </div>
    <div class="sidebar-bottom-btn">
      <el-button type="default" size="large" @click="gotoServerManager" class="server-btn">
        <el-icon><Setting /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SessionSidebar from './SessionSidebar.vue'
import { ArrowLeft, Menu, Setting } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const currentSessionId = computed(() => route.params.chatId || null)

function toggleSidebar() {
  collapsed.value = !collapsed.value
}
function gotoServerManager() {
  router.push('/servers')
}
function onSessionChange(id) {
  router.push(`/chat/${id}`)
}
</script>

<style scoped>
.side-bar {
  background: #f5f5f5;
  border-right: 1px solid #eee;
  width: 220px;
  min-width: 60px;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
}
.side-bar.collapsed {
  width: 60px;
}
.side-bar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 8px 8px 16px;
  min-height: 56px;
}
.logo {
  font-size: 1.2em;
  font-weight: bold;
  color: #3576f5;
  letter-spacing: 2px;
}
.sidebar-toggle {
  position: absolute;
  left: 200px;
  top: 18px;
  z-index: 30;
  box-shadow: 0 2px 8px #0002;
  background: #e6eaf0;
  border: 1.5px solid #e0e3e8;
  color: #6b7685;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border 0.2s, left 0.2s;
}
.sidebar-toggle:hover {
  background: #e3f0ff;
  color: #3576f5;
  border: 1.5px solid #3576f5;
}
.sidebar-toggle-collapsed {
  left: 10px !important;
  top: 18px;
}
.side-bar-content {
  min-height: 100px;
  background-color: red;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100% - 72px);
}
.side-bar.collapsed .side-bar-content {
  display: none;
}
.sidebar-bottom-btn {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  padding: 16px 0 12px 0;
  background: linear-gradient(to top, #f5f5f5 90%, transparent);
  text-align: center;
  height: 72px;
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