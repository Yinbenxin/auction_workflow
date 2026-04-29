# 001 - 竞拍工作平台 TDD

> 测试框架：pytest + httpx AsyncClient
> 覆盖范围：T0~T28b 全量任务层
> 对照依据：spec.md 验收标准 + Edge Cases + plan.md 接口清单

## 目录
- [测试策略](#测试策略)
- [测试环境配置](#测试环境配置)
- [后端单元测试](#后端单元测试)
  - [策略版本状态机](#策略版本状态机)
  - [红线字段检测](#红线字段检测)
  - [双人复核校验](#双人复核校验)
  - [临场修改状态机](#临场修改状态机)
  - [整改事项状态机](#整改事项状态机)
  - [复盘报告提交校验](#复盘报告提交校验)
  - [阶段门控校验](#阶段门控校验)
- [后端 API 集成测试](#后端-api-集成测试)
  - [认证接口](#认证接口)
  - [竞拍项目接口](#竞拍项目接口)
  - [策略版本接口](#策略版本接口)
  - [任务配置接口](#任务配置接口)
  - [执行前复核接口](#执行前复核接口)
  - [竞拍执行接口](#竞拍执行接口)
  - [实时监控接口](#实时监控接口)
  - [异常修改审批接口](#异常修改审批接口)
  - [复盘报告接口](#复盘报告接口)
  - [整改事项接口](#整改事项接口)
- [Edge Case 测试](#edge-case-测试)
- [前端测试](#前端测试)
  - [登录页](#登录页)
  - [竞拍项目页](#竞拍项目页)
  - [策略版本页](#策略版本页)
  - [任务配置页](#任务配置页)
  - [执行前复核页](#执行前复核页)
  - [竞拍执行页](#竞拍执行页)
  - [实时监控页](#实时监控页)
  - [异常修改页](#异常修改页)
  - [复盘报告页](#复盘报告页)
  - [整改事项页](#整改事项页)
- [测试覆盖率目标](#测试覆盖率目标)

---

## 测试策略

### 分层原则

| 层次 | 工具 | 覆盖目标 |
|------|------|---------|
| 单元测试 | pytest | 状态机、校验函数、业务规则纯逻辑 |
| API 集成测试 | pytest + httpx AsyncClient | 接口契约、权限校验、端到端业务流 |
| 前端组件测试 | Vitest + Vue Test Utils | 表单校验、角色权限渲染、状态展示 |
| 前端 E2E 测试 | Playwright | 关键业务流程（登录→策略→复核→执行→复盘） |

### TDD 节奏

每个任务（T0~T28b）遵循：

```
1. 写失败测试（Red）   → 描述期望行为
2. 写最小实现（Green） → 让测试通过
3. 重构（Refactor）   → 保持测试绿色
```

### 测试文件组织

```
backend/tests/
├── conftest.py              # 共享 fixture（DB、client、用户工厂）
├── unit/
│   ├── test_strategy_service.py
│   ├── test_modification_service.py
│   ├── test_review_service.py
│   └── test_retrospective_service.py
├── api/
│   ├── test_auth.py
│   ├── test_auctions.py
│   ├── test_strategies.py
│   ├── test_task_configs.py
│   ├── test_reviews.py
│   ├── test_executions.py
│   ├── test_monitors.py
│   ├── test_modifications.py
│   ├── test_retrospectives.py
│   └── test_rectifications.py
└── edge_cases/
    └── test_edge_cases.py

frontend/src/
├── views/__tests__/
│   ├── LoginView.test.ts
│   ├── AuctionListView.test.ts
│   ├── StrategyFormView.test.ts
│   ├── TaskConfigView.test.ts
│   ├── ReviewView.test.ts
│   ├── ExecutionLogView.test.ts
│   ├── MonitorView.test.ts
│   ├── ModificationView.test.ts
│   ├── RetrospectiveView.test.ts
│   └── RectificationView.test.ts
└── e2e/
    └── auction_workflow.spec.ts
```

---

## 测试环境配置

### conftest.py（后端共享 fixture）

```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/auction_test"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

# 用户工厂 fixture
@pytest_asyncio.fixture
async def make_user(db_session):
    from app.models.user import User
    from app.core.security import get_password_hash
    created = []
    async def _make(username: str, role: str):
        user = User(username=username, hashed_password=get_password_hash("password"), full_name=username, role=role)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        created.append(user)
        return user
    yield _make

def auth_header(user_id: str, role: str) -> dict:
    token = create_access_token({"sub": str(user_id), "role": role})
    return {"Authorization": f"Bearer {token}"}
```

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

### vitest.config.ts（前端）

```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})
```

---

## 后端单元测试

### 策略版本状态机

```python
# backend/tests/unit/test_strategy_service.py
import pytest
from app.services.strategy_service import transition_status, VALID_TRANSITIONS

class TestStrategyStateMachine:
    def test_draft_to_pending(self):
        transition_status("DRAFT", "PENDING")  # 不抛异常

    def test_pending_to_confirmed(self):
        transition_status("PENDING", "CONFIRMED")

    def test_confirmed_to_final(self):
        transition_status("CONFIRMED", "FINAL")

    def test_final_to_voided(self):
        transition_status("FINAL", "VOIDED")

    def test_voided_is_terminal(self):
        # EC-1：VOIDED 为终态
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_status("VOIDED", "DRAFT")

    def test_confirmed_cannot_go_to_draft(self):
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_status("CONFIRMED", "DRAFT")

    def test_final_cannot_go_to_confirmed(self):
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_status("FINAL", "CONFIRMED")

    def test_pending_reject_returns_to_draft(self):
        transition_status("PENDING", "DRAFT")

    @pytest.mark.parametrize("status", ["CONFIRMED", "FINAL"])
    def test_cannot_modify_confirmed_or_final(self, status):
        assert status not in VALID_TRANSITIONS.get("DRAFT", [])
```

### 红线字段检测

```python
# backend/tests/unit/test_strategy_service.py（续）
from app.services.strategy_service import has_red_line_change

class TestRedLineDetection:
    def test_no_change_returns_false(self):
        old = {"bid_price": 100, "bid_quantity": 50, "bid_time_points": ["09:00"],
               "trigger_conditions": {}, "fallback_plan": "兜底", "applicable_scenarios": []}
        assert has_red_line_change(old, dict(old)) is False

    @pytest.mark.parametrize("field", [
        "bid_price", "bid_quantity", "bid_time_points",
        "trigger_conditions", "fallback_plan", "applicable_scenarios"
    ])
    def test_each_red_line_field_triggers(self, field):
        # EC-2：6个红线字段任意一个变更都必须触发
        old = {"bid_price": 100, "bid_quantity": 50, "bid_time_points": ["09:00"],
               "trigger_conditions": {"type": "A"}, "fallback_plan": "兜底",
               "applicable_scenarios": ["场景A"]}
        new = dict(old)
        new[field] = "changed_value"
        assert has_red_line_change(old, new) is True

    def test_non_red_line_field_no_trigger(self):
        old = {"bid_price": 100, "bid_quantity": 50, "bid_time_points": [],
               "trigger_conditions": {}, "fallback_plan": "", "applicable_scenarios": [],
               "risk_notes": "旧备注"}
        new = dict(old)
        new["risk_notes"] = "新备注"
        assert has_red_line_change(old, new) is False
```

### 双人复核校验

```python
# backend/tests/unit/test_review_service.py
import pytest
from uuid import uuid4
from app.services.review_service import validate_dual_review, validate_checklist

class TestDualReviewValidation:
    def test_same_user_raises_error(self):
        # EC-3
        user_id = uuid4()
        with pytest.raises(ValueError, match="配置人与复核人不能为同一账号"):
            validate_dual_review(configurer_id=user_id, reviewer_id=user_id)

    def test_different_users_passes(self):
        validate_dual_review(configurer_id=uuid4(), reviewer_id=uuid4())

    def test_checklist_incomplete_raises_error(self):
        checklist = {f"item_{i}": True for i in range(1, 14)}
        checklist["item_7"] = False
        with pytest.raises(ValueError, match="复核清单未全部通过"):
            validate_checklist(checklist)

    def test_checklist_all_true_passes(self):
        checklist = {f"item_{i}": True for i in range(1, 14)}
        validate_checklist(checklist)  # 不抛异常

    def test_checklist_wrong_count_raises_error(self):
        checklist = {f"item_{i}": True for i in range(1, 10)}  # 只有9项
        with pytest.raises(ValueError, match="复核清单项数不足"):
            validate_checklist(checklist)
```

### 临场修改状态机

```python
# backend/tests/unit/test_modification_service.py
import pytest
from app.services.modification_service import transition_modification_status

class TestModificationStateMachine:
    def test_draft_to_pending_approval(self):
        transition_modification_status("DRAFT", "PENDING_APPROVAL")

    def test_pending_approval_to_rejected(self):
        transition_modification_status("PENDING_APPROVAL", "REJECTED")

    def test_pending_approval_to_pending_review(self):
        transition_modification_status("PENDING_APPROVAL", "PENDING_REVIEW")

    def test_pending_review_to_approved(self):
        transition_modification_status("PENDING_REVIEW", "APPROVED")

    def test_approved_to_executed(self):
        transition_modification_status("APPROVED", "EXECUTED")

    def test_emergency_executed_to_pending_post_explanation(self):
        transition_modification_status("EMERGENCY_EXECUTED", "PENDING_POST_EXPLANATION")

    def test_emergency_executed_to_pending_deviation(self):
        transition_modification_status("EMERGENCY_EXECUTED", "PENDING_DEVIATION_EXPLANATION")

    def test_post_explained_is_terminal(self):
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_modification_status("POST_EXPLAINED", "DRAFT")

    def test_rejected_is_terminal(self):
        # EC-5：REJECTED 是终态
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_modification_status("REJECTED", "APPROVED")

    def test_cannot_execute_without_approval(self):
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_modification_status("PENDING_APPROVAL", "EXECUTED")
```

### 整改事项状态机

```python
# backend/tests/unit/test_rectification_service.py
import pytest
from app.services.rectification_service import (
    transition_rectification_status, validate_completion, validate_delay
)

class TestRectificationStateMachine:
    def test_pending_to_in_progress(self):
        transition_rectification_status("PENDING", "IN_PROGRESS")

    def test_in_progress_to_completed(self):
        transition_rectification_status("IN_PROGRESS", "COMPLETED")

    def test_in_progress_to_delayed(self):
        transition_rectification_status("IN_PROGRESS", "DELAYED")

    def test_in_progress_to_closed(self):
        transition_rectification_status("IN_PROGRESS", "CLOSED")

    def test_completed_is_terminal(self):
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_rectification_status("COMPLETED", "PENDING")

    def test_pending_cannot_skip_to_completed(self):
        with pytest.raises(ValueError, match="非法状态流转"):
            transition_rectification_status("PENDING", "COMPLETED")

    def test_completed_requires_evidence(self):
        with pytest.raises(ValueError, match="完成证据不能为空"):
            validate_completion(evidence=None)

    def test_delayed_requires_reason_and_new_date(self):
        with pytest.raises(ValueError, match="延期原因不能为空"):
            validate_delay(delay_reason=None, new_due_date="2026-06-01")
        with pytest.raises(ValueError, match="新截止日期不能为空"):
            validate_delay(delay_reason="资源不足", new_due_date=None)
```

### 复盘报告提交校验

```python
# backend/tests/unit/test_retrospective_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.retrospective_service import validate_retrospective_submit

def _mock_retro(**overrides):
    r = MagicMock()
    for f in ["basic_info","strategy_summary","execution_summary","transaction_result",
              "deviation_analysis","anomaly_records","confirmation_records",
              "root_cause","improvement_actions","strategy_learnings"]:
        setattr(r, f, overrides.get(f, f"filled_{f}"))
    return r

class TestRetrospectiveSubmitValidation:
    @pytest.mark.asyncio
    async def test_no_final_strategy_raises_error(self):
        # EC-8
        with patch("app.services.retrospective_service.get_final_strategy", return_value=None):
            with pytest.raises(Exception, match="请先确认最终策略版本"):
                await validate_retrospective_submit("aid", _mock_retro(), None)

    @pytest.mark.asyncio
    async def test_pending_modification_blocks_archive(self):
        # EC-5：PENDING_APPROVAL 阻断
        with patch("app.services.retrospective_service.get_final_strategy", return_value=object()):
            with patch("app.services.retrospective_service.get_pending_modifications",
                       return_value=[{"status": "PENDING_APPROVAL"}]):
                with pytest.raises(Exception, match="存在未完成审批或复核的临场修改"):
                    await validate_retrospective_submit("aid", _mock_retro(), None)

    @pytest.mark.asyncio
    async def test_unhandled_emergency_blocks_archive(self):
        # EC-5：应急执行未补说明
        with patch("app.services.retrospective_service.get_final_strategy", return_value=object()):
            with patch("app.services.retrospective_service.get_pending_modifications", return_value=[]):
                with patch("app.services.retrospective_service.get_unhandled_emergency",
                           return_value=[{"id": "em1"}]):
                    with pytest.raises(Exception, match="存在未补说明的应急执行记录"):
                        await validate_retrospective_submit("aid", _mock_retro(), None)

    @pytest.mark.asyncio
    async def test_missing_required_field_blocks_archive(self):
        retro = _mock_retro(deviation_analysis=None)
        with patch("app.services.retrospective_service.get_final_strategy", return_value=object()):
            with patch("app.services.retrospective_service.get_pending_modifications", return_value=[]):
                with patch("app.services.retrospective_service.get_unhandled_emergency", return_value=[]):
                    with patch("app.services.retrospective_service.get_incomplete_rectification_items",
                               return_value=[]):
                        with pytest.raises(Exception, match="deviation_analysis"):
                            await validate_retrospective_submit("aid", retro, None)

    @pytest.mark.asyncio
    async def test_rejected_modification_does_not_block(self):
        # EC-5：REJECTED 且未执行不阻断
        with patch("app.services.retrospective_service.get_final_strategy", return_value=object()):
            with patch("app.services.retrospective_service.get_pending_modifications", return_value=[]):
                with patch("app.services.retrospective_service.get_unhandled_emergency", return_value=[]):
                    with patch("app.services.retrospective_service.get_incomplete_rectification_items",
                               return_value=[]):
                        await validate_retrospective_submit("aid", _mock_retro(), None)
```

### 阶段门控校验

```python
# backend/tests/unit/test_phase_gate.py
import pytest
from unittest.mock import MagicMock
from app.api.v1.auctions import check_phase_gate

class TestPhaseGate:
    def test_phase2_requires_phase1_confirmed(self):
        auction = MagicMock()
        auction.phase_statuses = {"1": "pending"}
        with pytest.raises(Exception, match="前置阶段未完成"):
            check_phase_gate(auction, 2)

    def test_phase2_passes_when_phase1_confirmed(self):
        auction = MagicMock()
        auction.phase_statuses = {"1": "confirmed"}
        check_phase_gate(auction, 2)

    def test_phase3_is_soft_block(self):
        auction = MagicMock()
        auction.phase_statuses = {}
        check_phase_gate(auction, 3)  # 不抛异常

    def test_phase5_requires_final_strategy(self):
        auction = MagicMock()
        auction.phase_statuses = {"4": "pending"}
        with pytest.raises(Exception, match="前置阶段未完成"):
            check_phase_gate(auction, 5)

    def test_phase7_requires_review_passed(self):
        auction = MagicMock()
        auction.phase_statuses = {"6": "pending"}
        with pytest.raises(Exception, match="前置阶段未完成"):
            check_phase_gate(auction, 7)

    def test_phase10_requires_execution_completed(self):
        auction = MagicMock()
        auction.phase_statuses = {"7": "in_progress"}
        with pytest.raises(Exception, match="前置阶段未完成"):
            check_phase_gate(auction, 10)
```

---

## 后端 API 集成测试

> 完整测试代码见各文件，以下为用例清单和覆盖说明。

### 认证接口

文件：`backend/tests/api/test_auth.py`（134 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_login_success | 正确用户名密码 | 200，返回 JWT token |
| test_login_wrong_password | 密码错误 | 401 |
| test_login_user_not_found | 用户名不存在 | 401 |
| test_get_me_with_valid_token | 有效 token | 200，返回用户信息 |
| test_get_me_without_token | 无 token | 401 |
| test_get_me_with_expired_token | 过期 token | 401 |

### 竞拍项目接口

文件：`backend/tests/api/test_auctions.py`（217 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_list_auctions | 获取列表 | 200，返回数组 |
| test_create_auction_as_data_analyst | 数据人员创建 | 201 |
| test_create_auction_forbidden | 非数据人员创建 | 403 |
| test_update_basic_info | 录入基础信息 | 200 |
| test_confirm_basic_info_as_business_owner | 业务负责人确认 | 200 |
| test_confirm_basic_info_forbidden | 非业务负责人确认 | 403 |
| test_phase_gate_blocks_without_confirmation | 基础信息未确认进入阶段02 | 400 |

### 策略版本接口

文件：`backend/tests/api/test_strategies.py`（392 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_create_strategy | 策略负责人创建 | 201 |
| test_create_emergency_without_pre_authorized | EMERGENCY 无预授权方案 | 400 |
| test_update_draft_strategy | 更新草稿版本 | 200 |
| test_update_confirmed_strategy | 更新 CONFIRMED 版本（EC-1） | 400 |
| test_submit_strategy | 提交待确认 | 200，状态变 PENDING |
| test_confirm_by_auditor | 审核人确认普通策略 | 200 |
| test_confirm_by_submitter_forbidden | 提交人确认自己的版本 | 403 |
| test_confirm_red_line_requires_business_owner | 红线字段变更仅审核人确认 | 400 |
| test_reject_strategy | 驳回附原因 | 200，状态变 DRAFT |
| test_finalize_strategy | 标记最终版本 | 200，状态变 FINAL |
| test_void_strategy | 作废版本 | 200，状态变 VOIDED |
| test_duplicate_version_code | 版本号重复（EC-9） | 409 |

### 任务配置接口

文件：`backend/tests/api/test_task_configs.py`（270 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_get_task_config | 获取任务配置 | 200 |
| test_update_task_config_as_trader | 交易员录入9字段配置 | 200 |
| test_update_task_config_forbidden | 非交易员录入 | 403 |
| test_confirm_task_config | 交易员确认 | 200 |
| test_phase_gate_no_final_strategy | 无最终版本录入任务配置 | 400 |

### 执行前复核接口

文件：`backend/tests/api/test_reviews.py`（407 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_create_review | 发起复核 | 201 |
| test_submit_review_all_passed | 13项全通过提交 | 200 |
| test_submit_review_same_user | 配置人=复核人（EC-3） | 400 |
| test_submit_review_incomplete_checklist | 清单未全部勾选 | 400 |
| test_mark_executable_after_review | 复核通过后标记可执行 | 200 |
| test_mark_executable_without_review | 复核未通过标记可执行（EC-4） | 400 |

### 竞拍执行接口

文件：`backend/tests/api/test_executions.py`（268 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_create_execution_log | 记录执行日志 | 201 |
| test_complete_execution | 标记执行完成 | 200 |
| test_complete_execution_without_review | 复核未通过时完成（EC-4） | 400 |
| test_list_execution_logs | 获取执行日志列表 | 200 |

### 实时监控接口

文件：`backend/tests/api/test_monitors.py`（282 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_create_normal_monitor_record | 记录正常监控数据 | 201 |
| test_create_anomaly_record | 记录异常事件（含 anomaly_type） | 201 |
| test_list_monitor_records | 获取全部监控记录 | 200 |
| test_filter_anomaly_records | 只获取异常记录 | 200，仅 anomaly 类型 |

### 异常修改审批接口

文件：`backend/tests/api/test_modifications.py`（534 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_submit_modification | 提交申请（reason/impact_scope 必填） | 201 |
| test_submit_modification_empty_reason | reason 为空（EC-12） | 400 |
| test_emergency_execute | 应急执行 | 201，状态 EMERGENCY_EXECUTED |
| test_approve_modification | 策略负责人审批通过 | 200 |
| test_approve_forbidden | 非策略负责人审批 | 403 |
| test_reject_modification | 驳回附原因 | 200，状态 REJECTED |
| test_review_modification | 复核人复核通过 | 200 |
| test_review_forbidden | 非复核人复核 | 403 |
| test_review_reject | 复核驳回 | 200 |
| test_execute_modification | 交易员标记执行（APPROVED 状态） | 200 |
| test_execute_without_approval | 非 APPROVED 状态执行 | 400 |
| test_post_explanation | 补充应急说明 | 200 |
| test_list_modifications | 获取修改记录列表 | 200 |

### 复盘报告接口

文件：`backend/tests/api/test_retrospectives.py`（407 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_create_retrospective | 创建复盘报告 | 201 |
| test_update_retrospective | 填写报告内容 | 200 |
| test_submit_retrospective_success | 所有校验通过提交归档 | 200 |
| test_submit_no_final_strategy | 无最终版本（EC-8） | 400 |
| test_submit_pending_modification | PENDING_APPROVAL 临场修改（EC-5） | 400 |
| test_submit_unhandled_emergency | 未补说明应急执行（EC-5） | 400 |
| test_submit_rejected_modification_ok | REJECTED 临场修改不阻断（EC-5） | 200 |
| test_submit_missing_required_field | 必填项为空 | 400，含字段名 |
| test_get_retrospective | 获取复盘报告 | 200 |

### 整改事项接口

文件：`backend/tests/api/test_rectifications.py`（464 行）

| 测试方法 | 场景 | 期望结果 |
|---------|------|---------|
| test_create_rectification_item | 创建整改事项 | 201 |
| test_create_without_measures | measures 为空 | 400 |
| test_create_without_due_date | due_date 为空 | 400 |
| test_list_rectification_items | 获取整改事项列表 | 200 |
| test_update_status_by_assignee | 责任人更新状态 | 200 |
| test_update_status_forbidden | 非责任人更新 | 403 |
| test_upload_evidence | 上传完成证据 | 200 |
| test_confirm_completion | 复盘负责人确认完成 | 200 |
| test_confirm_without_evidence | 无完成证据确认 | 400 |
| test_close_by_business_owner | 业务负责人关闭整改事项 | 200 |

---

## Edge Case 测试

文件：`backend/tests/edge_cases/test_edge_cases.py`（665 行）

| EC | 测试类 | 覆盖场景 |
|----|--------|---------|
| EC-1 | TestEC1StrategyStateIllegalTransition | CONFIRMED/FINAL 不允许直接修改；VOIDED 不可物理删除 |
| EC-2 | TestEC2RedLineFieldChange | 6个红线字段任意变更触发重新确认；未走确认流程拒绝提交 |
| EC-3 | TestEC3DualReviewSameUser | 配置人=复核人返回 400，错误信息精确 |
| EC-4 | TestEC4ExecuteWithoutReview | 复核未通过时标记可执行返回 400 |
| EC-5 | TestEC5ModificationControlMissing | PENDING_APPROVAL 阻断；PENDING_REVIEW 阻断；应急未补说明阻断；REJECTED 不阻断 |
| EC-6 | TestEC6ConcurrentConflict | 乐观锁 version 不匹配返回 409；成功更新后 version 自增 |
| EC-7 | TestEC7ExecutedVersionImmutable | FINAL+已执行版本不允许回滚或修改内容 |
| EC-8 | TestEC8RetrospectiveNoFinalStrategy | 无 FINAL 版本提交复盘返回 400 |
| EC-9 | TestEC9DuplicateVersionCode | 同项目同日期版本号重复返回 409 |
| EC-10 | TestEC10SoftBlockHistoryAnalysis | 历史分析未确认提示但不强制阻断（返回 200 含 warning） |
| EC-11 | TestEC11MonitorDataFeedAnomaly | 回传异常标记 anomaly 状态，关联执行日志 |
| EC-12 | TestEC12ModificationWithoutApproval | 红线字段修改未走审批流程返回 400；reason 为空返回 400 |

---

## 前端测试

> 完整测试代码见各文件，使用 Vitest + Vue Test Utils。

| 文件 | 路径 | 测试数 | 覆盖重点 |
|------|------|--------|---------|
| LoginView.test.ts | `frontend/tests/` | 3 | 表单校验、登录跳转、错误提示 |
| StrategyFormView.test.ts | `frontend/tests/` | 5 | EMERGENCY 字段显示、红线提示、CONFIRMED 禁用编辑 |
| TaskConfigView.test.ts | `frontend/tests/` | 3 | 9字段表单、截图上传、确认弹窗 |
| ReviewView.test.ts | `frontend/tests/` | 3 | 13项清单、未全勾选禁用提交、同人错误提示 |
| ModificationView.test.ts | `frontend/tests/` | 4 | 角色差异渲染（交易员/策略负责人/复核人）、REJECTED 状态展示 |
| RetrospectiveView.test.ts | `frontend/tests/` | 3 | 11项必填、应急说明条件显示、提交失败字段提示 |
| RectificationView.test.ts | `frontend/tests/` | 3 | 状态分组列表、必填校验、角色权限按钮 |

---

## 测试覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|-----------|------|
| 后端 services（状态机/校验） | ≥ 95% | 核心业务逻辑，必须高覆盖 |
| 后端 API 集成测试 | ≥ 85% | 接口契约和权限校验 |
| Edge Cases（EC-1~12） | 100% | 每个 EC 至少一个正向+一个负向用例 |
| 前端组件测试 | ≥ 80% | 关键交互和角色权限渲染 |
| 前端 E2E（Playwright） | 关键路径 | 登录→策略→复核→执行→复盘完整流程 |

### 运行命令

```bash
# 后端单元测试
cd backend && pytest tests/unit/ -v

# 后端 API 集成测试（需要测试数据库）
cd backend && pytest tests/api/ -v

# Edge Case 测试
cd backend && pytest tests/edge_cases/ -v

# 全量后端测试 + 覆盖率报告
cd backend && pytest --cov=app --cov-report=html --cov-report=term-missing

# 前端组件测试
cd frontend && npx vitest run

# 前端覆盖率报告
cd frontend && npx vitest run --coverage

# 前端 E2E 测试
cd frontend && npx playwright test
```

### 测试数据库初始化

```bash
# 创建测试数据库
createdb auction_test

# 运行迁移
cd backend && DATABASE_URL=postgresql+asyncpg://test:test@localhost/auction_test \
  alembic upgrade head
```
