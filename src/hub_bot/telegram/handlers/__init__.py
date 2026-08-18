"""Feature-based Telegram router composition."""

from aiogram import Router

from hub_bot.telegram.handlers.devices import router as devices_router
from hub_bot.telegram.handlers.feedback import router as feedback_router
from hub_bot.telegram.handlers.navigation import router as navigation_router
from hub_bot.telegram.handlers.stats import router as stats_router

router = Router(name=__name__)
router.include_routers(navigation_router, stats_router, devices_router, feedback_router)

__all__ = ["router"]
