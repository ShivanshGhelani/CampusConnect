from fastapi import APIRouter
from .admin.dashboard import router as dashboard_router
from .admin.auth import router as admin_auth_router
from .admin.events import router as events_router
from .admin.email_reminders import router as email_reminders_router
# from .admin.scheduler import router as scheduler_router

router = APIRouter(prefix="/admin", tags=["admin"])

# Include all admin sub-routers
router.include_router(dashboard_router)
router.include_router(admin_auth_router)
router.include_router(events_router)
router.include_router(email_reminders_router)
# router.include_router(scheduler_router)