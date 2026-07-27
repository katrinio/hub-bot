"""Tests for app screen renderers."""

from __future__ import annotations

from hub_bot.apps import HubApp
from hub_bot.renderers import render_app_screen


class TestRenderAppScreen:
    """Tests for render_app_screen function."""

    def test_renders_app_title_and_emoji(self) -> None:
        """Renderer should include app emoji and title."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="A test application.",
        )
        screen = render_app_screen(app)

        assert "🧪" in screen
        assert "Test App" in screen

    def test_renders_description(self) -> None:
        """Renderer should include app description."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="This is a test description.",
        )
        screen = render_app_screen(app)

        assert "This is a test description." in screen

    def test_renders_planned_features_with_bullets(self) -> None:
        """Renderer should show planned features with bullet points."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="A test application.",
            planned_features=("Feature 1", "Feature 2", "Feature 3"),
        )
        screen = render_app_screen(app)

        assert "В планах:" in screen
        assert "• Feature 1" in screen
        assert "• Feature 2" in screen
        assert "• Feature 3" in screen

    def test_empty_roadmap_no_header(self) -> None:
        """Renderer should not show roadmap header if planned_features is empty."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="A test application.",
            planned_features=(),
        )
        screen = render_app_screen(app)

        assert "В планах:" not in screen
        assert "•" not in screen

    def test_max_four_features(self) -> None:
        """Renderer should handle max 4 planned features."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="A test application.",
            planned_features=(
                "Feature 1",
                "Feature 2",
                "Feature 3",
                "Feature 4",
            ),
        )
        screen = render_app_screen(app)

        assert "• Feature 1" in screen
        assert "• Feature 4" in screen
        assert screen.count("•") == 4

    def test_single_feature(self) -> None:
        """Renderer should handle single planned feature."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="A test application.",
            planned_features=("Only feature",),
        )
        screen = render_app_screen(app)

        assert "В планах:" in screen
        assert "• Only feature" in screen

    def test_postbox_description(self) -> None:
        """Postbox should have a description."""
        from hub_bot.apps import APPS

        postbox = None
        for app in APPS:
            if app.slug == "postbox":
                postbox = app
                break

        assert postbox is not None
        assert postbox.description
        assert len(postbox.description) > 0

    def test_postbox_has_planned_features(self) -> None:
        """Postbox should have 2-4 planned features."""
        from hub_bot.apps import APPS

        postbox = None
        for app in APPS:
            if app.slug == "postbox":
                postbox = app
                break

        assert postbox is not None
        assert len(postbox.planned_features) >= 2
        assert len(postbox.planned_features) <= 4

    def test_screen_format_structure(self) -> None:
        """Screen should have proper structure with newlines."""
        app = HubApp(
            slug="test",
            title="Test App",
            emoji="🧪",
            description="Description.",
            planned_features=("Feature 1",),
        )
        screen = render_app_screen(app)

        # Check structure: title, blank line, description, blank line, features
        lines = screen.split("\n")
        assert len(lines) >= 5
        assert lines[0] == "🧪 Test App"
        assert lines[1] == ""
        assert lines[2] == "Description."
        assert lines[3] == ""
        assert lines[4] == "В планах:"
