from fastapi import APIRouter

from app.api.v1 import auth, auctions, confirmations, executions, modifications, monitors, rectifications, retrospectives, reviews, strategies, task_configs

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(auctions.router, prefix="/auctions", tags=["auctions"])
router.include_router(confirmations.router, prefix="/confirmations", tags=["confirmations"])
router.include_router(
    monitors.router,
    prefix="/auctions/{auction_id}/monitor-records",
    tags=["monitor-records"],
)
router.include_router(task_configs.router, prefix="/auctions", tags=["task-configs"])
router.include_router(executions.router, prefix="/auctions", tags=["executions"])
router.include_router(reviews.router, prefix="/auctions", tags=["reviews"])
router.include_router(
    strategies.router,
    prefix="/auctions/{auction_id}/strategies",
    tags=["strategies"],
)
router.include_router(
    modifications.router,
    prefix="/auctions/{auction_id}/modifications",
    tags=["modifications"],
)
router.include_router(retrospectives.router, prefix="/auctions", tags=["retrospectives"])
router.include_router(
    rectifications.retrospectives_router,
    prefix="/retrospectives",
    tags=["rectification-items"],
)
router.include_router(
    rectifications.items_router,
    prefix="/rectification-items",
    tags=["rectification-items"],
)
