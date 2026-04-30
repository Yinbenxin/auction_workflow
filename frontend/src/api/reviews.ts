import apiClient from './index'
import type { PreExecutionReview } from './types'

export const reviewApi = {
  get: (auctionId: string) =>
    apiClient.get<PreExecutionReview>(`/auctions/${auctionId}/review`),

  create: (auctionId: string, data: { strategy_version_id: string | null }) =>
    apiClient.post(`/auctions/${auctionId}/review`, data),

  updateChecklist: (auctionId: string, checklist: Record<string, boolean>) =>
    apiClient.put(`/auctions/${auctionId}/review/checklist`, { checklist }),

  submit: (auctionId: string, data: { status: string; comment?: string }) =>
    apiClient.post(`/auctions/${auctionId}/review/submit`, data),

  markExecutable: (auctionId: string) =>
    apiClient.post(`/auctions/${auctionId}/mark-executable`),
}
