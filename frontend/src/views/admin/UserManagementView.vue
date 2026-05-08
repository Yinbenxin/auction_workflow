<template>
  <div class="user-mgmt-page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="openCreateDialog">新增用户</el-button>
    </div>

    <el-table :data="users" v-loading="loading" border stripe style="width: 100%">
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="full_name" label="姓名" width="120" />
      <el-table-column label="系统角色" width="110">
        <template #default="{ row }">
          <el-tag :type="row.system_role === 'root' ? 'danger' : 'info'">
            {{ row.system_role === 'root' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="业务角色" min-width="180">
        <template #default="{ row }">
          <template v-if="row.user_roles?.length">
            <el-tag
              v-for="key in row.user_roles"
              :key="key"
              type="success"
              style="margin-right: 4px; margin-bottom: 2px"
            >{{ roleLabel(key) }}</el-tag>
          </template>
          <span v-else style="color: #909399; font-size: 13px">未分配</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">
          {{ row.created_at?.slice(0, 19).replace('T', ' ') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            link
            :disabled="row.id === authStore.user?.id"
            @click="openEditDialog(row)"
          >编辑</el-button>
          <el-button
            :type="row.is_active ? 'warning' : 'success'"
            link
            :disabled="row.id === authStore.user?.id"
            @click="toggleActive(row)"
          >{{ row.is_active ? '禁用' : '启用' }}</el-button>
          <el-popconfirm
            title="确认删除该用户？此操作不可恢复。"
            confirm-button-text="删除"
            cancel-button-text="取消"
            confirm-button-type="danger"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button
                type="danger"
                link
                :disabled="row.id === authStore.user?.id"
              >删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增用户弹窗 -->
    <el-dialog v-model="showCreate" title="新增用户" width="460px" @close="resetCreate">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="createForm.full_name" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="系统角色">
          <el-select v-model="createForm.system_role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="root" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务角色">
          <el-checkbox-group v-model="createForm.user_roles">
            <el-checkbox v-for="r in USER_ROLE_DEFS" :key="r.key" :value="r.key">
              {{ r.name }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleCreate">确认</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户弹窗 -->
    <el-dialog v-model="showEdit" title="编辑用户" width="460px">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="用户名">
          <el-input :value="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="editForm.full_name" />
        </el-form-item>
        <el-form-item label="系统角色">
          <el-select v-model="editForm.system_role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="root" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务角色">
          <el-checkbox-group v-model="editForm.user_roles">
            <el-checkbox v-for="r in USER_ROLE_DEFS" :key="r.key" :value="r.key">
              <span>{{ r.name }}</span>
              <span style="color: #909399; font-size: 12px; margin-left: 4px">{{ r.desc }}</span>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { usersApi } from '../../api/users'
import { useAuthStore } from '../../stores/auth'
import type { User } from '../../api/types'
import { USER_ROLE_DEFS } from '../../constants/userRoles'

const authStore = useAuthStore()
const users = ref<User[]>([])
const loading = ref(false)
const saving = ref(false)

const showCreate = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = ref({
  username: '',
  full_name: '',
  password: '',
  system_role: 'user' as 'root' | 'user',
  user_roles: [] as string[],
})
const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  full_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

const showEdit = ref(false)
const editingId = ref('')
const editForm = ref({
  username: '',
  full_name: '',
  system_role: 'user' as 'root' | 'user',
  user_roles: [] as string[],
})

function roleLabel(key: string): string {
  return USER_ROLE_DEFS.find(r => r.key === key)?.name ?? key
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await usersApi.adminList()
    users.value = res as unknown as User[]
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createForm.value = { username: '', full_name: '', password: 'password123', system_role: 'user', user_roles: [] }
  showCreate.value = true
}

function resetCreate() {
  createFormRef.value?.resetFields()
}

function openEditDialog(row: User) {
  editingId.value = row.id
  editForm.value = {
    username: row.username,
    full_name: row.full_name,
    system_role: row.system_role,
    user_roles: [...(row.user_roles ?? [])],
  }
  showEdit.value = true
}

async function handleCreate() {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await usersApi.adminCreate({
        username: createForm.value.username,
        full_name: createForm.value.full_name,
        password: createForm.value.password,
        system_role: createForm.value.system_role,
        user_roles: createForm.value.user_roles,
      })
      ElMessage.success('用户创建成功')
      showCreate.value = false
      await fetchUsers()
    } catch (err: unknown) {
      ElMessage.error(err instanceof Error ? err.message : '创建失败')
    } finally {
      saving.value = false
    }
  })
}

async function handleEdit() {
  saving.value = true
  try {
    await usersApi.adminUpdate(editingId.value, {
      full_name: editForm.value.full_name,
      system_role: editForm.value.system_role,
      user_roles: editForm.value.user_roles,
    })
    ElMessage.success('修改成功')
    showEdit.value = false
    await fetchUsers()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '修改失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: User) {
  try {
    await usersApi.adminUpdate(row.id, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? '已禁用' : '已启用')
    await fetchUsers()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '操作失败')
  }
}

async function handleDelete(row: User) {
  try {
    await usersApi.adminDelete(row.id)
    ElMessage.success('用户已删除')
    await fetchUsers()
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '删除失败')
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.user-mgmt-page {
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
</style>
