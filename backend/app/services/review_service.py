from uuid import UUID

from fastapi import HTTPException, status

CHECKLIST_KEYS = [f"item_{i}" for i in range(1, 14)]


def validate_dual_review(configurer_id: UUID, reviewer_id: UUID) -> None:
    """配置人与复核人不能是同一人（双人复核制度红线）。"""
    if configurer_id == reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": 400,
                "data": None,
                "message": "配置人与复核人不能是同一人，违反双人复核制度",
            },
        )


def validate_checklist_complete(checklist: dict) -> bool:
    """检查 item_1~item_13 是否全部为 True。

    Returns True if all 13 items are checked, False otherwise.
    """
    return all(checklist.get(key) is True for key in CHECKLIST_KEYS)
