"""Tests for /devices caching, single-flight refresh, and cooldown."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from hub_bot.services.device_catalog import DEVICE_CACHE_TTL_SECONDS, DeviceCatalog, RequestCooldown
from hub_bot.watcher import DeviceRecord

RECORDS = [DeviceRecord("j274ap", "Mac mini (M1, 2020)", "11.0", False)]


def test_default_cache_ttl_is_ten_minutes() -> None:
    assert DEVICE_CACHE_TTL_SECONDS == 600


@pytest.mark.asyncio
async def test_catalog_caches_devices_for_ttl() -> None:
    now = [100.0]
    fetcher = AsyncMock(return_value=RECORDS)
    catalog = DeviceCatalog(fetcher=fetcher, ttl_seconds=600, clock=lambda: now[0])

    first = await catalog.get_devices()
    now[0] += 599
    second = await catalog.get_devices()

    assert first == second == RECORDS
    fetcher.assert_awaited_once()


@pytest.mark.asyncio
async def test_catalog_refreshes_after_ttl() -> None:
    now = [100.0]
    updated = [DeviceRecord("j433ap", "iMac (24-inch, M3, 2023)", "14.8.3", True)]
    fetcher = AsyncMock(side_effect=[RECORDS, updated])
    catalog = DeviceCatalog(fetcher=fetcher, ttl_seconds=600, clock=lambda: now[0])

    assert await catalog.get_devices() == RECORDS
    now[0] += 600
    assert await catalog.get_devices() == updated
    assert fetcher.await_count == 2


@pytest.mark.asyncio
async def test_catalog_allows_only_one_active_fetch() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    fetch_count = 0

    async def fetcher() -> list[DeviceRecord]:
        nonlocal fetch_count
        fetch_count += 1
        started.set()
        await release.wait()
        return RECORDS

    catalog = DeviceCatalog(fetcher=fetcher)
    first = asyncio.create_task(catalog.get_devices())
    await started.wait()
    second = asyncio.create_task(catalog.get_devices())
    await asyncio.sleep(0)

    assert fetch_count == 1
    release.set()
    assert await asyncio.gather(first, second) == [RECORDS, RECORDS]
    assert fetch_count == 1


@pytest.mark.asyncio
async def test_catalog_shares_fetch_failure_with_concurrent_callers() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    fetch_count = 0

    async def fetcher() -> list[DeviceRecord]:
        nonlocal fetch_count
        fetch_count += 1
        started.set()
        await release.wait()
        raise OSError("GitHub unavailable")

    catalog = DeviceCatalog(fetcher=fetcher)
    first = asyncio.create_task(catalog.get_devices())
    await started.wait()
    second = asyncio.create_task(catalog.get_devices())
    await asyncio.sleep(0)
    release.set()
    results = await asyncio.gather(first, second, return_exceptions=True)

    assert fetch_count == 1
    assert all(isinstance(result, OSError) for result in results)


@pytest.mark.asyncio
async def test_catalog_uses_last_known_good_after_network_failure() -> None:
    now = [100.0]
    fetcher = AsyncMock(side_effect=[RECORDS, OSError("GitHub unavailable")])
    catalog = DeviceCatalog(fetcher=fetcher, ttl_seconds=10, failure_retry_seconds=5, clock=lambda: now[0])

    assert await catalog.get_devices() == RECORDS
    now[0] += 10
    assert await catalog.get_devices() == RECORDS
    now[0] += 4
    assert await catalog.get_devices() == RECORDS
    assert fetcher.await_count == 2


@pytest.mark.asyncio
async def test_catalog_does_not_hide_parser_structure_error() -> None:
    now = [100.0]
    fetcher = AsyncMock(side_effect=[RECORDS, ValueError("DEVICES changed")])
    catalog = DeviceCatalog(fetcher=fetcher, ttl_seconds=10, clock=lambda: now[0])

    assert await catalog.get_devices() == RECORDS
    now[0] += 10
    with pytest.raises(ValueError, match="DEVICES changed"):
        await catalog.get_devices()


@pytest.mark.asyncio
async def test_catalog_requires_non_empty_fetch_result() -> None:
    catalog = DeviceCatalog(fetcher=AsyncMock(return_value=[]))

    with pytest.raises(ValueError, match="empty device list"):
        await catalog.get_devices()


def test_cooldown_limits_repeated_key() -> None:
    now = [100.0]
    cooldown = RequestCooldown(seconds=30, clock=lambda: now[0])

    assert cooldown.try_acquire(("user", 1)) == 0
    now[0] += 10
    assert cooldown.try_acquire(("user", 1)) == 20
    assert cooldown.try_acquire(("user", 2)) == 0
    now[0] += 20
    assert cooldown.try_acquire(("user", 1)) == 0
