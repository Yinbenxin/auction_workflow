import apiClient from './index'
import type { User } from './types'

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface RegisterRequest {
  username: string
  password: string
  full_name: string
}

export const authApi = {
  login: (data: LoginRequest) => apiClient.post<TokenResponse>('/auth/login', data),
  me: () => apiClient.get<User>('/auth/me'),
  register: (data: RegisterRequest) => apiClient.post<User>('/auth/register', data),
  changePassword: (data: { old_password: string; new_password: string }) =>
    apiClient.put('/auth/me/password', data),
}
