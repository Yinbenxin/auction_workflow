from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.strategy import StrategyVersion

# ---------------------------------------------------------------------------
# 状态机
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, list[str]] = {
    "DRAFT":     ["PENDING", "VOIDED"],
    "PENDING":   ["DRAFT", "CONFIRMED"],
    "CONFIRMED": ["FINAL", "VOIDED"],
    "FINAL":     ["VOIDED"],
    "VOIDED":    [],
}

# ---------------------------------------------------------------------------
# 红线字段
# ---------------------------------------------------------------------------

RED_LINE_FIELDS: set[str] = {
    "bid_price",
    "bid_quantity",
    "bid_time_points",
    "trigger_conditions",
    "fallback_plan",
    "applicable_scenarios",
}


def transition_status(current: str, target: str) -> None:
    """校验状态流转是否合法，非法时抛 ValueError。"""
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise ValueError(
            f"不允许从 {current!r} 流转到 {target!r}，"
            f"合法目标状态：{allowed or '无'}"
        )


def has_red_line_change(old: StrategyVersion, new_data: dict[str, Any]) -> bool:
    """检测 new_data 中是否包含对红线字段的实质性变更。"""
    for field in RED_LINE_FIELDS:
        if field not in new_data:
            continue
        new_val = new_data[field]
        old_val = getattr(old, field, None)
        # Decimal vs float/str 统一转 str 比较
        if str(new_val) != str(old_val):
            return True
    return False


async def update_with_optimistic_lock(
    session: AsyncSession,
    model: type,
    record_id: UUID,
    expected_version: int,
    updates: dict[str, Any],
) -> None:
    """
    乐观锁更新：仅当 id 匹配且 version == expected_version 时执行更新，
    同时将 version 自增 1。rowcount == 0 时抛 HTTP 409。
    """
    updates_with_version = {**updates, "version": expected_version + 1}
    stmt = (
        update(model)
        .where(model.id == record_id, model.version == expected_version)
        .values(**updates_with_version)
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="数据已被其他操作修改，请刷新后重试（乐观锁冲突）",
        )


async def get_strategy_or_404(
    session: AsyncSession,
    auction_id: UUID,
    strategy_id: UUID,
) -> StrategyVersion:
    """按 auction_id + id 查询策略版本，不存在时抛 404。"""
    result = await session.execute(
        select(StrategyVersion).where(
            StrategyVersion.id == strategy_id,
            StrategyVersion.auction_id == auction_id,
        )
    )
    sv = result.scalar_one_or_none()
    if sv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="策略版本不存在",
        )
    return sv
