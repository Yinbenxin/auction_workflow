import apiClient from './index'
import type { Auction } from './types'

export interface AttachmentMeta {
  id: string
  filename: string
  size: number
  url: string
  uploaded_at: string
}

export const auctionApi = {
  list: () => apiClient.get<Auction[]>('/auctions'),
  get: (id: string) => apiClient.get<Auction>(`/auctions/${id}`),
  create: (data: { name: string; auction_date: string; description?: string; roles: Record<string, string> }) =>
    apiClient.post<Auction>('/auctions', data),
  update: (id: string, data: { name?: string; auction_date?: string; description?: string; roles?: Record<string, string> }) =>
    apiClient.put<Auction>(`/auctions/${id}`, data),
  delete: (id: string) => apiClient.delete(`/auctions/${id}`),

  // 阶段01
  updateBasicInfo: (id: string, data: { basic_info: object; version: number }) =>
    apiClient.put(`/auctions/${id}/basic-info`, data),
  confirmBasicInfo: (id: string) =>
    apiClient.post(`/auctions/${id}/basic-info/confirm`),
  uploadBasicInfoAttachment: (id: string, formData: FormData) =>
    apiClient.post<AttachmentMeta>(`/auctions/${id}/basic-info/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteBasicInfoAttachment: (id: string, fileId: string) =>
    apiClient.delete(`/auctions/${id}/basic-info/attachment/${fileId}`),

  // 阶段02
  updateHistoryAnalysis: (id: string, data: { history_analysis: object; version: number }) =>
    apiClient.put(`/auctions/${id}/history-analysis`, data),
  confirmHistoryAnalysis: (id: string) =>
    apiClient.post(`/auctions/${id}/history-analysis/confirm`),
  uploadHistoryAnalysisAttachment: (id: string, formData: FormData) =>
    apiClient.post<AttachmentMeta>(`/auctions/${id}/history-analysis/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteHistoryAnalysisAttachment: (id: string, fileId: string) =>
    apiClient.delete(`/auctions/${id}/history-analysis/attachment/${fileId}`),

  // 阶段03
  updateStrategy: (id: string, data: { strategy_data: object; version: number }) =>
    apiClient.put(`/auctions/${id}/strategy`, data),
  confirmStrategy: (id: string) =>
    apiClient.post(`/auctions/${id}/strategy/confirm`),

  // 阶段04 审批
  approveStrategy: (id: string, comment?: string) =>
    apiClient.post(`/auctions/${id}/strategy/approve`, { comment: comment || null }),
  rejectStrategy: (id: string, comment?: string) =>
    apiClient.post(`/auctions/${id}/strategy/reject`, { comment: comment || null }),

  // 阶段06 任务配置审批
  approveTaskConfig: (id: string, comment?: string) =>
    apiClient.post(`/auctions/${id}/task-config/approve`, { comment: comment || null }),
  rejectTaskConfig: (id: string, comment?: string) =>
    apiClient.post(`/auctions/${id}/task-config/reject`, { comment: comment || null }),
}
