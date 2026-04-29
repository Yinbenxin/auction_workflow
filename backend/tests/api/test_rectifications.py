"""
test_rectifications.py — 整改事项接口集成测试

覆盖阶段：10. 结果复盘与策略迭代（整改跟踪子流程）
涉及角色：
  - retrospective_owner  复盘负责人（创建、确认完成、关闭）
  - business_owner       业务负责人（可关闭整改事项）
  - assignee             责任人（更新状态、上传证据）
  - other_user           无权限用户（403 验证）

整改事项状态流：OPEN → IN_PROGRESS → PENDING_CONFIRM → CLOSED
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
import io

from tests.conftest import Roles


# ===========================================================================
# 测试夹具
# ===========================================================================

@pytest_asyncio.fixture
async def retrospective_id(client: AsyncClient, make_user, auth_header):
    """
    创建竞拍 → 创建复盘报告，返回复盘报告 ID（rid）。
    整改事项挂载在复盘报告下。
    """
    admin = await make_user("rect_admin", role=Roles.ADMIN)
    admin_headers = await auth_header(admin)

    # 创建竞拍
    auction_resp = await client.post(
        "/auctions",
        json={"name": "整改测试竞拍", "auction_date": "2026-04-28", "status": "COMPLETED"},
        headers=admin_headers,
    )
    assert auction_resp.status_code in (200, 201)
    auction_id = auction_resp.json()["id"]

    # 创建复盘报告
    retro_owner = await make_user("rect_retro_owner", role=Roles.RETROSPECTIVE_OWNER)
    retro_headers = await auth_header(retro_owner)
    retro_resp = await client.post(
        f"/auctions/{auction_id}/retrospective",
        json={"title": "整改测试复盘"},
        headers=retro_headers,
    )
    assert retro_resp.status_code in (200, 201)
    return retro_resp.json()["id"]


@pytest_asyncio.fixture
async def retro_owner(make_user):
    return await make_user("rect_owner", role=Roles.RETROSPECTIVE_OWNER)


@pytest_asyncio.fixture
async def assignee(make_user):
    """整改事项责任人（交易员角色）。"""
    return await make_user("rect_assignee", role=Roles.TRADER)


@pytest_asyncio.fixture
async def business_owner(make_user):
    return await make_user("rect_biz_owner", role=Roles.BUSINESS_OWNER)


@pytest_asyncio.fixture
async def other_user(make_user):
    """无整改权限的普通用户。"""
    return await make_user("rect_other", role=Roles.MONITOR)


async def _create_rectification_item(
    client, retrospective_id, retro_owner, assignee, auth_header, **extra
):
    """辅助函数：创建整改事项，返回整改事项对象。"""
    headers = await auth_header(retro_owner)
    payload = {
        "title": "优化触发条件设置",
        "measures": "在策略模板中增加触发条件校验步骤，并在培训中强化",
        "due_date": "2026-05-15",
        "assignee_id": assignee["id"],
        **extra,
    }
    resp = await client.post(
        f"/retrospectives/{retrospective_id}/rectification-items",
        json=payload,
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"创建整改事项失败: {resp.text}"
    return resp.json()


# ===========================================================================
# POST /retrospectives/{rid}/rectification-items — 创建整改事项
# ===========================================================================

class TestCreateRectificationItem:
    """复盘负责人创建整改事项。"""

    @pytest.mark.asyncio
    async def test_retro_owner_can_create_rectification_item(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：复盘负责人可在复盘报告下创建整改事项，
        指定责任人、整改措施和截止日期，初始状态为 OPEN。
        """
        headers = await auth_header(retro_owner)
        payload = {
            "title": "优化触发条件",
            "measures": "增加触发条件校验步骤",
            "due_date": "2026-05-15",
            "assignee_id": assignee["id"],
        }
        resp = await client.post(
            f"/retrospectives/{retrospective_id}/rectification-items",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["status"] == "OPEN"
        assert data["assignee_id"] == assignee["id"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_rectification_requires_measures(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：measures（整改措施）为必填字段，
        为空时返回 400，确保整改有明确的执行方案。
        """
        headers = await auth_header(retro_owner)
        payload = {
            "title": "优化触发条件",
            "measures": "",
            "due_date": "2026-05-15",
            "assignee_id": assignee["id"],
        }
        resp = await client.post(
            f"/retrospectives/{retrospective_id}/rectification-items",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_rectification_requires_due_date(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：due_date（截止日期）为必填字段，
        为空时返回 400，确保整改有明确的时间约束。
        """
        headers = await auth_header(retro_owner)
        payload = {
            "title": "优化触发条件",
            "measures": "增加校验步骤",
            "assignee_id": assignee["id"],
        }
        resp = await client.post(
            f"/retrospectives/{retrospective_id}/rectification-items",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_non_retro_owner_cannot_create_rectification(
        self, client: AsyncClient, retrospective_id, other_user, assignee, auth_header
    ):
        """非复盘负责人不得创建整改事项，返回 403。"""
        headers = await auth_header(other_user)
        payload = {
            "title": "优化触发条件",
            "measures": "增加校验步骤",
            "due_date": "2026-05-15",
            "assignee_id": assignee["id"],
        }
        resp = await client.post(
            f"/retrospectives/{retrospective_id}/rectification-items",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# GET /retrospectives/{rid}/rectification-items — 获取整改事项列表
# ===========================================================================

class TestGetRectificationItems:
    """获取复盘报告下的整改事项列表。"""

    @pytest.mark.asyncio
    async def test_get_rectification_items_returns_list(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：返回该复盘报告下所有整改事项，
        包含状态、责任人、截止日期等信息。
        """
        # 预置两条整改事项
        for i in range(2):
            await _create_rectification_item(
                client, retrospective_id, retro_owner, assignee, auth_header,
                title=f"整改事项 {i+1}",
                measures=f"整改措施 {i+1}",
            )

        headers = await auth_header(retro_owner)
        resp = await client.get(
            f"/retrospectives/{retrospective_id}/rectification-items",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_rectification_items_empty_when_none(
        self, client: AsyncClient, retrospective_id, retro_owner, auth_header
    ):
        """无整改事项时返回空列表。"""
        headers = await auth_header(retro_owner)
        resp = await client.get(
            f"/retrospectives/{retrospective_id}/rectification-items",
            headers=headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_rectification_items_unauthorized(
        self, client: AsyncClient, retrospective_id
    ):
        """未认证请求返回 401。"""
        resp = await client.get(
            f"/retrospectives/{retrospective_id}/rectification-items"
        )
        assert resp.status_code == 401


# ===========================================================================
# PUT /rectification-items/{iid} — 责任人更新状态
# ===========================================================================

class TestUpdateRectificationItem:
    """责任人更新整改事项状态。"""

    @pytest.mark.asyncio
    async def test_assignee_can_update_status_to_in_progress(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：责任人可将整改事项状态从 OPEN 更新为 IN_PROGRESS，
        表示已开始执行整改措施。
        """
        item = await _create_rectification_item(
            client, retrospective_id, retro_owner, assignee, auth_header
        )
        iid = item["id"]

        headers = await auth_header(assignee)
        resp = await client.put(
            f"/rectification-items/{iid}",
            json={"status": "IN_PROGRESS", "progress_note": "已开始优化触发条件模板"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_non_assignee_cannot_update_status(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee,
        other_user, auth_header
    ):
        """
        业务规则：只有责任人可更新整改事项状态，
        其他用户返回 403，防止越权修改。
        """
        item = await _create_rectification_item(
            client, retrospective_id, retro_owner, assignee, auth_header
        )
        iid = item["id"]

        headers = await auth_header(other_user)
        resp = await client.put(
            f"/rectification-items/{iid}",
            json={"status": "IN_PROGRESS"},
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /rectification-items/{iid}/upload-evidence — 上传完成证据
# ===========================================================================

class TestUploadEvidence:
    """责任人上传整改完成证据。"""

    @pytest.mark.asyncio
    async def test_assignee_can_upload_evidence(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：责任人完成整改后上传证据文件（截图、文档等），
        证据是复盘负责人确认完成的前提条件。
        """
        item = await _create_rectification_item(
            client, retrospective_id, retro_owner, assignee, auth_header
        )
        iid = item["id"]

        # 先更新为 IN_PROGRESS
        assignee_headers = await auth_header(assignee)
        await client.put(
            f"/rectification-items/{iid}",
            json={"status": "IN_PROGRESS"},
            headers=assignee_headers,
        )

        # 上传证据（multipart 或 JSON base64，根据实际接口调整）
        evidence_content = b"fake evidence file content"
        resp = await client.post(
            f"/rectification-items/{iid}/upload-evidence",
            files={"file": ("evidence.pdf", io.BytesIO(evidence_content), "application/pdf")},
            headers=assignee_headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "evidence_url" in data or "file_id" in data or "id" in data

    @pytest.mark.asyncio
    async def test_non_assignee_cannot_upload_evidence(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee,
        other_user, auth_header
    ):
        """非责任人不得上传证据，返回 403。"""
        item = await _create_rectification_item(
            client, retrospective_id, retro_owner, assignee, auth_header
        )
        iid = item["id"]

        headers = await auth_header(other_user)
        resp = await client.post(
            f"/rectification-items/{iid}/upload-evidence",
            files={"file": ("evidence.pdf", io.BytesIO(b"content"), "application/pdf")},
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /rectification-items/{iid}/confirm — 复盘负责人确认完成
# ===========================================================================

class TestConfirmRectificationItem:
    """复盘负责人确认整改事项完成。"""

    @pytest_asyncio.fixture
    async def item_with_evidence(
        self, client, retrospective_id, retro_owner, assignee, auth_header
    ):
        """创建整改事项并上传证据，返回 item id。"""
        item = await _create_rectification_item(
            client, retrospective_id, retro_owner, assignee, auth_header
        )
        iid = item["id"]

        assignee_headers = await auth_header(assignee)
        await client.put(
            f"/rectification-items/{iid}",
            json={"status": "IN_PROGRESS"},
            headers=assignee_headers,
        )
        await client.post(
            f"/rectification-items/{iid}/upload-evidence",
            files={"file": ("evidence.pdf", io.BytesIO(b"evidence"), "application/pdf")},
            headers=assignee_headers,
        )
        return iid

    @pytest.mark.asyncio
    async def test_retro_owner_can_confirm_completion(
        self, client: AsyncClient, item_with_evidence, retro_owner, auth_header
    ):
        """
        业务规则：复盘负责人在责任人上传证据后可确认整改完成，
        状态变更为 CLOSED。
        """
        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/rectification-items/{item_with_evidence}/confirm",
            json={"comment": "整改措施已落实，证据充分"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_confirm_without_evidence_returns_400(
        self, client: AsyncClient, retrospective_id, retro_owner, assignee, auth_header
    ):
        """
        业务规则：无完成证据时不得确认完成，返回 400。
        证据是整改闭环的必要条件，防止形式化整改。
        """
        item = await _create_rectification_item(
            client, retrospective_id, retro_owner, assignee, auth_header
        )
        iid = item["id"]

        headers = await auth_header(retro_owner)
        resp = await client.post(
            f"/rectification-items/{iid}/confirm",
            json={"comment": "确认完成"},
            headers=headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "evidence" in str(data).lower() or "证据" in str(data) or "EC" in str(data)

    @pytest.mark.asyncio
    async def test_business_owner_can_close_rectification_item(
        self, client: AsyncClient, item_with_evidence, business_owner, auth_header
    ):
        """
        业务规则：业务负责人也可关闭整改事项，
        提供双重确认机制，确保整改结果得到业务层认可。
        """
        headers = await auth_header(business_owner)
        resp = await client.post(
            f"/rectification-items/{item_with_evidence}/confirm",
            json={"comment": "业务层确认整改已落实"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "CLOSED"

    @pytest.mark.asyncio
    async def test_non_authorized_user_cannot_confirm(
        self, client: AsyncClient, item_with_evidence, other_user, auth_header
    ):
        """非复盘负责人/业务负责人不得确认整改完成，返回 403。"""
        headers = await auth_header(other_user)
        resp = await client.post(
            f"/rectification-items/{item_with_evidence}/confirm",
            json={"comment": "确认"},
            headers=headers,
        )
        assert resp.status_code == 403
