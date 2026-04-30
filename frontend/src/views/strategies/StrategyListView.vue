<template>
  <div class="strategy-list-view">
    <div class="page-header">
      <h2>策略版本管理</h2>
      <el-button type="primary" :icon="Plus" @click="goToCreate">
        新建策略版本
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="strategies"
      border
      stripe
      style="width: 100%"
    >
      <el-table-column label="版本号" prop="version_code" min-width="180">
        <template #default="{ row }">
          <el-link type="primary" @click="goToEdit(row.id)">
            {{ row.version_code }}
          </el-link>
        </template>
      </el-table-column>

      <el-table-column label="版本名" prop="version_name" min-width="160" />

      <el-table-column label="状态" prop="status" width="120">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="风险等级" prop="risk_level" width="110">
        <template #default="{ row }">
          <el-tag :type="riskTagType(row.risk_level)" size="small" effect="plain">
            {{ riskLabel(row.risk_level) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="创建时间" prop="created_at" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <!-- 编辑：仅 DRAFT -->
          <el-button
            v-if="row.status === 'DRAFT'"
            size="small"
            @click="goToEdit(row.id)"
          >
            编辑
          </el-button>

          <!-- 提交审批：仅 DRAFT -->
          <el-button
            v-if="row.status === 'DRAFT'"
            size="small"
            type="warning"
            @click="handleSubmit(row)"
          >
            提交
          </el-button>

          <!-- 确认：PENDING + auditor 角色 -->
          <el-button
            v-if="row.status === 'PENDING' && isAuditor"
            size="small"
            type="success"
            @click="handleConfirm(row)"
          >
            确认
          </el-button>

          <!-- 驳回：PENDING + auditor 角色 -->
          <el-button
            v-if="row.status === 'PENDING' && isAuditor"
            size="small"
            type="danger"
            @click="openRejectDialog(row)"
          >
            驳回
          </el-button>

          <!-- 标记最终版本：CONFIRMED -->
          <el-button
            v-if="row.status === 'CONFIRMED'"
            size="small"
            type="primary"
            @click="handleFinalize(row)"
          >
            标记最终版本
          </el-button>

          <!-- 作废：非 VOIDED 状态均可作废 -->
          <el-button
            v-if="row.status !== 'VOIDED'"
            size="small"
            type="danger"
            plain
            @click="handleVoid(row)"
          >
            作废
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 驳回对话框 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回策略版本" width="480px">
      <el-form>
        <el-form-item label="驳回原因" required>
          <el-input
            v-model="rejectComment"
            type="textarea"
            :rows="4"
            placeholder="请填写驳回原因"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="actionLoading" @click="confirmReject">
          确认驳回
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { strategyApi } from '../../api/strategies'
import { useAuthStore } from '../../stores/auth'
import type { StrategyVersion } from '../../api/types'

const props = defineProps<{ inlineMode?: boolean }>()
const emit = defineEmits<{ (e: 'navigate-to-form', vid: string): void }>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const auctionId = computed(() => route.params.id as string)
const isAuditor = computed(() => authStore.user?.role === 'auditor')

const loading = ref(false)
const actionLoading = ref(false)
const strategies = ref<StrategyVersion[]>([])

const rejectDialogVisible = ref(false)
const rejectComment = ref('')
const rejectTarget = ref<StrategyVersion | null>(null)

// 状态映射
const STATUS_LABEL: Record<string, string> = {
  DRAFT: '草稿',
  PENDING: '待审批',
  CONFIRMED: '已确认',
  FINAL: '最终版本',
  VOIDED: '已作废',
}

const STATUS_TAG_TYPE: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
  DRAFT: 'info',
  PENDING: 'warning',
  CONFIRMED: 'success',
  FINAL: 'success',
  VOIDED: 'danger',
}

const RISK_LABEL: Record<string, string> = {
  NORMAL: '正常',
  MEDIUM: '中等',
  HIGH: '高风险',
  EMERGENCY: '紧急',
}

const RISK_TAG_TYPE: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
  NORMAL: 'success',
  MEDIUM: 'warning',
  HIGH: 'danger',
  EMERGENCY: 'danger',
}

function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return STATUS_TAG_TYPE[status] ?? ''
}

function riskLabel(risk: string): string {
  return RISK_LABEL[risk] ?? risk
}

function riskTagType(risk: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return RISK_TAG_TYPE[risk] ?? ''
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function fetchStrategies() {
  loading.value = true
  try {
    const data = await strategyApi.list(auctionId.value)
    strategies.value = data as unknown as StrategyVersion[]
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '加载策略版本失败')
  } finally {
    loading.value = false
  }
}

function goToCreate() {
  if (props.inlineMode) emit('navigate-to-form', 'new')
  else router.push(`/auctions/${auctionId.value}/strategies/new`)
}

function goToEdit(vid: string) {
  if (props.inlineMode) emit('navigate-to-form', vid)
  else router.push(`/auctions/${auctionId.value}/strategies/${vid}/edit`)
}

async function handleSubmit(row: StrategyVersion) {
  await ElMessageBox.confirm(`确认提交策略版本 "${row.version_code}" 进入审批流程？`, '提交确认', {
    type: 'warning',
  })
  actionLoading.value = true
  try {
    await strategyApi.submit(auctionId.value, row.id)
    ElMessage.success('已提交审批')
    await fetchStrategies()
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '提交失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleConfirm(row: StrategyVersion) {
  await ElMessageBox.confirm(`确认通过策略版本 "${row.version_code}"？`, '确认审批', {
    type: 'success',
  })
  actionLoading.value = true
  try {
    await strategyApi.confirm(auctionId.value, row.id)
    ElMessage.success('已确认通过')
    await fetchStrategies()
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '确认失败')
  } finally {
    actionLoading.value = false
  }
}

function openRejectDialog(row: StrategyVersion) {
  rejectTarget.value = row
  rejectComment.value = ''
  rejectDialogVisible.value = true
}

async function confirmReject() {
  if (!rejectComment.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  if (!rejectTarget.value) return
  actionLoading.value = true
  try {
    await strategyApi.reject(auctionId.value, rejectTarget.value.id, rejectComment.value.trim())
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    await fetchStrategies()
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '驳回失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleFinalize(row: StrategyVersion) {
  await ElMessageBox.confirm(
    `确认将 "${row.version_code}" 标记为最终执行版本？此操作不可撤销。`,
    '标记最终版本',
    { type: 'warning' },
  )
  actionLoading.value = true
  try {
    await strategyApi.finalize(auctionId.value, row.id)
    ElMessage.success('已标记为最终版本')
    await fetchStrategies()
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '操作失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleVoid(row: StrategyVersion) {
  await ElMessageBox.confirm(
    `确认作废策略版本 "${row.version_code}"？作废后版本记录保留但不可执行。`,
    '作废确认',
    { type: 'warning' },
  )
  actionLoading.value = true
  try {
    await strategyApi.void(auctionId.value, row.id)
    ElMessage.success('已作废')
    await fetchStrategies()
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '作废失败')
  } finally {
    actionLoading.value = false
  }
}

onMounted(fetchStrategies)
</script>

<style scoped>
.strategy-list-view {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}
</style>
