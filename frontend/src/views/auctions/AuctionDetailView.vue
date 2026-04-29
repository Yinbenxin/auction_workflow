<template>
  <div class="auction-detail-page" v-loading="loading">
    <!-- 顶部项目信息 -->
    <div class="detail-header" v-if="auction">
      <div class="header-info">
        <h2>{{ auction.name }}</h2>
        <span class="auction-date">竞拍日期：{{ auction.auction_date }}</span>
      </div>
      <el-tag size="large" :type="phaseTagType(auction.current_phase)">
        {{ phaseLabel(auction.current_phase) }}
      </el-tag>
    </div>

    <!-- 10 阶段进度条 -->
    <el-card class="steps-card" v-if="auction">
      <el-steps :active="auction.current_phase - 1" finish-status="success" align-center>
        <el-step
          v-for="(label, idx) in PHASE_LABELS"
          :key="idx"
          :title="label"
          :status="stepStatus(idx + 1)"
        />
      </el-steps>
    </el-card>

    <!-- 阶段导航链接 -->
    <el-card class="nav-card" v-if="auction">
      <template #header>阶段导航</template>
      <div class="nav-links">
        <router-link :to="`/auctions/${auctionId}/strategies`">
          <el-button>策略版本</el-button>
        </router-link>
        <router-link :to="`/auctions/${auctionId}/task-config`">
          <el-button>任务配置</el-button>
        </router-link>
        <router-link :to="`/auctions/${auctionId}/review`">
          <el-button>执行前复核</el-button>
        </router-link>
        <router-link :to="`/auctions/${auctionId}/executions`">
          <el-button>竞拍执行</el-button>
        </router-link>
        <router-link :to="`/auctions/${auctionId}/monitors`">
          <el-button>实时监控</el-button>
        </router-link>
        <router-link :to="`/auctions/${auctionId}/modifications`">
          <el-button>临场修改</el-button>
        </router-link>
        <router-link :to="`/auctions/${auctionId}/retrospective`">
          <el-button>结果复盘</el-button>
        </router-link>
      </div>
    </el-card>

    <!-- 阶段01：基础信息录入 -->
    <el-card class="phase-card" v-if="auction">
      <template #header>
        <div class="phase-header">
          <span>阶段01 — 竞拍信息收集（基础信息录入）</span>
          <el-tag size="small" :type="phaseStatusTag(auction.phase_statuses['1'])">
            {{ phaseStatusLabel(auction.phase_statuses['1']) }}
          </el-tag>
        </div>
      </template>

      <el-form label-width="120px">
        <el-form-item label="基础信息（JSON）">
          <el-input
            v-model="basicInfoJson"
            type="textarea"
            :rows="6"
            placeholder='{"key": "value"}'
            :disabled="!canEditBasicInfo"
          />
        </el-form-item>
      </el-form>

      <div class="phase-actions">
        <el-button
          v-if="canEditBasicInfo"
          type="primary"
          :loading="savingBasicInfo"
          @click="handleSaveBasicInfo"
        >
          保存
        </el-button>
        <el-button
          v-if="isBusinessOwner && auction.phase_statuses['1'] !== 'confirmed'"
          type="success"
          :loading="confirmingBasicInfo"
          @click="handleConfirmBasicInfo"
        >
          确认
        </el-button>
      </div>
    </el-card>

    <!-- 阶段02：历史数据分析录入 -->
    <el-card class="phase-card" v-if="auction">
      <template #header>
        <div class="phase-header">
          <span>阶段02 — 历史数据分析</span>
          <el-tag size="small" :type="phaseStatusTag(auction.phase_statuses['2'])">
            {{ phaseStatusLabel(auction.phase_statuses['2']) }}
          </el-tag>
        </div>
      </template>

      <el-form label-width="120px">
        <el-form-item label="历史分析（JSON）">
          <el-input
            v-model="historyAnalysisJson"
            type="textarea"
            :rows="6"
            placeholder='{"key": "value"}'
            :disabled="!canEditHistoryAnalysis"
          />
        </el-form-item>
      </el-form>

      <div class="phase-actions">
        <el-button
          v-if="canEditHistoryAnalysis"
          type="primary"
          :loading="savingHistoryAnalysis"
          @click="handleSaveHistoryAnalysis"
        >
          保存
        </el-button>
        <el-button
          v-if="isStrategyOwner && auction.phase_statuses['2'] !== 'confirmed'"
          type="success"
          :loading="confirmingHistoryAnalysis"
          @click="handleConfirmHistoryAnalysis"
        >
          确认
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { auctionApi } from '../../api/auctions'
import type { Auction } from '../../api/types'

const route = useRoute()
const auctionId = computed(() => route.params.id as string)

const auction = ref<Auction | null>(null)
const loading = ref(false)

// JSON 编辑区
const basicInfoJson = ref('{}')
const historyAnalysisJson = ref('{}')

// 操作加载状态
const savingBasicInfo = ref(false)
const confirmingBasicInfo = ref(false)
const savingHistoryAnalysis = ref(false)
const confirmingHistoryAnalysis = ref(false)

const PHASE_LABELS = [
  '竞拍信息收集',
  '历史数据分析',
  '策略方案制定',
  '策略评审审批',
  '任务配置',
  '执行前复核',
  '正式竞拍执行',
  '实时监控',
  '异常修改审批',
  '结果复盘与策略迭代',
]

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

function stepStatus(phaseNum: number): 'success' | 'process' | 'wait' | 'error' | 'finish' {
  if (!auction.value) return 'wait'
  const status = auction.value.phase_statuses[String(phaseNum)]
  if (status === 'confirmed' || status === 'completed') return 'success'
  if (phaseNum === auction.value.current_phase) return 'process'
  if (phaseNum < auction.value.current_phase) return 'finish'
  return 'wait'
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

// 角色判断（从 localStorage 读取当前用户角色）
const currentRole = computed(() => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) return JSON.parse(userStr).role as string
  } catch {
    // ignore
  }
  return ''
})

const isBusinessOwner = computed(() => currentRole.value === 'business_owner')
const isStrategyOwner = computed(() => currentRole.value === 'strategy_owner')

const canEditBasicInfo = computed(() => {
  if (!auction.value) return false
  return (
    isBusinessOwner.value && auction.value.phase_statuses['1'] !== 'confirmed'
  )
})

const canEditHistoryAnalysis = computed(() => {
  if (!auction.value) return false
  return (
    isStrategyOwner.value && auction.value.phase_statuses['2'] !== 'confirmed'
  )
})

async function fetchAuction() {
  loading.value = true
  try {
    auction.value = (await auctionApi.get(auctionId.value)) as unknown as Auction
    basicInfoJson.value = JSON.stringify(auction.value.basic_info ?? {}, null, 2)
    historyAnalysisJson.value = JSON.stringify(auction.value.history_analysis ?? {}, null, 2)
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '获取项目详情失败')
  } finally {
    loading.value = false
  }
}

async function handleSaveBasicInfo() {
  if (!auction.value) return
  let parsed: object
  try {
    parsed = JSON.parse(basicInfoJson.value)
  } catch {
    ElMessage.error('JSON 格式错误，请检查基础信息内容')
    return
  }
  savingBasicInfo.value = true
  try {
    await auctionApi.updateBasicInfo(auctionId.value, {
      basic_info: parsed,
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

async function handleConfirmBasicInfo() {
  confirmingBasicInfo.value = true
  try {
    await auctionApi.confirmBasicInfo(auctionId.value)
    ElMessage.success('基础信息已确认')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '确认失败')
  } finally {
    confirmingBasicInfo.value = false
  }
}

async function handleSaveHistoryAnalysis() {
  if (!auction.value) return
  let parsed: object
  try {
    parsed = JSON.parse(historyAnalysisJson.value)
  } catch {
    ElMessage.error('JSON 格式错误，请检查历史分析内容')
    return
  }
  savingHistoryAnalysis.value = true
  try {
    await auctionApi.updateHistoryAnalysis(auctionId.value, {
      history_analysis: parsed,
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

async function handleConfirmHistoryAnalysis() {
  confirmingHistoryAnalysis.value = true
  try {
    await auctionApi.confirmHistoryAnalysis(auctionId.value)
    ElMessage.success('历史分析已确认')
    await fetchAuction()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '确认失败')
  } finally {
    confirmingHistoryAnalysis.value = false
  }
}

onMounted(fetchAuction)
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

.steps-card :deep(.el-step__title) {
  font-size: 12px;
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
</style>
