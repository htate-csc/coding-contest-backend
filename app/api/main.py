from fastapi import APIRouter

from app.api.routes import (
    ai_battles,
    contest_problems,
    contests,
    login,
    private,
    problems,
    submissions,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(contests.router)
api_router.include_router(problems.router)
api_router.include_router(contest_problems.router)
api_router.include_router(submissions.router)
api_router.include_router(ai_battles.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
