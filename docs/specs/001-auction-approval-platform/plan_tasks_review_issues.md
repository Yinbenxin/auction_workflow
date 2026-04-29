# Plan / Tasks 四次评审问题清单

评审对象：

- `docs/specs/001-auction-approval-platform/plan.md`
- `docs/specs/001-auction-approval-platform/tasks.md`

对照依据：

- `docs/specs/001-auction-approval-platform/spec.md`
- `竞拍流程规范落地方案.md`

## 评审结论

本轮复查后，上一轮保留的 `task_configs` 表缺少章节标题问题已修复。

当前 `plan.md` 和 `tasks.md` 已基本合理，未发现需要继续保留在问题清单中的阻塞性或一致性问题，可作为后续 API、DB、后端任务和前端任务实现的基础。

## 本轮已确认修复的问题

### 1. `task_configs` 表章节标题已补充

**所在文件：** `docs/specs/001-auction-approval-platform/plan.md`  
**所在章节：** `数据结构` → `task_configs（任务配置清单表）`

**原问题：**

`confirmations（确认记录表）` 后直接进入任务配置字段表，缺少：

```md
### task_configs（任务配置清单表）
```

导致目录锚点失效，并且容易混淆 `confirmations` 与 `task_configs` 的表边界。

**当前状态：已修复**

当前 `plan.md` 已补充：

```md
### task_configs（任务配置清单表）
```

目录锚点与正文标题已对齐。

## 已确认同步的关键内容

- `plan.md` 目录结构代码块已关闭，Markdown 结构正常。
- 前端目录树结构已修正，`retrospectives/` 与 `task-configs/` 层级清晰。
- `users` 角色枚举已包含 `auditor` 审核人。
- `task_configs` 已覆盖任务顺序、启停状态、垫子策略、补量策略、兜底任务和附件。
- `pre_execution_reviews` 已同步 13 项复核清单。
- `modifications` 表已支持申请、审批、复核、执行、应急、偏差、附件等字段。
- 异常修改接口已覆盖 `emergency-execute`、`approve`、`reject`、`review`、`review-reject`、`execute`、`post-explanation`。
- 复盘提交校验已覆盖最终版本、临场修改闭合、应急补说明/偏差标记、整改事项和必填项。
- `tasks.md` 中 T16/T23/T24/T27 已同步最新 spec 的核心流程和字段。
- `tasks.md` 的完整度检查点已移除旧版临场修改 `confirm` 口径。

## 剩余问题

暂无。

## 后续建议

虽然当前未发现需保留的问题，但进入实现阶段前建议继续注意：

- 根据 `plan.md` 中的状态枚举，在后端模型和 Pydantic schema 中统一命名，避免状态值出现大小写或中英文混用。
- 为临场修改状态机、复盘归档校验、13 项复核校验补充后端单元测试。
- 前端按角色隐藏不可操作按钮，避免仅依赖后端权限报错。
- `tasks.md` 中完整度检查点目前仍是未勾选状态，建议在实现完成或逐项验收后再勾选。

