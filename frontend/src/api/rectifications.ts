import apiClient from './index'
import type { RectificationItem } from './types'

export const rectificationApi = {
  list: (rid: string) =>
    apiClient.get<RectificationItem[]>(`/retrospectives/${rid}/rectification-items`),

  create: (rid: string, data: object) =>
    apiClient.post<RectificationItem>(`/retrospectives/${rid}/rectification-items`, data),

  update: (iid: string, data: object) =>
    apiClient.put(`/rectification-items/${iid}`, data),

  uploadEvidence: (iid: string, evidence: unknown[]) =>
    apiClient.post(`/rectification-items/${iid}/upload-evidence`, { evidence }),

  confirm: (iid: string, action: string, closeReason?: string) =>
    apiClient.post(`/rectification-items/${iid}/confirm`, {
      action,
      close_reason: closeReason,
    }),
}
