"""Tests for selecting the Asahi device monitored by the watcher."""

from unittest.mock import AsyncMock, patch

import pytest

from watcher.parser import DeviceRecord
from watcher.tracking import TRACKED_DEVICE_ID, fetch_tracked_device, select_tracked_device

TRACKED_DEVICE = DeviceRecord(
    device_id="j516sap",
    mac_model="MacBook Pro (16-inch, M3 Pro, 2023)",
    min_ver="14.8.3",
    expert_only=True,
)


def test_select_tracked_device_returns_only_j516sap() -> None:
    other = DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False)

    assert select_tracked_device([other, TRACKED_DEVICE]) == [TRACKED_DEVICE]
    assert TRACKED_DEVICE_ID == "j516sap"


def test_select_tracked_device_fails_when_device_disappears() -> None:
    other = DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False)

    with pytest.raises(ValueError, match="tracked device 'j516sap' is missing"):
        select_tracked_device([other])


def test_select_tracked_device_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="tracked device 'j516sap' occurs more than once"):
        select_tracked_device([TRACKED_DEVICE, TRACKED_DEVICE])


@pytest.mark.asyncio
async def test_fetch_tracked_device_filters_downloaded_devices() -> None:
    other = DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False)

    with patch("watcher.tracking.fetch_devices", new=AsyncMock(return_value=[other, TRACKED_DEVICE])) as fetch:
        records = await fetch_tracked_device("https://example.test/main.py", 5.0)

    assert records == [TRACKED_DEVICE]
    fetch.assert_awaited_once_with("https://example.test/main.py", 5.0)
