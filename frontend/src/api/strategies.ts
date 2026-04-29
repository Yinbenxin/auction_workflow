import apiClient from './index'
import type { StrategyVersion } from './types'

export const strategyApi = {
  list: (auctionId: string) =>
    apiClient.get<StrategyVersion[]>(`/auctions/${auctionId}/strategies`),

  get: (auctionId: string, vid: string) =>
    apiClient.get<StrategyVersion>(`/auctions/${auctionId}/strategies/${vid}`),

  create: (auctionId: string, data: object) =>
    apiClient.post<StrategyVersion>(`/auctions/${auctionId}/strategies`, data),

  update: (auctionId: string, vid: string, data: object) =>
    apiClient.put(`/auctions/${auctionId}/strategies/${vid}`, data),

  submit: (auctionId: string, vid: string) =>
    apiClient.post(`/auctions/${auctionId}/strategies/${vid}/submit`),

  confirm: (auctionId: string, vid: string) =>
    apiClient.post(`/auctions/${auctionId}/strategies/${vid}/confirm`),

  reject: (auctionId: string, vid: string, comment: string) =>
    apiClient.post(`/auctions/${auctionId}/strategies/${vid}/reject`, { comment }),

  finalize: (auctionId: string, vid: string) =>
    apiClient.post(`/auctions/${auctionId}/strategies/${vid}/finalize`),

  void: (auctionId: string, vid: string) =>
    apiClient.post(`/auctions/${auctionId}/strategies/${vid}/void`),
}
