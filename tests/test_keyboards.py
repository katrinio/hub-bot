from aiogram.types import InlineKeyboardMarkup

from hub_bot.keyboards import (
    build_app_keyboard,
    build_app_menu,
    build_back_to_hub,
    build_feedback_form_keyboard,
    build_postbox_auth_keyboard,
)


def test_app_menu_contains_postbox() -> None:
    """Test that application menu contains Postbox button."""
    keyboard = build_app_menu()
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) > 0

    # Check that first row contains Postbox button
    first_row = keyboard.inline_keyboard[0]
    assert len(first_row) == 1
    button = first_row[0]
    assert "Postbox" in button.text
    assert "📦" in button.text


def test_app_menu_callback_data() -> None:
    """Test that callback data is correctly formatted."""
    keyboard = build_app_menu()
    first_row = keyboard.inline_keyboard[0]
    button = first_row[0]

    # Callback data should be packed in hub:postbox format
    assert button.callback_data is not None
    assert "hub" in button.callback_data
    assert "postbox" in button.callback_data


def test_app_menu_reflects_registry() -> None:
    """Test that menu is built from registry, not hardcoded."""
    from hub_bot.apps import APPS

    keyboard = build_app_menu()
    assert len(keyboard.inline_keyboard) == len(APPS)


def test_back_to_hub_button() -> None:
    """Test that back to Hub button is correctly formatted."""
    keyboard = build_back_to_hub()
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 1

    button = keyboard.inline_keyboard[0][0]
    assert "The Hub" in button.text
    assert "←" in button.text


def test_back_to_hub_callback_data() -> None:
    """Test that back to Hub callback data is correctly formatted."""
    keyboard = build_back_to_hub()
    button = keyboard.inline_keyboard[0][0]

    assert button.callback_data is not None
    assert "hub" in button.callback_data
    assert "home" in button.callback_data


def test_postbox_auth_keyboard_structure() -> None:
    """Test that Postbox auth keyboard has correct structure."""
    auth_url = "https://postbox.finpipe.net/auth/hub?token=abc123"
    keyboard = build_postbox_auth_keyboard(auth_url)

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 4

    # First row: open button
    open_row = keyboard.inline_keyboard[0]
    assert len(open_row) == 1
    open_button = open_row[0]
    assert "Postbox" in open_button.text
    assert "↗" in open_button.text

    # Second row: refresh button
    refresh_row = keyboard.inline_keyboard[1]
    assert len(refresh_row) == 1
    refresh_button = refresh_row[0]
    assert "Обновить" in refresh_button.text
    assert "🔄" in refresh_button.text

    # Third row: feedback button
    feedback_row = keyboard.inline_keyboard[2]
    assert len(feedback_row) == 1
    feedback_button = feedback_row[0]
    assert "Обратная связь" in feedback_button.text
    assert "💬" in feedback_button.text

    # Fourth row: back button
    back_row = keyboard.inline_keyboard[3]
    assert len(back_row) == 1
    back_button = back_row[0]
    assert "The Hub" in back_button.text
    assert "←" in back_button.text


def test_postbox_auth_keyboard_url_button() -> None:
    """Test that open button contains correct URL."""
    auth_url = "https://postbox.finpipe.net/auth/hub?token=abc123"
    keyboard = build_postbox_auth_keyboard(auth_url)

    open_button = keyboard.inline_keyboard[0][0]
    assert open_button.url == auth_url


def test_postbox_auth_keyboard_back_button_callback() -> None:
    """Test that back button has correct callback data."""
    auth_url = "https://postbox.finpipe.net/auth/hub?token=abc123"
    keyboard = build_postbox_auth_keyboard(auth_url)

    back_button = keyboard.inline_keyboard[3][0]
    assert back_button.callback_data is not None
    assert "hub" in back_button.callback_data
    assert "home" in back_button.callback_data


def test_build_app_keyboard_structure() -> None:
    """Test that generic app keyboard has correct structure."""
    from hub_bot.apps import get_app

    app = get_app("postbox")
    assert app is not None

    keyboard = build_app_keyboard(app)
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 2

    # First row: feedback button
    feedback_row = keyboard.inline_keyboard[0]
    assert len(feedback_row) == 1
    feedback_button = feedback_row[0]
    assert "Обратная связь" in feedback_button.text
    assert "💬" in feedback_button.text

    # Second row: back button
    back_row = keyboard.inline_keyboard[1]
    assert len(back_row) == 1
    back_button = back_row[0]
    assert "The Hub" in back_button.text
    assert "←" in back_button.text


def test_build_feedback_form_keyboard_structure() -> None:
    """Test that feedback form keyboard has cancel button."""
    keyboard = build_feedback_form_keyboard()
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 1

    # Cancel button
    cancel_row = keyboard.inline_keyboard[0]
    assert len(cancel_row) == 1
    cancel_button = cancel_row[0]
    assert "Отмена" in cancel_button.text
