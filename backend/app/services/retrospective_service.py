from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retrospective import Retrospective
from app.models.strategy import StrategyVersion


async def get_retrospective_or_404(
    session: AsyncSession,
    auction_id: UUID,
) -> Retrospective:
    """按 auction_id 查询复盘报告，不存在时抛 404。"""
    result = await session.execute(
        select(Retrospective).where(Retrospective.auction_id == auction_id)
    )
    retro = result.scalar_one_or_none()
    if retro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="复盘报告不存在",
        )
    return retro


async def validate_retrospective_submit(
    auction_id: UUID,
    retrospective: Retrospective,
    session: AsyncSession,
) -> None:
    """
    提交归档前的 5 步校验：

    1. 必须关联最终版本（strategy_versions.status == 'FINAL'）
    2. 临场修改记录必须已闭合（不存在 PENDING_APPROVAL / PENDING_REVIEW 状态的 modification）
    3. 应急执行必须补说明（不存在 PENDING_POST_EXPLANATION / PENDING_DEVIATION_EXPLANATION 状态）
    4. 整改项必须已创建（若 improvement_actions 非空，则 rectification_items 表中必须有关联记录）
    5. 必填项校验：basic_info / strategy_summary / execution_summary / transaction_result /
       deviation_analysis / anomaly_records / confirmation_records / root_cause /
       improvement_actions / strategy_learnings 均不能为空
    """

    # ------------------------------------------------------------------
    # 步骤 1：关联策略版本必须是 FINAL 状态
    # ------------------------------------------------------------------
    sv_result = await session.execute(
        select(StrategyVersion).where(
            StrategyVersion.id == retrospective.strategy_version_id,
            StrategyVersion.auction_id == auction_id,
        )
    )
    sv = sv_result.scalar_one_or_none()
    if sv is None or sv.status != "FINAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="复盘报告必须关联最终版本（status=FINAL）的策略方案",
        )

    # ------------------------------------------------------------------
    # 步骤 2：临场修改记录必须已闭合
    # 使用动态查询避免循环依赖，直接查 modifications 表
    # ------------------------------------------------------------------
    open_mod_result = await session.execute(
        text(
            "SELECT COUNT(*) FROM modifications "
            "WHERE auction_id = :auction_id "
            "AND status IN ('PENDING_APPROVAL', 'PENDING_REVIEW')"
        ),
        {"auction_id": str(auction_id)},
    )
    open_mod_count = open_mod_result.scalar()
    if open_mod_count and open_mod_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"存在 {open_mod_count} 条未闭合的临场修改记录（PENDING_APPROVAL/PENDING_REVIEW），请先处理完毕",
        )

    # ------------------------------------------------------------------
    # 步骤 3：应急执行必须补说明
    # 查 modifications 表中待补说明的应急记录（is_emergency=true 且状态未闭合）
    # ------------------------------------------------------------------
    open_emergency_result = await session.execute(
        text(
            "SELECT COUNT(*) FROM modifications "
            "WHERE auction_id = :auction_id "
            "AND is_emergency = true "
            "AND status IN ('PENDING_POST_EXPLANATION', 'PENDING_DEVIATION_EXPLANATION')"
        ),
        {"auction_id": str(auction_id)},
    )
    open_emergency_count = open_emergency_result.scalar()
    if open_emergency_count and open_emergency_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"存在 {open_emergency_count} 条应急执行记录尚未补充说明（PENDING_POST_EXPLANATION/PENDING_DEVIATION_EXPLANATION）",
        )

    # ------------------------------------------------------------------
    # 步骤 4：若填写了整改项，则 rectification_items 表中必须有关联记录
    # ------------------------------------------------------------------
    if retrospective.improvement_actions and retrospective.improvement_actions.strip():
        rectification_result = await session.execute(
            text(
                "SELECT COUNT(*) FROM rectification_items "
                "WHERE retrospective_id = :retrospective_id"
            ),
            {"retrospective_id": str(retrospective.id)},
        )
        rectification_count = rectification_result.scalar()
        if not rectification_count or rectification_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="填写了整改措施（improvement_actions），但 rectification_items 表中尚无关联整改项记录",
            )

    # ------------------------------------------------------------------
    # 步骤 5：必填项校验
    # ------------------------------------------------------------------
    required_text_fields = [
        ("deviation_analysis", "偏差分析"),
        ("anomaly_records", "异常记录"),
        ("confirmation_records", "确认记录"),
        ("root_cause", "根因分析"),
        ("improvement_actions", "整改措施"),
        ("strategy_learnings", "策略经验"),
    ]
    required_json_fields = [
        ("basic_info", "基本信息"),
        ("strategy_summary", "策略摘要"),
        ("execution_summary", "执行摘要"),
        ("transaction_result", "成交结果"),
    ]

    missing: list[str] = []

    for field, label in required_text_fields:
        val = getattr(retrospective, field, None)
        if not val or not str(val).strip():
            missing.append(label)

    for field, label in required_json_fields:
        val = getattr(retrospective, field, None)
        if not val:
            missing.append(label)

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"以下必填项不能为空：{', '.join(missing)}",
        )
