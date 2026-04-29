"""
竞拍项目接口集成测试
覆盖：GET /auctions、POST /auctions、PUT /auctions/{id}/basic-info、
      POST /auctions/{id}/basic-info/confirm、阶段门控
"""
import pytest
from httpx import AsyncClient

from tests.conftest import (
    ROLE_DATA_STAFF,
    ROLE_BIZ_OWNER,
    ROLE_TRADER,
)

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _create_auction(client: AsyncClient, headers: dict, **overrides) -> dict:
    """创建一个竞拍项目，返回响应 body。"""
    payload = {
        "name": "重庆忠润竞拍",
        "auction_date": "2026-04-28",
        "description": "天然气竞拍测试项目",
        **overrides,
    }
    resp = await client.post("/auctions", json=payload, headers=headers)
    return resp


class TestListAuctions:
    """GET /auctions"""

    @pytest.mark.asyncio
    async def test_list_auctions_returns_list(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：任意已登录用户可获取竞拍项目列表，返回 200 及数组结构。
        """
        headers = await auth_header(username="list_trader", role=ROLE_TRADER)

        resp = await client.get("/auctions", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list) or "items" in body

    @pytest.mark.asyncio
    async def test_list_auctions_without_auth_returns_401(self, client: AsyncClient):
        """
        业务规则：未登录用户访问列表返回 401。
        """
        resp = await client.get("/auctions")
        assert resp.status_code == 401


class TestCreateAuction:
    """POST /auctions"""

    @pytest.mark.asyncio
    async def test_data_staff_can_create_auction(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：数据人员（DATA_STAFF）有权创建竞拍项目，返回 201 及新建项目信息。
        """
        headers = await auth_header(username="creator_ds", role=ROLE_DATA_STAFF)

        resp = await _create_auction(client, headers, name="创建测试项目")

        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["name"] == "创建测试项目"
        # 新建项目阶段应为 01（竞拍信息收集）
        assert body.get("phase") in ("PHASE_01", "01", 1)

    @pytest.mark.asyncio
    async def test_non_data_staff_create_auction_returns_403(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：非数据人员（如交易员）创建竞拍项目，返回 403 Forbidden。
        """
        headers = await auth_header(username="creator_trader", role=ROLE_TRADER)

        resp = await _create_auction(client, headers, name="越权创建项目")

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_auction_missing_required_field_returns_422(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：缺少必填字段（如 auction_date），FastAPI 返回 422。
        """
        headers = await auth_header(username="creator_ds2", role=ROLE_DATA_STAFF)

        resp = await client.post(
            "/auctions",
            json={"name": "缺少日期"},
            headers=headers,
        )

        assert resp.status_code == 422


class TestBasicInfo:
    """PUT /auctions/{id}/basic-info 及 POST /auctions/{id}/basic-info/confirm"""

    @pytest.mark.asyncio
    async def test_update_basic_info_success(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：数据人员可录入/更新竞拍基础信息（阶段01），返回 200。
        """
        ds_headers = await auth_header(username="bi_ds", role=ROLE_DATA_STAFF)
        create_resp = await _create_auction(client, ds_headers, name="基础信息测试")
        auction_id = create_resp.json()["id"]

        payload = {
            "gas_source": "四川盆地",
            "volume_mwh": 5000,
            "price_floor": 3.5,
            "price_ceiling": 5.0,
            "contact_person": "张三",
        }
        resp = await client.put(
            f"/auctions/{auction_id}/basic-info",
            json=payload,
            headers=ds_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["gas_source"] == "四川盆地"

    @pytest.mark.asyncio
    async def test_biz_owner_can_confirm_basic_info(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：业务负责人（BIZ_OWNER）确认基础信息后，项目进入阶段02。
        """
        ds_headers = await auth_header(username="bi_ds2", role=ROLE_DATA_STAFF)
        biz_headers = await auth_header(username="bi_biz", role=ROLE_BIZ_OWNER)

        create_resp = await _create_auction(client, ds_headers, name="确认基础信息测试")
        auction_id = create_resp.json()["id"]

        # 先录入基础信息
        await client.put(
            f"/auctions/{auction_id}/basic-info",
            json={"gas_source": "新疆", "volume_mwh": 3000},
            headers=ds_headers,
        )

        # 业务负责人确认
        resp = await client.post(
            f"/auctions/{auction_id}/basic-info/confirm",
            headers=biz_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("basic_info_confirmed") is True

    @pytest.mark.asyncio
    async def test_non_biz_owner_confirm_returns_403(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则：非业务负责人（如交易员）尝试确认基础信息，返回 403。
        """
        ds_headers = await auth_header(username="bi_ds3", role=ROLE_DATA_STAFF)
        trader_headers = await auth_header(username="bi_trader", role=ROLE_TRADER)

        create_resp = await _create_auction(client, ds_headers, name="越权确认测试")
        auction_id = create_resp.json()["id"]

        resp = await client.post(
            f"/auctions/{auction_id}/basic-info/confirm",
            headers=trader_headers,
        )

        assert resp.status_code == 403


class TestPhaseGating:
    """阶段门控：基础信息未确认时不得进入阶段02"""

    @pytest.mark.asyncio
    async def test_enter_phase02_without_confirmed_basic_info_returns_400(
        self, client: AsyncClient, auth_header
    ):
        """
        业务规则（阶段门控）：基础信息尚未经业务负责人确认时，
        尝试推进到阶段02（历史数据分析）应返回 400，
        detail 应说明前置条件未满足。
        """
        ds_headers = await auth_header(username="gate_ds", role=ROLE_DATA_STAFF)

        create_resp = await _create_auction(client, ds_headers, name="门控测试项目")
        auction_id = create_resp.json()["id"]

        # 直接尝试推进阶段，跳过确认步骤
        resp = await client.post(
            f"/auctions/{auction_id}/advance-phase",
            headers=ds_headers,
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body
