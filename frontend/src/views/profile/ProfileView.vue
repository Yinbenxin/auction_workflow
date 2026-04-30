<template>
  <div class="profile-page">
    <h2>个人信息</h2>

    <el-card class="profile-card" v-if="user">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ user.full_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="user.is_active ? 'success' : 'danger'">
            {{ user.is_active ? '正常' : '已禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ formatDate(user.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="profile-card">
      <template #header>修改密码</template>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px" style="max-width: 400px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码（至少6位）" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="changingPwd" @click="handleChangePassword">确认修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { authApi } from '../../api/auth'
import { storeToRefs } from 'pinia'

const authStore = useAuthStore()
const { user } = storeToRefs(authStore)

onMounted(() => {
  if (!user.value && authStore.token) {
    authStore.fetchMe()
  }
})

function formatDate(dt: string): string {
  return new Date(dt).toLocaleString('zh-CN')
}

// 修改密码
const pwdFormRef = ref<FormInstance>()
const changingPwd = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

const validateConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (value !== pwdForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少6位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleChangePassword() {
  if (!pwdFormRef.value) return
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  changingPwd.value = true
  try {
    await authApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码修改成功')
    pwdFormRef.value.resetFields()
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '修改失败')
  } finally {
    changingPwd.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 600px;
}

.profile-page h2 {
  margin-bottom: 20px;
  font-size: 18px;
  color: #303133;
}

.profile-card {
  border-radius: 8px;
  margin-bottom: 20px;
}
</style>
