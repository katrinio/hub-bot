"""Business concepts that do not depend on Telegram or persistence."""

from hub_bot.domain.apps import APPS, HubApp, get_app

__all__ = ["APPS", "HubApp", "get_app"]
