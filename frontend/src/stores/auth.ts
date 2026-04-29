import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)

  async function login(username: string, password: string): Promise<void> {
    const data = await apiClient.post<{ access_token: string }>('/auth/login', {
      username,
      password,
    })
    const accessToken = (data as unknown as { access_token: string }).access_token
    token.value = accessToken
    localStorage.setItem('token', accessToken)
    await fetchMe()
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  async function fetchMe(): Promise<void> {
    const data = await apiClient.get<User>('/auth/me')
    user.value = data as unknown as User
  }

  return { token, user, login, logout, fetchMe }
})
