from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.customers import router as customers_router
from app.api.routes.leads import router as leads_router
from app.api.routes.opportunities import router as opportunities_router
from app.api.routes.engagements import follow_router, activity_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(customers_router)
api_router.include_router(leads_router)
api_router.include_router(opportunities_router)
api_router.include_router(follow_router)
api_router.include_router(activity_router)
