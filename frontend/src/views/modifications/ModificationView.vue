<template>
  <div class="modification-view">
    <div class="page-header">
      <h2>临场修改管理</h2>
      <div class="header-actions">
        <!-- trader / monitor 可提交申请 -->
        <el-button
          v-if="canSubmitRequest"
          type="primary"
          @click="openCreateDialog"
        >
          提交临场修改申请
        </el-button>
        <!-- 仅 trader 可应急执行 -->
        <el-button
          v-if="isTrader"
          type="danger"
          @click="openEmergencyDialog"
        >
          应急执行
        </el-button>
      </div>
    </div>

    <!-- 修改记录列表 -->
    <el-table
      v-loading="loading"
      :data="modifications"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="80" show-overflow-tooltip />
      <el-table-column label="状态" width="160">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
          <el-tag v-if="row.is_emergency" type="danger" size="small" style="margin-left: 4px">
            应急
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="修改原因" min-width="160" show-overflow-tooltip />
      <el-table-column prop="impact_scope" label="影响范围" min-width="140" show-overflow-tooltip />
      <el-table-column prop="requested_by" label="申请人" width="100" />
      <el-table-column label="申请时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.requested_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <!-- strategy_owner：审批通过 / 驳回（PENDING_APPROVAL） -->
          <template v-if="isStrategyOwner && row.status === 'PENDING_APPROVAL'">
            <el-button type="success" size="small" @click="handleApprove(row)">审批通过</el-button>
            <el-button type="danger" size="small" @click="openRejectDialog(row, 'approve')">驳回</el-button>
          </template>

          <!-- reviewer：复核通过 / 驳回（PENDING_REVIEW） -->
          <template v-if="isReviewer && row.status === 'PENDING_REVIEW'">
            <el-button type="success" size="small" @click="handleReview(row)">复核通过</el-button>
            <el-button type="danger" size="small" @click="openRejectDialog(row, 'review')">驳回</el-button>
          </template>

          <!-- trader：标记执行（APPROVED） -->
          <template v-if="isTrader && row.status === 'APPROVED'">
            <el-button type="primary" size="small" @click="handleExecute(row)">标记执行</el-button>
          </template>

          <!-- trader / retrospective_owner：补充应急说明 -->
          <template
            v-if="
              (isTrader || isRetrospectiveOwner) &&
              (row.status === 'PENDING_POST_EXPLANATION' || row.status === 'PENDING_DEVIATION_EXPLANATION')
            "
          >
            <el-button type="warning" size="small" @click="openExplanationDialog(row)">
              补充说明
            </el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <!-- 提交临场修改申请 Dialog -->
    <el-dialog v-model="createDialogVisible" title="提交临场修改申请" width="520px" @close="resetCreateForm">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="修改原因" prop="reason">
          <el-input
            v-model="createForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请填写修改原因（必填）"
          />
        </el-form-item>
        <el-form-item label="影响范围" prop="impact_scope">
          <el-input
            v-model="createForm.impact_scope"
            type="textarea"
            :rows="2"
            placeholder="请描述影响范围（必填）"
          />
        </el-form-item>
        <el-form-item label="风险说明">
          <el-input
            v-model="createForm.risk_notes"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交</el-button>
      </template>
    </el-dialog>

    <!-- 应急执行 Dialog -->
    <el-dialog v-model="emergencyDialogVisible" title="应急执行" width="520px" @close="resetEmergencyForm">
      <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
        应急执行将跳过常规审批流程，请确认已获得授权。
      </el-alert>
      <el-form ref="emergencyFormRef" :model="emergencyForm" :rules="emergencyRules" label-width="120px">
        <el-form-item label="修改原因" prop="reason">
          <el-input
            v-model="emergencyForm.reason"
            type="textarea"
            :rows="3"
            placeholder="请填写应急执行原因（必填）"
          />
        </el-form-item>
        <el-form-item label="影响范围" prop="impact_scope">
          <el-input
            v-model="emergencyForm.impact_scope"
            type="textarea"
            :rows="2"
            placeholder="请描述影响范围（必填）"
          />
        </el-form-item>
        <el-form-item label="是否预授权">
          <el-switch v-model="emergencyForm.is_pre_authorized" />
          <span style="margin-left: 8px; color: #909399; font-size: 12px">
            {{ emergencyForm.is_pre_authorized ? '已预授权' : '未预授权（需事后补充说明）' }}
          </span>
        </el-form-item>
        <el-form-item label="风险说明">
          <el-input
            v-model="emergencyForm.risk_notes"
            type="textarea"
            :rows="2"
            placeholder="可选"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="emergencyDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="submitEmergency">确认应急执行</el-button>
      </template>
    </el-dialog>

    <!-- 驳回原因 Dialog -->
    <el-dialog v-model="rejectDialogVisible" title="填写驳回原因" width="440px" @close="resetRejectForm">
      <el-form ref="rejectFormRef" :model="rejectForm" :rules="rejectRules" label-width="90px">
        <el-form-item label="驳回原因" prop="comment">
          <el-input
            v-model="rejectForm.comment"
            type="textarea"
            :rows="4"
            placeholder="请填写驳回原因（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitting" @click="submitReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 补充应急说明 Dialog -->
    <el-dialog v-model="explanationDialogVisible" title="补充应急说明" width="480px" @close="resetExplanationForm">
      <el-form ref="explanationFormRef" :model="explanationForm" :rules="explanationRules" label-width="100px">
        <el-form-item label="事后说明" prop="post_explanation">
          <el-input
            v-model="explanationForm.post_explanation"
            type="textarea"
            :rows="4"
            placeholder="请填写应急执行的事后说明（必填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="explanationDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitExplanation">提交说明</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { modificationApi } from '@/api/modifications'
import { auctionApi } from '@/api/auctions'
import { useAuthStore } from '@/stores/auth'
import type { Modification, Auction } from '@/api/types'

// ---- Route & Auth ----
const route = useRoute()
const auctionId = computed(() => route.params.id as string)
const authStore = useAuthStore()
const currentUserId = computed(() => authStore.user?.id ?? '')

// ---- Auction (for role checks) ----
const auction = ref<Auction | null>(null)

const hasRole = (role: string) => {
  if (!auction.value) return false
  return (auction.value.roles ?? {})[role] === currentUserId.value
}

// ---- 角色判断 ----
const isTrader = computed(() => hasRole('trader'))
const isStrategyOwner = computed(() => hasRole('strategy_owner'))
const isReviewer = computed(() => hasRole('reviewer'))
const isRetrospectiveOwner = computed(() => hasRole('retrospective_owner'))
const canSubmitRequest = computed(() => hasRole('trader') || hasRole('monitor'))

// ---- 状态映射 ----
type TagType = 'success' | 'warning' | 'danger' | 'info' | 'primary' | ''

const STATUS_LABEL: Record<string, string> = {
  PENDING_APPROVAL: '待审批',
  APPROVED: '已审批',
  REJECTED: '已驳回',
  PENDING_REVIEW: '待复核',
  REVIEW_REJECTED: '复核驳回',
  EXECUTED: '已执行',
  EMERGENCY_EXECUTED: '应急执行',
  PENDING_POST_EXPLANATION: '待事后说明',
  PENDING_DEVIATION_EXPLANATION: '待偏差说明',
  CANCELLED: '已取消',
}

const STATUS_TAG_TYPE: Record<string, TagType> = {
  PENDING_APPROVAL: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
  PENDING_REVIEW: 'warning',
  REVIEW_REJECTED: 'danger',
  EXECUTED: 'success',
  EMERGENCY_EXECUTED: 'danger',
  PENDING_POST_EXPLANATION: 'warning',
  PENDING_DEVIATION_EXPLANATION: 'warning',
  CANCELLED: 'info',
}

const statusLabel = (status: string) => STATUS_LABEL[status] ?? status
const statusTagType = (status: string): TagType => STATUS_TAG_TYPE[status] ?? ''

// ---- 时间格式化 ----
const formatTime = (iso: string | null) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

// ---- 数据加载 ----
const loading = ref(false)
const modifications = ref<Modification[]>([])

const loadModifications = async () => {
  loading.value = true
  try {
    modifications.value = (await modificationApi.list(auctionId.value)) as unknown as Modification[]
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    auction.value = (await auctionApi.get(auctionId.value)) as unknown as Auction
  } catch {
    // non-critical for role checks
  }
  await loadModifications()
})

// ---- 提交申请 Dialog ----
const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const submitting = ref(false)

const createForm = ref({ reason: '', impact_scope: '', risk_notes: '' })
const createRules: FormRules = {
  reason: [{ required: true, message: '请填写修改原因', trigger: 'blur' }],
  impact_scope: [{ required: true, message: '请填写影响范围', trigger: 'blur' }],
}

const openCreateDialog = () => { createDialogVisible.value = true }
const resetCreateForm = () => {
  createForm.value = { reason: '', impact_scope: '', risk_notes: '' }
  createFormRef.value?.clearValidate()
}

const submitCreate = async () => {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await modificationApi.create(auctionId.value, createForm.value)
    ElMessage.success('申请已提交')
    createDialogVisible.value = false
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '提交失败')
  } finally {
    submitting.value = false
  }
}

// ---- 应急执行 Dialog ----
const emergencyDialogVisible = ref(false)
const emergencyFormRef = ref<FormInstance>()
const emergencyForm = ref({ reason: '', impact_scope: '', is_pre_authorized: false, risk_notes: '' })
const emergencyRules: FormRules = {
  reason: [{ required: true, message: '请填写应急执行原因', trigger: 'blur' }],
  impact_scope: [{ required: true, message: '请填写影响范围', trigger: 'blur' }],
}

const openEmergencyDialog = () => { emergencyDialogVisible.value = true }
const resetEmergencyForm = () => {
  emergencyForm.value = { reason: '', impact_scope: '', is_pre_authorized: false, risk_notes: '' }
  emergencyFormRef.value?.clearValidate()
}

const submitEmergency = async () => {
  const valid = await emergencyFormRef.value?.validate().catch(() => false)
  if (!valid) return
  try {
    await ElMessageBox.confirm(
      '应急执行将跳过审批流程，确认继续？',
      '确认应急执行',
      { type: 'warning', confirmButtonText: '确认执行', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    await modificationApi.emergencyExecute(auctionId.value, emergencyForm.value)
    ElMessage.success('应急执行已提交')
    emergencyDialogVisible.value = false
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '提交失败')
  } finally {
    submitting.value = false
  }
}

// ---- 审批通过 ----
const handleApprove = async (row: Modification) => {
  try {
    await ElMessageBox.confirm(`确认审批通过修改申请 #${row.id}？`, '审批确认', {
      type: 'warning',
      confirmButtonText: '确认通过',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await modificationApi.approve(auctionId.value, row.id)
    ElMessage.success('审批通过')
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '操作失败')
  }
}

// ---- 复核通过 ----
const handleReview = async (row: Modification) => {
  try {
    await ElMessageBox.confirm(`确认复核通过修改申请 #${row.id}？`, '复核确认', {
      type: 'warning',
      confirmButtonText: '确认通过',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await modificationApi.review(auctionId.value, row.id)
    ElMessage.success('复核通过')
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '操作失败')
  }
}

// ---- 标记执行 ----
const handleExecute = async (row: Modification) => {
  try {
    await ElMessageBox.confirm(`确认标记执行修改申请 #${row.id}？`, '执行确认', {
      type: 'warning',
      confirmButtonText: '确认执行',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await modificationApi.execute(auctionId.value, row.id)
    ElMessage.success('已标记执行')
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '操作失败')
  }
}

// ---- 驳回 Dialog ----
const rejectDialogVisible = ref(false)
const rejectFormRef = ref<FormInstance>()
const rejectForm = ref({ comment: '' })
const rejectRules: FormRules = {
  comment: [{ required: true, message: '请填写驳回原因', trigger: 'blur' }],
}

// 记录当前驳回的行和类型（approve 驳回 / review 驳回）
const rejectTarget = ref<{ row: Modification; type: 'approve' | 'review' } | null>(null)

const openRejectDialog = (row: Modification, type: 'approve' | 'review') => {
  rejectTarget.value = { row, type }
  rejectDialogVisible.value = true
}
const resetRejectForm = () => {
  rejectForm.value = { comment: '' }
  rejectFormRef.value?.clearValidate()
}

const submitReject = async () => {
  const valid = await rejectFormRef.value?.validate().catch(() => false)
  if (!valid || !rejectTarget.value) return
  const { row, type } = rejectTarget.value
  submitting.value = true
  try {
    if (type === 'approve') {
      await modificationApi.reject(auctionId.value, row.id, rejectForm.value.comment)
    } else {
      await modificationApi.reviewReject(auctionId.value, row.id, rejectForm.value.comment)
    }
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '操作失败')
  } finally {
    submitting.value = false
  }
}

// ---- 补充应急说明 Dialog ----
const explanationDialogVisible = ref(false)
const explanationFormRef = ref<FormInstance>()
const explanationForm = ref({ post_explanation: '' })
const explanationRules: FormRules = {
  post_explanation: [{ required: true, message: '请填写事后说明', trigger: 'blur' }],
}
const explanationTarget = ref<Modification | null>(null)

const openExplanationDialog = (row: Modification) => {
  explanationTarget.value = row
  explanationDialogVisible.value = true
}
const resetExplanationForm = () => {
  explanationForm.value = { post_explanation: '' }
  explanationFormRef.value?.clearValidate()
}

const submitExplanation = async () => {
  const valid = await explanationFormRef.value?.validate().catch(() => false)
  if (!valid || !explanationTarget.value) return
  submitting.value = true
  try {
    await modificationApi.postExplanation(
      auctionId.value,
      explanationTarget.value.id,
      explanationForm.value,
    )
    ElMessage.success('说明已提交')
    explanationDialogVisible.value = false
    await loadModifications()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '操作失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.modification-view {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 8px;
}
</style>
