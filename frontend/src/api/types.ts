/** 通用 API 响应包装类型 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/** 用户信息 */
export interface User {
  id: string
  username: string
  full_name: string
  is_active: boolean
  created_at: string
}

/** 竞拍项目 */
export interface Auction {
  id: string
  name: string
  auction_date: string
  description: string | null
  current_phase: number
  phase_statuses: Record<string, string>
  basic_info: Record<string, unknown>
  history_analysis: Record<string, unknown>
  strategy_data: Record<string, unknown>
  roles: Record<string, string>
  version: number
  created_by: string
  created_at: string
  updated_at: string
}

/** 策略版本 */
export interface StrategyVersion {
  id: string
  auction_id: string
  version_code: string
  version_name: string
  status: string
  bid_price: number | null
  bid_quantity: number | null
  bid_time_points: unknown[]
  trigger_conditions: Record<string, unknown>
  fallback_plan: string | null
  applicable_scenarios: unknown[]
  scenario_strategies: Record<string, unknown>
  risk_level: string
  pre_authorized_actions: unknown[] | null
  risk_notes: string | null
  previous_version_id: string | null
  version: number
  created_by: string
  created_at: string
  updated_at: string
}

/** 任务配置 */
export interface TaskConfig {
  id: string
  auction_id: string
  strategy_version_id: string
  tasks: unknown[]
  attachments: unknown[]
  status: string
  configured_by: string
  created_at: string
}

/** 执行前复核 */
export interface PreExecutionReview {
  id: string
  auction_id: string
  strategy_version_id: string
  checklist: Record<string, boolean>
  status: string
  configurer_id: string
  reviewer_id: string | null
  reviewed_at: string | null
  comment: string | null
}

/** 执行日志 */
export interface ExecutionLog {
  id: string
  auction_id: string
  task_number: string
  triggered_at: string
  bid_price: number | null
  bid_quantity: number | null
  system_status: string | null
  data_feed_status: string | null
  result: string | null
  notes: string | null
  logged_by: string
  created_at: string
}

/** 监控记录 */
export interface MonitorRecord {
  id: string
  auction_id: string
  record_type: string
  price_change: number | null
  remaining_quantity: number | null
  transaction_speed: string | null
  data_feed_normal: boolean
  system_normal: boolean
  anomaly_type: string | null
  anomaly_action: string | null
  recorded_by: string
  recorded_at: string
}

/** 临场修改 */
export interface Modification {
  id: string
  auction_id: string
  strategy_version_id: string
  status: string
  affected_fields: unknown[]
  before_value: Record<string, unknown>
  after_value: Record<string, unknown>
  reason: string
  impact_scope: string
  risk_notes: string | null
  is_emergency: boolean
  is_pre_authorized: boolean | null
  matched_emergency_rule_id: string | null
  deviation_reason: string | null
  post_explanation: string | null
  attachments: unknown[]
  requested_by: string
  requested_at: string
  approved_by: string | null
  approved_at: string | null
  approval_comment: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  review_comment: string | null
  executed_by: string | null
  executed_at: string | null
  execution_result: string | null
  created_at: string
  updated_at: string
}

/** 复盘报告 */
export interface Retrospective {
  id: string
  auction_id: string
  strategy_version_id: string
  basic_info: Record<string, unknown>
  strategy_summary: Record<string, unknown>
  execution_summary: Record<string, unknown>
  transaction_result: Record<string, unknown>
  deviation_analysis: string | null
  anomaly_records: string | null
  confirmation_records: string | null
  root_cause: string | null
  improvement_actions: string | null
  strategy_learnings: string | null
  emergency_explanation: string | null
  status: string
  created_by: string
  submitted_at: string | null
  created_at: string
  updated_at: string
}

/** 整改事项 */
export interface RectificationItem {
  id: string
  retrospective_id: string
  title: string
  description: string | null
  assignee_id: string
  measures: string
  due_date: string
  status: string
  evidence: unknown[]
  delay_reason: string | null
  close_reason: string | null
  confirmed_by: string | null
  confirmed_at: string | null
  created_by: string
  created_at: string
  updated_at: string
}
