<template>
  <div class="settings-menu">
    <el-dropdown trigger="click" placement="bottom-end">
      <el-avatar :size="36" style="background: #f5f5f5; color: #409eff; cursor: pointer;" >
        <el-icon size="24"><UserFilled /></el-icon>
      </el-avatar>
    </el-dropdown>
  </div>
</template>

<script setup>
import { UserFilled } from '@element-plus/icons-vue'
</script>

<style scoped>
.settings-menu {
  display: inline-block;
}
</style> 