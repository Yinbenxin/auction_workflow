"""
策略版本接口集成测试
覆盖：POST/PUT /auctions/{id}/strategies、提交/确认/驳回/最终化/作废
EC 编号对应业务规范中的错误码：
  EC-1：已确认版本不可修改
  EC-9：版本号重复
"""
import pytest
from httpx import AsyncClient

from tests.conftest import Roles


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

async def _setup_auction(client: AsyncClient, ds_headers: dict) -> str:
    """创建并返回竞拍项目 ID（假设后端已就绪）。"""
    resp = await client.post(
        "/auctions",
        json={"name": "策略测试项目", "auction_date": "2026-04-28"},
        headers=ds_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_strategy(
    client: AsyncClient,
    auction_id: str,
    headers: dict,
    **overrides,
) -> dict:
    """创建策略版本，返回完整响应对象。"""
    payload = {
        "version_name": "重庆忠润_20260428_v1.0",
        "price": 4.2,
        "volume": 5000,
        "bid_time": "09:30:00",
        "trigger_condition": "价格低于均价 5%",
        "fallback_plan": "保底价兜底",
        "risk_description": "市场波动风险",
        "risk_level": "NORMAL",
        **overrides,
    }
    return await client.post(
        f"/auctions/{auction_id}/strategies",
        json=payload,
        headers=headers,
    )


class TestCreateStrategy:
    """POST /auctions/{id}/strategies"""

    @pytest.mark.asyncio
    async def test_strategy_owner_can_create_strategy(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：策略负责人可创建策略版本，返回 201 及版本信息。
        策略版本格式：项目名称_竞拍日期_策略版本（如 重庆忠润_20260428_v1.0）。
        """
        ds_user = await make_user("st_ds1", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("st_so1", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)
        resp = await _create_strategy(client, auction_id, so_headers)

        assert resp.status_code == 201
        body = resp.json()
        assert body["version_name"] == "重庆忠润_20260428_v1.0"
        assert body["status"] == "DRAFT"
        assert "id" in body

    @pytest.mark.asyncio
    async def test_emergency_risk_without_pre_authorized_actions_returns_400(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：risk_level=EMERGENCY 时必须提供 pre_authorized_actions 字段，
        否则返回 400，detail 说明缺少预授权操作列表。
        """
        ds_user = await make_user("st_ds2", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("st_so2", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)
        resp = await _create_strategy(
            client,
            auction_id,
            so_headers,
            risk_level="EMERGENCY",
            # 故意不传 pre_authorized_actions
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "pre_authorized_actions" in body.get("detail", "").lower()

    @pytest.mark.asyncio
    async def test_duplicate_version_name_returns_409(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        EC-9：同一竞拍项目下版本号重复，返回 409 Conflict。
        """
        ds_user = await make_user("st_ds3", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("st_so3", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)

        # 第一次创建成功
        resp1 = await _create_strategy(
            client, auction_id, so_headers, version_name="重庆忠润_20260428_v1.0"
        )
        assert resp1.status_code == 201

        # 第二次使用相同版本号，应返回 409
        resp2 = await _create_strategy(
            client, auction_id, so_headers, version_name="重庆忠润_20260428_v1.0"
        )
        assert resp2.status_code == 409


class TestUpdateStrategy:
    """PUT /auctions/{id}/strategies/{vid}"""

    @pytest.mark.asyncio
    async def test_update_draft_strategy_success(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：DRAFT 状态的策略版本可以更新，返回 200 及更新后内容。
        """
        ds_user = await make_user("st_ds4", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("st_so4", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        resp = await client.put(
            f"/auctions/{auction_id}/strategies/{vid}",
            json={"price": 4.5, "volume": 6000},
            headers=so_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["price"] == 4.5
        assert body["volume"] == 6000

    @pytest.mark.asyncio
    async def test_update_confirmed_strategy_returns_400(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        EC-1：已确认（CONFIRMED）状态的策略版本不可修改，返回 400。
        已审批版本不得直接覆盖修改，必须新建版本。
        """
        ds_user = await make_user("st_ds5", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("st_so5", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("st_rv5", role=Roles.REVIEWER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        # 提交 → 确认，使版本进入 CONFIRMED 状态
        await client.post(f"/strategies/{vid}/submit", headers=so_headers)
        await client.post(f"/strategies/{vid}/confirm", headers=rv_headers)

        # 尝试修改已确认版本
        resp = await client.put(
            f"/auctions/{auction_id}/strategies/{vid}",
            json={"price": 9.9},
            headers=so_headers,
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "EC-1" in body.get("detail", "") or "confirmed" in body.get("detail", "").lower()


class TestStrategyWorkflow:
    """策略审批工作流：提交 → 确认/驳回 → 最终化/作废"""

    @pytest.mark.asyncio
    async def test_submit_strategy_changes_status_to_pending(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：策略负责人提交草稿版本后，状态变为 PENDING_CONFIRM。
        """
        ds_user = await make_user("wf_ds1", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so1", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        resp = await client.post(f"/strategies/{vid}/submit", headers=so_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "PENDING_CONFIRM"

    @pytest.mark.asyncio
    async def test_reviewer_can_confirm_normal_strategy(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：普通策略（无红线字段变更）由审核人确认即可，返回 200，状态变为 CONFIRMED。
        """
        ds_user = await make_user("wf_ds2", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so2", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("wf_rv2", role=Roles.REVIEWER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        await client.post(f"/strategies/{vid}/submit", headers=so_headers)
        resp = await client.post(f"/strategies/{vid}/confirm", headers=rv_headers)

        assert resp.status_code == 200
        assert resp.json()["status"] == "CONFIRMED"

    @pytest.mark.asyncio
    async def test_strategy_owner_cannot_confirm_own_submission(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：策略负责人不得确认自己提交的版本（防止自审自批），返回 403。
        双人复核是制度红线。
        """
        ds_user = await make_user("wf_ds3", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so3", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        await client.post(f"/strategies/{vid}/submit", headers=so_headers)

        # 策略负责人尝试确认自己提交的版本
        resp = await client.post(f"/strategies/{vid}/confirm", headers=so_headers)

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_redline_field_change_requires_biz_owner_confirm(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：涉及红线字段变更（价格/数量/时点/触发条件）时，
        仅审核人确认不够，还需业务负责人确认，否则返回 400。
        重大调整必须升主版本号（v1.x → v2.0）。
        """
        ds_user = await make_user("wf_ds4", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so4", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("wf_rv4", role=Roles.REVIEWER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)

        auction_id = await _setup_auction(client, ds_headers)
        # 创建含红线字段变更标记的策略版本
        create_resp = await _create_strategy(
            client,
            auction_id,
            so_headers,
            version_name="重庆忠润_20260428_v2.0",
            has_redline_change=True,  # 后端识别此标记触发双重审批
        )
        vid = create_resp.json()["id"]

        await client.post(f"/strategies/{vid}/submit", headers=so_headers)

        # 仅审核人确认，应返回 400（还需业务负责人）
        resp = await client.post(f"/strategies/{vid}/confirm", headers=rv_headers)

        assert resp.status_code == 400
        body = resp.json()
        assert "business_owner" in body.get("detail", "").lower() or "业务负责人" in body.get("detail", "")

    @pytest.mark.asyncio
    async def test_reject_strategy_with_reason(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：审核人可驳回策略版本并附原因，返回 200，状态变为 REJECTED。
        """
        ds_user = await make_user("wf_ds5", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so5", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("wf_rv5", role=Roles.REVIEWER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        await client.post(f"/strategies/{vid}/submit", headers=so_headers)
        resp = await client.post(
            f"/strategies/{vid}/reject",
            json={"reason": "价格设置不合理，需重新评估"},
            headers=rv_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "REJECTED"
        assert body.get("reject_reason") == "价格设置不合理，需重新评估"

    @pytest.mark.asyncio
    async def test_finalize_strategy_marks_as_final(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：业务负责人将已确认版本标记为最终版本，返回 200，
        is_final=True，交易员只能执行最终审批版本。
        """
        ds_user = await make_user("wf_ds6", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so6", role=Roles.STRATEGY_OWNER)
        rv_user = await make_user("wf_rv6", role=Roles.REVIEWER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)
        rv_headers = await auth_header(rv_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        await client.post(f"/strategies/{vid}/submit", headers=so_headers)
        await client.post(f"/strategies/{vid}/confirm", headers=rv_headers)

        resp = await client.post(f"/strategies/{vid}/finalize", headers=ds_headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["is_final"] is True

    @pytest.mark.asyncio
    async def test_void_strategy_preserves_record(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：作废版本后状态变为 VOID，但记录必须保留（不得删除历史版本）。
        作废版本仍可通过 GET 查询到，status=VOID。
        """
        ds_user = await make_user("wf_ds7", role=Roles.BUSINESS_OWNER)
        so_user = await make_user("wf_so7", role=Roles.STRATEGY_OWNER)
        ds_headers = await auth_header(ds_user)
        so_headers = await auth_header(so_user)

        auction_id = await _setup_auction(client, ds_headers)
        create_resp = await _create_strategy(client, auction_id, so_headers)
        vid = create_resp.json()["id"]

        # 作废
        void_resp = await client.post(f"/strategies/{vid}/void", headers=ds_headers)
        assert void_resp.status_code == 200
        assert void_resp.json()["status"] == "VOID"

        # 记录仍可查询
        get_resp = await client.get(
            f"/auctions/{auction_id}/strategies/{vid}",
            headers=ds_headers,
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "VOID"
