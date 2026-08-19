"""Selection of the Asahi device monitored by the watcher."""

from watcher.parser import DEFAULT_SOURCE_URL, DeviceRecord, fetch_devices

TRACKED_DEVICE_ID = "j516sap"


def select_tracked_device(
    records: list[DeviceRecord],
    device_id: str = TRACKED_DEVICE_ID,
) -> list[DeviceRecord]:
    """Return the configured device as a one-record list for delivery."""
    matches = [record for record in records if record.device_id == device_id]
    if not matches:
        raise ValueError(f"tracked device {device_id!r} is missing from DEVICES")
    if len(matches) > 1:
        raise ValueError(f"tracked device {device_id!r} occurs more than once")
    return matches


async def fetch_tracked_device(
    url: str = DEFAULT_SOURCE_URL,
    timeout: float = 30.0,
) -> list[DeviceRecord]:
    """Download all DEVICES safely and return only the monitored device."""
    records = await fetch_devices(url, timeout)
    return select_tracked_device(records)
