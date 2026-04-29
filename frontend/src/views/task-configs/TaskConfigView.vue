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
          <el-button
            v-if="!isConfirmed"
            type="primary"
            size="small"
            :icon="Plus"
            @click="addRow"
          >
            新增任务
          </el-button>
        </div>
      </template>

      <el-table :data="tasks" border stripe style="width: 100%">
        <el-table-column label="任务编号" prop="task_number" width="100" align="center">
          <template #default="{ row, $index }">
            <el-input
              v-if="!isConfirmed"
              v-model="row.task_number"
              size="small"
              placeholder="编号"
            />
            <span v-else>{{ row.task_number }}</span>
          </template>
        </el-table-column>

        <el-table-column label="任务时间" prop="task_time" width="160" align="center">
          <template #default="{ row }">
            <el-time-picker
              v-if="!isConfirmed"
              v-model="row.task_time"
              size="small"
              format="HH:mm:ss"
              value-format="HH:mm:ss"
              placeholder="选择时间"
              style="width: 100%"
            />
            <span v-else>{{ row.task_time }}</span>
          </template>
        </el-table-column>

        <el-table-column label="价格" prop="price" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-if="!isConfirmed"
              v-model="row.price"
              size="small"
              :precision="2"
              :min="0"
              controls-position="right"
              style="width: 100%"
            />
            <span v-else>{{ row.price }}</span>
          </template>
        </el-table-column>

        <el-table-column label="数量" prop="quantity" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-if="!isConfirmed"
              v-model="row.quantity"
              size="small"
              :min="0"
              controls-position="right"
              style="width: 100%"
            />
            <span v-else>{{ row.quantity }}</span>
          </template>
        </el-table-column>

        <el-table-column label="触发条件" prop="trigger_condition" min-width="140" align="center">
          <template #default="{ row }">
            <el-input
              v-if="!isConfirmed"
              v-model="row.trigger_condition"
              size="small"
              placeholder="触发条件"
            />
            <span v-else>{{ row.trigger_condition }}</span>
          </template>
        </el-table-column>

        <el-table-column label="任务顺序" prop="task_order" width="90" align="center">
          <template #default="{ row }">
            <el-input-number
              v-if="!isConfirmed"
              v-model="row.task_order"
              size="small"
              :min="1"
              controls-position="right"
              style="width: 100%"
            />
            <span v-else>{{ row.task_order }}</span>
          </template>
        </el-table-column>

        <el-table-column label="启停状态" prop="enabled" width="90" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              :disabled="isConfirmed"
              active-text="启"
              inactive-text="停"
            />
          </template>
        </el-table-column>

        <el-table-column label="垫子策略" prop="pad_strategy" width="130" align="center">
          <template #default="{ row }">
            <el-select
              v-if="!isConfirmed"
              v-model="row.pad_strategy"
              size="small"
              placeholder="请选择"
              style="width: 100%"
            >
              <el-option label="无" value="none" />
              <el-option label="固定垫子" value="fixed" />
              <el-option label="动态垫子" value="dynamic" />
              <el-option label="跟随垫子" value="follow" />
            </el-select>
            <span v-else>{{ padStrategyLabel(row.pad_strategy) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="补量策略" prop="supplement_strategy" width="130" align="center">
          <template #default="{ row }">
            <el-select
              v-if="!isConfirmed"
              v-model="row.supplement_strategy"
              size="small"
              placeholder="请选择"
              style="width: 100%"
            >
              <el-option label="无" value="none" />
              <el-option label="自动补量" value="auto" />
              <el-option label="手动补量" value="manual" />
              <el-option label="按比例补量" value="proportional" />
            </el-select>
            <span v-else>{{ supplementStrategyLabel(row.supplement_strategy) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="兜底任务" prop="is_fallback" width="80" align="center">
          <template #default="{ row }">
            <el-checkbox
              v-model="row.is_fallback"
              :disabled="isConfirmed"
            />
          </template>
        </el-table-column>

        <el-table-column v-if="!isConfirmed" label="操作" width="70" align="center" fixed="right">
          <template #default="{ $index }">
            <el-button
              type="danger"
              size="small"
              text
              :icon="Delete"
              @click="removeRow($index)"
            />
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

      <!-- 已上传文件列表（只读模式） -->
      <div v-if="isConfirmed && attachments.length > 0" class="attachment-list">
        <div
          v-for="(file, index) in attachments"
          :key="index"
          class="attachment-item"
        >
          <el-icon><Document /></el-icon>
          <span class="attachment-name">{{ file.name || file.filename }}</span>
          <span class="attachment-size" v-if="file.size">
            ({{ formatFileSize(file.size) }})
          </span>
        </div>
      </div>

      <el-empty
        v-if="isConfirmed && attachments.length === 0"
        description="暂无附件"
        :image-size="60"
      />
    </el-card>

    <!-- 底部操作 -->
    <div class="action-bar" v-if="!isConfirmed">
      <el-button
        type="primary"
        :loading="saving"
        @click="handleSave"
      >
        保存
      </el-button>
      <el-button
        type="success"
        :loading="confirming"
        @click="handleConfirm"
      >
        确认配置
      </el-button>
    </div>
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
  task_number: string
  task_time: string
  price: number | null
  quantity: number | null
  trigger_condition: string
  task_order: number
  enabled: boolean
  pad_strategy: string
  supplement_strategy: string
  is_fallback: boolean
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
    task_number: '',
    task_time: '',
    price: null,
    quantity: null,
    trigger_condition: '',
    task_order: tasks.value.length + 1,
    enabled: true,
    pad_strategy: 'none',
    supplement_strategy: 'none',
    is_fallback: false,
  }
}

const PAD_STRATEGY_MAP: Record<string, string> = {
  none: '无',
  fixed: '固定垫子',
  dynamic: '动态垫子',
  follow: '跟随垫子',
}

const SUPPLEMENT_STRATEGY_MAP: Record<string, string> = {
  none: '无',
  auto: '自动补量',
  manual: '手动补量',
  proportional: '按比例补量',
}

function padStrategyLabel(val: string): string {
  return PAD_STRATEGY_MAP[val] ?? val
}

function supplementStrategyLabel(val: string): string {
  return SUPPLEMENT_STRATEGY_MAP[val] ?? val
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

// ---- 上传回调 ----
function handleUploadSuccess(response: unknown, file: UploadFileItem) {
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
  const MAX_SIZE = 50 * 1024 * 1024 // 50MB
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
    // 同步 fileList 供 el-upload 展示
    fileList.value = attachments.value.map((a) => ({
      name: a.name || a.filename || '',
      size: a.size,
      url: a.url,
      status: 'success',
    }))
  } catch (err: unknown) {
    const error = err as { message?: string }
    // 404 表示尚未配置，显示空表格
    if (error?.message?.includes('404') || error?.message?.includes('not found')) {
      tasks.value = []
      attachments.value = []
      configStatus.value = ''
    } else {
      ElMessage.error(error?.message || '加载任务配置失败')
    }
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
    // 先保存再确认
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
  max-width: 1400px;
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
