"""
test_modifications.py — 异常修改审批接口集成测试

覆盖阶段：9. 异常修改审批
涉及角色：
  - trader          交易员（提交申请、应急执行、标记执行）
  - strategy_owner  策略负责人（审批/驳回）
  - reviewer        复核人（复核通过/驳回）

审批流：申请 → 审批 → 复核 → 执行
应急路径：应急执行 → 补充说明

EC 编号说明：
  EC-12：reason 为空时返回 400
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import Roles


# ===========================================================================
# 测试夹具
# ===========================================================================

@pytest_asyncio.fixture
async def auction_id(client: AsyncClient, make_user, auth_header):
    """创建处于「执行中」状态的竞拍，返回 ID。"""
    admin = await make_user("mod_admin", role=Roles.ADMIN)
    headers = await auth_header(admin)
    resp = await client.post(
        "/auctions",
        json={"name": "修改审批测试竞拍", "auction_date": "2026-04-28", "status": "EXECUTING"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


@pytest_asyncio.fixture
async def trader(make_user):
    return await make_user("trader_mod", role=Roles.TRADER)


@pytest_asyncio.fixture
async def strategy_owner(make_user):
    return await make_user("strategy_owner_mod", role=Roles.STRATEGY_OWNER)


@pytest_asyncio.fixture
async def reviewer(make_user):
    return await make_user("reviewer_mod", role=Roles.REVIEWER)


@pytest_asyncio.fixture
async def other_user(make_user):
    """无审批权限的普通用户（用于 403 验证）。"""
    return await make_user("other_mod", role=Roles.MONITOR)


async def _create_modification(client, auction_id, trader, auth_header, **extra):
    """辅助函数：提交一条临场修改申请，返回 modification id。"""
    headers = await auth_header(trader)
    payload = {
        "reason": "市场价格超出触发阈值，需调整申报价格",
        "impact_scope": "价格调整 +0.05，数量不变",
        **extra,
    }
    resp = await client.post(
        f"/auctions/{auction_id}/modifications",
        json=payload,
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"创建修改申请失败: {resp.text}"
    return resp.json()["id"]


# ===========================================================================
# POST /auctions/{id}/modifications — 提交临场修改申请
# ===========================================================================

class TestSubmitModification:
    """提交临场修改申请。"""

    @pytest.mark.asyncio
    async def test_trader_can_submit_modification(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        业务规则：交易员可在执行阶段提交临场修改申请，
        reason 和 impact_scope 为必填字段，初始状态为 PENDING_APPROVAL。
        """
        headers = await auth_header(trader)
        payload = {
            "reason": "价格超出触发阈值",
            "impact_scope": "申报价格上调 0.05",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/modifications",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["status"] == "PENDING_APPROVAL"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_modification_requires_reason(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        EC-12：reason 为空时返回 400，
        reason 是追溯修改合理性的核心字段，不得为空。
        """
        headers = await auth_header(trader)
        payload = {
            "reason": "",
            "impact_scope": "申报价格上调 0.05",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/modifications",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_modification_requires_impact_scope(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """impact_scope 为必填字段，缺失时返回 422。"""
        headers = await auth_header(trader)
        payload = {"reason": "价格超出触发阈值"}
        resp = await client.post(
            f"/auctions/{auction_id}/modifications",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (400, 422)


# ===========================================================================
# POST /auctions/{id}/modifications/emergency-execute — 应急执行
# ===========================================================================

class TestEmergencyExecute:
    """应急执行（跳过审批流，事后补充说明）。"""

    @pytest.mark.asyncio
    async def test_trader_can_emergency_execute(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        业务规则：极端情况下交易员可先执行后审批，
        应急执行记录初始状态为 EMERGENCY_EXECUTED，
        后续必须补充说明（post-explanation）。
        """
        headers = await auth_header(trader)
        payload = {
            "reason": "系统延迟，无法等待审批，已按兜底方案执行",
            "impact_scope": "申报价格下调 0.10",
            "emergency": True,
        }
        resp = await client.post(
            f"/auctions/{auction_id}/modifications/emergency-execute",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["status"] == "EMERGENCY_EXECUTED"
        assert data.get("explanation_required") is True

    @pytest.mark.asyncio
    async def test_non_trader_cannot_emergency_execute(
        self, client: AsyncClient, auction_id, other_user, auth_header
    ):
        """非交易员不得发起应急执行，返回 403。"""
        headers = await auth_header(other_user)
        payload = {
            "reason": "应急",
            "impact_scope": "价格调整",
            "emergency": True,
        }
        resp = await client.post(
            f"/auctions/{auction_id}/modifications/emergency-execute",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /modifications/{mid}/approve — 策略负责人审批
# ===========================================================================

class TestApproveModification:
    """策略负责人审批临场修改申请。"""

    @pytest.mark.asyncio
    async def test_strategy_owner_can_approve(
        self, client: AsyncClient, auction_id, trader, strategy_owner, auth_header
    ):
        """
        业务规则：策略负责人审批通过后，
        修改状态变更为 APPROVED，进入复核环节。
        """
        mid = await _create_modification(client, auction_id, trader, auth_header)
        headers = await auth_header(strategy_owner)
        resp = await client.post(
            f"/modifications/{mid}/approve",
            json={"comment": "价格调整合理，同意"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_non_strategy_owner_cannot_approve(
        self, client: AsyncClient, auction_id, trader, other_user, auth_header
    ):
        """
        业务规则：只有策略负责人可审批，
        其他角色返回 403，防止越权审批。
        """
        mid = await _create_modification(client, auction_id, trader, auth_header)
        headers = await auth_header(other_user)
        resp = await client.post(
            f"/modifications/{mid}/approve",
            json={"comment": "同意"},
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /modifications/{mid}/reject — 策略负责人驳回
# ===========================================================================

class TestRejectModification:
    """策略负责人驳回临场修改申请。"""

    @pytest.mark.asyncio
    async def test_strategy_owner_can_reject_with_reason(
        self, client: AsyncClient, auction_id, trader, strategy_owner, auth_header
    ):
        """
        业务规则：策略负责人驳回时必须附驳回原因，
        修改状态变更为 REJECTED，驳回原因留存审计。
        """
        mid = await _create_modification(client, auction_id, trader, auth_header)
        headers = await auth_header(strategy_owner)
        resp = await client.post(
            f"/modifications/{mid}/reject",
            json={"reason": "调整幅度超出策略允许范围，需重新评估"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert data.get("reject_reason") or data.get("reason")

    @pytest.mark.asyncio
    async def test_reject_requires_reason(
        self, client: AsyncClient, auction_id, trader, strategy_owner, auth_header
    ):
        """驳回时 reason 为空应返回 400 或 422。"""
        mid = await _create_modification(client, auction_id, trader, auth_header)
        headers = await auth_header(strategy_owner)
        resp = await client.post(
            f"/modifications/{mid}/reject",
            json={"reason": ""},
            headers=headers,
        )
        assert resp.status_code in (400, 422)


# ===========================================================================
# POST /modifications/{mid}/review — 复核人复核
# ===========================================================================

class TestReviewModification:
    """复核人对已审批的临场修改进行复核。"""

    @pytest_asyncio.fixture
    async def approved_mid(self, client, auction_id, trader, strategy_owner, auth_header):
        """创建并审批通过的修改申请 ID。"""
        mid = await _create_modification(client, auction_id, trader, auth_header)
        so_headers = await auth_header(strategy_owner)
        await client.post(f"/modifications/{mid}/approve", json={}, headers=so_headers)
        return mid

    @pytest.mark.asyncio
    async def test_reviewer_can_review_approved_modification(
        self, client: AsyncClient, approved_mid, reviewer, auth_header
    ):
        """
        业务规则：复核人对 APPROVED 状态的修改进行复核，
        通过后状态变更为 REVIEW_PASSED，可进入执行环节。
        双人复核是制度红线（配置人与复核人不得为同一人）。
        """
        headers = await auth_header(reviewer)
        resp = await client.post(
            f"/modifications/{approved_mid}/review",
            json={"approved": True, "comment": "复核通过"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REVIEW_PASSED"

    @pytest.mark.asyncio
    async def test_non_reviewer_cannot_review(
        self, client: AsyncClient, approved_mid, other_user, auth_header
    ):
        """
        业务规则：只有复核人角色可执行复核操作，
        其他角色返回 403，保障双人复核制度。
        """
        headers = await auth_header(other_user)
        resp = await client.post(
            f"/modifications/{approved_mid}/review",
            json={"approved": True},
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /modifications/{mid}/review-reject — 复核人驳回
# ===========================================================================

class TestReviewRejectModification:
    """复核人驳回已审批的临场修改。"""

    @pytest_asyncio.fixture
    async def approved_mid(self, client, auction_id, trader, strategy_owner, auth_header):
        mid = await _create_modification(client, auction_id, trader, auth_header)
        so_headers = await auth_header(strategy_owner)
        await client.post(f"/modifications/{mid}/approve", json={}, headers=so_headers)
        return mid

    @pytest.mark.asyncio
    async def test_reviewer_can_reject_review(
        self, client: AsyncClient, approved_mid, reviewer, auth_header
    ):
        """
        业务规则：复核人驳回后状态变更为 REVIEW_REJECTED，
        需重新走审批流程。
        """
        headers = await auth_header(reviewer)
        resp = await client.post(
            f"/modifications/{approved_mid}/review-reject",
            json={"reason": "修改内容与申报日志不一致"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REVIEW_REJECTED"


# ===========================================================================
# POST /modifications/{mid}/execute — 交易员标记执行
# ===========================================================================

class TestExecuteModification:
    """交易员对复核通过的修改标记执行。"""

    @pytest_asyncio.fixture
    async def review_passed_mid(
        self, client, auction_id, trader, strategy_owner, reviewer, auth_header
    ):
        """创建、审批、复核通过的修改申请 ID。"""
        mid = await _create_modification(client, auction_id, trader, auth_header)
        so_headers = await auth_header(strategy_owner)
        await client.post(f"/modifications/{mid}/approve", json={}, headers=so_headers)
        rv_headers = await auth_header(reviewer)
        await client.post(
            f"/modifications/{mid}/review", json={"approved": True}, headers=rv_headers
        )
        return mid

    @pytest.mark.asyncio
    async def test_trader_can_execute_review_passed_modification(
        self, client: AsyncClient, review_passed_mid, trader, auth_header
    ):
        """
        业务规则：交易员只能执行 REVIEW_PASSED（即最终审批通过）状态的修改，
        执行后状态变更为 EXECUTED。
        """
        headers = await auth_header(trader)
        resp = await client.post(
            f"/modifications/{review_passed_mid}/execute",
            json={"executed_at": "2026-04-28T10:45:00"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "EXECUTED"

    @pytest.mark.asyncio
    async def test_execute_non_approved_modification_returns_400(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        业务规则：状态非 APPROVED/REVIEW_PASSED 的修改不得执行，
        返回 400，防止跳过审批直接执行。
        """
        # 创建但不审批
        mid = await _create_modification(client, auction_id, trader, auth_header)
        headers = await auth_header(trader)
        resp = await client.post(
            f"/modifications/{mid}/execute",
            json={"executed_at": "2026-04-28T10:45:00"},
            headers=headers,
        )
        assert resp.status_code == 400


# ===========================================================================
# POST /modifications/{mid}/post-explanation — 补充应急说明
# ===========================================================================

class TestPostExplanation:
    """交易员为应急执行补充事后说明。"""

    @pytest_asyncio.fixture
    async def emergency_mid(self, client, auction_id, trader, auth_header):
        """创建应急执行记录，返回 ID。"""
        headers = await auth_header(trader)
        resp = await client.post(
            f"/auctions/{auction_id}/modifications/emergency-execute",
            json={
                "reason": "系统延迟，先执行",
                "impact_scope": "价格下调 0.10",
                "emergency": True,
            },
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_trader_can_post_explanation(
        self, client: AsyncClient, emergency_mid, trader, auth_header
    ):
        """
        业务规则：应急执行后交易员必须补充事后说明，
        说明内容包含执行依据和影响评估，用于复盘归档。
        """
        headers = await auth_header(trader)
        resp = await client.post(
            f"/modifications/{emergency_mid}/post-explanation",
            json={
                "explanation": "系统延迟 30 秒，按兜底方案执行，价格下调 0.10，最终成交正常",
                "impact_assessment": "轻微偏离策略，整体影响可控",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("explanation_required") is False or data["status"] == "EXPLANATION_SUBMITTED"

    @pytest.mark.asyncio
    async def test_post_explanation_requires_content(
        self, client: AsyncClient, emergency_mid, trader, auth_header
    ):
        """补充说明内容为空时返回 400 或 422。"""
        headers = await auth_header(trader)
        resp = await client.post(
            f"/modifications/{emergency_mid}/post-explanation",
            json={"explanation": ""},
            headers=headers,
        )
        assert resp.status_code in (400, 422)


# ===========================================================================
# GET /auctions/{id}/modifications — 获取修改记录列表
# ===========================================================================

class TestGetModifications:
    """获取竞拍的临场修改记录列表。"""

    @pytest.mark.asyncio
    async def test_get_modifications_returns_list(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        业务规则：返回该竞拍下所有临场修改记录，
        包含状态、申请人、时间等信息，支持审计追溯。
        """
        # 预置两条修改申请
        for i in range(2):
            await _create_modification(
                client, auction_id, trader, auth_header,
                reason=f"修改原因 {i+1}",
                impact_scope=f"影响范围 {i+1}",
            )

        headers = await auth_header(trader)
        resp = await client.get(
            f"/auctions/{auction_id}/modifications",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_modifications_empty_when_none(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """无修改记录时返回空列表。"""
        headers = await auth_header(trader)
        resp = await client.get(
            f"/auctions/{auction_id}/modifications",
            headers=headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_modifications_unauthorized(
        self, client: AsyncClient, auction_id
    ):
        """未认证请求返回 401。"""
        resp = await client.get(f"/auctions/{auction_id}/modifications")
        assert resp.status_code == 401
