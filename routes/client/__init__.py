from fastapi import APIRouter
from .client import router as client_router
from .event_registration import router as registration_router
from .feedback import router as feedback_router

router = APIRouter()

router.include_router(client_router, tags=["client"])
router.include_router(registration_router, tags=["registration"])
router.include_router(feedback_router, tags=["feedback"])
