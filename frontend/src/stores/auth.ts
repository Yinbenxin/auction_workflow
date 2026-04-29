import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api/auth'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  async function login(username: string, password: string): Promise<void> {
    const data = await authApi.login({ username, password })
    const resp = data as unknown as { access_token: string; user: User }
    token.value = resp.access_token
    localStorage.setItem('token', resp.access_token)
    // 直接从登录响应填充 user，避免额外 GET /auth/me 请求
    if (resp.user) {
      user.value = resp.user
    } else {
      await fetchMe()
    }
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  async function fetchMe(): Promise<void> {
    const data = await authApi.me()
    user.value = data as unknown as User
  }

  return { token, user, login, logout, fetchMe }
})
