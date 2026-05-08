"""创建系统管理员 root 账号，已存在则跳过。

用法：
  cd backend
  venv/Scripts/python scripts/create_root.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User

ROOT_USERNAME = "root"
ROOT_PASSWORD = "password123"
ROOT_FULL_NAME = "系统管理员"


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == ROOT_USERNAME))
        if result.scalar_one_or_none() is not None:
            print(f"用户 '{ROOT_USERNAME}' 已存在，跳过创建。")
            return

        root_user = User(
            username=ROOT_USERNAME,
            hashed_password=get_password_hash(ROOT_PASSWORD),
            full_name=ROOT_FULL_NAME,
            system_role="root",
        )
        session.add(root_user)
        await session.commit()
        print(f"root 账号创建成功，初始密码：{ROOT_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
