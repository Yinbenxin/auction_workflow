import apiClient from './index'
import type { User } from './types'

export interface AdminCreateRequest {
  username: string
  password: string
  full_name: string
  system_role?: 'root' | 'user'
  user_roles?: string[]
}

export interface AdminUpdateRequest {
  full_name?: string
  system_role?: 'root' | 'user'
  is_active?: boolean
  user_roles?: string[]
}

export const usersApi = {
  list: () => apiClient.get<User[]>('/auth/users'),
  adminList: () => apiClient.get<User[]>('/auth/admin/users'),
  adminCreate: (data: AdminCreateRequest) => apiClient.post<User>('/auth/admin/users', data),
  adminUpdate: (userId: string, data: AdminUpdateRequest) =>
    apiClient.put<User>(`/auth/admin/users/${userId}`, data),
  adminDelete: (userId: string) => apiClient.delete(`/auth/admin/users/${userId}`),
}
