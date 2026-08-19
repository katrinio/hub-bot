"""Persistent snapshots and change detection for the monitored device."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from watcher.parser import DeviceRecord

DEFAULT_STATE_PATH = Path("data/watcher/j516sap.json")


def load_device_snapshot(path: Path) -> DeviceRecord | None:
    """Load the previous device snapshot, or return None on the first run."""
    if not path.exists():
        return None
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read watcher state from {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"watcher state in {path} must be a JSON object")
    try:
        record = DeviceRecord(
            device_id=payload["device_id"],
            mac_model=payload["mac_model"],
            min_ver=payload["min_ver"],
            expert_only=payload["expert_only"],
        )
    except KeyError as error:
        raise ValueError(f"watcher state in {path} is missing {error.args[0]!r}") from error
    if not all(type(value) is str for value in (record.device_id, record.mac_model, record.min_ver)):
        raise ValueError(f"watcher state in {path} contains invalid text fields")
    if type(record.expert_only) is not bool:
        raise ValueError(f"watcher state in {path} contains invalid expert_only")
    return record


def save_device_snapshot(path: Path, record: DeviceRecord) -> None:
    """Atomically persist a successfully processed device state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(asdict(record), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def changed_fields(previous: DeviceRecord, current: DeviceRecord) -> dict[str, tuple[str | bool, str | bool]]:
    """Return changed user-facing fields and their previous/current values."""
    fields: dict[str, tuple[str | bool, str | bool]] = {
        "model": (previous.mac_model, current.mac_model),
        "min_ver": (previous.min_ver, current.min_ver),
        "expert_only": (previous.expert_only, current.expert_only),
    }
    return {name: values for name, values in fields.items() if values[0] != values[1]}
