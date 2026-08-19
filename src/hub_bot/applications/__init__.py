"""Application registry and authentication handoff."""

from hub_bot.applications.registry import APPS, HubApp, get_app

__all__ = ["APPS", "HubApp", "get_app"]
