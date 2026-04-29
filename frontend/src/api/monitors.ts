import apiClient from './index'
import type { MonitorRecord } from './types'

export const monitorApi = {
  list: (auctionId: string, recordType?: string) =>
    apiClient.get<MonitorRecord[]>(`/auctions/${auctionId}/monitor-records`, {
      params: { record_type: recordType },
    }),

  create: (auctionId: string, data: object) =>
    apiClient.post<MonitorRecord>(`/auctions/${auctionId}/monitor-records`, data),
}
