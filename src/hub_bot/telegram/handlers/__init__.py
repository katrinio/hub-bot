"""Feature-based Telegram router composition."""

from aiogram import Router

from hub_bot.telegram.handlers.applications import router as applications_router
from hub_bot.telegram.handlers.asahi_devices import router as asahi_devices_router
from hub_bot.telegram.handlers.feedback import router as feedback_router
from hub_bot.telegram.handlers.stats import router as stats_router

router = Router(name=__name__)
router.include_routers(applications_router, stats_router, asahi_devices_router, feedback_router)

__all__ = ["router"]
