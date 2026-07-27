from hub_bot.apps import APPS, get_app


def test_postbox_registered() -> None:
    """Test that Postbox is registered in APPS."""
    assert len(APPS) > 0
    postbox = next((app for app in APPS if app.slug == "postbox"), None)
    assert postbox is not None
    assert postbox.title == "Postbox"
    assert postbox.emoji == "📦"


def test_get_app_postbox() -> None:
    """Test that Postbox can be retrieved by slug."""
    app = get_app("postbox")
    assert app is not None
    assert app.slug == "postbox"
    assert app.title == "Postbox"
    assert app.emoji == "📦"


def test_get_app_nonexistent() -> None:
    """Test that get_app returns None for nonexistent app."""
    app = get_app("nonexistent")
    assert app is None
