from hub_bot.applications.registry import HubApp


def render_app_screen(app: HubApp) -> str:
    """Render an application overview screen."""
    lines = [f"{app.emoji} {app.title}", "", app.description]
    if app.planned_features:
        lines.extend(("", "В планах:"))
        lines.extend(f"• {feature}" for feature in app.planned_features)
    return "\n".join(lines)
