import apiClient from './index'
import type { TaskConfig } from './types'

export const taskConfigApi = {
  get: (auctionId: string) =>
    apiClient.get<TaskConfig>(`/auctions/${auctionId}/task-config`),

  update: (auctionId: string, data: object) =>
    apiClient.put(`/auctions/${auctionId}/task-config`, data),

  confirm: (auctionId: string) =>
    apiClient.post(`/auctions/${auctionId}/task-config/confirm`),
}
