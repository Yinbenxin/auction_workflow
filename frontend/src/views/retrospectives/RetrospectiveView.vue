<template>
  <div class="retrospective-view" style="max-width: 900px; margin: 0 auto; padding: 24px;">
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">
      <h2 style="margin: 0;">结果复盘报告</h2>
      <el-tag v-if="retrospective?.status === 'submitted'" type="success">已归档</el-tag>
    </div>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      :disabled="isReadonly"
    >
      <!-- 1. 基础信息 -->
      <el-form-item label="基础信息" prop="basic_info">
        <el-input
          v-model="form.basic_info"
          type="textarea"
          :rows="4"
          placeholder="请填写竞拍基础信息（项目名称、竞拍日期、参与方等）"
        />
      </el-form-item>

      <!-- 2. 策略摘要 -->
      <el-form-item label="策略摘要" prop="strategy_summary">
        <el-input
          v-model="form.strategy_summary"
          type="textarea"
          :rows="4"
          placeholder="请填写本次竞拍采用的策略版本及核心要点"
        />
      </el-form-item>

      <!-- 3. 执行情况 -->
      <el-form-item label="执行情况" prop="execution_summary">
        <el-input
          v-model="form.execution_summary"
          type="textarea"
          :rows="4"
          placeholder="请填写竞拍执行过程概述"
        />
      </el-form-item>

      <!-- 4. 成交结果 -->
      <el-form-item label="成交结果" prop="transaction_result">
        <el-input
          v-model="form.transaction_result"
          type="textarea"
          :rows="4"
          placeholder="请填写最终成交价格、数量及结果评价"
        />
      </el-form-item>

      <!-- 5. 偏差分析 -->
      <el-form-item label="偏差分析" prop="deviation_analysis">
        <el-input
          v-model="form.deviation_analysis"
          type="textarea"
          :rows="4"
          placeholder="请填写实际执行与策略方案的偏差情况及原因"
        />
      </el-form-item>

      <!-- 6. 异常记录 -->
      <el-form-item label="异常记录" prop="anomaly_records">
        <el-input
          v-model="form.anomaly_records"
          type="textarea"
          :rows="4"
          placeholder="请填写竞拍过程中发生的异常事件记录"
        />
      </el-form-item>

      <!-- 7. 确认记录 -->
      <el-form-item label="确认记录" prop="confirmation_records">
        <el-input
          v-model="form.confirmation_records"
          type="textarea"
          :rows="4"
          placeholder="请填写各关键节点的确认记录（双人复核等）"
        />
      </el-form-item>

      <!-- 8. 问题原因 -->
      <el-form-item label="问题原因" prop="root_cause">
        <el-input
          v-model="form.root_cause"
          type="textarea"
          :rows="4"
          placeholder="请填写本次竞拍存在问题的根本原因分析"
        />
      </el-form-item>

      <!-- 9. 改进措施 -->
      <el-form-item label="改进措施" prop="improvement_actions">
        <el-input
          v-model="form.improvement_actions"
          type="textarea"
          :rows="4"
          placeholder="请填写针对问题的具体改进措施"
        />
      </el-form-item>

      <!-- 10. 策略沉淀 -->
      <el-form-item label="策略沉淀" prop="strategy_learnings">
        <el-input
          v-model="form.strategy_learnings"
          type="textarea"
          :rows="4"
          placeholder="请填写本次竞拍的经验总结和策略沉淀"
        />
      </el-form-item>

      <!-- 11. 应急执行说明（有应急修改时显示且必填） -->
      <el-form-item
        v-if="hasEmergency"
        label="应急执行说明"
        prop="emergency_explanation"
      >
        <el-input
          v-model="form.emergency_explanation"
          type="textarea"
          :rows="4"
          placeholder="本次竞拍存在应急修改，请填写应急执行说明"
        />
      </el-form-item>

      <!-- 操作按钮 -->
      <el-form-item v-if="!isReadonly" style="margin-top: 16px;">
        <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
        <el-button type="primary" @click="confirmSubmit" :loading="submitting">
          提交归档
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 提交确认对话框 -->
    <el-dialog
      v-model="submitDialogVisible"
      title="确认提交归档"
      width="400px"
    >
      <p>提交后报告将归档，所有字段将变为只读，无法再修改。确认提交？</p>
      <template #footer>
        <el-button @click="submitDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doSubmit" :loading="submitting">
          确认提交
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
import { retrospectiveApi } from '../../api/retrospectives'
import type { Retrospective } from '../../api/types'

const route = useRoute()
const auctionId = route.params.id as string

const retrospective = ref<Retrospective | null>(null)
const formRef = ref<FormInstance>()
const saving = ref(false)
const submitting = ref(false)
const submitDialogVisible = ref(false)

// 是否有应急修改（从复盘数据中判断）
const hasEmergency = computed(() => {
  return !!retrospective.value?.emergency_explanation ||
    (retrospective.value as unknown as { has_emergency?: boolean })?.has_emergency === true
})

const isReadonly = computed(() => retrospective.value?.status === 'submitted')

const form = reactive({
  basic_info: '',
  strategy_summary: '',
  execution_summary: '',
  transaction_result: '',
  deviation_analysis: '',
  anomaly_records: '',
  confirmation_records: '',
  root_cause: '',
  improvement_actions: '',
  strategy_learnings: '',
  emergency_explanation: '',
})

const rules = computed<FormRules>(() => ({
  basic_info: [{ required: true, message: '请填写基础信息', trigger: 'blur' }],
  strategy_summary: [{ required: true, message: '请填写策略摘要', trigger: 'blur' }],
  execution_summary: [{ required: true, message: '请填写执行情况', trigger: 'blur' }],
  transaction_result: [{ required: true, message: '请填写成交结果', trigger: 'blur' }],
  deviation_analysis: [{ required: true, message: '请填写偏差分析', trigger: 'blur' }],
  anomaly_records: [{ required: true, message: '请填写异常记录', trigger: 'blur' }],
  confirmation_records: [{ required: true, message: '请填写确认记录', trigger: 'blur' }],
  root_cause: [{ required: true, message: '请填写问题原因', trigger: 'blur' }],
  improvement_actions: [{ required: true, message: '请填写改进措施', trigger: 'blur' }],
  strategy_learnings: [{ required: true, message: '请填写策略沉淀', trigger: 'blur' }],
  ...(hasEmergency.value
    ? { emergency_explanation: [{ required: true, message: '有应急修改时必须填写应急执行说明', trigger: 'blur' }] }
    : {}),
}))

function fillForm(data: Retrospective) {
  const toStr = (v: unknown): string => {
    if (v === null || v === undefined) return ''
    if (typeof v === 'string') return v
    return JSON.stringify(v)
  }
  form.basic_info = toStr(data.basic_info)
  form.strategy_summary = toStr(data.strategy_summary)
  form.execution_summary = toStr(data.execution_summary)
  form.transaction_result = toStr(data.transaction_result)
  form.deviation_analysis = toStr(data.deviation_analysis)
  form.anomaly_records = toStr(data.anomaly_records)
  form.confirmation_records = toStr(data.confirmation_records)
  form.root_cause = toStr(data.root_cause)
  form.improvement_actions = toStr(data.improvement_actions)
  form.strategy_learnings = toStr(data.strategy_learnings)
  form.emergency_explanation = toStr(data.emergency_explanation)
}

async function loadRetrospective() {
  try {
    const data = await retrospectiveApi.get(auctionId) as unknown as Retrospective
    retrospective.value = data
    fillForm(data)
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    // 404 表示尚未创建，忽略
    if (!msg.includes('404') && !msg.includes('not found')) {
      ElMessage.error(`加载复盘报告失败：${msg}`)
    }
  }
}

async function saveDraft() {
  saving.value = true
  try {
    const payload = buildPayload()
    if (retrospective.value) {
      await retrospectiveApi.update(auctionId, payload)
      ElMessage.success('草稿已保存')
    } else {
      const data = await retrospectiveApi.create(auctionId, payload) as unknown as Retrospective
      retrospective.value = data
      ElMessage.success('草稿已保存')
    }
  } catch (err: unknown) {
    ElMessage.error(`保存失败：${err instanceof Error ? err.message : String(err)}`)
  } finally {
    saving.value = false
  }
}

function confirmSubmit() {
  submitDialogVisible.value = true
}

async function doSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    submitDialogVisible.value = false
    ElMessage.warning('请填写所有必填项后再提交')
    return
  }
  submitting.value = true
  try {
    // 先保存最新内容，再提交
    const payload = buildPayload()
    if (retrospective.value) {
      await retrospectiveApi.update(auctionId, payload)
    } else {
      const data = await retrospectiveApi.create(auctionId, payload) as unknown as Retrospective
      retrospective.value = data
    }
    await retrospectiveApi.submit(auctionId)
    await loadRetrospective()
    submitDialogVisible.value = false
    ElMessage.success('复盘报告已提交归档')
  } catch (err: unknown) {
    ElMessage.error(`提交失败：${err instanceof Error ? err.message : String(err)}`)
  } finally {
    submitting.value = false
  }
}

function buildPayload(): Record<string, unknown> {
  return {
    basic_info: form.basic_info,
    strategy_summary: form.strategy_summary,
    execution_summary: form.execution_summary,
    transaction_result: form.transaction_result,
    deviation_analysis: form.deviation_analysis,
    anomaly_records: form.anomaly_records,
    confirmation_records: form.confirmation_records,
    root_cause: form.root_cause,
    improvement_actions: form.improvement_actions,
    strategy_learnings: form.strategy_learnings,
    emergency_explanation: form.emergency_explanation || null,
  }
}

onMounted(() => {
  loadRetrospective()
})
</script>
