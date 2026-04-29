<template>
  <div class="execution-log-view">
    <div class="page-header">
      <h2>竞拍执行日志</h2>
      <div class="header-actions">
        <el-tag v-if="isCompleted" type="success" size="large">已完成</el-tag>
        <el-button type="primary" @click="openCreateDialog">新增执行记录</el-button>
        <el-button
          v-if="isTrader"
          type="warning"
          :disabled="logs.length === 0 || isCompleted"
          @click="handleComplete"
        >
          标记执行完成
        </el-button>
      </div>
    </div>

    <el-table :data="logs" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="task_number" label="任务编号" width="120" />
      <el-table-column prop="triggered_at" label="触发时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.triggered_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="bid_price" label="申报价格" width="120">
        <template #default="{ row }">
          {{ row.bid_price != null ? row.bid_price : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="bid_quantity" label="申报数量" width="120">
        <template #default="{ row }">
          {{ row.bid_quantity != null ? row.bid_quantity : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="system_status" label="系统状态" width="120">
        <template #default="{ row }">
          <el-tag :type="row.system_status === 'normal' ? 'success' : 'danger'" size="small">
            {{ row.system_status || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="data_feed_status" label="数据回传状态" width="130">
        <template #default="{ row }">
          <el-tag :type="row.data_feed_status === 'normal' ? 'success' : 'warning'" size="small">
            {{ row.data_feed_status || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="result" label="成交结果" width="120">
        <template #default="{ row }">
          {{ row.result || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="notes" label="异常说明" min-width="160">
        <template #default="{ row }">
          {{ row.notes || '-' }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增执行记录弹窗 -->
    <el-dialog v-model="dialogVisible" title="新增执行记录" width="520px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="任务编号" prop="task_number">
          <el-input v-model="form.task_number" placeholder="请输入任务编号" />
        </el-form-item>
        <el-form-item label="触发时间" prop="triggered_at">
          <el-date-picker
            v-model="form.triggered_at"
            type="datetime"
            placeholder="选择触发时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="申报价格" prop="bid_price">
          <el-input-number v-model="form.bid_price" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="申报数量" prop="bid_quantity">
          <el-input-number v-model="form.bid_quantity" :precision="2" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="系统状态" prop="system_status">
          <el-select v-model="form.system_status" placeholder="请选择" style="width: 100%">
            <el-option label="正常" value="normal" />
            <el-option label="异常" value="abnormal" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据回传状态" prop="data_feed_status">
          <el-select v-model="form.data_feed_status" placeholder="请选择" style="width: 100%">
            <el-option label="正常" value="normal" />
            <el-option label="异常" value="abnormal" />
          </el-select>
        </el-form-item>
        <el-form-item label="成交结果" prop="result">
          <el-input v-model="form.result" placeholder="请输入成交结果" />
        </el-form-item>
        <el-form-item label="异常说明" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="3" placeholder="如有异常请说明" />
        </el-form-item>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { executionApi } from '../../api/executions'
import { useAuthStore } from '../../stores/auth'
import type { ExecutionLog } from '../../api/types'

const route = useRoute()
const authStore = useAuthStore()
const auctionId = computed(() => route.params.id as string)

const logs = ref<ExecutionLog[]>([])
const loading = ref(false)
const isCompleted = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const isTrader = computed(() => authStore.user?.role === 'trader')

const form = ref({
  task_number: '',
  triggered_at: '',
  bid_price: undefined as number | undefined,
  bid_quantity: undefined as number | undefined,
  system_status: '',
  data_feed_status: '',
  result: '',
  notes: '',
})

const rules: FormRules = {
  task_number: [{ required: true, message: '请输入任务编号', trigger: 'blur' }],
  triggered_at: [{ required: true, message: '请选择触发时间', trigger: 'change' }],
}

function formatDateTime(val: string): string {
  if (!val) return '-'
  return val.replace('T', ' ').slice(0, 19)
}

async function fetchLogs() {
  loading.value = true
  try {
    const data = await executionApi.list(auctionId.value)
    logs.value = (data as unknown as ExecutionLog[]) || []
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '加载执行日志失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  dialogVisible.value = true
}

function resetForm() {
  form.value = {
    task_number: '',
    triggered_at: '',
    bid_price: undefined,
    bid_quantity: undefined,
    system_status: '',
    data_feed_status: '',
    result: '',
    notes: '',
  }
  formRef.value?.clearValidate()
}

async function submitForm() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    await executionApi.create(auctionId.value, form.value)
    ElMessage.success('执行记录已新增')
    dialogVisible.value = false
    await fetchLogs()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '新增失败')
  } finally {
    submitting.value = false
  }
}

async function handleComplete() {
  try {
    await ElMessageBox.confirm('确认标记本次竞拍执行完成？此操作不可撤销。', '标记执行完成', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await executionApi.complete(auctionId.value)
    isCompleted.value = true
    ElMessage.success('已标记执行完成')
  } catch (e: unknown) {
    if ((e as string) !== 'cancel') {
      ElMessage.error((e as Error).message || '操作失败')
    }
  }
}

onMounted(fetchLogs)
</script>

<style scoped>
.execution-log-view {
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
