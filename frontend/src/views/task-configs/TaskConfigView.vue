<template>
  <div class="task-config-page">
    <div class="page-header">
      <h2>任务配置清单</h2>
      <el-tag v-if="isConfirmed" type="success" size="large">已确认</el-tag>
    </div>

    <!-- 任务列表 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>任务列表</span>
          <div class="header-actions" v-if="!isConfirmed">
            <el-button type="default" size="small" @click="handleImport">导入</el-button>
            <el-button type="primary" size="small" :icon="Plus" @click="addRow">新增任务</el-button>
          </div>
        </div>
      </template>

      <el-table :data="tasks" border stripe style="width: 100%" size="small">
        <!-- # 序号 -->
        <el-table-column label="#" width="50" align="center" fixed="left">
          <template #default="{ $index }">{{ $index + 1 }}</template>
        </el-table-column>

        <!-- 申报量 -->
        <el-table-column label="申报量(万方)" prop="volume" width="120" align="center">
          <template #default="{ row }">
            <el-input v-if="!isConfirmed" v-model="row.volume" size="small" placeholder="万方" />
            <span v-else>{{ row.volume }}</span>
          </template>
        </el-table-column>

        <!-- 底价选择 -->
        <el-table-column label="底价选择" width="200" align="center">
          <template #default="{ row }">
            <template v-if="!isConfirmed">
              <el-select v-model="row.priceMode" size="small" style="width: 80px; margin-right: 4px">
                <el-option label="系数" value="coeff" />
                <el-option label="垫子" value="pad" />
              </el-select>
              <template v-if="row.priceMode === 'coeff'">
                <el-select v-model="row.priceDiffer" size="small" style="width: 100px">
                  <el-option label="高" value="high" />
                  <el-option label="次" value="second" />
                  <el-option label="30%" value="30%" />
                  <el-option label="40%" value="40%" />
                  <el-option label="底" value="floor" />
                  <el-option label="均" value="avg" />
                </el-select>
              </template>
              <template v-else>
                <el-input v-model="row.padVolume" size="small" style="width: 100px" placeholder="目标量(万方)" />
              </template>
            </template>
            <span v-else>{{ formatPriceMode(row) }}</span>
          </template>
        </el-table-column>

        <!-- 上浮价 -->
        <el-table-column label="上浮价(元)" prop="priceIncrease" width="110" align="center">
          <template #default="{ row }">
            <el-input v-if="!isConfirmed" v-model="row.priceIncrease" size="small" placeholder="元" />
            <span v-else>{{ row.priceIncrease }}</span>
          </template>
        </el-table-column>

        <!-- 上限价 -->
        <el-table-column label="上限价(元)" prop="maxPrice" width="110" align="center">
          <template #default="{ row }">
            <el-input v-if="!isConfirmed" v-model="row.maxPrice" size="small" placeholder="元" />
            <span v-else>{{ row.maxPrice }}</span>
          </template>
        </el-table-column>

        <!-- 保证金 -->
        <el-table-column label="保证金(元)" prop="priceMargin" width="110" align="center">
          <template #default="{ row }">
            <el-input v-if="!isConfirmed" v-model="row.priceMargin" size="small" placeholder="元" />
            <span v-else>{{ row.priceMargin }}</span>
          </template>
        </el-table-column>

        <!-- 数据变动监测 -->
        <el-table-column label="数据变动监测" width="200" align="center">
          <template #default="{ row }">
            <template v-if="!isConfirmed">
              <el-select v-model="row.dataTriggerType" size="small" style="width: 90px; margin-right: 4px" clearable placeholder="类型">
                <el-option label="变化触发" value="change" />
                <el-option label="不变触发" value="stable" />
              </el-select>
              <el-input
                v-if="row.dataTriggerType"
                v-model="row.dataTriggerWindow"
                size="small"
                style="width: 90px"
                placeholder="窗口(ms)"
              />
            </template>
            <span v-else>{{ formatDataTrigger(row) }}</span>
          </template>
        </el-table-column>

        <!-- 互斥 -->
        <el-table-column label="互斥" prop="fallbackRef" width="90" align="center">
          <template #default="{ row }">
            <el-input
              v-if="!isConfirmed"
              v-model="row.fallbackRef"
              size="small"
              placeholder="序号N"
            />
            <span v-else>{{ row.fallbackRef || '—' }}</span>
          </template>
        </el-table-column>

        <!-- 验证 -->
        <el-table-column label="验证" prop="isValidate" width="70" align="center">
          <template #default="{ row }">
            <el-checkbox v-model="row.isValidate" :disabled="isConfirmed" />
          </template>
        </el-table-column>

        <!-- 成交时间 -->
        <el-table-column label="成交时间" prop="triggerTime" width="160" align="center">
          <template #default="{ row }">
            <el-input
              v-if="!isConfirmed"
              v-model="row.triggerTime"
              size="small"
              placeholder="HH:mm:ss.SSS"
            />
            <span v-else>{{ row.triggerTime }}</span>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column label="状态" prop="status" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row, $index }">
            <template v-if="!isConfirmed">
              <el-button
                v-if="row.status === 'pending' || row.status === 'failed'"
                size="small"
                text
                type="warning"
                @click="pauseRow(row)"
              >暂停</el-button>
              <el-button
                v-if="row.status === 'paused'"
                size="small"
                text
                type="success"
                @click="resumeRow(row)"
              >恢复</el-button>
              <el-button size="small" text @click="resetRow(row)">重置</el-button>
              <el-button size="small" text type="primary" @click="copyRow($index)">复制</el-button>
              <el-button size="small" text type="danger" :icon="Delete" @click="removeRow($index)" />
            </template>
            <template v-else>
              <el-button
                v-if="row.status === 'pending' || row.status === 'failed'"
                size="small"
                text
                type="warning"
                @click="pauseRow(row)"
              >暂停</el-button>
              <el-button
                v-if="row.status === 'paused'"
                size="small"
                text
                type="success"
                @click="resumeRow(row)"
              >恢复</el-button>
              <el-button size="small" text @click="resetRow(row)">重置</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 附件上传 -->
    <el-card class="section-card">
      <template #header>
        <span>附件上传</span>
      </template>

      <el-upload
        v-if="!isConfirmed"
        v-model:file-list="fileList"
        :action="uploadAction"
        :headers="uploadHeaders"
        multiple
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :on-remove="handleFileRemove"
        :before-upload="beforeUpload"
        drag
        class="upload-area"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">支持任意格式文件，单文件不超过 50MB</div>
        </template>
      </el-upload>

      <div v-if="isConfirmed && attachments.length > 0" class="attachment-list">
        <div v-for="(file, index) in attachments" :key="index" class="attachment-item">
          <el-icon><Document /></el-icon>
          <span class="attachment-name">{{ file.name || file.filename }}</span>
          <span class="attachment-size" v-if="file.size">({{ formatFileSize(file.size) }})</span>
        </div>
      </div>

      <el-empty v-if="isConfirmed && attachments.length === 0" description="暂无附件" :image-size="60" />
    </el-card>

    <!-- 底部操作 -->
    <div class="action-bar" v-if="!isConfirmed">
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      <el-button type="success" :loading="confirming" @click="handleConfirm">确认配置</el-button>
    </div>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入任务列表" width="600px">
      <el-input
        v-model="importJson"
        type="textarea"
        :rows="12"
        placeholder="粘贴 JSON 数组..."
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, UploadFilled, Document } from '@element-plus/icons-vue'
import { taskConfigApi } from '../../api/task_configs'

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

interface UploadFileItem {
  name: string
  size?: number
  url?: string
  response?: { url?: string; filename?: string }
  status?: string
}

// ---- 路由 ----
const route = useRoute()
const auctionId = computed(() => route.params.id as string)

// ---- 状态 ----
const configStatus = ref<string>('')
const tasks = ref<TaskRow[]>([])
const attachments = ref<AttachmentItem[]>([])
const fileList = ref<UploadFileItem[]>([])
const saving = ref(false)
const confirming = ref(false)
const importDialogVisible = ref(false)
const importJson = ref('')

const isConfirmed = computed(() => configStatus.value === 'confirmed')

// 上传配置
const uploadAction = computed(() => `/api/v1/auctions/${auctionId.value}/task-config/attachments`)
const uploadHeaders = computed(() => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
})

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

const STATUS_TAG_MAP: Record<string, string> = {
  pending: 'info',
  done: 'success',
  failed: 'danger',
  paused: 'warning',
  cancelled: '',
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

function statusTagType(s: string): string {
  return STATUS_TAG_MAP[s] ?? ''
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

function resetRow(row: TaskRow) {
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

// ---- 上传回调 ----
function handleUploadSuccess(_response: unknown, file: UploadFileItem) {
  ElMessage.success(`${file.name} 上传成功`)
}

function handleUploadError(_err: unknown, file: UploadFileItem) {
  ElMessage.error(`${file.name} 上传失败`)
}

function handleFileRemove(file: UploadFileItem) {
  attachments.value = attachments.value.filter(
    (a) => (a.name || a.filename) !== file.name,
  )
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
    fileList.value = attachments.value.map((a) => ({
      name: a.name || a.filename || '',
      size: a.size,
      url: a.url,
      status: 'success',
    }))
  } catch {
    tasks.value = []
    attachments.value = []
    configStatus.value = ''
  }
}

// ---- 保存 ----
async function handleSave() {
  saving.value = true
  try {
    await taskConfigApi.update(auctionId.value, {
      tasks: tasks.value,
      attachments: attachments.value,
    })
    ElMessage.success('保存成功')
  } catch (err: unknown) {
    const error = err as { message?: string }
    ElMessage.error(error?.message || '保存失败')
  } finally {
    saving.value = false
  }
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
  } catch (err: unknown) {
    const error = err as { message?: string }
    ElMessage.error(error?.message || '确认失败')
  } finally {
    confirming.value = false
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
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.upload-area {
  width: 100%;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;
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
