#!/usr/bin/env python3
"""Safely extract Asahi Installer devices and send them to Telegram."""

from __future__ import annotations

import argparse
import ast
import asyncio
import io
import os
import tokenize
import urllib.request
from dataclasses import dataclass
from typing import Any

from aiogram import Bot

from hub_bot.core.settings import get_bot_token

DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/AsahiLinux/asahi-installer/main/src/main.py"
TELEGRAM_MESSAGE_LIMIT = 4096


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


def parse_devices(source: str) -> list[DeviceRecord]:
    """Parse the literal DEVICES dictionary and its inline model comments."""
    tree = ast.parse(source, filename="src/main.py")
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DEVICES" for target in node.targets)
    ]
    if len(assignments) != 1:
        raise ValueError(f"expected exactly one DEVICES assignment, found {len(assignments)}")

    mapping = assignments[0].value
    if not isinstance(mapping, ast.Dict):
        raise ValueError("DEVICES must be a dictionary literal")

    comments = _comments_by_line(source)
    records: list[DeviceRecord] = []
    for key_node, value_node in zip(mapping.keys, mapping.values, strict=True):
        if key_node is None:
            raise ValueError("dictionary unpacking is not supported in DEVICES")
        device_id = _literal(key_node, str, "device_id")
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
    lines = ["Устройства Asahi Linux", f"Найдено: {len(records)}", ""]
    for record in records:
        expert_only = str(record.expert_only)
        lines.extend(
            (
                f"device_id: {record.device_id}",
                f"model: {record.mac_model}",
                f"min_ver: {record.min_ver} | expert_only: {expert_only}",
                "",
            )
        )
    return "\n".join(lines).rstrip()


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split text on line boundaries while respecting Telegram's limit."""
    if limit <= 0:
        raise ValueError("message limit must be positive")
    if not text:
        return []

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        remainder = line
        while len(remainder) > limit:
            if current:
                chunks.append(current.rstrip("\n"))
                current = ""
            chunks.append(remainder[:limit].rstrip("\n"))
            remainder = remainder[limit:]

        if len(current) + len(remainder) > limit:
            chunks.append(current.rstrip("\n"))
            current = remainder
        else:
            current += remainder

    if current:
        chunks.append(current.rstrip("\n"))
    return [chunk for chunk in chunks if chunk]


def _required_environment_variable(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Не задана обязательная переменная окружения {name}")
    return value


async def send_devices_to_telegram(records: list[DeviceRecord], bot: Bot, chat_id: str) -> int:
    """Format, split, and send all device records; return the message count."""
    messages = split_message(format_devices(records))
    for message in messages:
        await bot.send_message(chat_id=chat_id, text=message)
    return len(messages)


async def run(url: str, timeout: float) -> tuple[int, int]:
    """Download, parse, and send the current device list."""
    records = parse_devices(download_source(url, timeout))
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
    args = parser.parse_args()

    device_count, message_count = asyncio.run(run(args.url, args.timeout))
    print(f"Отправлено устройств: {device_count}; сообщений: {message_count}.")


if __name__ == "__main__":
    main()
