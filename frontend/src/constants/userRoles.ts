export const USER_ROLE_DEFS = [
  { key: 'trader',           name: '交易员',   desc: '负责竞拍现场执行与报价操作' },
  { key: 'strategist',       name: '策略师',   desc: '负责竞拍策略制定与方案审核' },
  { key: 'delivery_manager', name: '交付经理', desc: '负责项目整体交付与流程协调' },
] as const

export type UserRoleKey = typeof USER_ROLE_DEFS[number]['key']
