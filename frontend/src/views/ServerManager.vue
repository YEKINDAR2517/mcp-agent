<template>
  <div class="card-main">
    <div class="server-manager">
      <h2>MCP Server 管理</h2>
      <el-tabs v-model="activeTab" style="margin-bottom:16px;">
        <el-tab-pane label="SSE 协议服务器" name="sse">
          <el-table :data="sseServers" style="width: 100%" size="small">
            <template #empty>
              <div style="color:#999;text-align:center;padding:32px 0;">暂无SSE服务器</div>
            </template>
            <el-table-column prop="name" label="名称" width="120">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-input v-model="scope.row.name" size="small" />
                </template>
                <template v-else>
                  <span>{{ scope.row.name }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="url" label="地址" width="320">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-input v-model="scope.row.url" size="small" />
                </template>
                <template v-else>
                  <el-tooltip effect="dark" :content="scope.row.url" placement="top">
                    <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:inline-block;max-width:280px;vertical-align:middle;">{{ scope.row.url }}</span>
                  </el-tooltip>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="mode" label="模式" width="100">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-select v-model="scope.row.mode" size="small" style="width:80px">
                    <el-option label="SSE" value="sse" />
                    <el-option label="STDIO" value="stdio" />
                  </el-select>
                </template>
                <template v-else>
                  <span>{{ scope.row.mode || 'sse' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="api_key" label="API Key">
              <template #default="scope">
                <template v-if="(scope.row.mode || 'sse') === 'sse'">
                  <template v-if="scope.row.editing">
                    <el-input v-model="scope.row.api_key" size="small" />
                  </template>
                  <template v-else>
                    <span>{{ scope.row.api_key }}</span>
                  </template>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="启用/禁用" width="130">
              <template #default="scope">
                <el-switch
                  v-model="scope.row.enabled"
                  :active-value="true"
                  :inactive-value="false"
                  @change="(val) => onToggleEnabled(scope.row, val)"
                  :disabled="scope.row.editing"
                  active-text="启用"
                  inactive-text="禁用"
                  size="small"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-button @click="onSave(scope.row)" type="success" size="small" icon="Check" circle title="保存" />
                  <el-button @click="onCancel(scope.row)" type="info" size="small" icon="Refresh" circle title="取消" />
                </template>
                <template v-else>
                  <el-button @click="onEdit(scope.row)" type="primary" size="small" icon="Edit" circle title="编辑" />
                  <el-button @click="removeServer(scope.row)" type="danger" size="small" icon="Delete" circle title="删除" />
                  <el-button @click="showAbilities(scope.row)" type="info" size="small" icon="Menu" circle title="查看能力" />
                </template>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin: 12px 0; text-align: left;">
            <el-button type="primary" size="small" @click="addServer('sse')" icon="Plus">新增SSE</el-button>
            <el-button type="info" size="small" @click="() => loadServers(true)" icon="Refresh">刷新</el-button>
          </div>
        </el-tab-pane>
        <el-tab-pane label="STDIO 协议服务器" name="stdio">
          <el-table :data="stdioServers" style="width: 100%" size="small">
            <template #empty>
              <div style="color:#999;text-align:center;padding:32px 0;">暂无STDIO服务器</div>
            </template>
            <el-table-column prop="name" label="名称" width="120">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-input v-model="scope.row.name" size="small" />
                </template>
                <template v-else>
                  <span>{{ scope.row.name }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="mode" label="模式" width="100">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-select v-model="scope.row.mode" size="small" style="width:80px">
                    <el-option label="SSE" value="sse" />
                    <el-option label="STDIO" value="stdio" />
                  </el-select>
                </template>
                <template v-else>
                  <span>{{ scope.row.mode || 'stdio' }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="command" label="Command" width="120">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-input v-model="scope.row.command" size="small" placeholder="如 npx" />
                </template>
                <template v-else>
                  <span>{{ scope.row.command }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="args" label="Args" width="180">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-input v-model="scope.row.args" size="small" placeholder='如 ["your-pkg", "--stdio"]' />
                </template>
                <template v-else>
                  <span>{{ scope.row.args }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="env" label="Env" width="180">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-input v-model="scope.row.env" size="small" placeholder='如 ["your-pkg", "--stdio"]' />
                </template>
                <template v-else>
                  <span>{{ scope.row.env }}</span>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="启用/禁用" width="130">
              <template #default="scope">
                <el-switch
                  v-model="scope.row.enabled"
                  :active-value="true"
                  :inactive-value="false"
                  @change="(val) => onToggleEnabled(scope.row, val)"
                  :disabled="scope.row.editing"
                  active-text="启用"
                  inactive-text="禁用"
                  size="small"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="scope">
                <template v-if="scope.row.editing">
                  <el-button @click="onSave(scope.row)" type="success" size="small" icon="Check" circle title="保存" />
                  <el-button @click="onCancel(scope.row)" type="info" size="small" icon="Refresh" circle title="取消" />
                </template>
                <template v-else>
                  <el-button @click="onEdit(scope.row)" type="primary" size="small" icon="Edit" circle title="编辑" />
                  <el-button @click="removeServer(scope.row)" type="danger" size="small" icon="Delete" circle title="删除" />
                  <el-button @click="showAbilities(scope.row)" type="info" size="small" icon="Menu" circle title="查看能力" />
                </template>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin: 12px 0; text-align: left;">
            <el-button type="primary" size="small" @click="addServer('stdio')" icon="Plus">新增STDIO</el-button>
            <el-button type="info" size="small" @click="() => loadServers(true)" icon="Refresh">刷新</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
      <el-dialog v-model="abilityDialogVisible" :title="abilityServerName + ' 能力列表'" width="600px">
        <el-table :data="abilityList" size="small" style="width:100%" :row-key="row => row.name" :expand-row-keys="expandedRowKey ? [expandedRowKey] : []" @expand-change="onExpandChange">
          <el-table-column type="expand">
            <template #default="props">
              <div v-if="props.row.params && props.row.params.length" style="padding-left:60px;">
                <div style="font-weight:bold;margin-bottom:4px;">参数：</div>
                <el-table :data="props.row.params" size="small" style="width:100%">
                  <el-table-column prop="name" label="参数名" width="120">
                    <template #default="scope">
                      <span>{{ scope.row.name }}</span>
                      <span v-if="scope.row.required" style="color: #f56c6c; margin-left: 4px;">*</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="type" label="类型" width="80" />
                  <el-table-column prop="desc" label="描述" />
                </el-table>
              </div>
              <div v-else style="color:#888;padding-left:60px;">无参数</div>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" width="180" />
          <el-table-column prop="description" label="描述" />
        </el-table>
        <template #footer>
          <el-button @click="abilityDialogVisible = false">关闭</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { loadServers as apiLoadServers, saveServer as apiSaveServer, removeServer as apiRemoveServer, getServerAbilities, setServerEnabled } from '../utils/api'
import { Plus, Check, Refresh, Edit, Delete, Menu } from '@element-plus/icons-vue'
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

const servers = ref([])
const activeTab = ref('sse')
const abilityDialogVisible = ref(false)
const abilityList = ref([])
const abilityServerName = ref('')
const expandedRowKey = ref(null)

const sseServers = computed(() => servers.value.filter(s => (s.mode || 'sse') === 'sse'))
const stdioServers = computed(() => servers.value.filter(s => s.mode === 'stdio'))

async function loadServers(showMessage = false) {
  try {
    const data = await apiLoadServers()
    servers.value = data.map(s => ({ ...s, editing: false }))
    if (showMessage) {
      ElMessage.success('已加载')
    }
  } catch (e) {
    ElMessage.error('加载服务器列表失败')
  }
}

function addServer(mode) {
  servers.value.push({
    name: '',
    url: '',
    api_key: '',
    mode: mode,
    command: '',
    args: '',
    env: '',
    enabled: true,
    editing: true
  })
}

function onEdit(server) {
  server.editing = true
}

function onCancel(server) {
  if (!server.name && !server.url && !server.api_key) {
    servers.value = servers.value.filter(s => s !== server)
  } else {
    server.editing = false
  }
}

async function onSave(server) {
  try {
    await apiSaveServer(server)
    ElMessage.success('保存成功')
    loadServers(false)
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

async function removeServer(server) {
  try {
    await ElMessageBox.confirm(
      `确定要删除服务器「${server.name}」吗？此操作不可撤销。`,
      '确认删除',
      { type: 'warning' }
    )
    await apiRemoveServer(server._id)
    ElMessage.success('已删除')
    await loadServers(false)
  } catch (e) {
    // 用户取消或出错
  }
}

async function showAbilities(server) {
  try {
    const data = await getServerAbilities(server._id)
    // 适配 { functions: [...] } 结构
    let functions = Array.isArray(data) ? data : (Array.isArray(data.functions) ? data.functions : [])
    // 统一 params 字段，兼容多种协议返回
    functions = functions.map(fn => {
      let params = []
      // 1. params 为 OpenAI function-calling schema
      if (fn.params && typeof fn.params === 'object' && fn.params.properties) {
        params = Object.entries(fn.params.properties).map(([name, prop]) => ({
          name,
          type: prop.type || '',
          desc: prop.description || '',
          required: fn.params.required?.includes(name) || false
        }))
      }
      // 2. inputSchema 为 OpenAI function-calling schema
      else if (fn.inputSchema && typeof fn.inputSchema === 'object' && fn.inputSchema.properties) {
        params = Object.entries(fn.inputSchema.properties).map(([name, prop]) => ({
          name,
          type: prop.type || '',
          desc: prop.description || '',
          required: fn.inputSchema.required?.includes(name) || false
        }))
      }
      return { ...fn, params }
    })
    abilityList.value = functions
    abilityServerName.value = server.name
    abilityDialogVisible.value = true
  } catch (e) {
    abilityList.value = []
    ElMessage.error('获取服务器能力失败')
  }
}

function onExpandChange(expandedRowKeys) {
  expandedRowKey.value = expandedRowKeys.length ? expandedRowKeys[0] : null
}

async function onToggleEnabled(server, val) {
  try {
    ElMessage({
      type: 'info',
      message: val ? `正在启用服务器: ${server.name}...` : `正在禁用服务器: ${server.name}...`,
      duration: 0
    })
    await setServerEnabled(server._id, val)
    ElMessage.closeAll()
    ElMessage.success(val ? `服务器 ${server.name} 已启用并完成热加载` : `服务器 ${server.name} 已禁用并完成热卸载`)
    loadServers(false)
    // 如果能力弹窗正在打开且是当前 server，自动刷新能力
    if (abilityDialogVisible.value && abilityServerName.value === server.name) {
      await showAbilities(server)
    }
  } catch (e) {
    ElMessage.closeAll()
    ElMessage.error('切换失败')
    // 回滚
    server.enabled = !val
  }
}

onMounted(() => {
  loadServers(false)
})
</script>

<style scoped>
.card-main {
  background: #fff;
  border-radius: 18px;
  box-shadow: 0 4px 24px #3576f508, 0 1.5px 4px #0001;
  padding: 0px 36px 32px 36px;
  margin: 32px 32px 0 0;
  min-height: 600px;
}
.server-manager h2 {
  font-size: 2em;
  font-weight: 700;
  margin-bottom: 24px;
  letter-spacing: 1px;
}
.el-tabs {
  margin-bottom: 16px;
}
.json-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 8px;
  font-size: 12px;
  background: #fff;
}
.json-editor :deep(.vjs-tree) {
  font-family: monospace;
}
</style>