<template>
  <div class="monitor-view">
    <div class="page-header">
      <h2>实时监控</h2>
      <div class="header-actions">
        <el-radio-group v-model="filterType" @change="handleFilterChange">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="normal">正常</el-radio-button>
          <el-radio-button value="anomaly">异常</el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="openCreateDialog">新增监控记录</el-button>
      </div>
    </div>

    <el-table
      :data="records"
      v-loading="loading"
      border
      stripe
      style="width: 100%"
      :row-class-name="rowClassName"
    >
      <el-table-column prop="record_type" label="记录类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.record_type === 'anomaly' ? 'danger' : 'success'" size="small">
            {{ row.record_type === 'anomaly' ? '异常' : '正常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price_change" label="价格变化" width="110">
        <template #default="{ row }">
          {{ row.price_change != null ? row.price_change : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="remaining_quantity" label="剩余量" width="100">
        <template #default="{ row }">
          {{ row.remaining_quantity != null ? row.remaining_quantity : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="transaction_speed" label="成交速度" width="110">
        <template #default="{ row }">
          {{ row.transaction_speed || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="data_feed_normal" label="数据回传" width="100">
        <template #default="{ row }">
          <el-tag :type="row.data_feed_normal ? 'success' : 'danger'" size="small">
            {{ row.data_feed_normal ? '正常' : '异常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="system_normal" label="系统状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.system_normal ? 'success' : 'danger'" size="small">
            {{ row.system_normal ? '正常' : '异常' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="anomaly_type" label="异常类型" width="120">
        <template #default="{ row }">
          {{ row.anomaly_type || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="anomaly_action" label="处理动作" min-width="140">
        <template #default="{ row }">
          {{ row.anomaly_action || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="recorded_at" label="记录时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.recorded_at) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增监控记录弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增监控记录" width="540px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="记录类型" prop="record_type">
          <el-select v-model="form.record_type" placeholder="请选择" style="width: 100%">
            <el-option label="正常" value="normal" />
            <el-option label="异常" value="anomaly" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格变化" prop="price_change">
          <el-input-number v-model="form.price_change" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="剩余量" prop="remaining_quantity">
          <el-input-number v-model="form.remaining_quantity" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成交速度" prop="transaction_speed">
          <el-input v-model="form.transaction_speed" placeholder="如：快/慢/正常" />
        </el-form-item>
        <el-form-item label="数据回传" prop="data_feed_normal">
          <el-radio-group v-model="form.data_feed_normal">
            <el-radio :value="true">正常</el-radio>
            <el-radio :value="false">异常</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="系统状态" prop="system_normal">
          <el-radio-group v-model="form.system_normal">
            <el-radio :value="true">正常</el-radio>
            <el-radio :value="false">异常</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 异常专属字段 -->
        <template v-if="form.record_type === 'anomaly'">
          <el-form-item label="异常类型" prop="anomaly_type">
            <el-input v-model="form.anomaly_type" placeholder="请描述异常类型" />
          </el-form-item>
          <el-form-item label="处理动作" prop="anomaly_action">
            <el-input
              v-model="form.anomaly_action"
              type="textarea"
              :rows="3"
              placeholder="请描述处理动作"
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确认提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { monitorApi } from '../../api/monitors'
import type { MonitorRecord } from '../../api/types'

const route = useRoute()
const auctionId = computed(() => route.params.id as string)

const records = ref<MonitorRecord[]>([])
const loading = ref(false)
const filterType = ref('')
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  record_type: 'normal',
  price_change: undefined as number | undefined,
  remaining_quantity: undefined as number | undefined,
  transaction_speed: '',
  data_feed_normal: true,
  system_normal: true,
  anomaly_type: '',
  anomaly_action: '',
})

const rules = computed<FormRules>(() => ({
  record_type: [{ required: true, message: '请选择记录类型', trigger: 'change' }],
  anomaly_type:
    form.value.record_type === 'anomaly'
      ? [{ required: true, message: '请填写异常类型', trigger: 'blur' }]
      : [],
}))

function rowClassName({ row }: { row: MonitorRecord }): string {
  return row.record_type === 'anomaly' ? 'anomaly-row' : ''
}

function formatDateTime(val: string): string {
  if (!val) return '-'
  return val.replace('T', ' ').slice(0, 19)
}

async function fetchRecords(recordType?: string) {
  loading.value = true
  try {
    const data = await monitorApi.list(auctionId.value, recordType || undefined)
    records.value = (data as unknown as MonitorRecord[]) || []
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '加载监控记录失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange(val: string) {
  fetchRecords(val || undefined)
}

function openCreateDialog() {
  dialogVisible.value = true
}

function resetForm() {
  form.value = {
    record_type: 'normal',
    price_change: undefined,
    remaining_quantity: undefined,
    transaction_speed: '',
    data_feed_normal: true,
    system_normal: true,
    anomaly_type: '',
    anomaly_action: '',
  }
  formRef.value?.clearValidate()
}

async function submitForm() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await monitorApi.create(auctionId.value, form.value)
    ElMessage.success('监控记录已新增')
    dialogVisible.value = false
    await fetchRecords(filterType.value || undefined)
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '新增失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => fetchRecords())
</script>

<style scoped>
.monitor-view {
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
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>

<style>
/* 异常行红色背景（非 scoped，需穿透 el-table） */
.el-table .anomaly-row {
  background-color: #fff0f0 !important;
}

.el-table .anomaly-row:hover > td {
  background-color: #ffe0e0 !important;
}
</style>
