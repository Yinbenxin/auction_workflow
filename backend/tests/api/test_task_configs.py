"""
任务配置接口集成测试
覆盖：GET/PUT /auctions/{id}/task-config、POST confirm、阶段门控
"""
import pytest
from httpx import AsyncClient

from tests.conftest import Roles


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _setup_auction_with_final_strategy(
    client: AsyncClient,
    ds_headers: dict,
    so_headers: dict,
    rv_headers: dict,
) -> str:
    """
    创建竞拍项目并完成策略最终化，返回 auction_id。
    这是任务配置阶段的前置条件。
    """
    # 创建项目
    resp = await client.post(
        "/auctions",
        json={"name": "任务配置测试项目", "auction_date": "2026-04-28"},
        headers=ds_headers,
    )
    assert resp.status_code == 201
    auction_id = resp.json()["id"]

    # 创建策略版本
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

    # 提交 → 确认 → 最终化
    await client.post(f"/strategies/{vid}/submit", headers=so_headers)
    await client.post(f"/strategies/{vid}/confirm", headers=rv_headers)
    await client.post(f"/strategies/{vid}/finalize", headers=ds_headers)

    return auction_id


# 任务配置的 9 个必填字段（对应业务规范阶段05）
TASK_CONFIG_PAYLOAD = {
    "bid_account": "账户A",
    "bid_platform": "上海石油天然气交易中心",
    "bid_time_window": "09:30-10:00",
    "max_bid_price": 4.8,
    "min_bid_volume": 1000,
    "max_bid_volume": 5000,
    "price_step": 0.1,
    "auto_bid_enabled": True,
    "fallback_manual_bid": False,
}


class TestGetTaskConfig:
    """GET /auctions/{id}/task-config"""

    @pytest.mark.asyncio
    async def test_get_task_config_returns_config(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：已登录用户可获取竞拍项目的任务配置，返回 200。
        若尚未配置，返回空对象或默认值，不得返回 404。
        """
        ds_user = await make_user("tc_ds1", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("tc_so1", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("tc_rv1", role=Roles.REVIEWER)
        tr_user = await make_user("tc_tr1", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_with_final_strategy(
            client, ds_headers, so_headers, rv_headers
        )

        resp = await client.get(f"/auctions/{auction_id}/task-config", headers=tr_headers)

        assert resp.status_code == 200
        body = resp.json()
        # 返回对象或 null，不得是 404
        assert body is not None


class TestUpdateTaskConfig:
    """PUT /auctions/{id}/task-config"""

    @pytest.mark.asyncio
    async def test_trader_can_update_task_config_with_all_fields(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：交易员可录入任务配置，必须包含全部 9 个字段，返回 200。
        """
        ds_user = await make_user("tc_ds2", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("tc_so2", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("tc_rv2", role=Roles.REVIEWER)
        tr_user = await make_user("tc_tr2", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_with_final_strategy(
            client, ds_headers, so_headers, rv_headers
        )

        resp = await client.put(
            f"/auctions/{auction_id}/task-config",
            json=TASK_CONFIG_PAYLOAD,
            headers=tr_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["bid_account"] == "账户A"
        assert body["bid_platform"] == "上海石油天然气交易中心"
        assert body["max_bid_price"] == 4.8

    @pytest.mark.asyncio
    async def test_non_trader_update_task_config_returns_403(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：非交易员（如策略负责人）不得录入任务配置，返回 403。
        """
        ds_user = await make_user("tc_ds3", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("tc_so3", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("tc_rv3", role=Roles.REVIEWER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)

        auction_id = await _setup_auction_with_final_strategy(
            client, ds_headers, so_headers, rv_headers
        )

        # 策略负责人尝试录入任务配置
        resp = await client.put(
            f"/auctions/{auction_id}/task-config",
            json=TASK_CONFIG_PAYLOAD,
            headers=so_headers,
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_task_config_without_final_strategy_returns_400(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则（阶段门控）：无最终版本策略时，交易员录入任务配置应返回 400。
        任务配置是阶段05，依赖阶段04（策略最终化）完成。
        """
        ds_user = await make_user("tc_ds4", role=Roles.BUSINESS_OWNER)
        tr_user = await make_user("tc_tr4", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        tr_headers = await auth_header(tr_user)

        # 创建项目但不完成策略最终化
        resp = await client.post(
            "/auctions",
            json={"name": "无策略门控测试", "auction_date": "2026-04-28"},
            headers=ds_headers,
        )
        assert resp.status_code == 201
        auction_id = resp.json()["id"]

        # 直接尝试录入任务配置
        resp = await client.put(
            f"/auctions/{auction_id}/task-config",
            json=TASK_CONFIG_PAYLOAD,
            headers=tr_headers,
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body

    @pytest.mark.asyncio
    async def test_update_task_config_missing_required_field_returns_422(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：任务配置缺少必填字段（如 bid_account），FastAPI 返回 422。
        """
        ds_user = await make_user("tc_ds5", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("tc_so5", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("tc_rv5", role=Roles.REVIEWER)
        tr_user = await make_user("tc_tr5", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_with_final_strategy(
            client, ds_headers, so_headers, rv_headers
        )

        incomplete_payload = {k: v for k, v in TASK_CONFIG_PAYLOAD.items() if k != "bid_account"}
        resp = await client.put(
            f"/auctions/{auction_id}/task-config",
            json=incomplete_payload,
            headers=tr_headers,
        )

        assert resp.status_code == 422


class TestConfirmTaskConfig:
    """POST /auctions/{id}/task-config/confirm"""

    @pytest.mark.asyncio
    async def test_trader_can_confirm_task_config(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：交易员录入并确认任务配置后，返回 200，
        task_config_confirmed=True，项目可进入执行前复核阶段。
        """
        ds_user = await make_user("tc_ds6", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("tc_so6", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("tc_rv6", role=Roles.REVIEWER)
        tr_user = await make_user("tc_tr6", role=Roles.TRADER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)
        tr_headers = await auth_header(tr_user)

        auction_id = await _setup_auction_with_final_strategy(
            client, ds_headers, so_headers, rv_headers
        )

        # 先录入配置
        await client.put(
            f"/auctions/{auction_id}/task-config",
            json=TASK_CONFIG_PAYLOAD,
            headers=tr_headers,
        )

        # 确认配置
        resp = await client.post(
            f"/auctions/{auction_id}/task-config/confirm",
            headers=tr_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("task_config_confirmed") is True
