"""创建测试用户脚本，首次启动后运行一次。"""
import asyncio
import sys
import uuid

sys.path.insert(0, ".")

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User


TEST_USERS = [
    {"username": "business_owner1", "role": "business_owner", "full_name": "业务负责人一"},
    {"username": "trader1", "role": "trader", "full_name": "交易员一"},
    {"username": "reviewer1", "role": "reviewer", "full_name": "复核员一"},
    {"username": "auditor1", "role": "auditor", "full_name": "审计员一"},
    {"username": "strategy_owner1", "role": "strategy_owner", "full_name": "策略负责人一"},
]

PASSWORD = "password123"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        for u in TEST_USERS:
            user = User(
                id=uuid.uuid4(),
                username=u["username"],
                hashed_password=get_password_hash(PASSWORD),
                role=u["role"],
                full_name=u["full_name"],
            )
            db.add(user)
        await db.commit()

    print("测试用户创建成功（密码均为 password123）：")
    for u in TEST_USERS:
        print(f"  {u['username']}  role={u['role']}")


if __name__ == "__main__":
    asyncio.run(main())
