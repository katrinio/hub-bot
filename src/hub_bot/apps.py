from dataclasses import dataclass


@dataclass(frozen=True)
class HubApp:
    """Registered Hub application."""

    slug: str
    title: str
    emoji: str


APPS = (
    HubApp(
        slug="postbox",
        title="Postbox",
        emoji="📦",
    ),
)


def get_app(slug: str) -> HubApp | None:
    """Get app by slug or None if not found."""
    for app in APPS:
        if app.slug == slug:
            return app
    return None
