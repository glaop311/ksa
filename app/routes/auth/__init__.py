
from fastapi import APIRouter
from datetime import datetime

from .base import router as base_router
from .otp import router as otp_router
from .oauth import router as oauth_router
from .protected import router as protected_router

router = APIRouter()

router.include_router(base_router, tags=["Base Auth"])
router.include_router(otp_router, prefix="/otp", tags=["OTP Management"])
router.include_router(oauth_router, prefix="/oauth", tags=["OAuth"])
router.include_router(protected_router)
