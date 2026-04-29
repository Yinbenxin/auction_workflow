/** 通用 API 响应包装类型 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/** 用户信息 */
export interface User {
  id: number
  username: string
  full_name: string
  role: string
}

/** 竞拍项目 */
export interface Auction {
  id: number
  name: string
  auction_date: string
  current_phase: number
  phase_statuses: Record<string, string>
}
