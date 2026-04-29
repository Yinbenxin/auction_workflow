import apiClient from './index'
import type { ExecutionLog } from './types'

export const executionApi = {
  list: (auctionId: string) =>
    apiClient.get<ExecutionLog[]>(`/auctions/${auctionId}/execution-logs`),

  create: (auctionId: string, data: object) =>
    apiClient.post<ExecutionLog>(`/auctions/${auctionId}/execution-logs`, data),

  complete: (auctionId: string) =>
    apiClient.post(`/auctions/${auctionId}/execution-complete`),
}
