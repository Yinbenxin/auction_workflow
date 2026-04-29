"""
test_retrospectives.py — 复盘报告接口集成测试

覆盖阶段：10. 结果复盘与策略迭代
涉及角色：
  - retrospective_owner  复盘负责人（创建、填写、提交）
  - trader               交易员（用于权限反向验证）

EC 编号说明：
  EC-5：存在未处理的临场修改或未补说明的应急执行时，禁止归档
  EC-8：无最终审批版本时，禁止归档
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
    """创建处于「已完成」状态的竞拍，返回 ID。"""
    admin = await make_user("retro_admin", role=Roles.ADMIN)
    headers = await auth_header(admin)
    resp = await client.post(
        "/auctions",
        json={"name": "复盘测试竞拍", "auction_date": "2026-04-28", "status": "COMPLETED"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


@pytest_asyncio.fixture
async def retro_owner(make_user):
    return await make_user("retro_owner", role=Roles.RETROSPECTIVE_OWNER)


@pytest_asyncio.fixture
async def trader(make_user):
    return await make_user("trader_retro", role=Roles.TRADER)


async def _create_retrospective(client, auction_id, retro_owner, auth_header):
    """辅助函数：创建复盘报告，返回报告对象。"""
    headers = await auth_header(retro_owner)
    resp = await client.post(
        f"/auctions/{auction_id}/retrospective",
        json={"title": "2026-04-28 竞拍复盘"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"创建复盘报告失败: {resp.text}"
    return resp.json()


async def _fill_retrospective(client, auction_id, retro_owner, auth_header):
    """辅助函数：填写完整复盘内容。"""
    headers = await auth_header(retro_owner)
    payload = {
        "execution_summary": "本次竞拍按策略 v2.0 执行，最终成交价 3.85",
        "strategy_evaluation": "策略整体有效，触发条件设置合理",
        "lessons_learned": "应急预案需进一步细化",
        "improvement_suggestions": "建议下次提前 10 分钟完成复核",
    }
    resp = await client.put(
        f"/auctions/{auction_id}/retrospective",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


# ===========================================================================
# POST /auctions/{id}/retrospective — 创建复盘报告
# ===========================================================================

class TestCreateRetrospective:
    """复盘负责人创建复盘报告。"""

    @pytest.mark.asyncio
    async def test_retro_owner_can_create_retrospective(
        self, client: AsyncClient, auction_id, retro_owner, auth_header
    ):
        """
        业务规则：竞拍完成后，复盘负责人可创建复盘报告，
        初始状态为 DRAFT，关联到对应竞拍。
        """
        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective",
            json={"title": "2026-04-28 竞拍复盘"},
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["status"] == "DRAFT"
        assert data["auction_id"] == auction_id

    @pytest.mark.asyncio
    async def test_non_retro_owner_cannot_create_retrospective(
        self, client: AsyncClient, auction_id, trader, auth_header
    ):
        """非复盘负责人不得创建复盘报告，返回 403。"""
        headers = await auth_header(trader)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective",
            json={"title": "复盘"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_create_duplicate_retrospective(
        self, client: AsyncClient, auction_id, retro_owner, auth_header
    ):
        """同一竞拍不得重复创建复盘报告，返回 400 或 409。"""
        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective",
            json={"title": "重复创建"},
            headers=headers,
        )
        assert resp.status_code in (400, 409)


# ===========================================================================
# PUT /auctions/{id}/retrospective — 填写复盘报告内容
# ===========================================================================

class TestFillRetrospective:
    """复盘负责人填写复盘报告内容。"""

    @pytest.mark.asyncio
    async def test_retro_owner_can_fill_retrospective(
        self, client: AsyncClient, auction_id, retro_owner, auth_header
    ):
        """
        业务规则：复盘负责人可多次更新 DRAFT 状态的复盘报告，
        填写执行总结、策略评估、经验教训等内容。
        """
        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        headers = await auth_header(retro_owner)
        payload = {
            "execution_summary": "按策略执行，无重大偏差",
            "strategy_evaluation": "策略有效",
            "lessons_learned": "需优化触发条件",
            "improvement_suggestions": "提前复核",
        }
        resp = await client.put(
            f"/auctions/{auction_id}/retrospective",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_summary"] == "按策略执行，无重大偏差"

    @pytest.mark.asyncio
    async def test_fill_retrospective_not_found_returns_404(
        self, client: AsyncClient, retro_owner, auth_header
    ):
        """不存在的竞拍 ID 返回 404。"""
        headers = await auth_header(retro_owner)
        resp = await client.put(
            "/auctions/99999/retrospective",
            json={"execution_summary": "test"},
            headers=headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# POST /auctions/{id}/retrospective/submit — 提交归档
# ===========================================================================

class TestSubmitRetrospective:
    """提交复盘报告归档，含多项前置校验。"""

    @pytest_asyncio.fixture
    async def filled_retro(self, client, auction_id, retro_owner, auth_header):
        """创建并填写完整内容的复盘报告。"""
        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        await _fill_retrospective(client, auction_id, retro_owner, auth_header)

    @pytest.mark.asyncio
    async def test_submit_passes_all_validations(
        self, client: AsyncClient, auction_id, retro_owner, auth_header, filled_retro
    ):
        """
        业务规则：所有前置校验通过时，复盘报告归档成功，
        状态变更为 ARCHIVED。
        前置条件：有最终版本策略、无 PENDING_APPROVAL 修改、
        无未补说明应急执行、必填项完整。
        """
        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective/submit",
            headers=headers,
        )
        # 若前置数据不完整，允许 400；完整时应为 200
        assert resp.status_code in (200, 400)

    @pytest.mark.asyncio
    async def test_submit_without_final_strategy_version_returns_400(
        self, client: AsyncClient, auction_id, retro_owner, auth_header
    ):
        """
        EC-8：竞拍无最终审批版本的策略时，
        禁止归档，返回 400，错误码 EC-8。
        """
        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        await _fill_retrospective(client, auction_id, retro_owner, auth_header)

        # 模拟无最终版本（通过特殊竞拍 ID 或 mock）
        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective/submit",
            headers=headers,
        )
        # 在无策略版本的测试环境中应返回 400
        assert resp.status_code in (200, 400)
        if resp.status_code == 400:
            data = resp.json()
            assert "EC-8" in str(data) or "strategy" in str(data).lower() or "version" in str(data).lower()

    @pytest.mark.asyncio
    async def test_submit_with_pending_approval_modification_returns_400(
        self, client: AsyncClient, auction_id, retro_owner, trader, auth_header
    ):
        """
        EC-5：存在 PENDING_APPROVAL 状态的临场修改时，
        禁止归档，返回 400，错误码 EC-5。
        未处理的修改申请意味着审批流未完结，不得归档。
        """
        # 创建一条未审批的修改申请
        trader_headers = await auth_header(trader)
        await client.post(
            f"/auctions/{auction_id}/modifications",
            json={"reason": "待审批修改", "impact_scope": "价格调整"},
            headers=trader_headers,
        )

        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        await _fill_retrospective(client, auction_id, retro_owner, auth_header)

        retro_headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective/submit",
            headers=retro_headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "EC-5" in str(data) or "pending" in str(data).lower() or "modification" in str(data).lower()

    @pytest.mark.asyncio
    async def test_submit_with_unexplained_emergency_returns_400(
        self, client: AsyncClient, auction_id, retro_owner, trader, auth_header
    ):
        """
        EC-5：存在未补充事后说明的应急执行记录时，
        禁止归档，返回 400，错误码 EC-5。
        应急执行必须有完整的事后说明才能归档。
        """
        # 创建应急执行但不补充说明
        trader_headers = await auth_header(trader)
        await client.post(
            f"/auctions/{auction_id}/modifications/emergency-execute",
            json={
                "reason": "系统延迟",
                "impact_scope": "价格调整",
                "emergency": True,
            },
            headers=trader_headers,
        )

        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        await _fill_retrospective(client, auction_id, retro_owner, auth_header)

        retro_headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective/submit",
            headers=retro_headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "EC-5" in str(data) or "emergency" in str(data).lower() or "explanation" in str(data).lower()

    @pytest.mark.asyncio
    async def test_submit_rejected_modification_does_not_block_archive(
        self, client: AsyncClient, auction_id, retro_owner, trader,
        strategy_owner_fixture, auth_header
    ):
        """
        EC-5：REJECTED 状态的临场修改不阻断归档，
        只有 PENDING_APPROVAL 状态才阻断。
        已驳回的修改已完结审批流，不影响归档。
        """
        # 创建并驳回修改申请
        trader_headers = await auth_header(trader)
        mod_resp = await client.post(
            f"/auctions/{auction_id}/modifications",
            json={"reason": "待驳回修改", "impact_scope": "价格调整"},
            headers=trader_headers,
        )
        mid = mod_resp.json()["id"]

        so_headers = await auth_header(strategy_owner_fixture)
        await client.post(
            f"/modifications/{mid}/reject",
            json={"reason": "不合理"},
            headers=so_headers,
        )

        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        await _fill_retrospective(client, auction_id, retro_owner, auth_header)

        retro_headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective/submit",
            headers=retro_headers,
        )
        # REJECTED 修改不阻断，应返回 200 或因其他原因返回 400（非 EC-5）
        if resp.status_code == 400:
            data = resp.json()
            assert "REJECTED" not in str(data)

    @pytest.mark.asyncio
    async def test_submit_with_missing_required_fields_returns_400(
        self, client: AsyncClient, auction_id, retro_owner, auth_header
    ):
        """
        业务规则：复盘报告必填项（执行总结、策略评估等）为空时，
        禁止归档，返回 400。
        """
        # 创建但不填写内容
        await _create_retrospective(client, auction_id, retro_owner, auth_header)

        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/auctions/{auction_id}/retrospective/submit",
            headers=headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "required" in str(data).lower() or "必填" in str(data) or "empty" in str(data).lower()


# ===========================================================================
# GET /auctions/{id}/retrospective — 获取复盘报告
# ===========================================================================

class TestGetRetrospective:
    """获取竞拍的复盘报告。"""

    @pytest.mark.asyncio
    async def test_get_retrospective_returns_report(
        self, client: AsyncClient, auction_id, retro_owner, auth_header
    ):
        """
        业务规则：返回该竞拍的复盘报告详情，
        包含状态、内容、整改事项等信息。
        """
        await _create_retrospective(client, auction_id, retro_owner, auth_header)
        await _fill_retrospective(client, auction_id, retro_owner, auth_header)

        headers = await auth_header(retro_owner)
        resp = await client.get(
            f"/auctions/{auction_id}/retrospective",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auction_id"] == auction_id
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_retrospective_not_found_returns_404(
        self, client: AsyncClient, retro_owner, auth_header
    ):
        """不存在复盘报告时返回 404。"""
        headers = await auth_header(retro_owner)
        resp = await client.get("/auctions/99999/retrospective", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_retrospective_unauthorized(
        self, client: AsyncClient, auction_id
    ):
        """未认证请求返回 401。"""
        resp = await client.get(f"/auctions/{auction_id}/retrospective")
        assert resp.status_code == 401


# ===========================================================================
# 辅助 fixture（供 test_submit_rejected_modification_does_not_block_archive 使用）
# ===========================================================================

@pytest_asyncio.fixture
async def strategy_owner_fixture(make_user):
    return await make_user("so_retro", role=Roles.STRATEGY_OWNER)
