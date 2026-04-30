<template>
  <div class="app-wrapper">
    <!-- 顶部导航栏（登录/注册页不显示） -->
    <header v-if="showLayout" class="app-header">
      <span class="app-title">竞拍工作平台</span>
      <div class="header-right">
        <el-icon class="user-icon"><UserFilled /></el-icon>
        <span class="username">{{ authStore.user?.full_name || authStore.user?.username }}</span>
        <el-button type="danger" plain size="small" @click="handleLogout">退出</el-button>
      </div>
    </header>

    <!-- 主体：侧边栏 + 内容区 -->
    <div v-if="showLayout" class="app-body">
      <aside class="app-sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/auctions">
            <el-icon><List /></el-icon>
            <span>项目列表</span>
          </el-menu-item>
          <el-menu-item index="/profile">
            <el-icon><User /></el-icon>
            <span>个人信息</span>
          </el-menu-item>
        </el-menu>
      </aside>
      <main class="app-main">
        <RouterView />
      </main>
    </div>

    <!-- 登录/注册页全屏 -->
    <RouterView v-if="!showLayout" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, UserFilled, List } from '@element-plus/icons-vue'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const authOnlyRoutes = ['Login', 'Register']
const showLayout = computed(() => !authOnlyRoutes.includes(route.name as string))

// 侧边栏高亮：项目详情页及子页面都高亮"项目列表"
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/auctions')) return '/auctions'
  if (path.startsWith('/retrospectives')) return '/auctions'
  return path
})

// 刷新后 token 存在但 user 为 null，补充拉取
watch(
  showLayout,
  (val) => {
    if (val && authStore.token && !authStore.user) {
      authStore.fetchMe().catch(() => {
        authStore.logout()
        router.push({ name: 'Login' })
      })
    }
  },
  { immediate: true }
)

function handleLogout() {
  authStore.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: #1a2a4a;
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  flex-shrink: 0;
}

.app-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-icon {
  font-size: 16px;
  opacity: 0.85;
}

.username {
  font-size: 14px;
  opacity: 0.9;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.app-sidebar {
  width: 180px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  overflow-y: auto;
}

.sidebar-menu {
  border-right: none;
  height: 100%;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f7fa;
}
</style>
