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

export const authApi = {
  login: (data: LoginRequest) => apiClient.post<TokenResponse>('/auth/login', data),
  me: () => apiClient.get<User>('/auth/me'),
}
