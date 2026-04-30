import apiClient from './index'
import type { User } from './types'

export const usersApi = {
  list: () => apiClient.get<User[]>('/auth/users'),
}
