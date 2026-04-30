<template>
  <div class="rectification-view" style="max-width: 1100px; margin: 0 auto; padding: 24px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
      <h2 style="margin: 0;">整改事项跟踪</h2>
      <el-button type="primary" @click="openCreateDialog">新建整改事项</el-button>
    </div>

    <el-table
      :data="items"
      v-loading="loading"
      border
      stripe
      :row-class-name="rowClassName"
    >
      <el-table-column label="标题" prop="title" min-width="160" />
      <el-table-column label="责任人" prop="assignee_id" width="120" />
      <el-table-column label="整改措施" prop="measures" min-width="180" show-overflow-tooltip />
      <el-table-column label="截止日期" prop="due_date" width="120" />
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <!-- 更新状态 -->
            <el-select
              v-if="!isTerminal(row.status)"
              :model-value="row.status"
              size="small"
              style="width: 130px;"
              placeholder="更新状态"
              @change="(val: string) => updateStatus(row, val)"
            >
              <el-option
                v-for="s in editableStatuses"
                :key="s.value"
                :label="s.label"
                :value="s.value"
              />
            </el-select>

            <!-- 上传完成证据 -->
            <el-upload
              v-if="!isTerminal(row.status)"
              :show-file-list="false"
              :before-upload="(file: File) => handleUpload(row, file)"
              action="#"
            >
              <el-button size="small">上传证据</el-button>
            </el-upload>

            <!-- 确认完成（business_owner / retrospective_owner，COMPLETED 状态） -->
            <el-button
              v-if="row.status === 'COMPLETED' && !row.confirmed_by"
              size="small"
              type="success"
              @click="openConfirmDialog(row, 'confirm')"
            >
              确认完成
            </el-button>

            <!-- 关闭 -->
            <el-button
              v-if="!isTerminal(row.status)"
              size="small"
              type="danger"
              plain
              @click="openConfirmDialog(row, 'close')"
            >
              关闭
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建整改事项对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建整改事项" width="520px" @close="resetCreateForm">
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-position="top"
      >
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请填写整改事项标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
        <el-form-item label="整改措施" prop="measures">
          <el-input v-model="createForm.measures" type="textarea" :rows="3" placeholder="请填写具体整改措施" />
        </el-form-item>
        <el-form-item label="截止日期" prop="due_date">
          <el-date-picker
            v-model="createForm.due_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择截止日期"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="责任人 ID" prop="assignee_id">
          <el-input v-model="createForm.assignee_id" placeholder="请填写责任人用户 ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 确认完成 / 关闭 对话框 -->
    <el-dialog
      v-model="confirmDialogVisible"
      :title="confirmAction === 'close' ? '关闭整改事项' : '确认完成'"
      width="420px"
    >
      <template v-if="confirmAction === 'close'">
        <el-form :model="confirmForm" label-position="top">
          <el-form-item label="关闭原因" required>
            <el-input
              v-model="confirmForm.closeReason"
              type="textarea"
              :rows="3"
              placeholder="请填写关闭原因"
            />
          </el-form-item>
        </el-form>
      </template>
      <template v-else>
        <p>确认该整改事项已完成？此操作将记录确认人信息。</p>
      </template>
      <template #footer>
        <el-button @click="confirmDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="doConfirm"
          :loading="confirming"
          :disabled="confirmAction === 'close' && !confirmForm.closeReason"
        >
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { rectificationApi } from '../../api/rectifications'
import type { RectificationItem } from '../../api/types'

const route = useRoute()
const props = defineProps<{ retrospectiveId?: string }>()
const rid = computed(() => props.retrospectiveId || route.params.rid as string || '')

const items = ref<RectificationItem[]>([])
const loading = ref(false)

// ── 状态映射 ──────────────────────────────────────────────
const STATUS_LABEL: Record<string, string> = {
  PENDING: '待处理',
  IN_PROGRESS: '处理中',
  COMPLETED: '已完成',
  DELAYED: '已延期',
  CLOSED: '已关闭',
}

const STATUS_TAG_TYPE: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
  PENDING: 'info',
  IN_PROGRESS: '',
  COMPLETED: 'success',
  DELAYED: 'warning',
  CLOSED: 'danger',
}

const editableStatuses = [
  { value: 'PENDING', label: '待处理' },
  { value: 'IN_PROGRESS', label: '处理中' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'DELAYED', label: '已延期' },
]

function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return STATUS_TAG_TYPE[status] ?? ''
}

function isTerminal(status: string): boolean {
  return status === 'CLOSED'
}

// 超过截止日期且未完成/关闭的行高亮为橙色
function rowClassName({ row }: { row: RectificationItem }): string {
  if (isTerminal(row.status) || row.status === 'COMPLETED') return ''
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(row.due_date)
  if (due < today) return 'row-overdue'
  return ''
}

// ── 加载列表 ──────────────────────────────────────────────
async function loadItems() {
  if (!rid.value) return
  loading.value = true
  try {
    const data = await rectificationApi.list(rid.value) as unknown as RectificationItem[]
    items.value = data
  } catch {
    // 尚未创建整改事项，静默忽略
  } finally {
    loading.value = false
  }
}

// ── 更新状态 ──────────────────────────────────────────────
async function updateStatus(row: RectificationItem, newStatus: string) {
  try {
    await rectificationApi.update(row.id, { status: newStatus })
    row.status = newStatus
    ElMessage.success('状态已更新')
  } catch (err: unknown) {
    ElMessage.error(`更新失败：${err instanceof Error ? err.message : String(err)}`)
  }
}

// ── 上传证据 ──────────────────────────────────────────────
async function handleUpload(row: RectificationItem, file: File): Promise<boolean> {
  try {
    // 将文件名作为证据条目上传（实际项目可替换为 FormData 上传后取 URL）
    const evidence = [{ name: file.name, size: file.size, type: file.type }]
    await rectificationApi.uploadEvidence(row.id, evidence)
    ElMessage.success(`证据 "${file.name}" 上传成功`)
  } catch (err: unknown) {
    ElMessage.error(`上传失败：${err instanceof Error ? err.message : String(err)}`)
  }
  // 返回 false 阻止 el-upload 默认上传行为
  return false
}

// ── 确认完成 / 关闭 ───────────────────────────────────────
const confirmDialogVisible = ref(false)
const confirming = ref(false)
const confirmAction = ref<'confirm' | 'close'>('confirm')
const confirmTargetRow = ref<RectificationItem | null>(null)
const confirmForm = reactive({ closeReason: '' })

function openConfirmDialog(row: RectificationItem, action: 'confirm' | 'close') {
  confirmTargetRow.value = row
  confirmAction.value = action
  confirmForm.closeReason = ''
  confirmDialogVisible.value = true
}

async function doConfirm() {
  if (!confirmTargetRow.value) return
  if (confirmAction.value === 'close' && !confirmForm.closeReason) {
    ElMessage.warning('请填写关闭原因')
    return
  }
  confirming.value = true
  try {
    const action = confirmAction.value === 'close' ? 'close' : 'confirm'
    await rectificationApi.confirm(
      confirmTargetRow.value.id,
      action,
      confirmAction.value === 'close' ? confirmForm.closeReason : undefined,
    )
    confirmDialogVisible.value = false
    ElMessage.success(confirmAction.value === 'close' ? '整改事项已关闭' : '已确认完成')
    await loadItems()
  } catch (err: unknown) {
    ElMessage.error(`操作失败：${err instanceof Error ? err.message : String(err)}`)
  } finally {
    confirming.value = false
  }
}

// ── 新建整改事项 ──────────────────────────────────────────
const createDialogVisible = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()

const createForm = reactive({
  title: '',
  description: '',
  measures: '',
  due_date: '',
  assignee_id: '',
})

const createRules: FormRules = {
  title: [{ required: true, message: '请填写标题', trigger: 'blur' }],
  measures: [{ required: true, message: '请填写整改措施', trigger: 'blur' }],
  due_date: [{ required: true, message: '请选择截止日期', trigger: 'change' }],
  assignee_id: [{ required: true, message: '请填写责任人 ID', trigger: 'blur' }],
}

function openCreateDialog() {
  createDialogVisible.value = true
}

function resetCreateForm() {
  createForm.title = ''
  createForm.description = ''
  createForm.measures = ''
  createForm.due_date = ''
  createForm.assignee_id = ''
  createFormRef.value?.clearValidate()
}

async function submitCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    const data = await rectificationApi.create(rid.value, {
      title: createForm.title,
      description: createForm.description || null,
      measures: createForm.measures,
      due_date: createForm.due_date,
      assignee_id: createForm.assignee_id,
    }) as unknown as RectificationItem
    items.value.push(data)
    createDialogVisible.value = false
    ElMessage.success('整改事项已创建')
  } catch (err: unknown) {
    ElMessage.error(`创建失败：${err instanceof Error ? err.message : String(err)}`)
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadItems()
})
</script>

<style scoped>
/* 超期未完成行橙色高亮 */
:deep(.row-overdue) {
  background-color: #fff3e0 !important;
}
:deep(.row-overdue:hover > td) {
  background-color: #ffe0b2 !important;
}
</style>
