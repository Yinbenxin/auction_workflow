# auction_workflow — 竞拍流程管理系统

## 快速启动

### 前置条件

- Python 3.12+
- Node.js 18+
- PostgreSQL 15+（或 Docker）

### 数据库（Docker 方式）

```bash
docker run -d --name pg-auction -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=auction_workflow -p 5432:5432 postgres:15
```

### 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install --prefer-binary -r requirements.txt

cp .env.example .env           # 按需编辑

python -m alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 8951 --reload
```

`.env` 内容：

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/auction_workflow
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
| 后端 API | http://localhost:8951 |
| API 文档 (Swagger) | http://localhost:8951/docs |

## 初始化脚本（首次启动后各运行一次）

```bash
cd backend
venv\Scripts\activate

# 创建测试账号（密码均为 password123）
python scripts/create_test_users.py

# 创建系统管理员 root（密码 password123）
python scripts/create_root.py
```

## 账号说明

### 系统管理员

| 用户名 | 初始密码 | 说明 |
|--------|----------|------|
| `root` | `password123` | 系统管理员，可管理账号和分配业务角色 |

### 测试账号（密码均为 `password123`）

| 用户名 | 说明 |
|--------|------|
| `business_owner1` | 业务负责人 |
| `trader1` | 交易员 |
| `reviewer1` | 复核员 |
| `auditor1` | 审计员 |
| `strategy_owner1` | 策略负责人 |

## 业务角色

用户的业务角色由管理员在「用户管理」页面分配，支持多选：

| 角色 | 说明 |
|------|------|
| 交易员 | 负责竞拍现场执行与报价操作 |
| 策略师 | 负责竞拍策略制定与方案审核 |
| 交付经理 | 负责项目整体交付与流程协调 |

## Python 3.14 兼容说明

项目依赖在 Python 3.14 下需使用以下版本（已在 requirements.txt 中固定）：

- `pydantic` / `pydantic-core`：需 2.13+ 版本
- `asyncpg`：需 0.31+ 版本
- `sqlalchemy`：需 2.0.41+ 版本
- `bcrypt`：需 4.0.1（passlib 与新版 bcrypt 不兼容，已直接使用 bcrypt）
- `alembic`：需 1.14+ 版本

## 变更记录

详见 [CHANGELOG.md](./CHANGELOG.md)

