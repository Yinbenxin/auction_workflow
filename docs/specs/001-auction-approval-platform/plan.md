# 001 - 竞拍工作平台 Plan

## 目录
- [技术架构](#技术架构)
- [数据结构](#数据结构)
- [接口清单](#接口清单)
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
│   │   │   └── retrospective.py    # 复盘报告
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── auctions.py
│   │   │       ├── strategies.py
│   │   │       ├── confirmations.py
│   │   │       ├── reviews.py
│   │   │       ├── executions.py
│   │   │       ├── monitors.py
│   │   │       ├── modifications.py
│   │   │       └── retrospectives.py
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── strategy_service.py
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
│   │   │   └── retrospectives/     # 复盘报告
│   │   ├── router/
│   │   └── components/
│   └── package.json
└── docs/

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

角色枚举：`business_owner`（业务负责人）、`strategy_owner`（策略负责人）、`trader`（交易员）、`reviewer`（复核人）、`data_analyst`（数据人员）、`monitor`（监控人员）、`retrospective_owner`（复盘负责人）

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

### task_configs（任务配置清单表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| strategy_version_id | UUID FK→strategy_versions | 关联最终版本 |
| tasks | JSONB | 任务列表（编号/时间/价格/数量/触发条件/兜底标识） |
| status | VARCHAR(20) | pending / confirmed |
| configured_by | UUID FK→users | 配置人（交易员） |
| created_at | TIMESTAMPTZ | 创建时间 |

### pre_execution_reviews（执行前复核表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| strategy_version_id | UUID FK→strategy_versions | 关联最终版本 |
| checklist | JSONB | 12项清单勾选状态 `{item_1: true, item_2: false, ...}` |
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

### modifications（临场修改记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| auction_id | UUID FK→auctions | 所属竞拍项目 |
| field_name | VARCHAR(100) | 修改字段名 |
| before_value | TEXT | 修改前内容 |
| after_value | TEXT | 修改后内容 |
| reason | TEXT NOT NULL | 修改原因（不允许为空） |
| impact_scope | TEXT NOT NULL | 影响范围（不允许为空） |
| is_emergency | BOOLEAN | 是否为应急执行 |
| status | VARCHAR(20) | pending / confirmed |
| modified_by | UUID FK→users | 修改人 |
| modified_at | TIMESTAMPTZ | 修改时间 |

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
| POST | /auctions/{id}/strategies/{vid}/confirm | 必须 | 确认策略版本（策略负责人/业务负责人） |
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

### 异常修改留痕

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/modifications | 必须 | 获取临场修改记录列表 |
| POST | /auctions/{id}/modifications | 必须 | 新增临场修改记录（交易员/监控人员） |
| POST | /auctions/{id}/modifications/{mid}/confirm | 必须 | 确认临场修改（策略负责人） |

### 复盘报告

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|:----:|------|
| GET | /auctions/{id}/retrospective | 必须 | 获取复盘报告 |
| POST | /auctions/{id}/retrospective | 必须 | 创建复盘报告（复盘负责人） |
| PUT | /auctions/{id}/retrospective | 必须 | 更新复盘报告内容（复盘负责人） |
| POST | /auctions/{id}/retrospective/submit | 必须 | 提交归档复盘报告（复盘负责人） |

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
    2: lambda a: a.phase_statuses.get("1") == "confirmed",   # 阶段02需阶段01已确认
    3: lambda a: True,   # 阶段03软阻断，只提示不强制
    4: lambda a: a.phase_statuses.get("3") == "has_strategy",
    5: lambda a: a.phase_statuses.get("4") == "confirmed",
    6: lambda a: a.phase_statuses.get("5") == "confirmed",
    7: lambda a: a.phase_statuses.get("6") == "passed",
    10: lambda a: a.phase_statuses.get("7") == "completed",
}

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

    # 2. 存在未确认的应急修改时，必须填写 emergency_explanation
    has_emergency = await has_unconfirmed_emergency(auction_id, session)
    if has_emergency and not retrospective.emergency_explanation:
        raise HTTPException(400, "存在未确认的临场修改记录，请补充说明后再提交")

    # 3. 必填项校验
    required_fields = [
        "basic_info", "strategy_summary", "execution_summary",
        "transaction_result", "deviation_analysis", "anomaly_records",
        "confirmation_records", "root_cause", "improvement_actions", "strategy_learnings"
    ]
    for field in required_fields:
        if not getattr(retrospective, field):
            raise HTTPException(400, f"复盘报告必填项 [{field}] 未填写")
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
| 确认机制（负责人点击确认） | `POST /confirm` 接口 + confirmations 表记录 |
| 红线字段变更重新确认 | `has_red_line_change()` 检测 + 状态机约束 |
| 双人复核身份校验 | `validate_dual_review()` + pre_execution_reviews.reviewer_id ≠ configurer_id |
| 版本号唯一性 | `(auction_id, version_code)` 唯一约束 |
| 作废版本保留 | VOIDED 为终态，无物理删除接口 |
| 并发冲突防护 | 乐观锁 version 字段 + `update_with_optimistic_lock()` |
| 阶段门控 | `check_phase_gate()` 前置校验 |
| 复盘必填项校验 | `validate_retrospective_submit()` 提交时校验 |
