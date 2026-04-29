<template>
  <div class="strategy-form-view">
    <div class="page-header">
      <h2>{{ isEdit ? '编辑策略版本' : '新建策略版本' }}</h2>
    </div>

    <el-form
      ref="formRef"
      v-loading="loading"
      :model="form"
      :rules="rules"
      label-width="140px"
      class="strategy-form"
    >
      <!-- 基本信息 -->
      <el-divider content-position="left">基本信息</el-divider>

      <el-form-item label="版本号" prop="version_code">
        <el-input v-model="form.version_code" placeholder="如：重庆忠润_20260428_v1.0" />
      </el-form-item>

      <el-form-item label="版本名" prop="version_name">
        <el-input v-model="form.version_name" placeholder="请输入版本名称" />
      </el-form-item>

      <el-form-item label="风险等级" prop="risk_level">
        <el-select v-model="form.risk_level" placeholder="请选择风险等级" style="width: 200px">
          <el-option label="正常 (NORMAL)" value="NORMAL" />
          <el-option label="中等 (MEDIUM)" value="MEDIUM" />
          <el-option label="高风险 (HIGH)" value="HIGH" />
          <el-option label="紧急 (EMERGENCY)" value="EMERGENCY" />
        </el-select>
      </el-form-item>

      <el-form-item label="风险说明" prop="risk_notes">
        <el-input
          v-model="form.risk_notes"
          type="textarea"
          :rows="3"
          placeholder="请描述风险情况及应对措施"
        />
      </el-form-item>

      <!-- 红线字段 -->
      <el-divider content-position="left">
        <span class="redline-divider-label">核心申报参数（红线字段）</span>
      </el-divider>

      <el-alert
        type="error"
        :closable="false"
        show-icon
        class="redline-alert"
        description="以下 6 个字段为制度红线字段，必须填写完整，任何修改须升版本号并重新审批。"
      />

      <el-form-item prop="bid_price">
        <template #label>
          <span class="redline-label">申报价格</span>
        </template>
        <el-input-number
          v-model="form.bid_price"
          :precision="2"
          :min="0"
          placeholder="请输入申报价格"
          style="width: 240px"
        />
        <span class="field-unit">元/单位</span>
      </el-form-item>

      <el-form-item prop="bid_quantity">
        <template #label>
          <span class="redline-label">申报数量</span>
        </template>
        <el-input-number
          v-model="form.bid_quantity"
          :precision="0"
          :min="0"
          placeholder="请输入申报数量"
          style="width: 240px"
        />
        <span class="field-unit">单位</span>
      </el-form-item>

      <el-form-item prop="bid_time_points">
        <template #label>
          <span class="redline-label">申报时点</span>
        </template>
        <el-input
          v-model="form.bid_time_points_text"
          type="textarea"
          :rows="3"
          placeholder="请描述申报时点安排，如：09:30 首次申报，10:00 追加申报"
        />
      </el-form-item>

      <el-form-item prop="trigger_conditions_text">
        <template #label>
          <span class="redline-label">触发条件</span>
        </template>
        <el-input
          v-model="form.trigger_conditions_text"
          type="textarea"
          :rows="4"
          placeholder="请描述策略触发条件，如：当市场价格低于 X 时触发追加申报"
        />
      </el-form-item>

      <el-form-item prop="fallback_plan">
        <template #label>
          <span class="redline-label">兜底方案</span>
        </template>
        <el-input
          v-model="form.fallback_plan"
          type="textarea"
          :rows="4"
          placeholder="请描述兜底方案，确保在主策略失效时的备选执行路径"
        />
      </el-form-item>

      <el-form-item prop="applicable_scenarios_text">
        <template #label>
          <span class="redline-label">适用场景</span>
        </template>
        <el-input
          v-model="form.applicable_scenarios_text"
          type="textarea"
          :rows="3"
          placeholder="请描述本策略版本适用的市场场景和条件"
        />
      </el-form-item>

      <!-- 应急预授权方案（risk_level=EMERGENCY 时显示） -->
      <template v-if="form.risk_level === 'EMERGENCY'">
        <el-divider content-position="left">
          <span class="emergency-divider-label">预授权应急方案（紧急必填）</span>
        </el-divider>

        <el-alert
          type="warning"
          :closable="false"
          show-icon
          class="redline-alert"
          description="风险等级为紧急时，必须填写预授权应急方案，供交易员在无法及时审批时参照执行。"
        />

        <el-form-item prop="pre_authorized_actions_text">
          <template #label>
            <span class="emergency-label">预授权应急方案</span>
          </template>
          <el-input
            v-model="form.pre_authorized_actions_text"
            type="textarea"
            :rows="5"
            placeholder="请详细描述预授权的应急操作步骤，包括触发条件、操作范围和授权边界"
          />
        </el-form-item>
      </template>

      <!-- 操作按钮 -->
      <el-form-item class="form-actions">
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ isEdit ? '保存修改' : '创建策略版本' }}
        </el-button>
        <el-button @click="handleCancel">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { strategyApi } from '../../api/strategies'
import type { StrategyVersion } from '../../api/types'

const route = useRoute()
const router = useRouter()

const auctionId = computed(() => route.params.id as string)
const vid = computed(() => route.params.vid as string | undefined)
const isEdit = computed(() => !!vid.value && vid.value !== 'new')

const loading = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

interface FormState {
  version_code: string
  version_name: string
  risk_level: string
  risk_notes: string
  bid_price: number | null
  bid_quantity: number | null
  bid_time_points_text: string
  trigger_conditions_text: string
  fallback_plan: string
  applicable_scenarios_text: string
  pre_authorized_actions_text: string
}

const form = reactive<FormState>({
  version_code: '',
  version_name: '',
  risk_level: 'NORMAL',
  risk_notes: '',
  bid_price: null,
  bid_quantity: null,
  bid_time_points_text: '',
  trigger_conditions_text: '',
  fallback_plan: '',
  applicable_scenarios_text: '',
  pre_authorized_actions_text: '',
})

const rules = computed<FormRules>(() => ({
  version_code: [{ required: true, message: '请输入版本号', trigger: 'blur' }],
  version_name: [{ required: true, message: '请输入版本名', trigger: 'blur' }],
  risk_level: [{ required: true, message: '请选择风险等级', trigger: 'change' }],
  bid_price: [{ required: true, message: '申报价格为红线字段，必须填写', trigger: 'blur' }],
  bid_quantity: [{ required: true, message: '申报数量为红线字段，必须填写', trigger: 'blur' }],
  bid_time_points: [{ required: true, message: '申报时点为红线字段，必须填写', trigger: 'blur' }],
  trigger_conditions_text: [
    { required: true, message: '触发条件为红线字段，必须填写', trigger: 'blur' },
  ],
  fallback_plan: [{ required: true, message: '兜底方案为红线字段，必须填写', trigger: 'blur' }],
  applicable_scenarios_text: [
    { required: true, message: '适用场景为红线字段，必须填写', trigger: 'blur' },
  ],
  ...(form.risk_level === 'EMERGENCY'
    ? {
        pre_authorized_actions_text: [
          { required: true, message: '紧急风险等级必须填写预授权应急方案', trigger: 'blur' },
        ],
      }
    : {}),
}))

function strategyToForm(s: StrategyVersion) {
  form.version_code = s.version_code ?? ''
  form.version_name = s.version_name ?? ''
  form.risk_level = s.risk_level ?? 'NORMAL'
  form.risk_notes = s.risk_notes ?? ''
  form.bid_price = s.bid_price ?? null
  form.bid_quantity = s.bid_quantity ?? null
  form.bid_time_points_text = Array.isArray(s.bid_time_points)
    ? s.bid_time_points.join('\n')
    : ''
  form.trigger_conditions_text =
    typeof s.trigger_conditions === 'object' && s.trigger_conditions !== null
      ? (s.trigger_conditions as Record<string, unknown>).description as string ?? JSON.stringify(s.trigger_conditions)
      : ''
  form.fallback_plan = s.fallback_plan ?? ''
  form.applicable_scenarios_text = Array.isArray(s.applicable_scenarios)
    ? s.applicable_scenarios.join('\n')
    : ''
  form.pre_authorized_actions_text = Array.isArray(s.pre_authorized_actions)
    ? s.pre_authorized_actions.join('\n')
    : ''
}

function formToPayload() {
  return {
    version_code: form.version_code,
    version_name: form.version_name,
    risk_level: form.risk_level,
    risk_notes: form.risk_notes || null,
    bid_price: form.bid_price,
    bid_quantity: form.bid_quantity,
    bid_time_points: form.bid_time_points_text
      ? form.bid_time_points_text.split('\n').filter(Boolean)
      : [],
    trigger_conditions: form.trigger_conditions_text
      ? { description: form.trigger_conditions_text }
      : {},
    fallback_plan: form.fallback_plan || null,
    applicable_scenarios: form.applicable_scenarios_text
      ? form.applicable_scenarios_text.split('\n').filter(Boolean)
      : [],
    pre_authorized_actions:
      form.risk_level === 'EMERGENCY' && form.pre_authorized_actions_text
        ? form.pre_authorized_actions_text.split('\n').filter(Boolean)
        : null,
  }
}

async function loadStrategy() {
  if (!isEdit.value || !vid.value) return
  loading.value = true
  try {
    const data = await strategyApi.get(auctionId.value, vid.value)
    strategyToForm(data as unknown as StrategyVersion)
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '加载策略版本失败')
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = formToPayload()
    if (isEdit.value && vid.value) {
      await strategyApi.update(auctionId.value, vid.value, payload)
      ElMessage.success('策略版本已更新')
    } else {
      await strategyApi.create(auctionId.value, payload)
      ElMessage.success('策略版本已创建')
    }
    router.push(`/auctions/${auctionId.value}/strategies`)
  } catch (err: unknown) {
    ElMessage.error((err as Error).message || '保存失败')
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  router.push(`/auctions/${auctionId.value}/strategies`)
}

onMounted(loadStrategy)
</script>

<style scoped>
.strategy-form-view {
  padding: 24px;
  max-width: 860px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.strategy-form {
  background: #fff;
  padding: 24px 32px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

/* 红线字段标签 */
.redline-label {
  color: #f56c6c;
  font-weight: 600;
}

.redline-label::before {
  content: '* ';
  color: #f56c6c;
}

/* 应急字段标签 */
.emergency-label {
  color: #e6a23c;
  font-weight: 600;
}

.emergency-label::before {
  content: '* ';
  color: #e6a23c;
}

.redline-divider-label {
  color: #f56c6c;
  font-weight: 600;
  font-size: 14px;
}

.emergency-divider-label {
  color: #e6a23c;
  font-weight: 600;
  font-size: 14px;
}

.redline-alert {
  margin-bottom: 20px;
}

.field-unit {
  margin-left: 8px;
  color: #909399;
  font-size: 13px;
}

.form-actions {
  margin-top: 32px;
}
</style>
