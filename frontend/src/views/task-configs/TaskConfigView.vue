<template>
  <div class="task-config-page">
    <div class="page-header" v-if="!props.hideHeader">
      <div class="page-title">
        <h2>任务配置清单</h2>
        <el-tag v-if="isConfirmed" type="success">已确认</el-tag>
        <span v-if="autosaving" class="autosave-hint">保存中...</span>
      </div>
      <div class="header-actions" v-if="!isConfirmed">
        <el-button size="small" @click="handleImport">导入</el-button>
        <el-button type="primary" size="small" :icon="Plus" @click="addRow">新增任务</el-button>
      </div>
    </div>

    <!-- 任务表格 -->
    <div class="table-wrapper">
      <table class="task-table">
        <colgroup>
          <col style="width:36px" />   <!-- # -->
          <col style="width:50px" />   <!-- 申报量 -->
          <col style="width:150px" />  <!-- 底价选择 -->
          <col style="width:68px" />   <!-- 上浮价 -->
          <col style="width:68px" />   <!-- 上限价 -->
          <col style="width:68px" />   <!-- 保证金 -->
          <col style="width:150px" />  <!-- 数据变动监测 -->
          <col style="width:28px" />   <!-- 互斥 -->
          <col style="width:44px" />   <!-- 验证 -->
          <col style="width:80px" />   <!-- 成交时间 -->
          <col style="width:68px" />   <!-- 状态 -->
          <col style="width:130px" />  <!-- 操作 -->
        </colgroup>
        <thead>
          <tr>
            <th>#</th>
            <th>申报量</th>
            <th>底价选择</th>
            <th>上浮价</th>
            <th>上限价</th>
            <th>保证金</th>
            <th>数据变动监测</th>
            <th>互斥</th>
            <th>验证</th>
            <th class="sc-time">成交时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="tasks.length === 0">
            <td colspan="12" style="padding: 32px 0; text-align: center; color: #aaa;">
              暂无任务，点击「新增任务」开始配置
            </td>
          </tr>
          <tr v-for="(row, index) in tasks" :key="index">
            <!-- # -->
            <td>{{ index + 1 }}</td>

            <!-- 申报量 -->
            <td>
              <input v-if="!isConfirmed" v-model="row.volume" class="sc-input" style="width:44px" placeholder="量" />
              <span v-else>{{ row.volume || '—' }}</span>
            </td>

            <!-- 底价选择 -->
            <td>
              <template v-if="!isConfirmed">
                <select v-model="row.priceMode" class="sc-input" style="width:56px">
                  <option value="coeff">系数</option>
                  <option value="pad">垫子</option>
                </select>
                <select v-if="row.priceMode === 'coeff'" v-model="row.priceDiffer" class="sc-input" style="width:52px; margin-left:3px">
                  <option value="high">高</option>
                  <option value="second">次</option>
                  <option value="30%">30%</option>
                  <option value="40%">40%</option>
                  <option value="floor">底</option>
                  <option value="avg">均</option>
                </select>
                <input v-else v-model="row.padVolume" class="sc-input" style="width:52px; margin-left:3px" placeholder="目标量" />
              </template>
              <span v-else>{{ formatPriceMode(row) }}</span>
            </td>

            <!-- 上浮价 -->
            <td class="col-narrow">
              <input v-if="!isConfirmed" v-model="row.priceIncrease" class="sc-input sc-input-narrow" style="width:30px" placeholder="元" />
              <span v-else>{{ row.priceIncrease || '—' }}</span>
            </td>

            <!-- 上限价 -->
            <td class="col-narrow">
              <input v-if="!isConfirmed" v-model="row.maxPrice" class="sc-input sc-input-narrow" style="width:30px" placeholder="元" />
              <span v-else>{{ row.maxPrice || '—' }}</span>
            </td>

            <!-- 保证金 -->
            <td class="col-narrow">
              <input v-if="!isConfirmed" v-model="row.priceMargin" class="sc-input sc-input-narrow" style="width:30px" placeholder="元" />
              <span v-else>{{ row.priceMargin || '—' }}</span>
            </td>

            <!-- 数据变动监测 -->
            <td>
              <template v-if="!isConfirmed">
                <select v-model="row.dataTriggerType" class="sc-input" style="width:68px">
                  <option value="">不检查</option>
                  <option value="change">变化</option>
                  <option value="stable">不变</option>
                </select>
                <input v-model="row.dataTriggerWindow" class="sc-input" style="width:60px; margin-left:3px" placeholder="ms" />
              </template>
              <span v-else>{{ formatDataTrigger(row) }}</span>
            </td>

            <!-- 互斥 -->
            <td>
              <input v-if="!isConfirmed" v-model="row.fallbackRef" class="sc-input" style="width:24px" placeholder="#" />
              <span v-else>{{ row.fallbackRef || '#' }}</span>
            </td>

            <!-- 验证 -->
            <td>
              <input type="checkbox" v-model="row.isValidate" :disabled="isConfirmed" class="sc-validate-input" />
            </td>

            <!-- 成交时间 -->
            <td class="sc-time">
              <input v-if="!isConfirmed" v-model="row.triggerTime" class="sc-input sc-time-input" style="width:76px" placeholder="HH:mm:ss.S" />
              <span v-else class="mono">{{ row.triggerTime || '—' }}</span>
            </td>

            <!-- 状态 -->
            <td>
              <span class="sc-status" :class="'sc-status-' + row.status">{{ statusLabel(row.status) }}</span>
            </td>

            <!-- 操作 -->
            <td style="white-space: nowrap;">
              <button
                v-if="row.status === 'pending' || row.status === 'failed'"
                class="sc-pause-btn" @click="pauseRow(row)"
              >暂停</button>
              <button
                v-if="row.status === 'paused'"
                class="sc-resume-btn" @click="resumeRow(row)"
              >恢复</button>
              <button v-if="!isConfirmed" class="sc-copy-btn" @click="copyRow(index)">复制</button>
              <button v-if="!isConfirmed" class="sc-del-btn" @click="removeRow(index)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 附件上传 -->
    <el-card class="section-card" style="margin-top: 20px;">
      <template #header><span>附件</span></template>
      <div class="attachment-area">
        <el-upload
          v-if="!isConfirmed"
          :show-file-list="false"
          accept=".pdf"
          :http-request="uploadAttachmentRequest"
          :before-upload="beforeUpload"
          multiple
        >
          <el-button size="small" :loading="uploadingAttachment">上传 PDF</el-button>
        </el-upload>
        <div class="attachment-list" v-if="attachments.length">
          <div v-for="(file, i) in attachments" :key="i" class="attachment-item">
            <el-icon><Document /></el-icon>
            <span class="att-name">{{ file.name || file.filename }}</span>
            <span class="att-size" v-if="file.size">{{ formatFileSize(file.size) }}</span>
            <el-button link type="primary" size="small" @click="toggleAttachmentPreview(file.url)">
              {{ attachmentPreviewUrl === file.url ? '收起' : '预览' }}
            </el-button>
            <el-button
              v-if="!isConfirmed"
              link type="danger" size="small"
              @click="removeAttachment(i)"
            >删除</el-button>
          </div>
        </div>
        <span v-else class="no-attachment">暂无附件</span>
        <div v-if="attachmentPreviewUrl && attachments.some(a => a.url === attachmentPreviewUrl)" class="pdf-preview">
          <iframe :src="attachmentPreviewUrl" width="100%" height="600px" />
        </div>
      </div>
    </el-card>

    <!-- 底部操作 -->
    <div class="action-bar">
      <template v-if="!isConfirmed">
        <el-button type="success" :loading="confirming" @click="handleConfirm">确认配置</el-button>
      </template>
      <template v-else>
        <el-button type="primary" :loading="saving" @click="handleReopen">修改</el-button>
      </template>
    </div>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入任务列表" width="600px">
      <el-input v-model="importJson" type="textarea" :rows="12" placeholder="粘贴 JSON 数组..." />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Document } from '@element-plus/icons-vue'
import { taskConfigApi } from '../../api/task_configs'

const props = withDefaults(defineProps<{ hideHeader?: boolean }>(), { hideHeader: false })

// ---- 类型定义 ----
interface TaskRow {
  volume: string
  priceMode: 'coeff' | 'pad'
  priceDiffer: string
  padVolume: string
  priceIncrease: string
  maxPrice: string
  priceMargin: string
  dataTriggerType: string
  dataTriggerWindow: string
  fallbackRef: string
  isValidate: boolean
  triggerTime: string
  status: 'pending' | 'done' | 'failed' | 'paused' | 'cancelled'
}

interface AttachmentItem {
  name?: string
  filename?: string
  size?: number
  url?: string
}


// ---- 路由 ----
const route = useRoute()
const auctionId = computed(() => route.params.id as string)

const emit = defineEmits<{ (e: 'phase-updated'): void }>()

// ---- 状态 ----
const configStatus = ref<string>('')
const tasks = ref<TaskRow[]>([])
const attachments = ref<AttachmentItem[]>([])
const saving = ref(false)
const confirming = ref(false)
const uploadingAttachment = ref(false)
const attachmentPreviewUrl = ref<string | null>(null)
function toggleAttachmentPreview(url?: string) {
  if (!url) return
  attachmentPreviewUrl.value = attachmentPreviewUrl.value === url ? null : url
}
const importDialogVisible = ref(false)
const importJson = ref('')

const isConfirmed = computed(() => configStatus.value === 'confirmed')

// 自动保存：tasks 变化后 debounce 1.5s 保存
let autosaveTimer: ReturnType<typeof setTimeout> | null = null
const autosaving = ref(false)

function scheduleAutosave() {
  if (isConfirmed.value) return
  if (autosaveTimer) clearTimeout(autosaveTimer)
  autosaveTimer = setTimeout(async () => {
    autosaving.value = true
    try {
      await taskConfigApi.update(auctionId.value, {
        tasks: tasks.value,
        attachments: attachments.value,
      })
    } catch {
      // 静默失败，不打扰用户
    } finally {
      autosaving.value = false
    }
  }, 1500)
}

// ---- 工具函数 ----
function createEmptyRow(): TaskRow {
  return {
    volume: '',
    priceMode: 'coeff',
    priceDiffer: 'high',
    padVolume: '',
    priceIncrease: '',
    maxPrice: '',
    priceMargin: '',
    dataTriggerType: '',
    dataTriggerWindow: '',
    fallbackRef: '',
    isValidate: false,
    triggerTime: '',
    status: 'pending',
  }
}

const STATUS_LABEL_MAP: Record<string, string> = {
  pending: '待执行',
  done: '已完成',
  failed: '失败',
  paused: '已暂停',
  cancelled: '已取消',
}


const PRICE_DIFFER_LABEL: Record<string, string> = {
  high: '高',
  second: '次',
  '30%': '30%',
  '40%': '40%',
  floor: '底',
  avg: '均',
}

function statusLabel(s: string): string {
  return STATUS_LABEL_MAP[s] ?? s
}


function formatPriceMode(row: TaskRow): string {
  if (row.priceMode === 'pad') return `垫子 目标量:${row.padVolume}`
  return `系数 ${PRICE_DIFFER_LABEL[row.priceDiffer] ?? row.priceDiffer}`
}

function formatDataTrigger(row: TaskRow): string {
  if (!row.dataTriggerType) return '—'
  const typeLabel = row.dataTriggerType === 'change' ? '变化触发' : '不变触发'
  return `${typeLabel} ${row.dataTriggerWindow}ms`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ---- 表格操作 ----
function addRow() {
  tasks.value.push(createEmptyRow())
}

function removeRow(index: number) {
  tasks.value.splice(index, 1)
}

function copyRow(index: number) {
  const copy = { ...tasks.value[index], status: 'pending' as const }
  tasks.value.splice(index + 1, 0, copy)
}

function pauseRow(row: TaskRow) {
  row.status = 'paused'
}

function resumeRow(row: TaskRow) {
  row.status = 'pending'
}


// ---- 导入 ----
function handleImport() {
  importJson.value = ''
  importDialogVisible.value = true
}

function confirmImport() {
  try {
    const parsed = JSON.parse(importJson.value)
    if (!Array.isArray(parsed)) {
      ElMessage.error('JSON 必须是数组格式')
      return
    }
    const rows: TaskRow[] = parsed.map((item: Record<string, unknown>) => ({
      volume: String(item.volume ?? ''),
      priceMode: (item.priceMode === 'pad' ? 'pad' : 'coeff') as 'coeff' | 'pad',
      priceDiffer: String(item.priceDiffer ?? 'high'),
      padVolume: String(item.padVolume ?? ''),
      priceIncrease: String(item.priceIncrease ?? ''),
      maxPrice: String(item.maxPrice ?? ''),
      priceMargin: String(item.priceMargin ?? ''),
      dataTriggerType: String(item.dataTriggerType ?? ''),
      dataTriggerWindow: String(item.dataTriggerWindow ?? ''),
      fallbackRef: String(item.fallbackRef ?? ''),
      isValidate: Boolean(item.isValidate),
      triggerTime: String(item.triggerTime ?? ''),
      status: (['pending', 'done', 'failed', 'paused', 'cancelled'].includes(String(item.status))
        ? item.status
        : 'pending') as TaskRow['status'],
    }))
    tasks.value = rows
    importDialogVisible.value = false
    ElMessage.success(`已导入 ${rows.length} 条任务`)
  } catch {
    ElMessage.error('JSON 解析失败，请检查格式')
  }
}

// ---- 附件上传 ----
async function uploadAttachmentRequest(req: { file: File }) {
  uploadingAttachment.value = true
  try {
    const fd = new FormData()
    fd.append('file', req.file)
    const token = localStorage.getItem('token')
    const res = await fetch(`/api/v1/auctions/${auctionId.value}/task-config/attachments`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    })
    if (!res.ok) throw new Error('上传失败')
    const meta = await res.json()
    attachments.value = [...attachments.value, meta.data ?? meta]
    await taskConfigApi.update(auctionId.value, { tasks: tasks.value, attachments: attachments.value })
    ElMessage.success(`${req.file.name} 上传成功`)
  } catch {
    ElMessage.error(`${req.file.name} 上传失败`)
  } finally {
    uploadingAttachment.value = false
  }
  return false
}

function removeAttachment(index: number) {
  attachments.value = attachments.value.filter((_, i) => i !== index)
}

function beforeUpload(file: File): boolean {
  const MAX_SIZE = 50 * 1024 * 1024
  if (file.size > MAX_SIZE) {
    ElMessage.error(`文件 ${file.name} 超过 50MB 限制`)
    return false
  }
  return true
}

// ---- 数据加载 ----
async function loadConfig() {
  try {
    const data = await taskConfigApi.get(auctionId.value) as unknown as {
      status: string
      tasks: TaskRow[]
      attachments: AttachmentItem[]
    }
    configStatus.value = data.status ?? ''
    tasks.value = Array.isArray(data.tasks) ? data.tasks : []
    attachments.value = Array.isArray(data.attachments) ? data.attachments : []
  } catch {
    tasks.value = []
    attachments.value = []
    configStatus.value = ''
  }
  // 加载完成后再启动自动保存监听，避免初始化时触发覆盖
  watch(tasks, scheduleAutosave, { deep: true })
}


// ---- 确认配置 ----
async function handleConfirm() {
  await ElMessageBox.confirm(
    '确认后所有字段将变为只读，无法再修改。是否继续？',
    '确认配置',
    {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    },
  )
  confirming.value = true
  try {
    await taskConfigApi.update(auctionId.value, {
      tasks: tasks.value,
      attachments: attachments.value,
    })
    await taskConfigApi.confirm(auctionId.value)
    configStatus.value = 'confirmed'
    ElMessage.success('配置已确认')
    emit('phase-updated')
  } catch (err: unknown) {
    const error = err as { message?: string }
    ElMessage.error(error?.message || '确认失败')
  } finally {
    confirming.value = false
  }
}

// ---- 修改（回退已确认状态） ----
async function handleReopen() {
  saving.value = true
  try {
    await taskConfigApi.update(auctionId.value, {
      tasks: tasks.value,
      attachments: attachments.value,
    })
    configStatus.value = 'pending'
    ElMessage.success('已回退为可编辑状态')
    emit('phase-updated')
  } catch (err: unknown) {
    const error = err as { message?: string }
    ElMessage.error(error?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

// ---- 生命周期 ----
onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.task-config-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.autosave-hint {
  font-size: 12px;
  color: #909399;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 表格容器 */
.table-wrapper {
  overflow-x: auto;
  overflow-y: auto;
  max-height: 420px;
  border: 1px solid #eee;
  border-radius: 6px;
  background: #fff;
  margin-bottom: 20px;
  scroll-behavior: smooth;
}

/* 插件风格表格 */
.task-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.task-table th,
.task-table td {
  border: 1px solid #eee;
  padding: 5px 6px;
  text-align: center;
  white-space: nowrap;
}

.task-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #555;
  position: sticky;
  top: 0;
  z-index: 1;
}

.task-table tbody tr:hover td {
  background: #fafafa;
}

/* 输入框 — 与插件一致 */
.sc-input {
  width: 90px;
  height: 24px;
  padding: 0 4px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 12px;
  box-sizing: border-box;
}

.sc-time-input {
  width: 140px;
}

.sc-validate-input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.sc-time { width: 104px; }
.sc-time-input { width: 95px !important; }
.col-narrow { width: 52px; }
.sc-input-narrow { width: 43px !important; }

/* 状态文字 */
.sc-status { font-size: 12px; font-weight: bold; }
.sc-status-pending  { color: #f90; }
.sc-status-done     { color: #0a0; }
.sc-status-failed   { color: #d93025; }
.sc-status-cancelled{ color: #aaa; }
.sc-status-paused   { color: #888; }

/* 操作按钮 */
.sc-del-btn {
  padding: 0 8px;
  height: 22px;
  background: #f55;
  border: 0;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 12px;
}

.sc-pause-btn {
  padding: 0 6px;
  height: 22px;
  background: #f90;
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 2px;
}

.sc-resume-btn {
  padding: 0 6px;
  height: 22px;
  background: #0a0;
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 2px;
}

.sc-copy-btn {
  padding: 0 6px;
  height: 22px;
  background: #4a9eff;
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 2px;
}

.mono {
  font-family: monospace;
  font-size: 13px;
}

.section-card { margin-bottom: 20px; }
.upload-area { width: 100%; }

.attachment-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 13px;
}

.att-name {
  flex: 1;
  color: #409eff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-size {
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}

.no-attachment {
  font-size: 13px;
  color: #c0c4cc;
}

.pdf-preview {
  margin-top: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}

.pdf-preview iframe {
  display: block;
  border: none;
}

.attachment-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-size {
  color: #909399;
  font-size: 12px;
  flex-shrink: 0;
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 0;
}
</style>
