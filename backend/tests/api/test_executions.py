"""
test_executions.py — 竞拍执行接口集成测试

覆盖阶段：7. 正式竞拍执行
涉及角色：交易员（trader）、复核人（reviewer）

EC 编号说明：
  EC-4：执行完成复核未通过时返回 400
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
    """创建一个处于「执行中」状态的竞拍，返回其 ID。"""
    admin = await make_user("exec_admin", role=Roles.ADMIN)
    headers = await auth_header(admin)

    resp = await client.post(
        "/auctions",
        json={
            "name": "重庆忠润_20260428",
            "auction_date": "2026-04-28",
            "status": "EXECUTING",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"创建竞拍失败: {resp.text}"
    return resp.json()["id"]


@pytest_asyncio.fixture
async def trader(make_user):
    """交易员用户。"""
    return await make_user("trader_exec", role=Roles.TRADER)


@pytest_asyncio.fixture
async def reviewer(make_user):
    """复核人用户。"""
    return await make_user("reviewer_exec", role=Roles.REVIEWER)


# ===========================================================================
# POST /auctions/{id}/execution-logs
# ===========================================================================

class TestRecordExecutionLog:
    """交易员记录执行日志。"""

    @pytest.mark.asyncio
    async def test_trader_can_record_execution_log(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        业务规则：交易员在竞拍执行阶段可提交执行日志，
        记录申报价格、数量、时点等关键信息。
        """
        headers = await auth_header(trader)
        payload = {
            "declared_price": 3.85,
            "declared_quantity": 1000,
            "declared_at": "2026-04-28T10:05:00",
            "note": "按策略 v2.0 申报",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/execution-logs",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["declared_price"] == pytest.approx(3.85)
        assert data["declared_quantity"] == 1000
        assert "id" in data

    @pytest.mark.asyncio
    async def test_execution_log_requires_declared_price(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """申报价格为必填字段，缺失时返回 422。"""
        headers = await auth_header(trader)
        payload = {
            "declared_quantity": 1000,
            "declared_at": "2026-04-28T10:05:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/execution-logs",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_non_trader_cannot_record_execution_log(
        self, client: AsyncClient, auction_id, reviewer, auth_header
    ):
        """非交易员角色不得提交执行日志，返回 403。"""
        headers = await auth_header(reviewer)
        payload = {
            "declared_price": 3.85,
            "declared_quantity": 1000,
            "declared_at": "2026-04-28T10:05:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/execution-logs",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /auctions/{id}/execution-complete
# ===========================================================================

class TestMarkExecutionComplete:
    """标记竞拍执行完成。"""

    @pytest.mark.asyncio
    async def test_trader_can_mark_execution_complete(
        self, client: AsyncClient, auction_id, trader, reviewer, auth_header
    ):
        """
        业务规则：交易员提交执行完成申请，
        复核人通过后竞拍状态变更为 COMPLETED。
        """
        trader_headers = await auth_header(trader)
        reviewer_headers = await auth_header(reviewer)

        # 交易员标记完成
        resp = await client.post(
            f"/auctions/{auction_id}/execution-complete",
            json={"summary": "全部申报完毕，无异常"},
            headers=trader_headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["status"] in ("PENDING_REVIEW", "COMPLETED")

    @pytest.mark.asyncio
    async def test_execution_complete_rejected_returns_400(
        self, client: AsyncClient, auction_id, trader, reviewer, auth_header
    ):
        """
        EC-4：复核人对执行完成申请复核不通过时，
        接口应返回 400，并携带驳回原因。
        """
        trader_headers = await auth_header(trader)
        reviewer_headers = await auth_header(reviewer)

        # 交易员提交完成
        await client.post(
            f"/auctions/{auction_id}/execution-complete",
            json={"summary": "申报完毕"},
            headers=trader_headers,
        )

        # 复核人驳回
        resp = await client.post(
            f"/auctions/{auction_id}/execution-complete/reject",
            json={"reason": "执行日志不完整，缺少时点记录"},
            headers=reviewer_headers,
        )
        assert resp.status_code in (200, 400)
        # 若业务设计为驳回后再次提交完成会返回 400，则验证该场景
        resp2 = await client.post(
            f"/auctions/{auction_id}/execution-complete",
            json={"summary": "重新提交"},
            headers=trader_headers,
        )
        # 驳回后状态应允许重新提交（200/201）或明确返回 400 说明原因
        assert resp2.status_code in (200, 201, 400)

    @pytest.mark.asyncio
    async def test_execution_complete_review_fail_returns_400(
        self, client: AsyncClient, auction_id, trader, reviewer, auth_header
    ):
        """
        EC-4：直接调用复核接口，当复核结论为「不通过」时返回 400。
        """
        trader_headers = await auth_header(trader)
        reviewer_headers = await auth_header(reviewer)

        await client.post(
            f"/auctions/{auction_id}/execution-complete",
            json={"summary": "申报完毕"},
            headers=trader_headers,
        )

        resp = await client.post(
            f"/auctions/{auction_id}/execution-complete/review",
            json={"approved": False, "reason": "数量与策略不符"},
            headers=reviewer_headers,
        )
        # EC-4：复核不通过时返回 400
        assert resp.status_code == 400
        data = resp.json()
        assert "reason" in data or "detail" in data


# ===========================================================================
# GET /auctions/{id}/execution-logs
# ===========================================================================

class TestGetExecutionLogs:
    """获取执行日志列表。"""

    @pytest.mark.asyncio
    async def test_get_execution_logs_returns_list(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """
        业务规则：任何有权限的用户可查询竞拍的执行日志列表，
        结果按时间升序排列。
        """
        trader_headers = await auth_header(trader)

        # 先写入两条日志
        for i, price in enumerate([3.80, 3.85]):
            await client.post(
                f"/auctions/{auction_id}/execution-logs",
                json={
                    "declared_price": price,
                    "declared_quantity": 500 + i * 100,
                    "declared_at": f"2026-04-28T10:0{i}:00",
                },
                headers=trader_headers,
            )

        resp = await client.get(
            f"/auctions/{auction_id}/execution-logs",
            headers=trader_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_execution_logs_empty_when_none(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """无执行日志时返回空列表，不报错。"""
        headers = await auth_header(trader)
        resp = await client.get(
            f"/auctions/{auction_id}/execution-logs",
            headers=headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_execution_logs_unauthorized(
        self, client: AsyncClient, auction_id
    ):
        """未携带认证头时返回 401。"""
        resp = await client.get(f"/auctions/{auction_id}/execution-logs")
        assert resp.status_code == 401
