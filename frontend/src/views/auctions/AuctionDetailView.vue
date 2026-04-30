<template>
  <div class="auction-detail-page" v-loading="loading">
    <!-- 顶部项目信息 -->
    <div class="detail-header" v-if="auction">
      <div class="header-info">
        <h2>{{ auction.name }}</h2>
        <span class="auction-date">竞拍日期：{{ auction.auction_date }}</span>
        <p v-if="auction.description" class="auction-desc">{{ auction.description }}</p>
      </div>
      <el-tag size="large" :type="phaseTagType(auction.current_phase)">
        {{ phaseLabel(auction.current_phase) }}
      </el-tag>
    </div>

    <!-- 阶段进度网格 -->
    <div class="phase-grid" v-if="auction">
      <div
        v-for="p in PHASES"
        :key="p.num"
        class="phase-cell"
        :class="[phaseCellClass(p.num), { 'phase-selected': selectedPhase === p.num }]"
        @click="handlePhaseClick(p.num)"
      >
        <div class="phase-num">{{ String(p.num).padStart(2, '0') }}</div>
        <div class="phase-name">{{ p.short }}</div>
        <div class="phase-owner">{{ ownerName(p.role) }}</div>
      </div>
    </div>

    <!-- 阶段01：基础信息录入 -->
    <el-card class="phase-card" id="phase-1" v-if="auction && selectedPhase === 1">
      <template #header>
        <div class="phase-header">
          <span>阶段01 — 竞拍信息收集</span>
          <el-tag size="small" :type="phaseStatusTag(auction.phase_statuses['1'])">
            {{ phaseStatusLabel(auction.phase_statuses['1']) }}
          </el-tag>
        </div>
      </template>

      <el-form label-width="120px">
        <el-form-item label="信息描述">
          <el-input
            v-model="basicInfoText"
            type="textarea"
            :rows="6"
            placeholder="请输入竞拍基础信息..."
            :disabled="!canEditBasicInfo"
          />
        </el-form-item>
        <el-form-item label="附件（PDF）">
          <div class="attachment-area">
            <el-upload
              v-if="canEditBasicInfo"
              :show-file-list="false"
              accept=".pdf"
              :http-request="uploadBasicInfoRequest"
            >
              <el-button size="small" :loading="uploadingBasicInfo">上传 PDF</el-button>
            </el-upload>
            <div class="attachment-list" v-if="basicInfoAttachments.length">
              <div v-for="att in basicInfoAttachments" :key="att.id" class="attachment-item">
                <el-icon><Document /></el-icon>
                <span class="att-name">{{ att.filename }}</span>
                <span class="att-size">{{ formatSize(att.size) }}</span>
                <el-button link type="primary" size="small" @click="togglePreview(att.url)">
                  {{ previewUrl === att.url ? '收起' : '预览' }}
                </el-button>
                <el-button
                  v-if="canEditBasicInfo"
                  link
                  type="danger"
                  size="small"
                  @click="handleDeleteBasicInfoAttachment(att.id)"
                >删除</el-button>
              </div>
            </div>
            <span v-else class="no-attachment">暂无附件</span>
            <div v-if="previewUrl && basicInfoAttachments.some(a => a.url === previewUrl)" class="pdf-preview">
              <iframe :src="previewUrl" width="100%" height="600px" />
            </div>
          </div>
        </el-form-item>
      </el-form>

      <div class="phase-actions">
        <el-button
          v-if="isBusinessOwner && auction.phase_statuses['1'] === 'confirmed'"
          type="primary"
          :loading="savingBasicInfo"
          @click="handleSaveBasicInfo"
        >
          修改
        </el-button>
        <el-button
          v-if="isBusinessOwner && auction.phase_statuses['1'] !== 'confirmed'"
          type="success"
          :loading="confirmingBasicInfo"
          @click="handleConfirmAndSaveBasicInfo"
        >
          确认
        </el-button>
      </div>
    </el-card>

    <!-- 阶段02：历史数据分析录入 -->
    <el-card class="phase-card" id="phase-2" v-if="auction && selectedPhase === 2">
      <template #header>
        <div class="phase-header">
          <span>阶段02 — 历史数据分析</span>
          <el-tag size="small" :type="phaseStatusTag(auction.phase_statuses['2'])">
            {{ phaseStatusLabel(auction.phase_statuses['2']) }}
          </el-tag>
        </div>
      </template>

      <el-form label-width="120px">
        <el-form-item label="分析内容">
          <el-input
            v-model="historyAnalysisText"
            type="textarea"
            :rows="6"
            placeholder="请输入历史数据分析内容..."
            :disabled="!canEditHistoryAnalysis"
          />
        </el-form-item>
        <el-form-item label="附件（PDF）">
          <div class="attachment-area">
            <el-upload
              v-if="canEditHistoryAnalysis"
              :show-file-list="false"
              accept=".pdf"
              :http-request="uploadHistoryAnalysisRequest"
            >
              <el-button size="small" :loading="uploadingHistoryAnalysis">上传 PDF</el-button>
            </el-upload>
            <div class="attachment-list" v-if="historyAnalysisAttachments.length">
              <div v-for="att in historyAnalysisAttachments" :key="att.id" class="attachment-item">
                <el-icon><Document /></el-icon>
                <span class="att-name">{{ att.filename }}</span>
                <span class="att-size">{{ formatSize(att.size) }}</span>
                <el-button link type="primary" size="small" @click="togglePreview(att.url)">
                  {{ previewUrl === att.url ? '收起' : '预览' }}
                </el-button>
                <el-button
                  v-if="canEditHistoryAnalysis"
                  link
                  type="danger"
                  size="small"
                  @click="handleDeleteHistoryAnalysisAttachment(att.id)"
                >删除</el-button>
              </div>
            </div>
            <span v-else class="no-attachment">暂无附件</span>
            <div v-if="previewUrl && historyAnalysisAttachments.some(a => a.url === previewUrl)" class="pdf-preview">
              <iframe :src="previewUrl" width="100%" height="600px" />
            </div>
          </div>
        </el-form-item>
      </el-form>

      <div class="phase-actions">
        <el-button
          v-if="isStrategyOwner && auction.phase_statuses['2'] === 'confirmed'"
          type="primary"
          :loading="savingHistoryAnalysis"
          @click="handleSaveHistoryAnalysis"
        >
          修改
        </el-button>
        <el-button
          v-if="isStrategyOwner && auction.phase_statuses['2'] !== 'confirmed'"
          type="success"
          :loading="confirmingHistoryAnalysis"
          @click="handleConfirmAndSaveHistoryAnalysis"
        >
          确认
        </el-button>
      </div>
    </el-card>

    <!-- 阶段03：策略制定（单一策略内联表单） -->
    <el-card class="phase-card" id="phase-3" v-if="auction && selectedPhase === 3">
      <template #header>
        <div class="phase-header">
          <span>阶段03 — 策略方案制定</span>
          <el-tag size="small" :type="phaseStatusTag(auction.phase_statuses['3'])">
            {{ phaseStatusLabel(auction.phase_statuses['3']) }}
          </el-tag>
        </div>
      </template>

      <el-form label-width="120px">
        <el-form-item label="风险等级">
          <el-select v-model="strategyForm.risk_level" :disabled="!canEditStrategy" style="width:160px">
            <el-option label="低风险" value="LOW" />
            <el-option label="正常" value="NORMAL" />
            <el-option label="高风险" value="HIGH" />
          </el-select>
        </el-form-item>
        <el-form-item label="申报价格">
          <el-input-number v-model="strategyForm.bid_price" :precision="2" :min="0" :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="申报数量">
          <el-input-number v-model="strategyForm.bid_quantity" :precision="0" :min="0" :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="申报时点">
          <el-input v-model="strategyForm.bid_time_points" type="textarea" :rows="2" placeholder="描述申报时点安排..." :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="触发条件">
          <el-input v-model="strategyForm.trigger_conditions" type="textarea" :rows="3" placeholder="描述触发条件..." :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="兜底方案">
          <el-input v-model="strategyForm.fallback_plan" type="textarea" :rows="3" placeholder="描述兜底方案..." :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="适用场景">
          <el-input v-model="strategyForm.applicable_scenarios" type="textarea" :rows="2" placeholder="描述适用场景..." :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="预授权操作">
          <el-input v-model="strategyForm.pre_authorized_actions" type="textarea" :rows="2" placeholder="描述预授权操作..." :disabled="!canEditStrategy" />
        </el-form-item>
        <el-form-item label="风险说明">
          <el-input v-model="strategyForm.risk_notes" type="textarea" :rows="2" placeholder="风险说明..." :disabled="!canEditStrategy" />
        </el-form-item>
      </el-form>

      <div class="phase-actions">
        <el-button
          v-if="isStrategyOwner && auction.phase_statuses['3'] === 'confirmed'"
          type="primary"
          :loading="savingStrategy"
          @click="handleSaveStrategy"
        >
          修改
        </el-button>
        <el-button
          v-if="isStrategyOwner && auction.phase_statuses['3'] !== 'confirmed'"
          type="success"
          :loading="confirmingStrategy"
          @click="handleConfirmAndSaveStrategy"
        >
          确认
        </el-button>
      </div>
    </el-card>

    <!-- 阶段04：策略审批 -->
    <div v-if="auction && selectedPhase === 4" class="phase-card phase-inline">
      <StrategyListView
        :inline-mode="true"
        @navigate-to-form="(vid: string) => strategyVid = vid"
      />
    </div>

    <!-- 阶段05：任务配置 -->
    <div v-if="auction && selectedPhase === 5" class="phase-card phase-inline">
      <TaskConfigView />
    </div>

    <!-- 阶段06：执行前复核 -->
    <div v-if="auction && selectedPhase === 6" class="phase-card phase-inline">
      <ReviewView />
    </div>

    <!-- 阶段07：正式执行 -->
    <div v-if="auction && selectedPhase === 7" class="phase-card phase-inline">
      <ExecutionLogView />
    </div>

    <!-- 阶段08：实时监控 -->
    <div v-if="auction && selectedPhase === 8" class="phase-card phase-inline">
      <MonitorView />
    </div>

    <!-- 阶段09：异常审批 -->
    <div v-if="auction && selectedPhase === 9" class="phase-card phase-inline">
      <ModificationView />
    </div>

    <!-- 阶段10：结果复盘 -->
    <div v-if="auction && selectedPhase === 10" class="phase-card phase-inline">
      <RetrospectiveView />
      <RectificationView />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import { auctionApi } from '../../api/auctions'
import type { AttachmentMeta } from '../../api/auctions'
import { usersApi } from '../../api/users'
import type { Auction, User } from '../../api/types'
import { useAuthStore } from '../../stores/auth'
import StrategyListView from '../strategies/StrategyListView.vue'
import TaskConfigView from '../task-configs/TaskConfigView.vue'
import ReviewView from '../reviews/ReviewView.vue'
import ExecutionLogView from '../executions/ExecutionLogView.vue'
import MonitorView from '../monitors/MonitorView.vue'
import ModificationView from '../modifications/ModificationView.vue'
import RetrospectiveView from '../retrospectives/RetrospectiveView.vue'
import RectificationView from '../retrospectives/RectificationView.vue'

const route = useRoute()
const auctionId = computed(() => route.params.id as string)
const authStore = useAuthStore()

const auction = ref<Auction | null>(null)
const loading = ref(false)
const users = ref<User[]>([])

// 阶段01
const basicInfoText = ref('')
const basicInfoAttachments = ref<AttachmentMeta[]>([])
const savingBasicInfo = ref(false)
const confirmingBasicInfo = ref(false)
const uploadingBasicInfo = ref(false)

// 阶段02
const historyAnalysisText = ref('')
const historyAnalysisAttachments = ref<AttachmentMeta[]>([])
const savingHistoryAnalysis = ref(false)
const confirmingHistoryAnalysis = ref(false)
const uploadingHistoryAnalysis = ref(false)

// 阶段03 策略表单
const strategyForm = reactive({
  risk_level: 'NORMAL',
  bid_price: null as number | null,
  bid_quantity: null as number | null,
  bid_time_points: '',
  trigger_conditions: '',
  fallback_plan: '',
  applicable_scenarios: '',
  pre_authorized_actions: '',
  risk_notes: '',
})
const savingStrategy = ref(false)
const confirmingStrategy = ref(false)

// PDF 预览
const previewUrl = ref<string | null>(null)
function togglePreview(url: string) {
  previewUrl.value = previewUrl.value === url ? null : url
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function uploadBasicInfoRequest(req: { file: File }) {
  return handleUploadBasicInfo(req.file)
}

function uploadHistoryAnalysisRequest(req: { file: File }) {
  return handleUploadHistoryAnalysis(req.file)
}

// 阶段定义：短名 + 对应角色
const PHASES = [
  { num: 1,  short: '信息收集',   role: 'business_owner' },
  { num: 2,  short: '历史分析',   role: 'data_analyst' },
  { num: 3,  short: '策略制定',   role: 'strategy_owner' },
  { num: 4,  short: '策略审批',   role: 'auditor' },
  { num: 5,  short: '任务配置',   role: 'trader' },
  { num: 6,  short: '执行复核',   role: 'reviewer' },
  { num: 7,  short: '正式执行',   role: 'trader' },
  { num: 8,  short: '实时监控',   role: 'monitor' },
  { num: 9,  short: '异常审批',   role: 'strategy_owner' },
  { num: 10, short: '结果复盘',   role: 'retrospective_owner' },
]

const PHASE_LABELS = PHASES.map(p => p.short)

function phaseLabel(phase: number): string {
  return PHASE_LABELS[phase - 1] ?? `阶段${phase}`
}

function phaseTagType(phase: number): 'success' | 'warning' | 'danger' | 'info' | '' {
  if (phase <= 2) return 'info'
  if (phase <= 4) return ''
  if (phase <= 6) return 'warning'
  if (phase <= 8) return 'success'
  return 'danger'
}

function phaseCellClass(phaseNum: number) {
  if (!auction.value) return 'phase-wait'
  const status = auction.value.phase_statuses[String(phaseNum)]
  const doneStatuses = ['confirmed', 'completed', 'passed', 'executable', 'archived', 'FINAL']
  if (status && doneStatuses.includes(status)) return 'phase-done'
  if (phaseNum === auction.value.current_phase) return 'phase-active'
  if (phaseNum < auction.value.current_phase) return 'phase-done'
  return 'phase-wait'
}

// 根据角色名找到对应用户的姓名
function ownerName(role: string): string {
  if (!auction.value) return '—'
  const userId = (auction.value.roles || {})[role]
  if (!userId) return '—'
  const user = users.value.find(u => u.id === userId)
  return user ? user.full_name : '—'
}

function phaseStatusLabel(status: string | undefined): string {
  const map: Record<string, string> = {
    pending: '待录入',
    in_progress: '进行中',
    confirmed: '已确认',
    completed: '已完成',
  }
  return map[status ?? ''] ?? '待录入'
}

function phaseStatusTag(status: string | undefined): 'success' | 'warning' | 'info' | '' {
  if (status === 'confirmed' || status === 'completed') return 'success'
  if (status === 'in_progress') return 'warning'
  return 'info'
}

// 角色判断：基于 auction.roles 和当前登录用户
const currentUserId = computed(() => authStore.user?.id ?? '')

// 阶段点击
const selectedPhase = ref<number | null>(null)
const strategyVid = ref<string | null>(null)

function handlePhaseClick(phaseNum: number) {
  if (selectedPhase.value === phaseNum) {
    selectedPhase.value = null
  } else {
    selectedPhase.value = phaseNum
    if (phaseNum !== 3 && phaseNum !== 4) strategyVid.value = null
  }
}

const isBusinessOwner = computed(() => {
  if (!auction.value) return false
  return (auction.value.roles || {})['business_owner'] === currentUserId.value
})

const isStrategyOwner = computed(() => {
  if (!auction.value) return false
  return (auction.value.roles || {})['strategy_owner'] === currentUserId.value
})

const canEditBasicInfo = computed(() => isBusinessOwner.value)

const canEditHistoryAnalysis = computed(() => isStrategyOwner.value)

const canEditStrategy = computed(() => isStrategyOwner.value)

function loadStrategyForm(data: Record<string, unknown>) {
  strategyForm.risk_level = (data.risk_level as string) || 'NORMAL'
  strategyForm.bid_price = (data.bid_price as number | null) ?? null
  strategyForm.bid_quantity = (data.bid_quantity as number | null) ?? null
  strategyForm.bid_time_points = (data.bid_time_points as string) || ''
  strategyForm.trigger_conditions = (data.trigger_conditions as string) || ''
  strategyForm.fallback_plan = (data.fallback_plan as string) || ''
  strategyForm.applicable_scenarios = (data.applicable_scenarios as string) || ''
  strategyForm.pre_authorized_actions = (data.pre_authorized_actions as string) || ''
  strategyForm.risk_notes = (data.risk_notes as string) || ''
}

async function fetchAuction() {
  loading.value = true
  try {
    auction.value = (await auctionApi.get(auctionId.value)) as unknown as Auction
    const bi = auction.value.basic_info ?? {}
    basicInfoText.value = (bi.text as string) || ''
    basicInfoAttachments.value = (bi.attachments as AttachmentMeta[]) || []
    const ha = auction.value.history_analysis ?? {}
    historyAnalysisText.value = (ha.text as string) || ''
    historyAnalysisAttachments.value = (ha.attachments as AttachmentMeta[]) || []
    loadStrategyForm(auction.value.strategy_data ?? {})
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '获取项目详情失败')
  } finally {
    loading.value = false
  }
}

async function handleSaveBasicInfo() {
  if (!auction.value) return
  savingBasicInfo.value = true
  try {
    await auctionApi.updateBasicInfo(auctionId.value, {
      basic_info: { text: basicInfoText.value, attachments: basicInfoAttachments.value },
      version: auction.value.version,
    })
    ElMessage.success('基础信息已保存')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    savingBasicInfo.value = false
  }
}

async function handleConfirmAndSaveBasicInfo() {
  if (!auction.value) return
  confirmingBasicInfo.value = true
  try {
    await auctionApi.updateBasicInfo(auctionId.value, {
      basic_info: { text: basicInfoText.value, attachments: basicInfoAttachments.value },
      version: auction.value.version,
    })
    await auctionApi.confirmBasicInfo(auctionId.value)
    ElMessage.success('基础信息已确认')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '确认失败')
  } finally {
    confirmingBasicInfo.value = false
  }
}

async function handleUploadBasicInfo(file: File) {
  uploadingBasicInfo.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const meta = (await auctionApi.uploadBasicInfoAttachment(auctionId.value, fd)) as unknown as AttachmentMeta
    basicInfoAttachments.value = [...basicInfoAttachments.value, meta]
    // persist attachments immediately
    await auctionApi.updateBasicInfo(auctionId.value, {
      basic_info: { text: basicInfoText.value, attachments: basicInfoAttachments.value },
      version: auction.value!.version,
    })
    await fetchAuction()
    ElMessage.success('附件上传成功')
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '上传失败')
  } finally {
    uploadingBasicInfo.value = false
  }
  return false // prevent el-upload default behavior
}

async function handleDeleteBasicInfoAttachment(fileId: string) {
  if (!auction.value) return
  try {
    await auctionApi.deleteBasicInfoAttachment(auctionId.value, fileId)
    basicInfoAttachments.value = basicInfoAttachments.value.filter(a => a.id !== fileId)
    await auctionApi.updateBasicInfo(auctionId.value, {
      basic_info: { text: basicInfoText.value, attachments: basicInfoAttachments.value },
      version: auction.value.version,
    })
    await fetchAuction()
    ElMessage.success('附件已删除')
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '删除失败')
  }
}

async function handleSaveHistoryAnalysis() {
  if (!auction.value) return
  savingHistoryAnalysis.value = true
  try {
    await auctionApi.updateHistoryAnalysis(auctionId.value, {
      history_analysis: { text: historyAnalysisText.value, attachments: historyAnalysisAttachments.value },
      version: auction.value.version,
    })
    ElMessage.success('历史分析已保存')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    savingHistoryAnalysis.value = false
  }
}

async function handleConfirmAndSaveHistoryAnalysis() {
  if (!auction.value) return
  confirmingHistoryAnalysis.value = true
  try {
    await auctionApi.updateHistoryAnalysis(auctionId.value, {
      history_analysis: { text: historyAnalysisText.value, attachments: historyAnalysisAttachments.value },
      version: auction.value.version,
    })
    await auctionApi.confirmHistoryAnalysis(auctionId.value)
    ElMessage.success('历史分析已确认')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '确认失败')
  } finally {
    confirmingHistoryAnalysis.value = false
  }
}

async function handleUploadHistoryAnalysis(file: File) {
  uploadingHistoryAnalysis.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const meta = (await auctionApi.uploadHistoryAnalysisAttachment(auctionId.value, fd)) as unknown as AttachmentMeta
    historyAnalysisAttachments.value = [...historyAnalysisAttachments.value, meta]
    await auctionApi.updateHistoryAnalysis(auctionId.value, {
      history_analysis: { text: historyAnalysisText.value, attachments: historyAnalysisAttachments.value },
      version: auction.value!.version,
    })
    await fetchAuction()
    ElMessage.success('附件上传成功')
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '上传失败')
  } finally {
    uploadingHistoryAnalysis.value = false
  }
  return false
}

async function handleDeleteHistoryAnalysisAttachment(fileId: string) {
  if (!auction.value) return
  try {
    await auctionApi.deleteHistoryAnalysisAttachment(auctionId.value, fileId)
    historyAnalysisAttachments.value = historyAnalysisAttachments.value.filter(a => a.id !== fileId)
    await auctionApi.updateHistoryAnalysis(auctionId.value, {
      history_analysis: { text: historyAnalysisText.value, attachments: historyAnalysisAttachments.value },
      version: auction.value.version,
    })
    await fetchAuction()
    ElMessage.success('附件已删除')
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '删除失败')
  }
}

async function handleSaveStrategy() {
  if (!auction.value) return
  savingStrategy.value = true
  try {
    await auctionApi.updateStrategy(auctionId.value, {
      strategy_data: { ...strategyForm },
      version: auction.value.version,
    })
    ElMessage.success('策略已保存')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    savingStrategy.value = false
  }
}

async function handleConfirmAndSaveStrategy() {
  if (!auction.value) return
  confirmingStrategy.value = true
  try {
    await auctionApi.updateStrategy(auctionId.value, {
      strategy_data: { ...strategyForm },
      version: auction.value.version,
    })
    await auctionApi.confirmStrategy(auctionId.value)
    ElMessage.success('策略已确认')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '确认失败')
  } finally {
    confirmingStrategy.value = false
  }
}

onMounted(async () => {
  await fetchAuction()
  try {
    users.value = (await usersApi.list()) as unknown as User[]
  } catch {
    // non-critical
  }
})
</script>

<style scoped>
.auction-detail-page {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-info h2 {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
}

.auction-date {
  color: #666;
  font-size: 14px;
}

.auction-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: #606266;
  max-width: 600px;
  line-height: 1.5;
}

/* 阶段网格 */
.phase-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 8px;
}

.phase-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 4px 8px;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
  background: #fafafa;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
}

.phase-cell:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.phase-cell.phase-selected {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.3);
}

.phase-cell.phase-active {
  border-color: #409eff;
  background: #ecf5ff;
}

.phase-cell.phase-done {
  border-color: #67c23a;
  background: #f0f9eb;
}

.phase-cell.phase-wait {
  opacity: 0.6;
}

.phase-num {
  font-size: 11px;
  color: #909399;
  font-weight: 600;
  margin-bottom: 4px;
}

.phase-active .phase-num { color: #409eff; }
.phase-done .phase-num   { color: #67c23a; }

.phase-name {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
  line-height: 1.3;
  margin-bottom: 6px;
}

.phase-owner {
  font-size: 11px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.nav-links a {
  text-decoration: none;
}

.phase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.phase-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.phase-inline {
  padding: 0;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

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
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.att-name:hover {
  text-decoration: underline;
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
</style>
