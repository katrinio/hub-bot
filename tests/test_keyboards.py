from aiogram.types import InlineKeyboardMarkup

from hub_bot.keyboards import build_app_menu, build_back_to_hub


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
