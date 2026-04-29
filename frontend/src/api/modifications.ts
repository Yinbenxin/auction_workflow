import apiClient from './index'
import type { Modification } from './types'

export const modificationApi = {
  /** 获取竞拍的临场修改列表 */
  list: (auctionId: string) =>
    apiClient.get<Modification[]>(`/auctions/${auctionId}/modifications`),

  /** 提交临场修改申请 */
  create: (auctionId: string, data: object) =>
    apiClient.post<Modification>(`/auctions/${auctionId}/modifications`, data),

  /** 应急执行（无需审批，直接执行） */
  emergencyExecute: (auctionId: string, data: object) =>
    apiClient.post(`/auctions/${auctionId}/modifications/emergency-execute`, data),

  /** 审批通过 */
  approve: (auctionId: string, mid: string, data?: object) =>
    apiClient.post(`/auctions/${auctionId}/modifications/${mid}/approve`, data),

  /** 审批驳回 */
  reject: (auctionId: string, mid: string, comment: string) =>
    apiClient.post(`/auctions/${auctionId}/modifications/${mid}/reject`, { comment }),

  /** 复核通过 */
  review: (auctionId: string, mid: string, data?: object) =>
    apiClient.post(`/auctions/${auctionId}/modifications/${mid}/review`, data),

  /** 复核驳回 */
  reviewReject: (auctionId: string, mid: string, comment: string) =>
    apiClient.post(`/auctions/${auctionId}/modifications/${mid}/review-reject`, { comment }),

  /** 标记执行 */
  execute: (auctionId: string, mid: string, data?: object) =>
    apiClient.post(`/auctions/${auctionId}/modifications/${mid}/execute`, data),

  /** 补充应急说明（事后解释） */
  postExplanation: (auctionId: string, mid: string, data: object) =>
    apiClient.post(`/auctions/${auctionId}/modifications/${mid}/post-explanation`, data),
}
