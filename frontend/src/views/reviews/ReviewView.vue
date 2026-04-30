<template>
  <div class="review-view">
    <div class="page-header">
      <h2>执行前复核</h2>
      <el-tag v-if="review?.status === 'passed'" type="success" size="large">复核通过</el-tag>
      <el-tag v-else-if="review?.status === 'failed'" type="danger" size="large">复核不通过</el-tag>
      <el-tag v-else-if="review?.status === 'pending'" type="warning" size="large">待复核</el-tag>
    </div>

    <!-- 双人复核提示 -->
    <el-alert
      v-if="isConfigurer"
      title="请由其他人员完成复核"
      description="根据双人复核制度，配置人不得自行完成复核，请由其他人员登录后完成复核操作。"
      type="warning"
      show-icon
      :closable="false"
      class="dual-review-alert"
    />

    <!-- 无复核记录时 trader 可发起 -->
    <el-card v-if="!review && isTrader" class="action-card">
      <p class="hint-text">当前竞拍尚未发起执行前复核，请先发起复核流程。</p>
      <el-button type="primary" :loading="initiating" @click="handleInitiate">
        发起复核
      </el-button>
    </el-card>

    <!-- 复核主体 -->
    <template v-if="review">
      <!-- 复核清单 -->
      <el-card class="checklist-card">
        <template #header>
          <span class="card-title">复核清单</span>
          <span class="checklist-progress">
            {{ checkedCount }} / {{ CHECKLIST_ITEMS.length }} 项已确认
          </span>
        </template>

        <div class="checklist-items">
          <div
            v-for="item in CHECKLIST_ITEMS"
            :key="item.key"
            class="checklist-item"
          >
            <el-checkbox
              v-model="localChecklist[item.key]"
              :disabled="!isReviewer || review.status === 'passed' || review.status === 'failed'"
              @change="handleChecklistChange"
            >
              {{ item.label }}
            </el-checkbox>
          </div>
        </div>
      </el-card>

      <!-- 复核结论（仅 reviewer 且状态为 pending 时可操作） -->
      <el-card v-if="isReviewer && review.status === 'pending'" class="conclusion-card">
        <template #header>
          <span class="card-title">复核结论</span>
        </template>

        <el-form :model="conclusionForm" label-width="80px">
          <el-form-item label="结论">
            <el-radio-group v-model="conclusionForm.status">
              <el-radio value="passed">通过</el-radio>
              <el-radio value="failed">不通过</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="备注">
            <el-input
              v-model="conclusionForm.comment"
              type="textarea"
              :rows="3"
              placeholder="请输入复核备注（选填）"
            />
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="submitting"
              :disabled="!conclusionForm.status || !allChecked"
              @click="handleSubmit"
            >
              提交复核结论
            </el-button>
            <span v-if="!allChecked" class="submit-hint">请先完成所有清单项</span>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 已提交的复核结论展示 -->
      <el-card v-if="review.status === 'passed' || review.status === 'failed'" class="conclusion-card">
        <template #header>
          <span class="card-title">复核结论</span>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="结论">
            <el-tag :type="review.status === 'passed' ? 'success' : 'danger'">
              {{ review.status === 'passed' ? '通过' : '不通过' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="review.comment" label="备注">
            {{ review.comment }}
          </el-descriptions-item>
          <el-descriptions-item v-if="review.reviewed_at" label="复核时间">
            {{ review.reviewed_at }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- trader 标记可执行按钮 -->
      <el-card v-if="isTrader" class="action-card">
        <el-button
          type="success"
          :loading="marking"
          :disabled="review.status !== 'passed'"
          @click="handleMarkExecutable"
        >
          标记为可执行
        </el-button>
        <span v-if="review.status !== 'passed'" class="submit-hint">
          复核通过后方可标记为可执行
        </span>
      </el-card>
    </template>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="8" animated />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { reviewApi } from '../../api/reviews'
import { useAuthStore } from '../../stores/auth'
import type { PreExecutionReview } from '../../api/types'

const CHECKLIST_ITEMS = [
  { key: 'strategy_version_confirmed', label: '策略版本已确认为最终版本' },
  { key: 'task_config_confirmed', label: '任务配置已完成并确认' },
  { key: 'price_matches_strategy', label: '申报价格与策略一致' },
  { key: 'quantity_matches_strategy', label: '申报数量与策略一致' },
  { key: 'time_point_matches_strategy', label: '申报时点与策略一致' },
  { key: 'trigger_condition_matches_strategy', label: '触发条件与策略一致' },
  { key: 'fallback_plan_configured', label: '兜底方案已配置' },
  { key: 'cushion_strategy_configured', label: '垫子策略已配置' },
  { key: 'supplement_strategy_configured', label: '补量策略已配置' },
  { key: 'task_order_confirmed', label: '任务顺序已确认' },
  { key: 'start_stop_status_confirmed', label: '启停状态已确认' },
  { key: 'system_status_normal', label: '系统状态正常' },
  { key: 'data_feed_normal', label: '数据回传正常' },
]

const route = useRoute()
const authStore = useAuthStore()

const auctionId = computed(() => route.params.id as string)
const currentUser = computed(() => authStore.user)
const isTrader = computed(() => currentUser.value?.role === 'trader')
const isReviewer = computed(() => currentUser.value?.role === 'reviewer')
const isConfigurer = computed(
  () => review.value?.configurer_id === currentUser.value?.id,
)

const loading = ref(false)
const initiating = ref(false)
const submitting = ref(false)
const marking = ref(false)

const review = ref<PreExecutionReview | null>(null)

// 本地清单状态，从 review.checklist 初始化
const localChecklist = reactive<Record<string, boolean>>(
  Object.fromEntries(CHECKLIST_ITEMS.map((item) => [item.key, false])),
)

const conclusionForm = reactive<{ status: string; comment: string }>({
  status: '',
  comment: '',
})

const checkedCount = computed(
  () => CHECKLIST_ITEMS.filter((item) => localChecklist[item.key]).length,
)

const allChecked = computed(
  () => checkedCount.value === CHECKLIST_ITEMS.length,
)

function syncChecklist(checklist: Record<string, boolean>) {
  CHECKLIST_ITEMS.forEach((item) => {
    localChecklist[item.key] = checklist[item.key] ?? false
  })
}

async function fetchReview() {
  loading.value = true
  try {
    const data = await reviewApi.get(auctionId.value)
    review.value = data as unknown as PreExecutionReview
    if (review.value?.checklist) {
      syncChecklist(review.value.checklist)
    }
  } catch {
    // 尚未发起复核，静默忽略
  } finally {
    loading.value = false
  }
}

async function handleInitiate() {
  initiating.value = true
  try {
    // strategy_version_id 由后端从当前竞拍最终审批版本获取，前端传空占位
    await reviewApi.create(auctionId.value, { strategy_version_id: '' })
    ElMessage.success('复核已发起')
    await fetchReview()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '发起复核失败')
  } finally {
    initiating.value = false
  }
}

async function handleChecklistChange() {
  if (!review.value) return
  try {
    await reviewApi.updateChecklist(auctionId.value, { ...localChecklist })
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '更新清单失败')
  }
}

async function handleSubmit() {
  if (!conclusionForm.status) return
  submitting.value = true
  try {
    await reviewApi.submit(auctionId.value, {
      status: conclusionForm.status,
      comment: conclusionForm.comment || undefined,
    })
    ElMessage.success('复核结论已提交')
    await fetchReview()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '提交复核结论失败')
  } finally {
    submitting.value = false
  }
}

async function handleMarkExecutable() {
  marking.value = true
  try {
    await reviewApi.markExecutable(auctionId.value)
    ElMessage.success('已标记为可执行')
    await fetchReview()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '标记可执行失败')
  } finally {
    marking.value = false
  }
}

onMounted(fetchReview)
</script>

<style scoped>
.review-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: #1a1a1a;
}

.dual-review-alert {
  border-radius: 6px;
}

.card-title {
  font-weight: 600;
  font-size: 15px;
}

.checklist-card .el-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.checklist-progress {
  font-size: 13px;
  color: #909399;
}

.checklist-items {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
}

.checklist-item {
  display: flex;
  align-items: center;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hint-text {
  margin: 0 0 12px;
  color: #606266;
  font-size: 14px;
}

.submit-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.loading-wrapper {
  padding: 24px;
}
</style>
