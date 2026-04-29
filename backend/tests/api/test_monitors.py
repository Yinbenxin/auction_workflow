"""
test_monitors.py — 实时监控接口集成测试

覆盖阶段：8. 实时监控
涉及角色：监控人员（monitor）

record_type 枚举：
  normal  — 正常监控数据
  anomaly — 异常事件（需携带 anomaly_type / anomaly_action）
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
    admin = await make_user("monitor_admin", role=Roles.ADMIN)
    headers = await auth_header(admin)
    resp = await client.post(
        "/auctions",
        json={"name": "监控测试竞拍", "auction_date": "2026-04-28", "status": "EXECUTING"},
        headers=headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


@pytest_asyncio.fixture
async def monitor_user(make_user):
    """监控人员用户。"""
    return await make_user("monitor_user", role=Roles.MONITOR)


@pytest_asyncio.fixture
async def trader_user(make_user):
    """交易员用户（用于权限反向验证）。"""
    return await make_user("trader_monitor", role=Roles.TRADER)


# ===========================================================================
# POST /auctions/{id}/monitor-records — 正常监控数据
# ===========================================================================

class TestRecordNormalMonitor:
    """监控人员记录正常监控数据。"""

    @pytest.mark.asyncio
    async def test_monitor_can_record_normal_data(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """
        业务规则：监控人员在竞拍执行期间可提交正常监控记录，
        包含市场价格、系统状态等观测数据。
        """
        headers = await auth_header(monitor_user)
        payload = {
            "record_type": "normal",
            "market_price": 3.82,
            "system_status": "online",
            "note": "市场平稳，无异常",
            "recorded_at": "2026-04-28T10:10:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["record_type"] == "normal"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_normal_record_does_not_require_anomaly_fields(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """正常记录不需要 anomaly_type / anomaly_action 字段。"""
        headers = await auth_header(monitor_user)
        payload = {
            "record_type": "normal",
            "market_price": 3.80,
            "recorded_at": "2026-04-28T10:15:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_non_monitor_cannot_record(
        self, client: AsyncClient, auction_id, trader_user, auth_header
    ):
        """非监控人员角色不得提交监控记录，返回 403。"""
        headers = await auth_header(trader_user)
        payload = {
            "record_type": "normal",
            "market_price": 3.80,
            "recorded_at": "2026-04-28T10:15:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 403


# ===========================================================================
# POST /auctions/{id}/monitor-records — 异常事件
# ===========================================================================

class TestRecordAnomalyMonitor:
    """监控人员记录异常事件。"""

    @pytest.mark.asyncio
    async def test_monitor_can_record_anomaly_event(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """
        业务规则：record_type=anomaly 时必须携带 anomaly_type（异常类型）
        和 anomaly_action（处置措施），用于后续复盘追溯。
        """
        headers = await auth_header(monitor_user)
        payload = {
            "record_type": "anomaly",
            "market_price": 4.10,
            "anomaly_type": "price_spike",
            "anomaly_action": "通知策略负责人，暂停申报",
            "note": "市场价格异常拉升，超出策略触发阈值",
            "recorded_at": "2026-04-28T10:20:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json=payload,
            headers=headers,
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["record_type"] == "anomaly"
        assert data["anomaly_type"] == "price_spike"
        assert data["anomaly_action"] == "通知策略负责人，暂停申报"

    @pytest.mark.asyncio
    async def test_anomaly_record_requires_anomaly_type(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """异常记录缺少 anomaly_type 时返回 422。"""
        headers = await auth_header(monitor_user)
        payload = {
            "record_type": "anomaly",
            "market_price": 4.10,
            "anomaly_action": "暂停申报",
            "recorded_at": "2026-04-28T10:20:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_anomaly_record_requires_anomaly_action(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """异常记录缺少 anomaly_action 时返回 422。"""
        headers = await auth_header(monitor_user)
        payload = {
            "record_type": "anomaly",
            "market_price": 4.10,
            "anomaly_type": "price_spike",
            "recorded_at": "2026-04-28T10:20:00",
        }
        resp = await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 422


# ===========================================================================
# GET /auctions/{id}/monitor-records
# ===========================================================================

class TestGetMonitorRecords:
    """获取监控记录列表。"""

    @pytest_asyncio.fixture(autouse=True)
    async def seed_records(self, client: AsyncClient, auction_id, monitor_user, auth_header):
        """预置一条正常记录和一条异常记录。"""
        headers = await auth_header(monitor_user)
        await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json={
                "record_type": "normal",
                "market_price": 3.80,
                "recorded_at": "2026-04-28T10:00:00",
            },
            headers=headers,
        )
        await client.post(
            f"/auctions/{auction_id}/monitor-records",
            json={
                "record_type": "anomaly",
                "market_price": 4.20,
                "anomaly_type": "system_lag",
                "anomaly_action": "切换备用通道",
                "recorded_at": "2026-04-28T10:30:00",
            },
            headers=headers,
        )

    @pytest.mark.asyncio
    async def test_get_all_monitor_records(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """
        业务规则：不带过滤参数时返回全部监控记录，
        包含正常记录和异常记录。
        """
        headers = await auth_header(monitor_user)
        resp = await client.get(
            f"/auctions/{auction_id}/monitor-records",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_anomaly_records_only(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """
        业务规则：?type=anomaly 过滤参数只返回异常记录，
        便于快速定位需要复盘的事件。
        """
        headers = await auth_header(monitor_user)
        resp = await client.get(
            f"/auctions/{auction_id}/monitor-records?type=anomaly",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert all(r["record_type"] == "anomaly" for r in data)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_normal_records_only(
        self, client: AsyncClient, auction_id, monitor_user, auth_header
    ):
        """?type=normal 过滤参数只返回正常记录。"""
        headers = await auth_header(monitor_user)
        resp = await client.get(
            f"/auctions/{auction_id}/monitor-records?type=normal",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["record_type"] == "normal" for r in data)

    @pytest.mark.asyncio
    async def test_get_monitor_records_unauthorized(
        self, client: AsyncClient, auction_id
    ):
        """未认证请求返回 401。"""
        resp = await client.get(f"/auctions/{auction_id}/monitor-records")
        assert resp.status_code == 401
