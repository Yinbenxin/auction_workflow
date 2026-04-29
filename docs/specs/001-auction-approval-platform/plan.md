# 001 - 竞拍工作平台 Plan

## 目录
- [技术架构](#技术架构)
- [数据结构](#数据结构)
  - [users](#users用户表)
  - [auctions](#auctions竞拍项目表)
  - [strategy_versions](#strategy_versions策略版本表)
  - [confirmations](#confirmations确认记录表)
  - [task_configs](#task_configs任务配置清单表)
  - [pre_execution_reviews](#pre_execution_reviews执行前复核表)
  - [execution_logs](#execution_logs竞拍执行日志表)
  - [monitor_records](#monitor_records监控记录表)
  - [modifications](#modifications临场修改记录表)
  - [retrospectives](#retrospectives复盘报告表)
  - [rectification_items](#rectification_items整改事项表)
- [接口清单](#接口清单)
  - [认证](#认证)
  - [竞拍项目](#竞拍项目)
  - [策略版本](#策略版本)
  - [任务配置](#任务配置)
  - [执行前复核](#执行前复核)
  - [竞拍执行](#竞拍执行)
  - [实时监控](#实时监控)
  - [异常修改审批与留痕](#异常修改审批与留痕)
  - [复盘报告](#复盘报告)
  - [整改事项](#整改事项)
- [核心逻辑设计](#核心逻辑设计)
- [架构决策](#架构决策)

---

## 技术架构

### 技术选型

| 层次 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 异步支持好，自动生成 OpenAPI 文档 |
| ORM | SQLAlchemy 2.x | 异步 ORM，配合 asyncpg |
| 数据库 | PostgreSQL 15+ | 支持 JSONB、行级锁，适合审批流场景 |
| 数据库迁移 | Alembic | SQLAlchemy 官方迁移工具 |
| 认证 | JWT (python-jose) | 无状态，前后端分离友好 |
| 密码哈希 | bcrypt (passlib) | 安全密码存储 |
| 前端框架 | Vue 3 + TypeScript | Composition API |
| 前端构建 | Vite | 快速热更新 |
| UI 组件库 | Element Plus | Vue 3 生态成熟组件库 |
| HTTP 客户端 | Axios | 前端请求封装 |
| 状态管理 | Pinia | Vue 3 官方推荐 |

### 目录结构

```
auction_workflow/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── core/
│   │   │   ├── config.py           # 配置（环境变量）
│   │   │   ├── security.py         # JWT 工具
│   │   │   └── database.py         # 数据库连接
│   │   ├── models/                 # SQLAlchemy 模型
│   │   │   ├── user.py
│   │   │   ├── auction.py          # 竞拍项目
│   │   │   ├── strategy.py         # 策略版本
│   │   │   ├── confirmation.py     # 确认记录
│   │   │   ├── review.py           # 执行前复核
│   │   │   ├── execution.py        # 执行日志
│   │   │   ├── monitor.py          # 监控记录
│   │   │   ├── modification.py     # 临场修改
│   │   │   ├── retrospective.py    # 复盘报告
│   │   │   └── rectification.py    # 整改事项
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── auctions.py
│   │   │       ├── strategies.py
│   │   │       ├── confirmations.py
│   │   │       ├── task_configs.py
│   │   │       ├── reviews.py
│   │   │       ├── executions.py
│   │   │       ├── monitors.py
│   │   │       ├── modifications.py
│   │   │       ├── retrospectives.py
│   │   │       └── rectifications.py
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── strategy_service.py
│   │   │   ├── modification_service.py
│   │   │   ├── review_service.py
│   │   │   └── retrospective_service.py
│   │   └── dependencies.py         # FastAPI 依赖注入
│   ├── migrations/                 # Alembic 迁移文件
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                    # Axios 接口封装
│   │   ├── stores/                 # Pinia 状态
│   │   ├── views/                  # 页面组件
│   │   │   ├── auth/
│   │   │   ├── auctions/           # 竞拍项目
│   │   │   ├── strategies/         # 策略版本
│   │   │   ├── reviews/            # 执行前复核
│   │   │   ├── executions/         # 竞拍执行
│   │   │   ├── monitors/           # 实时监控
│   │   │   ├── modifications/      # 异常修改
│   │   │   ├── retrospectives/     # 复盘报告
│   │   │   │   └── RectificationView.vue
│   │   │   └── task-configs/       # 任务配置
│   │   ├── router/
│   │   └── components/
│   └── package.json
└── docs/
```

---

## 数据结构

### users（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| username | VARCHAR(50) UNIQUE | 登录名 |
| hashed_password | VARCHAR(255) | bcrypt 哈希 |
| full_name | VARCHAR(100) | 显示名 |
| role | VARCHAR(50) | 角色枚举（见下） |
| is_active | BOOLEAN | 是否启用 |
| created_at | TIMESTAMPTZ | 创建时间 |

角色枚举：`business_owner`（业务负责人）、`strategy_owner`（策略负责人）、`auditor`（审核人）、`trader`（交易员）、`reviewer`（复核人）、`data_analyst`（数据人员）、`monitor`（监控人员）、`retrospective_owner`（复盘负责人）

> 策略提交人与审核人必须为不同账号（strategy_owner 不能确认自己提交的策略版本）。

### auctions（竞拍项目表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| name | VARCHAR(200) | 项目名称，如"重庆忠润" |
| auction_date | DATE | 竞拍日期 |
| current_phase | SMALLINT | 当前阶段 1-10 |
| phase_statuses | JSONB | 各阶段状态 `{1: "confirmed", 2: "pending", ...}` |
| basic_info | JSONB | 阶段01基础信息（公告、规则、时间、投放量等） |
| history_analysis | JSONB | 阶段02历史分析数据 |
| version | INTEGER DEFAULT 0 | 乐观锁版本号 |
| created_by | UUID FK→users | 创建人 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

### strategy_versions（策略版本表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| version_code | VARCHAR(50) | 版本号，如 v1.0 |
| version_name | VARCHAR(200) | 完整版本名，如 重庆忠润_20260428_v1.0 |
| status | VARCHAR(20) | DRAFT/PENDING/CONFIRMED/FINAL/VOIDED |
| bid_price | NUMERIC(18,4) | 申报价格（红线字段） |
| bid_quantity | NUMERIC(18,2) | 申报数量（红线字段） |
| bid_time_points | JSONB | 申报时点列表（红线字段） |
| trigger_conditions | JSONB | 触发条件（红线字段） |
| fallback_plan | TEXT | 兜底方案（红线字段） |
| applicable_scenarios | JSONB | 适用场景（红线字段） |
| scenario_strategies | JSONB | 分档策略（场景→价格/数量/时点） |
| risk_level | VARCHAR(20) DEFAULT 'NORMAL' | 风险等级：NORMAL/MEDIUM/HIGH/EMERGENCY（管理标签，不决定确认人） |
| pre_authorized_actions | JSONB | 预授权应急方案（EMERGENCY 等级必填） |
| risk_notes | TEXT | 风险说明 |
| previous_version_id | UUID FK→strategy_versions | 上一版本（用于追溯） |
| version | INTEGER DEFAULT 0 | 乐观锁版本号 |
| created_by | UUID FK→users | 创建人 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

唯一约束：`(auction_id, version_code)` 防止版本号重复

### confirmations（确认记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| target_type | VARCHAR(50) | 确认对象类型（auction_basic_info / history_analysis / strategy_version / task_config / modification） |
| target_id | UUID | 确认对象 ID |
| action | VARCHAR(20) | confirm（确认）/ reject（驳回） |
| comment | TEXT | 驳回原因或备注 |
| confirmed_by | UUID FK→users | 操作人 |
| confirmed_at | TIMESTAMPTZ | 操作时间 |

> 临场修改（modification）的审批、复核、执行动作主要记录在 `modifications` 表的专用字段中（approved_by/reviewed_by/executed_by 等），`confirmations.target_type='modification'` 可保留用于补充记录，但事实状态以 `modifications.status` 为准。

### task_configs（任务配置清单表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| strategy_version_id | UUID FK→strategy_versions | 关联最终版本 |
| tasks | JSONB | 任务列表（任务编号/任务时间/价格/数量/触发条件/任务顺序/启停状态/垫子策略/补量策略/兜底任务标识） |
| attachments | JSONB | 配置截图或导出文件 |
| status | VARCHAR(20) | pending / confirmed |
| configured_by | UUID FK→users | 配置人（交易员） |
| created_at | TIMESTAMPTZ | 创建时间 |

### pre_execution_reviews（执行前复核表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| strategy_version_id | UUID FK→strategy_versions | 关联最终版本 |
| checklist | JSONB | 13项清单勾选状态 `{item_1: true, item_2: false, ...}` |
| status | VARCHAR(20) | pending / passed / failed |
| configurer_id | UUID FK→users | 配置人（交易员） |
| reviewer_id | UUID FK→users | 复核人（不能与 configurer_id 相同） |
| reviewed_at | TIMESTAMPTZ | 复核提交时间 |
| comment | TEXT | 复核备注 |

### execution_logs（竞拍执行日志表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| task_number | VARCHAR(50) | 任务编号 |
| triggered_at | TIMESTAMPTZ | 触发时间 |
| bid_price | NUMERIC(18,4) | 实际申报价格 |
| bid_quantity | NUMERIC(18,2) | 实际申报数量 |
| system_status | VARCHAR(50) | 系统状态 |
| data_feed_status | VARCHAR(50) | 数据回传状态 |
| result | TEXT | 成交结果 |
| notes | TEXT | 异常说明 |
| logged_by | UUID FK→users | 记录人 |
| created_at | TIMESTAMPTZ | 记录时间 |

### monitor_records（监控记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| record_type | VARCHAR(20) | normal（正常）/ anomaly（异常） |
| price_change | NUMERIC(18,4) | 价格变化 |
| remaining_quantity | NUMERIC(18,2) | 剩余量 |
| transaction_speed | VARCHAR(50) | 成交速度描述 |
| data_feed_normal | BOOLEAN | 数据回传是否正常 |
| system_normal | BOOLEAN | 系统是否正常 |
| anomaly_type | VARCHAR(100) | 异常类型（若有） |
| anomaly_action | TEXT | 处理动作（若有） |
| recorded_by | UUID FK→users | 记录人 |
| recorded_at | TIMESTAMPTZ | 记录时间 |

> 第一版不单独拆 `anomaly_events` 表，异常事件通过 `record_type='anomaly'` 及 `anomaly_type`/`anomaly_action` 字段承载，与正常监控记录共表存储。

### modifications（临场修改记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| strategy_version_id | UUID FK→strategy_versions | 关联策略版本 |
| status | VARCHAR(30) | 状态枚举（见下） |
| affected_fields | JSONB | 修改涉及的字段列表 |
| before_value | JSONB | 修改前内容 |
| after_value | JSONB | 修改后内容 |
| reason | TEXT NOT NULL | 修改原因（必填） |
| impact_scope | TEXT NOT NULL | 影响范围（必填） |
| risk_notes | TEXT | 风险说明 |
| is_emergency | BOOLEAN DEFAULT FALSE | 是否为应急执行 |
| is_pre_authorized | BOOLEAN | 是否命中预授权规则 |
| matched_emergency_rule_id | VARCHAR(100) | 命中的预授权规则标识 |
| deviation_reason | TEXT | 非预授权应急偏差原因 |
| post_explanation | TEXT | 应急执行事后补说明 |
| attachments | JSONB | 附件/证据材料 |
| requested_by | UUID FK→users | 申请人 |
| requested_at | TIMESTAMPTZ | 申请时间 |
| approved_by | UUID FK→users | 审批人（策略负责人） |
| approved_at | TIMESTAMPTZ | 审批时间 |
| approval_comment | TEXT | 审批意见/驳回原因 |
| reviewed_by | UUID FK→users | 复核人 |
| reviewed_at | TIMESTAMPTZ | 复核时间 |
| review_comment | TEXT | 复核意见/驳回原因 |
| executed_by | UUID FK→users | 执行人（交易员） |
| executed_at | TIMESTAMPTZ | 执行时间 |
| execution_result | TEXT | 执行结果说明 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

状态枚举：`DRAFT`、`PENDING_APPROVAL`、`REJECTED`、`PENDING_REVIEW`、`APPROVED`、`EXECUTED`、`EMERGENCY_EXECUTED`、`PENDING_POST_EXPLANATION`、`PENDING_DEVIATION_EXPLANATION`、`POST_EXPLAINED`

### retrospectives（复盘报告表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| strategy_version_id | UUID FK→strategy_versions | 关联最终版本（必填） |
| basic_info | JSONB | 基础信息（项目名/日期/需求量/投放量） |
| strategy_summary | JSONB | 策略摘要（价格/数量/时点/触发条件/兜底） |
| execution_summary | JSONB | 执行情况（实际任务/触发时间/申报价格/数量） |
| transaction_result | JSONB | 成交结果（成交量/价格/是否达标） |
| deviation_analysis | TEXT | 偏差分析 |
| anomaly_records | TEXT | 异常记录 |
| confirmation_records | TEXT | 确认记录 |
| root_cause | TEXT | 问题原因 |
| improvement_actions | TEXT | 改进措施 |
| strategy_learnings | TEXT | 策略沉淀 |
| emergency_explanation | TEXT | 应急执行说明（有应急修改时必填） |
| status | VARCHAR(20) | draft / submitted |
| created_by | UUID FK→users | 创建人 |
| submitted_at | TIMESTAMPTZ | 提交归档时间 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

### rectification_items（整改事项表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| retrospective_id | UUID FK→retrospectives | 关联复盘报告 |
| title | VARCHAR(200) | 整改事项标题 |
| description | TEXT | 问题描述 |
| assignee_id | UUID FK→users | 责任人 |
| measures | TEXT NOT NULL | 整改措施（必填） |
| due_date | DATE NOT NULL | 截止日期（必填） |
| status | VARCHAR(20) | PENDING / IN_PROGRESS / COMPLETED / DELAYED / CLOSED |
| evidence | JSONB | 完成证据（文件路径或说明，已完成时必填） |
| delay_reason | TEXT | 延期原因（已延期时必填） |
| close_reason | TEXT | 关闭原因（已关闭时必填） |
| confirmed_by | UUID FK→users | 确认完成/关闭的操作人 |
| confirmed_at | TIMESTAMPTZ | 确认时间 |
| created_by | UUID FK→users | 创建人（复盘负责人） |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

---

## 接口清单

所有接口前缀：`/api/v1`，鉴权方式：`Bearer JWT`（标注"公开"的除外）

### 认证

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| POST | /auth/login | 公开 | 用户登录，返回 JWT |
| GET | /auth/me | 必须 | 获取当前用户信息 |

### 竞拍项目

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions | 必须 | 竞拍项目列表 |
| POST | /auctions | 必须 | 创建竞拍项目 |
| GET | /auctions/{id} | 必须 | 竞拍项目详情（含阶段状态） |
| PUT | /auctions/{id}/basic-info | 必须 | 更新阶段01基础信息 |
| POST | /auctions/{id}/basic-info/confirm | 必须 | 确认阶段01基础信息（业务负责人） |
| PUT | /auctions/{id}/history-analysis | 必须 | 更新阶段02历史分析数据 |
| POST | /auctions/{id}/history-analysis/confirm | 必须 | 确认阶段02历史分析（策略负责人） |

### 策略版本

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/strategies | 必须 | 策略版本列表（含历史） |
| POST | /auctions/{id}/strategies | 必须 | 创建策略版本（策略负责人） |
| GET | /auctions/{id}/strategies/{vid} | 必须 | 策略版本详情 |
| PUT | /auctions/{id}/strategies/{vid} | 必须 | 更新草稿版本（仅 DRAFT 状态可改） |
| POST | /auctions/{id}/strategies/{vid}/submit | 必须 | 提交待确认（策略负责人） |
| POST | /auctions/{id}/strategies/{vid}/confirm | 必须 | 确认策略版本（审核人；红线字段变更时业务负责人也需确认） |
| POST | /auctions/{id}/strategies/{vid}/reject | 必须 | 驳回策略版本（附原因） |
| POST | /auctions/{id}/strategies/{vid}/finalize | 必须 | 标记为最终版本（策略负责人） |
| POST | /auctions/{id}/strategies/{vid}/void | 必须 | 作废策略版本（策略负责人） |
| GET | /auctions/{id}/strategies/{vid}/confirmations | 必须 | 查看确认记录 |

### 任务配置

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/task-config | 必须 | 获取任务配置清单 |
| PUT | /auctions/{id}/task-config | 必须 | 更新任务配置（交易员） |
| POST | /auctions/{id}/task-config/confirm | 必须 | 确认任务配置完成（交易员） |

### 执行前复核

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/review | 必须 | 获取复核记录 |
| POST | /auctions/{id}/review | 必须 | 发起执行前复核（交易员） |
| PUT | /auctions/{id}/review/checklist | 必须 | 更新复核清单勾选状态（复核人） |
| POST | /auctions/{id}/review/submit | 必须 | 提交复核结论（复核人） |
| POST | /auctions/{id}/mark-executable | 必须 | 标记任务可执行（交易员，需复核通过） |

### 竞拍执行

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/execution-logs | 必须 | 获取执行日志列表 |
| POST | /auctions/{id}/execution-logs | 必须 | 新增执行日志条目（交易员） |
| POST | /auctions/{id}/execution-complete | 必须 | 标记竞拍执行完成（交易员） |

### 实时监控

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/monitor-records | 必须 | 获取监控记录列表 |
| POST | /auctions/{id}/monitor-records | 必须 | 新增监控记录（监控人员） |

### 异常修改审批与留痕

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/modifications | 必须 | 获取临场修改记录列表 |
| POST | /auctions/{id}/modifications | 必须 | 提交临场修改申请（交易员/监控人员） |
| POST | /auctions/{id}/modifications/emergency-execute | 必须 | 应急执行（倒计时阶段，交易员） |
| POST | /auctions/{id}/modifications/{mid}/approve | 必须 | 审批通过（策略负责人） |
| POST | /auctions/{id}/modifications/{mid}/reject | 必须 | 审批驳回（策略负责人，附原因） |
| POST | /auctions/{id}/modifications/{mid}/review | 必须 | 复核通过（复核人） |
| POST | /auctions/{id}/modifications/{mid}/review-reject | 必须 | 复核驳回（复核人，附原因） |
| POST | /auctions/{id}/modifications/{mid}/execute | 必须 | 标记执行（交易员，需 APPROVED 状态） |
| POST | /auctions/{id}/modifications/{mid}/post-explanation | 必须 | 补充应急说明或标记流程偏差（交易员/复盘负责人） |

### 复盘报告

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/retrospective | 必须 | 获取复盘报告 |
| POST | /auctions/{id}/retrospective | 必须 | 创建复盘报告（复盘负责人） |
| PUT | /auctions/{id}/retrospective | 必须 | 更新复盘报告内容（复盘负责人） |
| POST | /auctions/{id}/retrospective/submit | 必须 | 提交归档复盘报告（复盘负责人） |

### 整改事项

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| POST | /retrospectives/{rid}/rectification-items | 必须 | 创建整改事项（复盘负责人） |
| GET | /retrospectives/{rid}/rectification-items | 必须 | 查询整改事项列表 |
| PUT | /rectification-items/{iid} | 必须 | 更新整改事项状态/内容（责任人或复盘负责人） |
| POST | /rectification-items/{iid}/upload-evidence | 必须 | 上传完成证据 |
| POST | /rectification-items/{iid}/confirm | 必须 | 确认整改完成或关闭（业务负责人或复盘负责人） |

---

## 核心逻辑设计

### 策略版本状态机

```python
# backend/app/services/strategy_service.py

VALID_TRANSITIONS = {
    "DRAFT":     ["PENDING", "VOIDED"],
    "PENDING":   ["DRAFT", "CONFIRMED"],   # DRAFT=驳回, CONFIRMED=确认通过
    "CONFIRMED": ["FINAL", "VOIDED"],
    "FINAL":     ["VOIDED"],
    "VOIDED":    [],                        # 终态
}

def transition_status(current: str, target: str) -> None:
    if target not in VALID_TRANSITIONS.get(current, []):
        raise ValueError(f"非法状态流转: {current} → {target}")
```

### 红线字段变更检测

```python
RED_LINE_FIELDS = {
    "bid_price", "bid_quantity", "bid_time_points",
    "trigger_conditions", "fallback_plan", "applicable_scenarios"
}

def has_red_line_change(old: StrategyVersion, new_data: dict) -> bool:
    for field in RED_LINE_FIELDS:
        if field in new_data and getattr(old, field) != new_data[field]:
            return True
    return False

# 调用方：若 has_red_line_change 为 True 且当前版本非 DRAFT，
# 必须先创建新版本，不允许直接修改
```

### 乐观锁并发控制

```python
# 更新时携带 version 字段，后端校验
async def update_with_optimistic_lock(session, model, id, version, updates):
    result = await session.execute(
        update(model)
        .where(model.id == id, model.version == version)
        .values(**updates, version=version + 1)
    )
    if result.rowcount == 0:
        raise ConflictError("数据已被他人修改，请刷新后重试")
```

### 双人复核校验

```python
# backend/app/api/v1/reviews.py

def validate_dual_review(configurer_id: UUID, reviewer_id: UUID) -> None:
    if configurer_id == reviewer_id:
        raise HTTPException(
            status_code=400,
            detail="配置人与复核人不能为同一账号，请由不同人员完成复核"
        )
```

### 阶段门控校验

```python
PHASE_GATES = {
    # 阶段02：基础信息已由业务负责人确认
    2: lambda a: a.phase_statuses.get("1") == "confirmed",
    # 阶段03：软阻断，历史分析未确认时提示但允许继续
    3: lambda a: True,
    # 阶段04 → 阶段05：存在 strategy_versions.status == FINAL
    5: lambda a: a.phase_statuses.get("4") == "has_final_strategy",
    # 阶段05 → 阶段06：task_configs.status == confirmed
    6: lambda a: a.phase_statuses.get("5") == "confirmed",
    # 阶段06 → 阶段07：pre_execution_reviews.status == passed 且 13 项清单全部为 true
    7: lambda a: a.phase_statuses.get("6") == "passed",
    # 阶段07 → 阶段10：竞拍执行已标记完成
    10: lambda a: a.phase_statuses.get("7") == "completed",
}

# 阶段10 归档门控由 validate_retrospective_submit() 负责，不在此处处理

def check_phase_gate(auction, target_phase: int) -> None:
    gate = PHASE_GATES.get(target_phase)
    if gate and not gate(auction):
        raise HTTPException(status_code=400, detail=f"前置阶段未完成，无法进入阶段 {target_phase}")
```

### 复盘报告提交校验

```python
async def validate_retrospective_submit(auction_id, retrospective, session):
    # 1. 必须关联最终版本
    final = await get_final_strategy(auction_id, session)
    if not final:
        raise HTTPException(400, "请先确认最终策略版本后再提交复盘报告")

    # 2. 临场修改记录必须已闭合（不存在 PENDING_APPROVAL / PENDING_REVIEW）
    pending_mods = await get_pending_modifications(auction_id, session)
    if pending_mods:
        raise HTTPException(400, "存在未完成审批或复核的临场修改，请处理后再提交复盘")

    # 3. 应急执行必须补说明或标记流程偏差
    unhandled_emergency = await get_unhandled_emergency(auction_id, session)
    if unhandled_emergency:
        raise HTTPException(400, "存在未补说明的应急执行记录，请补充后再提交复盘")

    # 4. 发现的问题必须已创建整改项（整改项需填写责任人、措施、截止时间）
    incomplete_items = await get_incomplete_rectification_items(auction_id, session)
    if incomplete_items:
        raise HTTPException(400, "存在未填写责任人/措施/截止时间的整改事项，请完善后再提交")

    # 5. 必填项校验
    required_fields = [
        "basic_info", "strategy_summary", "execution_summary",
        "transaction_result", "deviation_analysis", "anomaly_records",
        "confirmation_records", "root_cause", "improvement_actions", "strategy_learnings"
    ]
    for field in required_fields:
        if not getattr(retrospective, field):
            raise HTTPException(400, f"复盘报告必填项 [{field}] 未填写")

# 注意：
# - REJECTED 且未执行的临场修改申请不阻断归档（已驳回属于正常过程记录）
# - REJECTED 但存在执行记录属于流程违规，需在 post-explanation 接口中标记偏差原因后方可归档
# - 非预授权应急执行必须通过 post-explanation 接口标记 deviation_reason，否则 get_unhandled_emergency() 会返回该记录
```

---

## 架构决策

### 接口契约
- 所有接口返回统一结构：`{"code": 0, "data": ..., "message": "ok"}`
- 错误码：`400` 业务校验失败，`401` 未认证，`403` 权限不足，`409` 并发冲突
- 不破坏现有接口，新增接口均在 `/api/v1/` 前缀下

### 权限隔离
- JWT payload 携带 `user_id` 和 `role`
- 每个接口通过 FastAPI Dependency 校验角色权限
- 无多租户隔离（第一版所有用户共享数据）

### DB 兼容性
- 使用 Alembic 管理所有 schema 变更，禁止手动修改数据库
- PostgreSQL 15+，使用 JSONB 存储灵活结构字段（任务列表、场景策略等）
- 所有时间字段使用 TIMESTAMPTZ（带时区）

### 跨模块边界
- `auctions` 是核心聚合根，所有子资源通过 `auction_id` 关联
- `strategy_versions` 独立管理版本生命周期，其他模块只读引用
- `confirmations` 是通用确认记录表，通过 `target_type + target_id` 关联任意对象

### spec 业务规则对应关系

| spec 业务规则 | plan 技术实现 |
|---|---|
| 分级确认机制（策略负责人提交 + 审核人确认 + 必要时业务负责人确认） | strategy submit/confirm/reject 接口 + confirmations 表记录 + 角色/账号校验（提交人≠审核人） |
| 红线字段变更重新确认 | `has_red_line_change()` 检测 + 状态机约束 |
| 双人复核身份校验 | `validate_dual_review()` + pre_execution_reviews.reviewer_id ≠ configurer_id |
| 版本号唯一性 | `(auction_id, version_code)` 唯一约束 |
| 作废版本保留 | VOIDED 为终态，无物理删除接口 |
| 并发冲突防护 | 乐观锁 version 字段 + `update_with_optimistic_lock()` |
| 阶段门控 | `check_phase_gate()` 前置校验 |
| 临场修改审批与留痕 | modifications 状态机 + approve/reject/review/execute/post-explanation 接口 |
| 整改事项闭环 | rectification_items 状态机 + 归档前创建整改项校验 |
| 复盘必填项校验 | `validate_retrospective_submit()` 提交时校验 |
