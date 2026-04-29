"""
执行前复核接口集成测试
覆盖：POST /auctions/{id}/review、review/submit、mark-executable
EC 编号：
  EC-3：配置人与复核人相同（违反双人复核制度红线）
  EC-4：复核未通过时不得标记可执行
"""
import pytest
from httpx import AsyncClient

from tests.conftest import Roles


# ---------------------------------------------------------------------------
# 13 项复核清单（全部勾选表示通过）
# ---------------------------------------------------------------------------
CHECKLIST_ALL_PASS = {
    "strategy_version_confirmed": True,
    "task_config_confirmed": True,
    "bid_account_verified": True,
    "bid_platform_accessible": True,
    "price_range_verified": True,
    "volume_range_verified": True,
    "bid_time_window_verified": True,
    "trigger_condition_verified": True,
    "fallback_plan_verified": True,
    "risk_description_acknowledged": True,
    "emergency_contact_ready": True,
    "system_connectivity_checked": True,
    "dual_person_review_confirmed": True,
}

CHECKLIST_INCOMPLETE = {
    **CHECKLIST_ALL_PASS,
    "system_connectivity_checked": False,  # 故意漏掉一项
}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _setup_auction_ready_for_review(
    client: AsyncClient,
    ds_headers: dict,
    so_headers: dict,
    rv_headers: dict,
    tr_headers: dict,
) -> str:
    """
    创建竞拍项目并完成策略最终化 + 任务配置确认，
    使项目进入可发起复核的状态，返回 auction_id。
    """
    # 创建项目
    resp = await client.post(
        "/auctions",
        json={"name": "复核测试项目", "auction_date": "2026-04-28"},
        headers=ds_headers,
    )
    assert resp.status_code == 201
    auction_id = resp.json()["id"]

    # 策略版本：创建 → 提交 → 确认 → 最终化
    strategy_resp = await client.post(
        f"/auctions/{auction_id}/strategies",
        json={
            "version_name": "重庆忠润_20260428_v1.0",
            "price": 4.2,
            "volume": 5000,
            "bid_time": "09:30:00",
            "trigger_condition": "价格低于均价 5%",
            "fallback_plan": "保底价兜底",
            "risk_description": "市场波动风险",
            "risk_level": "NORMAL",
        },
        headers=so_headers,
    )
    assert strategy_resp.status_code == 201
    vid = strategy_resp.json()["id"]

    await client.post(f"/strategies/{vid}/submit", headers=so_headers)
    await client.post(f"/strategies/{vid}/confirm", headers=rv_headers)
    await client.post(f"/strategies/{vid}/finalize", headers=ds_headers)

    # 任务配置：录入 + 确认
    await client.put(
        f"/auctions/{auction_id}/task-config",
        json={
            "bid_account": "账户A",
            "bid_platform": "上海石油天然气交易中心",
            "bid_time_window": "09:30-10:00",
            "max_bid_price": 4.8,
            "min_bid_volume": 1000,
            "max_bid_volume": 5000,
            "price_step": 0.1,
            "auto_bid_enabled": True,
            "fallback_manual_bid": False,
        },
        headers=tr_headers,
    )
    await client.post(
        f"/auctions/{auction_id}/task-config/confirm",
        headers=tr_headers,
    )

    return auction_id


class TestInitiateReview:
    """POST /auctions/{id}/review — 发起复核"""

    @pytest.mark.asyncio
    async def test_trader_can_initiate_review(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：交易员在任务配置确认后可发起执行前复核，返回 200，
        review_status 变为 IN_REVIEW。
        """
        ds_user = await make_user("rv_ds1", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so1", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv1", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr1", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )

        resp = await client.post(
            f"/auctions/{auction_id}/review",
            headers=tr_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("review_status") == "IN_REVIEW"

    @pytest.mark.asyncio
    async def test_non_trader_cannot_initiate_review(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：非交易员不得发起复核，返回 403。
        """
        ds_user = await make_user("rv_ds2", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so2", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv2", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr2", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )

        # 策略负责人尝试发起复核
        resp = await client.post(
            f"/auctions/{auction_id}/review",
            headers=so_headers,
        )

        assert resp.status_code == 403


class TestSubmitReview:
    """POST /auctions/{id}/review/submit — 复核人提交复核结果"""

    @pytest.mark.asyncio
    async def test_reviewer_submit_all_checklist_pass(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：复核人提交 13 项清单全部通过，返回 200，
        review_status 变为 REVIEW_PASSED。
        """
        ds_user = await make_user("rv_ds3", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so3", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv3", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr3", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        await client.post(f"/auctions/{auction_id}/review", headers=tr_headers)

        resp = await client.post(
            f"/auctions/{auction_id}/review/submit",
            json={"checklist": CHECKLIST_ALL_PASS},
            headers=rv_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("review_status") == "REVIEW_PASSED"

    @pytest.mark.asyncio
    async def test_same_person_as_configurator_returns_403_ec3(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        EC-3：配置人与复核人为同一人，违反双人复核制度红线，返回 400。
        同一人配置、同一人复核是禁止项。
        """
        ds_user = await make_user("rv_ds4", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so4", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv4", role=Roles.REVIEWER)
        # 交易员同时担任复核人（同一账号）
        tr_user = await make_user("rv_tr4", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        await client.post(f"/auctions/{auction_id}/review", headers=tr_headers)

        # 交易员（配置人）尝试自己提交复核（EC-3）
        resp = await client.post(
            f"/auctions/{auction_id}/review/submit",
            json={"checklist": CHECKLIST_ALL_PASS},
            headers=tr_headers,  # 与配置人相同
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "EC-3" in body.get("detail", "") or "dual" in body.get("detail", "").lower() or "双人" in body.get("detail", "")

    @pytest.mark.asyncio
    async def test_incomplete_checklist_returns_400(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：13 项清单未全部勾选（有 False 项），返回 400，
        detail 说明哪些项未通过。
        """
        ds_user = await make_user("rv_ds5", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so5", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv5", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr5", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        await client.post(f"/auctions/{auction_id}/review", headers=tr_headers)

        resp = await client.post(
            f"/auctions/{auction_id}/review/submit",
            json={"checklist": CHECKLIST_INCOMPLETE},
            headers=rv_headers,
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body

    @pytest.mark.asyncio
    async def test_missing_checklist_items_returns_422(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：请求体缺少 checklist 字段，FastAPI 返回 422。
        """
        ds_user = await make_user("rv_ds6", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so6", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv6", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr6", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        await client.post(f"/auctions/{auction_id}/review", headers=tr_headers)

        resp = await client.post(
            f"/auctions/{auction_id}/review/submit",
            json={},  # 缺少 checklist
            headers=rv_headers,
        )

        assert resp.status_code == 422


class TestMarkExecutable:
    """POST /auctions/{id}/mark-executable — 标记可执行"""

    @pytest.mark.asyncio
    async def test_mark_executable_after_review_passed(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：复核通过后，业务负责人可将项目标记为可执行，
        返回 200，is_executable=True。
        交易员只能执行已标记可执行的项目。
        """
        ds_user = await make_user("rv_ds7", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so7", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv7", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr7", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        await client.post(f"/auctions/{auction_id}/review", headers=tr_headers)
        await client.post(
            f"/auctions/{auction_id}/review/submit",
            json={"checklist": CHECKLIST_ALL_PASS},
            headers=rv_headers,
        )

        resp = await client.post(
            f"/auctions/{auction_id}/mark-executable",
            headers=ds_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("is_executable") is True

    @pytest.mark.asyncio
    async def test_mark_executable_without_review_passed_returns_400_ec4(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        EC-4：复核未通过（或尚未复核）时，尝试标记可执行返回 400。
        必须先完成复核才能进入正式竞拍执行阶段。
        """
        ds_user = await make_user("rv_ds8", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so8", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv8", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr8", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        # 故意跳过复核步骤，直接尝试标记可执行

        resp = await client.post(
            f"/auctions/{auction_id}/mark-executable",
            headers=ds_headers,
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "EC-4" in body.get("detail", "") or "review" in body.get("detail", "").lower() or "复核" in body.get("detail", "")

    @pytest.mark.asyncio
    async def test_mark_executable_after_review_failed_returns_400_ec4(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        EC-4：复核结果为未通过（清单有 False 项被强制提交），
        标记可执行应返回 400。
        """
        ds_user = await make_user("rv_ds9", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("rv_so9", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("rv_rv9", role=Roles.REVIEWER)
        tr_user = await make_user("rv_tr9", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_ready_for_review(
            client, ds_headers, so_headers, rv_headers, tr_headers
        )
        await client.post(f"/auctions/{auction_id}/review", headers=tr_headers)

        # 提交含失败项的复核（后端应记录 REVIEW_FAILED 状态）
        await client.post(
            f"/auctions/{auction_id}/review/submit",
            json={"checklist": CHECKLIST_INCOMPLETE, "force": True},
            headers=rv_headers,
        )

        resp = await client.post(
            f"/auctions/{auction_id}/mark-executable",
            headers=ds_headers,
        )

        assert resp.status_code == 400
