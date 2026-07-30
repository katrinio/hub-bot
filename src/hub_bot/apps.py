from dataclasses import dataclass


@dataclass(frozen=True)
class HubApp:
    """Registered Hub application."""

    slug: str
    title: str
    emoji: str
    description: str
    planned_features: tuple[str, ...] = ()
    auth_path: str | None = None  # e.g., "auth/hub" for Postbox


APPS = (
    HubApp(
        slug="postbox",
        title="Postbox",
        emoji="📦",
        description="Трекер обычной почты и отправлений.",
        planned_features=(
            "- удаление записи из журнала",
            "- удаление всех данных пользователя (сброс профиля)",
            "- небольшие UI/UX-полировки по мере использования",
        ),
        auth_path="auth/hub",
    ),
)


def get_app(slug: str) -> HubApp | None:
    """Get app by slug or None if not found."""
    for app in APPS:
        if app.slug == slug:
            return app
    return None
