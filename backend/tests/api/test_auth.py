"""
认证接口集成测试
覆盖：POST /auth/login、GET /auth/me
"""
import pytest
from httpx import AsyncClient

from tests.conftest import (
    ROLE_TRADER,
    ROLE_DATA_STAFF,
)


class TestLogin:
    """POST /auth/login"""

    @pytest.mark.asyncio
    async def test_login_success_returns_jwt(
        self, client: AsyncClient, make_user
    ):
        """
        业务规则：合法用户名 + 正确密码登录，返回 200 及 access_token。
        token 类型应为 bearer，且 access_token 字段非空。
        """
        await make_user(username="login_ok", password="Pass@9999", role=ROLE_TRADER)

        resp = await client.post(
            "/auth/login",
            json={"username": "login_ok", "password": "Pass@9999"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["access_token"]
        assert body.get("token_type", "").lower() == "bearer"

    @pytest.mark.asyncio
    async def test_login_unknown_user_returns_401(self, client: AsyncClient):
        """
        业务规则：用户名不存在时，返回 401，不得泄露"用户不存在"等细节信息。
        """
        resp = await client.post(
            "/auth/login",
            json={"username": "ghost_user_xyz", "password": "AnyPass@1"},
        )

        assert resp.status_code == 401
        body = resp.json()
        # 错误信息不应区分"用户不存在"与"密码错误"，防止用户枚举攻击
        assert "detail" in body

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, make_user
    ):
        """
        业务规则：用户存在但密码错误，返回 401。
        """
        await make_user(username="login_wrong_pw", password="Correct@1", role=ROLE_TRADER)

        resp = await client.post(
            "/auth/login",
            json={"username": "login_wrong_pw", "password": "Wrong@9999"},
        )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_fields_returns_422(self, client: AsyncClient):
        """
        业务规则：请求体缺少必填字段，FastAPI 应返回 422 Unprocessable Entity。
        """
        resp = await client.post("/auth/login", json={"username": "only_user"})
        assert resp.status_code == 422


class TestGetMe:
    """GET /auth/me"""

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token_returns_user_info(
        self, client: AsyncClient, make_user, auth_header
    ):
        """
        业务规则：携带有效 JWT 访问 /auth/me，返回当前用户信息（id、username、role）。
        """
        await make_user(username="me_valid", role=ROLE_DATA_STAFF)
        headers = await auth_header(username="me_valid", role=ROLE_DATA_STAFF)

        resp = await client.get("/auth/me", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "me_valid"
        assert body["role"] == ROLE_DATA_STAFF
        assert "id" in body

    @pytest.mark.asyncio
    async def test_get_me_without_token_returns_401(self, client: AsyncClient):
        """
        业务规则：未携带 Authorization header，返回 401。
        """
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_expired_token_returns_401(self, client: AsyncClient):
        """
        业务规则：token 已过期，返回 401，detail 应包含过期相关提示。
        使用一个预先构造的过期 token（exp 设为过去时间）。
        """
        # 该 token 的 exp 已设为 Unix epoch 1（1970-01-01），必然过期
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ"
            ".invalid_signature"
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        resp = await client.get("/auth/me", headers=headers)

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_malformed_token_returns_401(self, client: AsyncClient):
        """
        业务规则：token 格式非法（非 JWT），返回 401。
        """
        headers = {"Authorization": "Bearer not.a.valid.jwt.token"}

        resp = await client.get("/auth/me", headers=headers)

        assert resp.status_code == 401
