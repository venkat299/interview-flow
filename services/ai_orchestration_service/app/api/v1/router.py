from fastapi import APIRouter
from .endpoints import interview

api_router = APIRouter()
api_router.include_router(interview.router, prefix="/interview", tags=["interview"])
