"""Caching and request throttling for the Asahi device catalog."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Hashable

from watcher import DeviceRecord, fetch_devices

DEVICE_CACHE_TTL_SECONDS = 10 * 60
DEVICE_FETCH_FAILURE_RETRY_SECONDS = 60
DEVICES_COOLDOWN_SECONDS = 30

logger = logging.getLogger(__name__)

DeviceFetcher = Callable[[], Awaitable[list[DeviceRecord]]]
Clock = Callable[[], float]


class DeviceCatalog:
    """Keep one fresh device snapshot and serialize upstream refreshes."""

    def __init__(
        self,
        fetcher: DeviceFetcher = fetch_devices,
        ttl_seconds: float = DEVICE_CACHE_TTL_SECONDS,
        failure_retry_seconds: float = DEVICE_FETCH_FAILURE_RETRY_SECONDS,
        clock: Clock = time.monotonic,
    ) -> None:
        self._fetcher = fetcher
        self._ttl_seconds = ttl_seconds
        self._failure_retry_seconds = failure_retry_seconds
        self._clock = clock
        self._records: list[DeviceRecord] | None = None
        self._expires_at = 0.0
        self._refresh_task: asyncio.Task[list[DeviceRecord]] | None = None

    def _fresh_records(self, now: float) -> list[DeviceRecord] | None:
        if self._records is not None and now < self._expires_at:
            return list(self._records)
        return None

    async def _refresh(self) -> list[DeviceRecord]:
        try:
            records = await self._fetcher()
        except OSError as error:
            if self._records is None:
                raise
            self._expires_at = self._clock() + self._failure_retry_seconds
            logger.warning("Asahi device refresh failed; using last-known-good data: %s", type(error).__name__)
            return list(self._records)

        if not records:
            raise ValueError("device fetcher returned an empty device list")
        self._records = list(records)
        self._expires_at = self._clock() + self._ttl_seconds
        return list(self._records)

    async def get_devices(self) -> list[DeviceRecord]:
        """Return fresh devices, or stale known-good data during a network outage."""
        if fresh := self._fresh_records(self._clock()):
            return fresh

        task = self._refresh_task
        if task is not None and task.done():
            self._refresh_task = None
            task = None
        if task is None:
            task = asyncio.create_task(self._refresh())
            self._refresh_task = task
        try:
            return await asyncio.shield(task)
        finally:
            if task.done() and self._refresh_task is task:
                self._refresh_task = None


class RequestCooldown:
    """Simple in-memory cooldown keyed by user or chat."""

    def __init__(self, seconds: float = DEVICES_COOLDOWN_SECONDS, clock: Clock = time.monotonic) -> None:
        self._seconds = seconds
        self._clock = clock
        self._deadlines: dict[Hashable, float] = {}

    def try_acquire(self, key: Hashable) -> float:
        """Return zero when allowed, otherwise remaining cooldown seconds."""
        now = self._clock()
        deadline = self._deadlines.get(key, 0.0)
        if deadline > now:
            return deadline - now
        self._deadlines[key] = now + self._seconds
        return 0.0
