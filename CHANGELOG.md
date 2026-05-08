# CHANGELOG

## [2026-05-08] 初始功能建设

### 基础设施
- Docker 方式启动 PostgreSQL 15，简化本地开发环境搭建
- 后端端口调整为 8001，前端 Vite 代理同步更新

### Python 3.14 兼容性修复
- 升级 `pydantic` 至 2.13.4，`pydantic-core` 至 2.46.4（原版本无 3.14 预编译包）
- 升级 `asyncpg` 至 0.31.0（修复 `_PyLong_AsByteArray` 签名变更导致的编译错误）
- 升级 `sqlalchemy` 至 2.0.41（修复 `FastIntFlag.__firstlineno__` 冲突）
- 升级 `alembic` 至 1.18.4
- 移除 `passlib`，改用 `bcrypt` 直接调用（passlib 与新版 bcrypt 不兼容）

### 系统管理员（root）
- 新增 `system_role` 字段（PostgreSQL ENUM：`root` / `user`，默认 `user`）
- 新增后端依赖 `require_root`，保护管理员专属接口
- 新增管理员 API：
  - `GET /auth/admin/users` — 列出所有用户
  - `POST /auth/admin/users` — 创建用户（含系统角色和业务角色）
  - `PUT /auth/admin/users/{user_id}` — 修改系统角色、启用/禁用、业务角色
- 新增初始化脚本 `backend/scripts/create_root.py`（初始密码 `changeme123`）
- 数据库迁移 `014_add_system_role_to_users.py`

### 业务角色管理
- 新增 `user_roles` 字段（PostgreSQL TEXT[]，默认空数组），支持一用户多角色
- 固定三种业务角色（前端常量，不入库）：
  - `trader` — 交易员，负责竞拍现场执行与报价操作
  - `strategist` — 策略师，负责竞拍策略制定与方案审核
  - `delivery_manager` — 交付经理，负责项目整体交付与流程协调
- 数据库迁移 `015_add_user_roles.py`

### 前端
- 新增「用户管理」页面（仅 root 可见）：用户列表、新增用户、编辑角色、启用/禁用
- 路由守卫：非 root 用户访问 `/admin/users` 自动重定向
- 个人信息页：移除"姓名"行，改为展示业务角色名称及说明；无角色时显示"暂未分配"
- 新增前端常量文件 `frontend/src/constants/userRoles.ts`
