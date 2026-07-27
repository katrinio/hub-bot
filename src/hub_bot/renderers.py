"""Renderers for Hub Bot screens."""

from hub_bot.apps import HubApp


def render_app_screen(app: HubApp) -> str:
    """Render application screen with description and roadmap.

    Args:
        app: HubApp instance with metadata

    Returns:
        Formatted screen text
    """
    lines = [f"{app.emoji} {app.title}", "", app.description]

    if app.planned_features:
        lines.append("")
        lines.append("В планах:")
        for feature in app.planned_features:
            lines.append(f"• {feature}")

    return "\n".join(lines)
