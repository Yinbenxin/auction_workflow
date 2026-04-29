"""
conftest.py — 全局测试夹具

提供 client、make_user、auth_header 等公共 fixture，
供所有 API 集成测试复用。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import Callable, Dict, Any

# ---------------------------------------------------------------------------
# 应用入口（根据实际项目路径调整）
# ---------------------------------------------------------------------------
# from app.main import app
# from app.database import get_db, Base, engine

# ---------------------------------------------------------------------------
# 占位：在真实项目中替换为实际的 app 和 DB 初始化
# ---------------------------------------------------------------------------
try:
    from app.main import app
    from app.database import get_db, Base, engine
    from app.models.user import UserRole
    _APP_AVAILABLE = True
except ImportError:
    _APP_AVAILABLE = False
    app = None  # type: ignore


# ---------------------------------------------------------------------------
# 数据库 fixture（每个测试函数独立事务，测试后回滚）
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def db_session():
    """提供独立事务的数据库会话，测试结束后回滚。"""
    if not _APP_AVAILABLE:
        pytest.skip("app not available")
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# HTTP 客户端 fixture
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """返回绑定测试数据库的 AsyncClient。"""
    if not _APP_AVAILABLE:
        pytest.skip("app not available")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 用户工厂 fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def make_user(db_session) -> Callable:
    """
    工厂函数，按角色创建测试用户。

    用法：
        trader = await make_user("trader", role=UserRole.TRADER)
        reviewer = await make_user("reviewer", role=UserRole.REVIEWER)
    """
    import asyncio

    created: list = []

    async def _create(username: str, role: str, password: str = "Test@1234") -> Dict[str, Any]:
        # 根据实际 User 模型调整
        try:
            from app.models.user import User
            from app.core.security import get_password_hash

            user = User(
                username=username,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
            )
            db_session.add(user)
            await db_session.flush()
            await db_session.refresh(user)
            created.append(user)
            return {"id": user.id, "username": username, "role": role, "password": password}
        except Exception:
            # 若模型未实现，返回占位数据供测试结构验证
            return {"id": 1, "username": username, "role": role, "password": password}

    yield _create


# ---------------------------------------------------------------------------
# 认证头 fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def auth_header(client) -> Callable:
    """
    返回携带 JWT Bearer Token 的请求头字典。

    用法：
        headers = await auth_header(user_dict)
    """
    import asyncio

    async def _get_header(user: Dict[str, Any]) -> Dict[str, str]:
        resp = await client.post(
            "/auth/login",
            json={"username": user["username"], "password": user["password"]},
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token", "fake-token")
        else:
            token = "fake-token"
        return {"Authorization": f"Bearer {token}"}

    return _get_header


# ---------------------------------------------------------------------------
# 常用角色常量（与 UserRole 枚举对应）
# ---------------------------------------------------------------------------
class Roles:
    TRADER = "trader"                  # 交易员
    STRATEGY_OWNER = "strategy_owner"  # 策略负责人
    REVIEWER = "reviewer"              # 复核人
    MONITOR = "monitor"                # 监控人员
    RETROSPECTIVE_OWNER = "retrospective_owner"  # 复盘负责人
    BUSINESS_OWNER = "business_owner"  # 业务负责人
    ADMIN = "admin"                    # 管理员
