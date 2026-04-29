# TDD 测试覆盖率目标与运行命令

## 目录
- [覆盖率目标](#覆盖率目标)
- [后端测试命令](#后端测试命令)
- [前端测试命令](#前端测试命令)
- [覆盖率报告生成](#覆盖率报告生成)

---

## 覆盖率目标

| 模块 | 测试类型 | 覆盖率目标 | 说明 |
|------|----------|-----------|------|
| `backend/app/services/` | 后端单元测试 | **90%** | 状态机、版本管理、审批逻辑是核心，不允许低于此线 |
| `backend/app/api/` | 后端 API 集成测试 | **85%** | 覆盖所有路由的正常路径和主要错误路径 |
| `frontend/src/views/` | 前端组件测试 | **80%** | 覆盖所有页面的核心交互和角色权限分支 |
| 状态机转换逻辑 | 关键业务路径 | **95%** | 每一条状态转换边都必须有对应测试 |
| 审批流校验逻辑 | 关键业务路径 | **95%** | 双人复核、审批状态拦截是制度红线，不允许漏测 |
| 红线字段变更检测 | 关键业务路径 | **95%** | 价格/数量/时点/触发条件变更必须全覆盖 |
| `backend/tests/edge_cases/` | Edge Case 测试 | **100%** | EC-1 到 EC-12 全部场景必须覆盖 |

---

## 后端测试命令

```bash
# 运行全部后端测试
pytest backend/tests/ -v

# 只运行 edge case 测试
pytest backend/tests/edge_cases/ -v

# 只运行单元测试（services 层）
pytest backend/tests/unit/ -v

# 只运行 API 集成测试
pytest backend/tests/integration/ -v

# 运行时显示每个测试的耗时（排查慢测试）
pytest backend/tests/ -v --durations=10

# 失败时立即停止（快速反馈模式）
pytest backend/tests/ -x
```

---

## 前端测试命令

```bash
# 运行全部前端测试（单次）
npx vitest run

# 监听模式（开发时使用）
npx vitest

# 只运行指定测试文件
npx vitest run frontend/tests/LoginView.test.ts

# 运行匹配关键字的测试
npx vitest run --reporter=verbose -t "红线字段"
```

---

## 覆盖率报告生成

```bash
# 后端：生成 HTML 覆盖率报告（需安装 pytest-cov）
pytest backend/tests/ \
  --cov=backend/app \
  --cov-report=html:coverage/backend \
  --cov-report=term-missing \
  --cov-fail-under=85

# 后端：仅输出终端摘要（CI 环境使用）
pytest backend/tests/ \
  --cov=backend/app \
  --cov-report=term-missing

# 前端：生成 V8 覆盖率报告（需在 vitest.config.ts 中配置 coverage provider）
npx vitest run --coverage

# 前端：指定覆盖率输出目录
npx vitest run --coverage --coverage.reportsDirectory=coverage/frontend

# 查看后端 HTML 报告（macOS）
open coverage/backend/index.html

# 查看前端 HTML 报告（macOS）
open coverage/frontend/index.html
```

### vitest.config.ts 覆盖率配置参考

```typescript
// frontend/vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: './coverage/frontend',
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
      include: ['src/views/**', 'src/stores/**', 'src/composables/**'],
      exclude: ['src/main.ts', 'src/router/index.ts'],
    },
  },
})
```

### pytest.ini 覆盖率配置参考

```ini
# backend/pytest.ini
[pytest]
testpaths = tests
asyncio_mode = auto

[coverage:run]
source = app
omit =
    app/main.py
    app/config.py
    */migrations/*

[coverage:report]
fail_under = 85
show_missing = true
```
