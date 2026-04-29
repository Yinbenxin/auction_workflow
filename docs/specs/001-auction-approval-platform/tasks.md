> ⚠️ 需求已冻结（2026-04-29）。实现阶段的需求变更必须走 change-request，不能直接改代码。

# 001 - 竞拍工作平台 Tasks

## 目录
- [当前进度](#当前进度)
- [完整度检查点](#完整度检查点)
  - [spec 覆盖](#spec-覆盖)
  - [plan 覆盖](#plan-覆盖)
- [环境初始化](#环境初始化)
- [DB 迁移层](#db-迁移层按依赖顺序)
- [后端层](#后端层)
  - [模型层](#模型层与迁移并行)
- [前端层](#前端层)

---

## 当前进度
- spec 分析阶段：✓ 完成
- plan/tasks 同步：✓ 完成
- 环境初始化：✓ 完成（T0 后端 + T0-fe 前端）
- DB 层：✓ 完成（T1~T7b，9 个迁移文件，跨层验证 ✓）
- 后端层：✓ 完成（T8~T19，43个接口，跨层验证 ✓）
- 前端层：✓ 完成（T20~T28b，12个页面，跨层验证 ✓）

## 完整度检查点

### spec 覆盖
- [ ] US-01~03 竞拍信息收集 → T1, T8, T9, T21
- [ ] US-04~05 历史数据分析 → T1, T8, T9, T21
- [ ] US-06~08 策略方案制定 → T2, T3, T10, T11, T22
- [ ] US-09~11 策略评审确认 → T3, T10, T11, T22
- [ ] US-12~13 任务配置 → T4, T12, T23
- [ ] US-14~16 执行前复核 → T5, T13, T24
- [ ] US-17~18 竞拍执行 → T6, T14, T25
- [ ] US-19~20 实时监控 → T6, T15, T26
- [ ] US-21~25 异常修改审批与留痕 → T6, T16, T27
- [ ] US-26~28 结果复盘 → T7, T17, T28
- [ ] US-29~30 整改事项跟踪 → T7b, T17b, T28b
- [ ] EC-1 版本状态非法流转 → T3, T10
- [ ] EC-2 红线字段变更重新确认 → T3, T10
- [ ] EC-3 双人复核同一人 → T5, T13
- [ ] EC-4 未复核强行执行 → T5, T13
- [ ] EC-5 临场修改管控缺失（含 REJECTED 不阻断归档） → T6, T16, T17, T27, T28
- [ ] EC-6 并发冲突 → T3, T10
- [ ] EC-9 版本号重复 → T2, T10

### plan 覆盖
- [ ] POST /auth/login → T9, T21
- [ ] GET/POST /auctions → T8, T21
- [ ] PUT /auctions/{id}/basic-info + confirm → T8, T21
- [ ] PUT /auctions/{id}/history-analysis + confirm → T8, T21
- [ ] GET/POST /auctions/{id}/strategies → T10, T22
- [ ] POST /strategies/{vid}/submit|confirm|reject|finalize|void → T10, T22
- [ ] GET/PUT /auctions/{id}/task-config + confirm → T12, T23
- [ ] GET/POST /auctions/{id}/review + submit → T13, T24
- [ ] POST /auctions/{id}/mark-executable → T13, T24
- [ ] GET/POST /auctions/{id}/execution-logs → T14, T25
- [ ] GET/POST /auctions/{id}/monitor-records → T15, T26
- [ ] GET/POST /auctions/{id}/modifications + emergency-execute + approve/reject/review/review-reject/execute/post-explanation → T16, T27
- [ ] GET/POST/PUT /auctions/{id}/retrospective + submit → T17, T28
- [ ] POST/GET /retrospectives/{rid}/rectification-items → T17b, T28b
- [ ] PUT /rectification-items/{iid} + upload-evidence + confirm → T17b, T28b
- [ ] DB: users → T0
- [ ] DB: auctions → T1
- [ ] DB: strategy_versions（含 risk_level） → T2
- [ ] DB: confirmations → T3
- [ ] DB: task_configs → T4
- [ ] DB: pre_execution_reviews（13项清单） → T5
- [ ] DB: execution_logs, monitor_records, modifications → T6
- [ ] DB: retrospectives → T7
- [ ] DB: rectification_items → T7b

---

## 环境初始化

- [ ] **T0** `backend/requirements.txt` + `backend/app/core/database.py` + `backend/app/core/config.py` + `backend/app/core/security.py` + `backend/app/main.py`
  - 初始化 FastAPI 项目结构，配置 SQLAlchemy 异步连接、JWT 工具、环境变量
  - 创建 users 表 Alembic 迁移

- [ ] **T0-fe** `frontend/package.json` + `frontend/src/main.ts` + `frontend/src/router/index.ts`
  - 初始化 Vue 3 + TypeScript + Vite + Element Plus + Pinia + Axios 项目结构

---

## DB 迁移层（按依赖顺序）

- [ ] **T1** `backend/migrations/versions/001_create_auctions.py`
  - 创建 auctions 表（含 basic_info、history_analysis JSONB 字段、phase_statuses、version 乐观锁）

- [ ] **T2** `backend/migrations/versions/002_create_strategy_versions.py`
  - 创建 strategy_versions 表（含6个红线字段、risk_level、pre_authorized_actions、risk_notes、previous_version_id 自引用、唯一约束 auction_id+version_code）

- [ ] **T3** `backend/migrations/versions/003_create_confirmations.py`
  - 创建 confirmations 通用确认记录表（target_type + target_id 多态关联）

- [ ] **T4** `backend/migrations/versions/004_create_task_configs.py`
  - 创建 task_configs 表（含 strategy_version_id、tasks JSONB、attachments、configured_by、status）

- [ ] **T5** `backend/migrations/versions/005_create_pre_execution_reviews.py`
  - 创建 pre_execution_reviews 表（含 13 项 checklist JSONB、configurer_id、reviewer_id、status）

- [ ] **T6** `backend/migrations/versions/006_create_execution_monitor_modification.py`
  - 创建 execution_logs、monitor_records、modifications 三张表；modifications 含审批/复核/执行/应急/偏差/附件字段和状态枚举（10个状态值）

- [ ] **T7** `backend/migrations/versions/007_create_retrospectives.py`
  - 创建 retrospectives 表（含11个必填项字段、emergency_explanation）

- [ ] **T7b** `backend/migrations/versions/008_create_rectification_items.py`
  - 创建 rectification_items 表（关联 retrospective_id、assignee_id、measures/due_date NOT NULL、status、evidence/delay_reason/close_reason JSONB）

---

## 后端层

### 模型层（与迁移并行）

- [ ] **T8** `backend/app/models/auction.py`
  - Auction SQLAlchemy 模型，含 phase_statuses JSONB、version 乐观锁字段

- [ ] **T9** `backend/app/models/user.py` + `backend/app/api/v1/auth.py`
  - User 模型 + 登录接口（POST /auth/login）+ JWT 生成 + GET /auth/me

- [ ] **T10** `backend/app/models/strategy.py` + `backend/app/services/strategy_service.py` + `backend/app/api/v1/strategies.py`
  - StrategyVersion 模型（含 risk_level/pre_authorized_actions）+ 状态机（VALID_TRANSITIONS）+ 红线字段检测（has_red_line_change）+ 乐观锁 + 版本号唯一校验
  - 校验：risk_level=EMERGENCY 时 pre_authorized_actions 必填；confirm 接口校验提交人与审核人不能为同一账号
  - 接口：GET/POST /strategies, PUT /strategies/{vid}, submit/confirm/reject/finalize/void

- [ ] **T11** `backend/app/models/confirmation.py` + `backend/app/api/v1/confirmations.py`
  - Confirmation 通用确认记录模型 + 查询接口

- [ ] **T12** `backend/app/models/task_config.py` + `backend/app/api/v1/task_configs.py`
  - TaskConfig 模型 + GET/PUT /task-config + POST /task-config/confirm

- [ ] **T13** `backend/app/models/review.py` + `backend/app/services/review_service.py` + `backend/app/api/v1/reviews.py`
  - PreExecutionReview 模型 + 双人复核校验（validate_dual_review）+ 复核状态前置校验
  - 接口：GET/POST /review, PUT /review/checklist, POST /review/submit, POST /mark-executable

- [ ] **T14** `backend/app/models/execution.py` + `backend/app/api/v1/executions.py`
  - ExecutionLog 模型 + GET/POST /execution-logs + POST /execution-complete

- [ ] **T15** `backend/app/models/monitor.py` + `backend/app/api/v1/monitors.py`
  - MonitorRecord 模型 + GET/POST /monitor-records

- [ ] **T16** `backend/app/models/modification.py` + `backend/app/services/modification_service.py` + `backend/app/api/v1/modifications.py`
  - Modification 模型（含完整状态机字段：审批人/复核人/执行人/应急标记/偏差标记）+ 临场修改状态机
  - 接口：GET/POST /modifications、POST /modifications/emergency-execute、approve/reject/review/review-reject/execute/post-explanation

- [ ] **T17** `backend/app/models/retrospective.py` + `backend/app/services/retrospective_service.py` + `backend/app/api/v1/retrospectives.py`
  - Retrospective 模型 + 提交校验（validate_retrospective_submit：最终版本关联、临场修改闭合、应急执行补说明、整改项已创建、11项必填）
  - 接口：GET/POST/PUT /retrospective + POST /retrospective/submit

- [ ] **T17b** `backend/app/models/rectification.py` + `backend/app/api/v1/rectifications.py`
  - RectificationItem 模型（measures/due_date NOT NULL、status 状态机）
  - 接口：POST/GET /retrospectives/{rid}/rectification-items、PUT /rectification-items/{iid}、POST /rectification-items/{iid}/upload-evidence、POST /rectification-items/{iid}/confirm

- [ ] **T18** `backend/app/api/v1/auctions.py`
  - Auction CRUD + 阶段门控（check_phase_gate）+ basic-info/history-analysis 录入与确认接口

- [ ] **T19** `backend/app/dependencies.py`
  - FastAPI 依赖注入：get_current_user、require_role(roles)、get_db

---

## 前端层

- [ ] **T20** `frontend/src/api/index.ts` + `frontend/src/stores/auth.ts`
  - Axios 封装（统一错误处理、JWT 注入）+ 登录 store + 登录页 `frontend/src/views/auth/LoginView.vue`

- [ ] **T21** `frontend/src/views/auctions/AuctionListView.vue` + `frontend/src/views/auctions/AuctionDetailView.vue`
  - 竞拍项目列表、详情（含阶段进度展示）、基础信息录入与确认、历史分析录入与确认

- [ ] **T22** `frontend/src/views/strategies/StrategyListView.vue` + `frontend/src/views/strategies/StrategyFormView.vue`
  - 策略版本列表、创建/编辑表单（含6个红线字段）、提交/确认/驳回/标记最终版本/作废操作、版本历史

- [ ] **T23** `frontend/src/views/task-configs/TaskConfigView.vue`
  - 任务配置清单录入（任务编号/时间/价格/数量/触发条件/任务顺序/启停状态/垫子策略/补量策略/兜底任务/配置截图上传）、确认操作

- [ ] **T24** `frontend/src/views/reviews/ReviewView.vue`
  - 执行前复核页面：13项清单逐项勾选（含垫子/补量策略、任务顺序和启停状态）、提交复核结论、标记可执行（复核通过后解锁）

- [ ] **T25** `frontend/src/views/executions/ExecutionLogView.vue`
  - 竞拍执行日志录入、标记执行完成

- [ ] **T26** `frontend/src/views/monitors/MonitorView.vue`
  - 监控数据录入、异常事件记录

- [ ] **T27** `frontend/src/views/modifications/ModificationView.vue`
  - 临场修改申请表单（reason/impact_scope 必填）、策略负责人审批/驳回页面、复核人复核/驳回页面、交易员执行标记、应急执行入口、事后补说明和流程偏差标记页面（按角色展示不同操作）

- [ ] **T28** `frontend/src/views/retrospectives/RetrospectiveView.vue`
  - 复盘报告填写（11项必填）、应急说明（有应急修改时显示）、提交归档

- [ ] **T28b** `frontend/src/views/retrospectives/RectificationView.vue`
  - 整改事项列表（关联复盘报告）、创建整改项（责任人/措施/截止时间必填）、更新状态、上传完成证据、确认完成/关闭操作
