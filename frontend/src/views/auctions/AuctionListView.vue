<template>
  <div class="auction-list-page">
    <div class="page-header">
      <h2>竞拍项目列表</h2>
      <el-button type="primary" @click="openCreateDialog">新建竞拍项目</el-button>
    </div>

    <el-tabs v-model="activeTab" class="list-tabs">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="进行中" name="active" />
      <el-tab-pane label="已完成" name="completed" />
    </el-tabs>

    <el-table :data="filteredAuctions" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="name" label="项目名称" min-width="160">
        <template #default="{ row }">
          <router-link :to="`/auctions/${row.id}`" class="auction-link">
            {{ row.name }}
          </router-link>
        </template>
      </el-table-column>
      <el-table-column prop="auction_date" label="竞拍日期" width="130" />
      <el-table-column label="创建日期" width="130">
        <template #default="{ row }">
          {{ row.created_at?.slice(0, 10) }}
        </template>
      </el-table-column>
      <el-table-column label="创建人" width="110">
        <template #default="{ row }">
          {{ userNameById(row.created_by) }}
        </template>
      </el-table-column>
      <el-table-column label="当前阶段" width="160">
        <template #default="{ row }">
          <el-tag :type="phaseTagType(row.current_phase)">
            {{ phaseLabel(row.current_phase) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.current_phase >= 10 ? 'success' : 'warning'">
            {{ row.current_phase >= 10 ? '已完成' : '进行中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="$router.push(`/auctions/${row.id}`)">
            详情
          </el-button>
          <el-button type="warning" link @click="openEditDialog(row)">
            修改
          </el-button>
          <el-popconfirm
            title="确认删除该竞拍项目？此操作不可恢复。"
            confirm-button-text="删除"
            cancel-button-text="取消"
            confirm-button-type="danger"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button type="danger" link>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建竞拍项目弹窗 -->
    <el-dialog v-model="showCreateDialog" title="新建竞拍项目" width="560px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
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
        <el-form-item label="项目描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入项目描述（选填）" />
        </el-form-item>

        <el-divider content-position="left">角色分配</el-divider>

        <el-form-item v-for="role in ROLE_DEFS" :key="role.value" :label="role.label">
          <el-select
            v-model="form.roles[role.value]"
            placeholder="请选择用户"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="`${u.full_name}（${u.username}）`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- 修改竞拍项目弹窗 -->
    <el-dialog v-model="showEditDialog" title="修改竞拍项目" width="560px" @close="resetEditForm">
      <el-form ref="editFormRef" :model="editForm" :rules="rules" label-width="110px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="竞拍日期" prop="auction_date">
          <el-date-picker
            v-model="editForm.auction_date"
            type="date"
            placeholder="请选择竞拍日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="项目描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="请输入项目描述（选填）" />
        </el-form-item>

        <el-divider content-position="left">角色分配</el-divider>

        <el-form-item v-for="role in ROLE_DEFS" :key="role.value" :label="role.label">
          <el-select
            v-model="editForm.roles[role.value]"
            placeholder="请选择用户"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="`${u.full_name}（${u.username}）`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEdit">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { auctionApi } from '../../api/auctions'
import { usersApi } from '../../api/users'
import type { Auction, User } from '../../api/types'

const router = useRouter()

const auctions = ref<Auction[]>([])
const users = ref<User[]>([])
const loading = ref(false)
const activeTab = ref<'all' | 'active' | 'completed'>('all')

// 新建
const showCreateDialog = ref(false)
const creating = ref(false)
const formRef = ref<FormInstance>()
const form = ref({ name: '', auction_date: today(), description: '', roles: {} as Record<string, string> })

// 修改
const showEditDialog = ref(false)
const saving = ref(false)
const editFormRef = ref<FormInstance>()
const editingId = ref('')
const editForm = ref({ name: '', auction_date: '', description: '', roles: {} as Record<string, string> })

const ROLE_DEFS = [
  { value: 'business_owner',      label: '业务负责人' },
  { value: 'strategy_owner',      label: '策略负责人' },
  { value: 'auditor',             label: '审计员' },
  { value: 'trader',              label: '交易员' },
  { value: 'reviewer',            label: '复核人' },
  { value: 'data_analyst',        label: '数据分析师' },
  { value: 'monitor',             label: '监控员' },
  { value: 'retrospective_owner', label: '复盘负责人' },
]

const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  auction_date: [{ required: true, message: '请选择竞拍日期', trigger: 'change' }],
}

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

const filteredAuctions = computed(() => {
  if (activeTab.value === 'active') return auctions.value.filter(a => a.current_phase < 10)
  if (activeTab.value === 'completed') return auctions.value.filter(a => a.current_phase >= 10)
  return auctions.value
})

const PHASE_LABELS: Record<number, string> = {
  1: '信息收集', 2: '历史分析', 3: '策略制定', 4: '策略审批',
  5: '任务配置', 6: '执行复核', 7: '正式执行', 8: '实时监控',
  9: '异常审批', 10: '结果复盘',
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

function userNameById(id: string): string {
  const u = users.value.find(u => u.id === id)
  return u ? u.full_name : '—'
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

async function loadUsers() {
  if (users.value.length > 0) return
  try {
    users.value = (await usersApi.list()) as unknown as User[]
  } catch {
    // non-critical
  }
}

async function openCreateDialog() {
  form.value = { name: '', auction_date: today(), description: '', roles: {} }
  showCreateDialog.value = true
  await loadUsers()
}

async function openEditDialog(row: Auction) {
  editingId.value = row.id
  editForm.value = {
    name: row.name,
    auction_date: row.auction_date,
    description: row.description ?? '',
    roles: { ...(row.roles || {}) },
  }
  showEditDialog.value = true
  await loadUsers()
}

async function handleCreate() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    creating.value = true
    try {
      const roles: Record<string, string> = {}
      for (const [k, v] of Object.entries(form.value.roles)) {
        if (v) roles[k] = v
      }
      const auction = (await auctionApi.create({
        name: form.value.name,
        auction_date: form.value.auction_date,
        description: form.value.description || undefined,
        roles,
      })) as unknown as Auction
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

async function handleEdit() {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const roles: Record<string, string> = {}
      for (const [k, v] of Object.entries(editForm.value.roles)) {
        if (v) roles[k] = v
      }
      await auctionApi.update(editingId.value, {
        name: editForm.value.name,
        auction_date: editForm.value.auction_date,
        description: editForm.value.description || undefined,
        roles,
      })
      ElMessage.success('修改成功')
      showEditDialog.value = false
      await fetchAuctions()
    } catch (err: unknown) {
      ElMessage.error(err instanceof Error ? err.message : '修改失败')
    } finally {
      saving.value = false
    }
  })
}

function resetForm() {
  form.value = { name: '', auction_date: today(), description: '', roles: {} }
  formRef.value?.resetFields()
}

function resetEditForm() {
  editFormRef.value?.resetFields()
}

async function handleDelete(id: string) {
  try {
    await auctionApi.delete(id)
    ElMessage.success('删除成功')
    await fetchAuctions()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '删除失败')
  }
}

onMounted(async () => {
  await Promise.all([fetchAuctions(), loadUsers()])
})
</script>

<style scoped>
.auction-list-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.list-tabs {
  margin-bottom: 16px;
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
