from hub_bot.callback_data import AppCallback, HomeCallback


def test_app_callback_pack() -> None:
    """Test that AppCallback packs to expected format."""
    callback = AppCallback(app="postbox")
    packed = callback.pack()

    assert packed.startswith("hub")
    assert "postbox" in packed


def test_app_callback_unpack() -> None:
    """Test that AppCallback can be unpacked."""
    callback = AppCallback(app="postbox")
    packed = callback.pack()
    unpacked = AppCallback.unpack(packed)

    assert unpacked.app == "postbox"


def test_home_callback_pack() -> None:
    """Test that HomeCallback packs to expected format."""
    callback = HomeCallback()
    packed = callback.pack()

    assert packed.startswith("hub")
    assert "home" in packed


def test_home_callback_unpack() -> None:
    """Test that HomeCallback can be unpacked."""
    callback = HomeCallback()
    packed = callback.pack()
    unpacked = HomeCallback.unpack(packed)

    assert unpacked.action == "home"


def test_app_callback_namespace() -> None:
    """Test that callback data uses hub namespace."""
    callback = AppCallback(app="postbox")
    packed = callback.pack()

    # Should be in format hub:...
    parts = packed.split(":")
    assert parts[0] == "hub"
