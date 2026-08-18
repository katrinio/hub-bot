#!/usr/bin/env python3
"""Safely extract Asahi Installer devices and send them to Telegram."""

from __future__ import annotations

import argparse
import ast
import asyncio
import io
import logging
import os
import tokenize
import urllib.request
from dataclasses import dataclass
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError

from hub_bot.core.settings import get_bot_token

DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/AsahiLinux/asahi-installer/main/src/main.py"
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_MAX_RETRIES = 2
TELEGRAM_MAX_RETRY_DELAY = 30.0
_DEVELOPMENT_VM_DEVICE_ID = "vma2macosap"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceRecord:
    device_id: str
    mac_model: str
    min_ver: str
    expert_only: bool


def download_source(url: str = DEFAULT_SOURCE_URL, timeout: float = 30.0) -> str:
    """Download the Python source as text without importing or executing it."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "asahi-devices-parser/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        encoding = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(encoding)


def _comments_by_line(source: str) -> dict[int, str]:
    """Return inline Python comments indexed by their one-based line number."""
    comments: dict[int, str] = {}
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for token in tokens:
        if token.type == tokenize.COMMENT:
            comments[token.start[0]] = token.string.removeprefix("#").strip()
    return comments


def _literal(node: ast.AST, expected_type: type[Any], field: str) -> Any:
    """Read a literal AST value and validate its type."""
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError) as error:
        raise ValueError(f"DEVICES {field} must be a literal") from error
    if type(value) is not expected_type:
        raise ValueError(f"DEVICES {field} must be {expected_type.__name__}, got {type(value).__name__}")
    return value


def _device_arguments(call: ast.Call) -> tuple[str, bool]:
    """Extract Device(min_ver, expert_only), supporting positional or keyword arguments."""
    if not isinstance(call.func, ast.Name) or call.func.id != "Device":
        raise ValueError("every DEVICES value must be a Device(...) call")

    arguments: dict[str, ast.AST] = {}
    positional_names = ("min_ver", "expert_only")
    if len(call.args) > len(positional_names):
        raise ValueError("Device(...) has too many positional arguments")
    for index, value in enumerate(call.args):
        arguments[positional_names[index]] = value
    for keyword in call.keywords:
        if keyword.arg is None or keyword.arg not in positional_names:
            raise ValueError("Device(...) contains an unsupported keyword argument")
        if keyword.arg in arguments:
            raise ValueError(f"Device(...) specifies {keyword.arg} more than once")
        arguments[keyword.arg] = keyword.value

    missing = [name for name in positional_names if name not in arguments]
    if missing:
        raise ValueError(f"Device(...) is missing: {', '.join(missing)}")

    min_ver = _literal(arguments["min_ver"], str, "min_ver")
    expert_only = _literal(arguments["expert_only"], bool, "expert_only")
    return min_ver, expert_only


def _is_devices_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "DEVICES"


def _devices_subscript_id(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Subscript) or not _is_devices_name(node.value):
        return None
    try:
        value = ast.literal_eval(node.slice)
    except (ValueError, TypeError):
        return "<dynamic>"
    return value if isinstance(value, str) else "<non-string>"


def _is_allow_vm_guard(node: ast.AST) -> bool:
    """Recognize Asahi's explicit development-only ALLOW_VM branch."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "environ"
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "os"
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "ALLOW_VM"
    )


def _validate_no_later_devices_mutations(statements: list[ast.stmt]) -> None:
    """Reject unsupported changes to DEVICES after its literal declaration."""

    def visit(node: ast.AST, allow_development_vm: bool = False) -> None:
        if isinstance(node, ast.If) and _is_allow_vm_guard(node.test):
            for branch_statement in node.body:
                visit(branch_statement, allow_development_vm=True)
            for branch_statement in node.orelse:
                visit(branch_statement)
            return

        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            targets.append(node.target)
        elif isinstance(node, ast.Delete):
            targets.extend(node.targets)

        for target in targets:
            if _is_devices_name(target):
                raise ValueError("DEVICES is reassigned after its literal declaration")
            device_id = _devices_subscript_id(target)
            if device_id is not None:
                is_known_development_vm = (
                    allow_development_vm
                    and device_id == _DEVELOPMENT_VM_DEVICE_ID
                    and isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "Device"
                )
                if is_known_development_vm:
                    continue
                raise ValueError(f"DEVICES is mutated after its literal declaration: {device_id}")

        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and _is_devices_name(node.func.value)
            and node.func.attr in {"clear", "pop", "popitem", "setdefault", "update", "__delitem__", "__setitem__"}
        ):
            raise ValueError(f"DEVICES.{node.func.attr}(...) mutation is not supported")

        for child in ast.iter_child_nodes(node):
            visit(child, allow_development_vm)

    for statement in statements:
        visit(statement)


def parse_devices(source: str) -> list[DeviceRecord]:
    """Parse the literal DEVICES dictionary and its inline model comments."""
    tree = ast.parse(source, filename="src/main.py")
    assignments = [
        (index, node)
        for index, node in enumerate(tree.body)
        if isinstance(node, ast.Assign) and any(_is_devices_name(target) for target in node.targets)
    ]
    if len(assignments) != 1:
        raise ValueError(f"expected exactly one DEVICES assignment, found {len(assignments)}")

    assignment_index, assignment = assignments[0]
    mapping = assignment.value
    if not isinstance(mapping, ast.Dict):
        raise ValueError("DEVICES must be a dictionary literal")
    if not mapping.keys:
        raise ValueError("DEVICES must not be empty")
    _validate_no_later_devices_mutations(tree.body[assignment_index + 1 :])

    comments = _comments_by_line(source)
    records: list[DeviceRecord] = []
    device_ids: set[str] = set()
    for key_node, value_node in zip(mapping.keys, mapping.values, strict=True):
        if key_node is None:
            raise ValueError("dictionary unpacking is not supported in DEVICES")
        device_id = _literal(key_node, str, "device_id")
        if device_id in device_ids:
            raise ValueError(f"duplicate DEVICES device_id: {device_id!r}")
        device_ids.add(device_id)
        if not isinstance(value_node, ast.Call):
            raise ValueError(f"DEVICES[{device_id!r}] must contain Device(...)")
        min_ver, expert_only = _device_arguments(value_node)

        comment_line = value_node.end_lineno or value_node.lineno
        mac_model = comments.get(comment_line)
        if not mac_model:
            raise ValueError(f"DEVICES[{device_id!r}] has no inline Mac model comment")

        records.append(
            DeviceRecord(
                device_id=device_id,
                mac_model=mac_model,
                min_ver=min_ver,
                expert_only=expert_only,
            )
        )
    return records


def format_devices(records: list[DeviceRecord]) -> str:
    """Format parsed devices as readable plain text for Telegram."""
    heading = f"Устройства Asahi Linux\nНайдено: {len(records)}"
    records_text = "\n\n".join(_format_device_record(record) for record in records)
    return f"{heading}\n\n{records_text}".rstrip()


def _format_device_record(record: DeviceRecord) -> str:
    return (
        f"device_id: {record.device_id}\n"
        f"model: {record.mac_model}\n"
        f"min_ver: {record.min_ver} | expert_only: {record.expert_only}"
    )


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


def _required_environment_variable(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Не задана обязательная переменная окружения {name}")
    return value


async def fetch_devices(url: str = DEFAULT_SOURCE_URL, timeout: float = 30.0) -> list[DeviceRecord]:
    """Download and parse devices without blocking the asyncio event loop."""
    source = await asyncio.to_thread(download_source, url, timeout)
    return parse_devices(source)


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


async def run(url: str, timeout: float) -> tuple[int, int]:
    """Download, parse, and send the current device list."""
    records = await fetch_devices(url, timeout)
    try:
        token = get_bot_token()
    except ValueError:
        raise ValueError("Не задана обязательная переменная окружения TELEGRAM_BOT_TOKEN") from None
    chat_id = _required_environment_variable("TELEGRAM_CHAT_ID")

    bot = Bot(token=token)
    try:
        message_count = await send_devices_to_telegram(records, bot, chat_id)
    finally:
        await bot.session.close()
    return len(records), message_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Отправить список устройств Asahi Linux в Telegram.")
    parser.add_argument("--url", default=DEFAULT_SOURCE_URL, help="URL исходного src/main.py")
    parser.add_argument("--timeout", type=float, default=30.0, help="таймаут загрузки в секундах")
    parser.add_argument("--dry-run", action="store_true", help="вывести результат без отправки в Telegram")
    args = parser.parse_args()

    if args.dry_run:
        records = asyncio.run(fetch_devices(args.url, args.timeout))
        print(format_devices(records))
        return

    device_count, message_count = asyncio.run(run(args.url, args.timeout))
    print(f"Отправлено устройств: {device_count}; сообщений: {message_count}.")


if __name__ == "__main__":
    main()
