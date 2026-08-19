"""Telegram formatting and delivery for Asahi device records."""

import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError

from watcher.monitoring import changed_fields
from watcher.parser import DeviceRecord

TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_MAX_RETRIES = 2
TELEGRAM_MAX_RETRY_DELAY = 30.0

logger = logging.getLogger(__name__)


def _format_device_record(record: DeviceRecord) -> str:
    return (
        f"device_id: {record.device_id}\n"
        f"model: {record.mac_model}\n"
        f"min_ver: {record.min_ver} | expert_only: {record.expert_only}"
    )


def format_devices(records: list[DeviceRecord]) -> str:
    """Format parsed devices as readable plain text."""
    heading = f"Устройства Asahi Linux\nНайдено: {len(records)}"
    records_text = "\n\n".join(_format_device_record(record) for record in records)
    return f"{heading}\n\n{records_text}".rstrip()


def format_device_change(previous: DeviceRecord, current: DeviceRecord) -> str:
    """Format a notification containing only fields that changed."""
    changes = changed_fields(previous, current)
    if not changes:
        raise ValueError("cannot format a device change without changed fields")
    lines = ["Изменение устройства Asahi Linux", f"device_id: {current.device_id}", f"model: {current.mac_model}", ""]
    lines.extend(f"{name}: {old_value} → {new_value}" for name, (old_value, new_value) in changes.items())
    return "\n".join(lines)


def _pack_device_records(records: list[DeviceRecord], payload_limit: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for record in records:
        block = _format_device_record(record)
        if len(block) > payload_limit:
            raise ValueError(f"device record {record.device_id!r} exceeds Telegram's message limit")
        candidate = block if not current else f"{current}\n\n{block}"
        if len(candidate) > payload_limit:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def build_device_messages(records: list[DeviceRecord], limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Build Telegram messages without splitting individual device records."""
    if limit <= 0:
        raise ValueError("message limit must be positive")
    if not records:
        raise ValueError("cannot format an empty device list")

    heading = f"Устройства Asahi Linux\nНайдено: {len(records)}"
    all_records = "\n\n".join(_format_device_record(record) for record in records)
    single_message = f"{heading}\n\n{all_records}"
    if len(single_message) <= limit:
        return [single_message]

    max_part_count = len(records)
    largest_prefix = f"{heading}\nЧасть {max_part_count}/{max_part_count}\n\n"
    payload_limit = limit - len(largest_prefix)
    if payload_limit <= 0:
        raise ValueError("Telegram message limit is too small for the device list heading")
    chunks = _pack_device_records(records, payload_limit)
    part_count = len(chunks)
    messages = [f"{heading}\nЧасть {index}/{part_count}\n\n{chunk}" for index, chunk in enumerate(chunks, 1)]
    if any(len(message) > limit for message in messages):
        raise ValueError("failed to split device list within Telegram's message limit")
    return messages


async def _send_message_with_retry(
    bot: Bot,
    chat_id: int | str,
    text: str,
    message_thread_id: int | None,
    max_retries: int,
) -> None:
    if max_retries < 0:
        raise ValueError("max_retries must not be negative")

    for attempt in range(max_retries + 1):
        try:
            kwargs: dict[str, Any] = {"chat_id": chat_id, "text": text}
            if message_thread_id is not None:
                kwargs["message_thread_id"] = message_thread_id
            await bot.send_message(**kwargs)
            return
        except TelegramRetryAfter as error:
            if attempt == max_retries:
                raise
            delay = min(float(error.retry_after), TELEGRAM_MAX_RETRY_DELAY)
            logger.warning("Telegram rate limit; retrying device message in %.1f seconds", delay)
        except (TelegramNetworkError, TelegramServerError):
            if attempt == max_retries:
                raise
            delay = min(float(2**attempt), TELEGRAM_MAX_RETRY_DELAY)
            logger.warning("Transient Telegram error; retrying device message in %.1f seconds", delay)
        await asyncio.sleep(delay)


async def send_devices_to_telegram(
    records: list[DeviceRecord],
    bot: Bot,
    chat_id: int | str,
    message_thread_id: int | None = None,
    max_retries: int = TELEGRAM_MAX_RETRIES,
) -> int:
    """Format, split, and send all device records; return the message count."""
    messages = build_device_messages(records)
    for message in messages:
        await _send_message_with_retry(bot, chat_id, message, message_thread_id, max_retries)
    return len(messages)


async def send_device_change_to_telegram(
    previous: DeviceRecord,
    current: DeviceRecord,
    bot: Bot,
    chat_id: int | str,
    max_retries: int = TELEGRAM_MAX_RETRIES,
) -> None:
    """Send a single change notification with the standard retry policy."""
    await _send_message_with_retry(
        bot,
        chat_id,
        format_device_change(previous, current),
        message_thread_id=None,
        max_retries=max_retries,
    )
