import apiClient from './index'
import type { Retrospective } from './types'

export const retrospectiveApi = {
  get: (auctionId: string) =>
    apiClient.get<Retrospective>(`/auctions/${auctionId}/retrospective`),

  create: (auctionId: string, data: object) =>
    apiClient.post<Retrospective>(`/auctions/${auctionId}/retrospective`, data),

  update: (auctionId: string, data: object) =>
    apiClient.put(`/auctions/${auctionId}/retrospective`, data),

  submit: (auctionId: string) =>
    apiClient.post(`/auctions/${auctionId}/retrospective/submit`),
}
