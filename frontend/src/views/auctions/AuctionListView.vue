<template>
  <div class="auction-list-page">
    <div class="page-header">
      <h2>竞拍项目列表</h2>
      <el-button type="primary" @click="showCreateDialog = true">新建竞拍项目</el-button>
    </div>

    <el-table :data="auctions" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="name" label="项目名称" min-width="180">
        <template #default="{ row }">
          <router-link :to="`/auctions/${row.id}`" class="auction-link">
            {{ row.name }}
          </router-link>
        </template>
      </el-table-column>
      <el-table-column prop="auction_date" label="竞拍日期" width="140" />
      <el-table-column label="当前阶段" width="180">
        <template #default="{ row }">
          <el-tag :type="phaseTagType(row.current_phase)">
            {{ phaseLabel(row.current_phase) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="$router.push(`/auctions/${row.id}`)">
            查看详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建竞拍项目弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建竞拍项目" width="480px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="竞拍日期" prop="auction_date">
          <el-date-picker
            v-model="form.auction_date"
            type="date"
            placeholder="请选择竞拍日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { auctionApi } from '../../api/auctions'
import type { Auction } from '../../api/types'

const router = useRouter()

const auctions = ref<Auction[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  name: '',
  auction_date: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  auction_date: [{ required: true, message: '请选择竞拍日期', trigger: 'change' }],
}

const PHASE_LABELS: Record<number, string> = {
  1: '竞拍信息收集',
  2: '历史数据分析',
  3: '策略方案制定',
  4: '策略评审审批',
  5: '任务配置',
  6: '执行前复核',
  7: '正式竞拍执行',
  8: '实时监控',
  9: '异常修改审批',
  10: '结果复盘与策略迭代',
}

function phaseLabel(phase: number): string {
  return PHASE_LABELS[phase] ?? `阶段${phase}`
}

function phaseTagType(phase: number): 'success' | 'warning' | 'danger' | 'info' | '' {
  if (phase <= 2) return 'info'
  if (phase <= 4) return ''
  if (phase <= 6) return 'warning'
  if (phase <= 8) return 'success'
  return 'danger'
}

async function fetchAuctions() {
  loading.value = true
  try {
    auctions.value = (await auctionApi.list()) as unknown as Auction[]
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '获取列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    creating.value = true
    try {
      const auction = (await auctionApi.create(form.value)) as unknown as Auction
      ElMessage.success('创建成功')
      showCreateDialog.value = false
      router.push(`/auctions/${auction.id}`)
    } catch (err: unknown) {
      ElMessage.error(err instanceof Error ? err.message : '创建失败')
    } finally {
      creating.value = false
    }
  })
}

function resetForm() {
  form.value = { name: '', auction_date: '' }
  formRef.value?.resetFields()
}

onMounted(fetchAuctions)
</script>

<style scoped>
.auction-list-page {
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
}

.auction-link {
  color: var(--el-color-primary);
  text-decoration: none;
  font-weight: 500;
}

.auction-link:hover {
  text-decoration: underline;
}
</style>
