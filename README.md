# auction_workflow — 竞拍流程管理系统

## 快速启动

### 前置条件

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+

### 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 创建数据库
psql -U postgres -c "CREATE DATABASE auction_workflow;"

# 配置环境变量
cp .env.example .env  # 或直接创建 .env，见下方说明

# 运行迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

`.env` 内容：

```
DATABASE_URL=postgresql+asyncpg://postgres@localhost/auction_workflow
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |

## 测试账号

密码均为 `password123`。

| 用户名 | 角色 | 说明 |
|--------|------|------|
| `business_owner1` | business_owner | 业务负责人，负责创建竞拍和确认基础信息 |
| `trader1` | trader | 交易员，负责执行竞拍 |
| `reviewer1` | reviewer | 复核员，负责执行前复核和修改审批 |
| `auditor1` | auditor | 审计员，负责策略作废审批 |
| `strategy_owner1` | strategy_owner | 策略负责人，负责策略制定和提交 |

创建测试账号的脚本（首次启动后运行一次）：

```bash
cd backend
source venv/bin/activate
python3 scripts/create_test_users.py
```
