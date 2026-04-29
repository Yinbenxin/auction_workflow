import apiClient from './index'
import type { Auction } from './types'

export const auctionApi = {
  list: () => apiClient.get<Auction[]>('/auctions'),
  get: (id: string) => apiClient.get<Auction>(`/auctions/${id}`),
  create: (data: { name: string; auction_date: string }) =>
    apiClient.post<Auction>('/auctions', data),
  updateBasicInfo: (id: string, data: { basic_info: object; version: number }) =>
    apiClient.put(`/auctions/${id}/basic-info`, data),
  confirmBasicInfo: (id: string) =>
    apiClient.post(`/auctions/${id}/basic-info/confirm`),
  updateHistoryAnalysis: (
    id: string,
    data: { history_analysis: object; version: number },
  ) => apiClient.put(`/auctions/${id}/history-analysis`, data),
  confirmHistoryAnalysis: (id: string) =>
    apiClient.post(`/auctions/${id}/history-analysis/confirm`),
}
