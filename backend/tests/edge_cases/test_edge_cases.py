"""
Edge Case 测试套件 — 竞拍工作审批平台
覆盖 EC-1 到 EC-12 全部边界场景
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------

@pytest.fixture
def confirmed_strategy():
    """已确认状态的策略版本（不可直接修改）"""
    return {
        "id": "strat-001",
        "version": "重庆忠润_20260428_v1.0",
        "status": "CONFIRMED",
        "price": 100.0,
        "quantity": 500,
        "submit_time": "09:30",
        "trigger_condition": "价格低于95时触发",
        "fallback_plan": "保底方案A",
        "risk_description": "市场波动风险",
        "approval_status": "APPROVED",
        "optimistic_lock_version": 3,
    }


@pytest.fixture
def final_strategy():
    """最终状态的策略版本（不可直接修改）"""
    return {
        "id": "strat-002",
        "version": "重庆忠润_20260428_v2.0",
        "status": "FINAL",
        "price": 105.0,
        "quantity": 600,
        "submit_time": "10:00",
        "trigger_condition": "价格低于100时触发",
        "fallback_plan": "保底方案B",
        "risk_description": "流动性风险",
        "approval_status": "APPROVED",
        "optimistic_lock_version": 5,
    }


@pytest.fixture
def draft_strategy():
    """草稿状态的策略版本（可修改）"""
    return {
        "id": "strat-003",
        "version": "重庆忠润_20260428_v3.0",
        "status": "DRAFT",
        "price": 98.0,
        "quantity": 400,
        "submit_time": "11:00",
        "trigger_condition": "价格低于90时触发",
        "fallback_plan": "保底方案C",
        "risk_description": "操作风险",
        "approval_status": "PENDING",
        "optimistic_lock_version": 1,
    }


@pytest.fixture
def executed_strategy():
    """已执行状态的策略版本（不可回滚或修改）"""
    return {
        "id": "strat-004",
        "version": "重庆忠润_20260428_v1.0",
        "status": "EXECUTED",
        "price": 100.0,
        "quantity": 500,
        "optimistic_lock_version": 7,
    }


# ---------------------------------------------------------------------------
# EC-1：CONFIRMED/FINAL 状态版本不允许直接修改内容
# ---------------------------------------------------------------------------

class TestEC1ConfirmedFinalImmutable:

    @pytest.mark.asyncio
    async def test_confirmed_strategy_rejects_direct_edit(
        self, async_client: AsyncClient, confirmed_strategy
    ):
        """CONFIRMED 状态版本直接修改内容应返回 403"""
        response = await async_client.patch(
            f"/api/strategies/{confirmed_strategy['id']}",
            json={"price": 110.0},
        )
        assert response.status_code == 403
        assert "CONFIRMED" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_final_strategy_rejects_direct_edit(
        self, async_client: AsyncClient, final_strategy
    ):
        """FINAL 状态版本直接修改内容应返回 403"""
        response = await async_client.patch(
            f"/api/strategies/{final_strategy['id']}",
            json={"quantity": 700},
        )
        assert response.status_code == 403
        assert "FINAL" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_draft_strategy_allows_edit(
        self, async_client: AsyncClient, draft_strategy
    ):
        """DRAFT 状态版本允许修改，应返回 200"""
        response = await async_client.patch(
            f"/api/strategies/{draft_strategy['id']}",
            json={"price": 99.0},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# EC-2：红线字段变更必须触发重新确认流程
# ---------------------------------------------------------------------------

class TestEC2RedlineFieldsRequireReconfirmation:

    # 红线字段列表：价格、数量、申报时点、触发条件
    REDLINE_FIELDS = ["price", "quantity", "submit_time", "trigger_condition"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field,new_value", [
        ("price", 120.0),
        ("quantity", 800),
        ("submit_time", "14:00"),
        ("trigger_condition", "无条件触发"),
    ])
    async def test_redline_field_change_triggers_reconfirmation(
        self, async_client: AsyncClient, draft_strategy, field, new_value
    ):
        """修改红线字段后策略状态应重置为 PENDING_RECONFIRM"""
        response = await async_client.patch(
            f"/api/strategies/{draft_strategy['id']}",
            json={field: new_value},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PENDING_RECONFIRM", (
            f"修改红线字段 {field} 后状态应为 PENDING_RECONFIRM，实际为 {data['status']}"
        )
        assert data["reconfirmation_required"] is True

    @pytest.mark.asyncio
    async def test_non_redline_field_change_no_reconfirmation(
        self, async_client: AsyncClient, draft_strategy
    ):
        """修改非红线字段（如 risk_description）不应触发重新确认"""
        response = await async_client.patch(
            f"/api/strategies/{draft_strategy['id']}",
            json={"risk_description": "更新后的风险说明"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("reconfirmation_required") is not True


# ---------------------------------------------------------------------------
# EC-3：双人复核同一人拒绝
# ---------------------------------------------------------------------------

class TestEC3DualReviewSamePersonRejected:

    @pytest.mark.asyncio
    async def test_same_person_cannot_configure_and_review(
        self, async_client: AsyncClient
    ):
        """配置人与复核人相同时，复核操作应返回 403"""
        user_id = "user-alice"
        # 模拟 alice 既是配置人又尝试复核
        response = await async_client.post(
            "/api/reviews/",
            json={
                "strategy_id": "strat-003",
                "reviewer_id": user_id,
                "configurator_id": user_id,  # 同一人
                "checklist": [True] * 13,
            },
        )
        assert response.status_code == 403
        assert "双人复核" in response.json()["detail"] or "same person" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_different_persons_review_succeeds(
        self, async_client: AsyncClient
    ):
        """配置人与复核人不同时，复核操作应成功"""
        response = await async_client.post(
            "/api/reviews/",
            json={
                "strategy_id": "strat-003",
                "reviewer_id": "user-bob",
                "configurator_id": "user-alice",
                "checklist": [True] * 13,
            },
        )
        assert response.status_code in (200, 201)


# ---------------------------------------------------------------------------
# EC-4：未完成复核强行执行拒绝
# ---------------------------------------------------------------------------

class TestEC4ExecutionWithoutReviewRejected:

    @pytest.mark.asyncio
    async def test_execution_blocked_when_review_incomplete(
        self, async_client: AsyncClient
    ):
        """复核未完成时尝试执行策略应返回 403"""
        response = await async_client.post(
            "/api/executions/",
            json={
                "strategy_id": "strat-003",
                "executor_id": "user-trader",
            },
        )
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "复核" in detail or "review" in detail.lower()

    @pytest.mark.asyncio
    async def test_execution_allowed_after_review_complete(
        self, async_client: AsyncClient
    ):
        """复核完成后执行策略应成功（使用已复核的策略 ID）"""
        response = await async_client.post(
            "/api/executions/",
            json={
                "strategy_id": "strat-reviewed-001",  # 已完成复核的策略
                "executor_id": "user-trader",
            },
        )
        assert response.status_code in (200, 201)


# ---------------------------------------------------------------------------
# EC-5：临场修改管控
# ---------------------------------------------------------------------------

class TestEC5OnSiteModificationControl:

    @pytest.mark.asyncio
    async def test_pending_approval_blocks_onsite_modification(
        self, async_client: AsyncClient
    ):
        """PENDING_APPROVAL 状态下临场修改应被阻断，返回 403"""
        response = await async_client.post(
            "/api/modifications/",
            json={
                "strategy_id": "strat-pending-approval",
                "modification_type": "ONSITE",
                "reason": "市场突变",
                "new_price": 115.0,
            },
        )
        assert response.status_code == 403
        assert "PENDING_APPROVAL" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_pending_review_blocks_onsite_modification(
        self, async_client: AsyncClient
    ):
        """PENDING_REVIEW 状态下临场修改应被阻断，返回 403"""
        response = await async_client.post(
            "/api/modifications/",
            json={
                "strategy_id": "strat-pending-review",
                "modification_type": "ONSITE",
                "reason": "市场突变",
                "new_price": 115.0,
            },
        )
        assert response.status_code == 403
        assert "PENDING_REVIEW" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_emergency_without_explanation_blocked(
        self, async_client: AsyncClient
    ):
        """应急执行未填写说明时应被阻断，返回 422"""
        response = await async_client.post(
            "/api/modifications/",
            json={
                "strategy_id": "strat-003",
                "modification_type": "EMERGENCY",
                # 缺少 emergency_reason 字段
                "new_price": 115.0,
            },
        )
        assert response.status_code == 422
        errors = response.json()["detail"]
        field_names = [e["loc"][-1] for e in errors] if isinstance(errors, list) else []
        assert "emergency_reason" in field_names or "emergency" in str(errors).lower()

    @pytest.mark.asyncio
    async def test_rejected_status_does_not_block_modification(
        self, async_client: AsyncClient
    ):
        """REJECTED 状态下允许提交新的修改申请，不应阻断"""
        response = await async_client.post(
            "/api/modifications/",
            json={
                "strategy_id": "strat-rejected-001",
                "modification_type": "NORMAL",
                "reason": "重新申请修改",
                "new_price": 108.0,
            },
        )
        # REJECTED 状态不阻断，应允许提交
        assert response.status_code in (200, 201)


# ---------------------------------------------------------------------------
# EC-6：并发操作乐观锁冲突
# ---------------------------------------------------------------------------

class TestEC6OptimisticLockConflict:

    @pytest.mark.asyncio
    async def test_stale_version_returns_409(
        self, async_client: AsyncClient, confirmed_strategy
    ):
        """提交过期的 version 字段时应返回 409 Conflict"""
        stale_version = confirmed_strategy["optimistic_lock_version"] - 1
        response = await async_client.patch(
            f"/api/strategies/{confirmed_strategy['id']}",
            json={
                "price": 110.0,
                "optimistic_lock_version": stale_version,  # 过期版本号
            },
        )
        assert response.status_code == 409
        assert "conflict" in response.json()["detail"].lower() or "版本冲突" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_correct_version_succeeds(
        self, async_client: AsyncClient, draft_strategy
    ):
        """提交正确的 version 字段时应成功更新"""
        response = await async_client.patch(
            f"/api/strategies/{draft_strategy['id']}",
            json={
                "risk_description": "更新说明",
                "optimistic_lock_version": draft_strategy["optimistic_lock_version"],
            },
        )
        assert response.status_code == 200
        # 更新后版本号应自增
        assert response.json()["optimistic_lock_version"] == draft_strategy["optimistic_lock_version"] + 1


# ---------------------------------------------------------------------------
# EC-7：已执行版本不允许回滚或修改
# ---------------------------------------------------------------------------

class TestEC7ExecutedVersionImmutable:

    @pytest.mark.asyncio
    async def test_executed_strategy_rejects_modification(
        self, async_client: AsyncClient, executed_strategy
    ):
        """EXECUTED 状态版本修改应返回 403"""
        response = await async_client.patch(
            f"/api/strategies/{executed_strategy['id']}",
            json={"price": 95.0},
        )
        assert response.status_code == 403
        assert "EXECUTED" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_executed_strategy_rejects_rollback(
        self, async_client: AsyncClient, executed_strategy
    ):
        """EXECUTED 状态版本回滚应返回 403"""
        response = await async_client.post(
            f"/api/strategies/{executed_strategy['id']}/rollback",
        )
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "回滚" in detail or "rollback" in detail.lower()


# ---------------------------------------------------------------------------
# EC-8：复盘报告无最终版本拒绝提交
# ---------------------------------------------------------------------------

class TestEC8RetrospectiveRequiresFinalVersion:

    @pytest.mark.asyncio
    async def test_retrospective_rejected_without_final_version(
        self, async_client: AsyncClient
    ):
        """无最终版本策略时提交复盘报告应返回 422"""
        response = await async_client.post(
            "/api/retrospectives/",
            json={
                "auction_id": "auction-no-final",  # 该竞拍无 FINAL 版本
                "summary": "本次竞拍总结",
                "lessons_learned": "经验教训",
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "最终版本" in detail or "FINAL" in detail

    @pytest.mark.asyncio
    async def test_retrospective_allowed_with_final_version(
        self, async_client: AsyncClient
    ):
        """存在最终版本策略时提交复盘报告应成功"""
        response = await async_client.post(
            "/api/retrospectives/",
            json={
                "auction_id": "auction-with-final",  # 该竞拍有 FINAL 版本
                "summary": "本次竞拍总结",
                "lessons_learned": "经验教训",
                "result_analysis": "结果分析",
                "strategy_evaluation": "策略评估",
            },
        )
        assert response.status_code in (200, 201)


# ---------------------------------------------------------------------------
# EC-9：版本号重复拒绝创建
# ---------------------------------------------------------------------------

class TestEC9DuplicateVersionRejected:

    @pytest.mark.asyncio
    async def test_duplicate_version_string_returns_409(
        self, async_client: AsyncClient
    ):
        """创建已存在版本号的策略应返回 409"""
        payload = {
            "version": "重庆忠润_20260428_v1.0",  # 已存在的版本号
            "price": 100.0,
            "quantity": 500,
            "submit_time": "09:30",
            "trigger_condition": "价格低于95时触发",
            "fallback_plan": "保底方案A",
            "risk_description": "市场波动风险",
        }
        response = await async_client.post("/api/strategies/", json=payload)
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "版本号" in detail or "version" in detail.lower()

    @pytest.mark.asyncio
    async def test_unique_version_string_creates_successfully(
        self, async_client: AsyncClient
    ):
        """创建唯一版本号的策略应成功"""
        payload = {
            "version": "重庆忠润_20260428_v99.0",  # 唯一版本号
            "price": 100.0,
            "quantity": 500,
            "submit_time": "09:30",
            "trigger_condition": "价格低于95时触发",
            "fallback_plan": "保底方案A",
            "risk_description": "市场波动风险",
        }
        response = await async_client.post("/api/strategies/", json=payload)
        assert response.status_code in (200, 201)


# ---------------------------------------------------------------------------
# EC-10：历史分析未完成软阻断（提示但不强制）
# ---------------------------------------------------------------------------

class TestEC10HistoricalAnalysisSoftBlock:

    @pytest.mark.asyncio
    async def test_strategy_creation_warns_when_analysis_incomplete(
        self, async_client: AsyncClient
    ):
        """历史分析未完成时创建策略应返回 200 但携带警告信息"""
        response = await async_client.post(
            "/api/strategies/",
            json={
                "version": "重庆忠润_20260429_v1.0",
                "auction_id": "auction-no-analysis",  # 该竞拍历史分析未完成
                "price": 100.0,
                "quantity": 500,
                "submit_time": "09:30",
                "trigger_condition": "价格低于95时触发",
                "fallback_plan": "保底方案A",
                "risk_description": "市场波动风险",
            },
        )
        # 软阻断：不强制拒绝，但返回警告
        assert response.status_code in (200, 201)
        data = response.json()
        assert data.get("warnings") is not None
        warnings = data["warnings"]
        assert any("历史分析" in w or "historical_analysis" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_strategy_creation_no_warning_when_analysis_complete(
        self, async_client: AsyncClient
    ):
        """历史分析已完成时创建策略不应携带警告"""
        response = await async_client.post(
            "/api/strategies/",
            json={
                "version": "重庆忠润_20260429_v2.0",
                "auction_id": "auction-with-analysis",  # 历史分析已完成
                "price": 100.0,
                "quantity": 500,
                "submit_time": "09:30",
                "trigger_condition": "价格低于95时触发",
                "fallback_plan": "保底方案A",
                "risk_description": "市场波动风险",
            },
        )
        assert response.status_code in (200, 201)
        data = response.json()
        warnings = data.get("warnings", [])
        assert not any("历史分析" in w for w in warnings)


# ---------------------------------------------------------------------------
# EC-11：监控数据回传异常标记
# ---------------------------------------------------------------------------

class TestEC11MonitoringDataAnomalyMarking:

    @pytest.mark.asyncio
    async def test_anomaly_data_gets_flagged(
        self, async_client: AsyncClient
    ):
        """回传的监控数据超出阈值时应被标记为异常"""
        response = await async_client.post(
            "/api/monitoring/data",
            json={
                "auction_id": "auction-001",
                "timestamp": "2026-04-28T10:05:00",
                "actual_price": 200.0,   # 远超预期价格，触发异常
                "expected_price": 100.0,
                "actual_quantity": 500,
            },
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["is_anomaly"] is True
        assert data["anomaly_type"] is not None

    @pytest.mark.asyncio
    async def test_normal_data_not_flagged(
        self, async_client: AsyncClient
    ):
        """正常范围内的监控数据不应被标记为异常"""
        response = await async_client.post(
            "/api/monitoring/data",
            json={
                "auction_id": "auction-001",
                "timestamp": "2026-04-28T10:05:00",
                "actual_price": 101.0,   # 在正常偏差范围内
                "expected_price": 100.0,
                "actual_quantity": 500,
            },
        )
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["is_anomaly"] is False

    @pytest.mark.asyncio
    async def test_anomaly_triggers_alert(
        self, async_client: AsyncClient
    ):
        """异常数据回传后应触发告警记录"""
        with patch("app.services.alert_service.send_alert", new_callable=AsyncMock) as mock_alert:
            await async_client.post(
                "/api/monitoring/data",
                json={
                    "auction_id": "auction-001",
                    "timestamp": "2026-04-28T10:05:00",
                    "actual_price": 200.0,
                    "expected_price": 100.0,
                    "actual_quantity": 500,
                },
            )
            mock_alert.assert_called_once()


# ---------------------------------------------------------------------------
# EC-12：异常修改未走审批流程直接执行拒绝
# ---------------------------------------------------------------------------

class TestEC12AbnormalModificationRequiresApproval:

    @pytest.mark.asyncio
    async def test_unapproved_modification_execution_rejected(
        self, async_client: AsyncClient
    ):
        """未经审批的异常修改直接执行应返回 403"""
        response = await async_client.post(
            "/api/executions/",
            json={
                "strategy_id": "strat-modified-unapproved",  # 有未审批的修改
                "executor_id": "user-trader",
                "skip_approval_check": False,
            },
        )
        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "审批" in detail or "approval" in detail.lower()

    @pytest.mark.asyncio
    async def test_approved_modification_execution_allowed(
        self, async_client: AsyncClient
    ):
        """经过审批的异常修改可以正常执行"""
        response = await async_client.post(
            "/api/executions/",
            json={
                "strategy_id": "strat-modified-approved",  # 修改已审批
                "executor_id": "user-trader",
            },
        )
        assert response.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_emergency_execution_requires_post_hoc_explanation(
        self, async_client: AsyncClient
    ):
        """应急执行后必须补充说明，否则后续操作应被阻断"""
        # 应急执行（绕过审批）
        exec_response = await async_client.post(
            "/api/executions/",
            json={
                "strategy_id": "strat-003",
                "executor_id": "user-trader",
                "execution_type": "EMERGENCY",
                "emergency_reason": "市场极端波动，无法等待审批",
            },
        )
        assert exec_response.status_code in (200, 201)
        execution_id = exec_response.json()["id"]

        # 未补充说明时，后续复盘提交应被阻断
        retro_response = await async_client.post(
            "/api/retrospectives/",
            json={
                "auction_id": "auction-001",
                "execution_id": execution_id,
                "summary": "复盘总结",
                # 缺少 emergency_post_explanation
            },
        )
        assert retro_response.status_code == 422
        detail = retro_response.json()["detail"]
        assert "应急" in str(detail) or "emergency" in str(detail).lower()
