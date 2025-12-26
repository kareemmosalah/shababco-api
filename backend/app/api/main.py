from fastapi import APIRouter

from app.api.routes import attendees, auth_google, events, items, login, private, users, utils, webhooks, tickets
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(attendees.router)  # Attendee authentication
api_router.include_router(auth_google.router)  # Google OAuth
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(events.router)
api_router.include_router(tickets.router)
api_router.include_router(webhooks.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)

