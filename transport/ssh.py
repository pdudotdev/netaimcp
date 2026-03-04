"""Scrapli SSH executor for Cisco IOS-XE devices (asyncssh transport)."""
import asyncio
import logging

from scrapli import AsyncScrapli
from core.settings import (
    USERNAME, PASSWORD, SSH_STRICT_KEY,
    SSH_TIMEOUT_TRANSPORT, SSH_TIMEOUT_OPS,
    SSH_RETRIES, SSH_RETRY_DELAY,
)

log = logging.getLogger("ainoc.transport.ssh")


def _connection_params(device: dict) -> dict:
    return {
        "host":              device["host"],
        "platform":          device["platform"],
        "transport":         device["transport"],
        "auth_username":     USERNAME,
        "auth_password":     PASSWORD,
        "auth_strict_key":   SSH_STRICT_KEY,
        "timeout_transport": SSH_TIMEOUT_TRANSPORT,
        "timeout_ops":       SSH_TIMEOUT_OPS,
    }


async def execute_ssh(device: dict, command: str) -> tuple[str, object]:
    """Execute a show command via Scrapli SSH.

    Returns (raw_output, parsed_output) where parsed_output is a Genie-parsed
    dict for IOS devices, or None if parsing is unavailable.

    Retries up to SSH_RETRIES times on transient connection failures.
    """
    last_exc = None
    for attempt in range(1 + SSH_RETRIES):
        try:
            async with AsyncScrapli(**_connection_params(device)) as conn:
                response = await conn.send_command(command)
                raw_output = response.result
                parsed_output = None
                if device.get("cli_style") == "ios":
                    try:
                        parsed_output = response.genie_parse_output()
                    except Exception:
                        # Genie lacks a parser for this command or the output format is unexpected.
                        # Fall back to raw text — the caller handles None parsed_output gracefully.
                        parsed_output = None
            return raw_output, parsed_output
        except Exception as e:
            last_exc = e
            if attempt < SSH_RETRIES:
                log.warning(
                    "SSH attempt %d/%d failed for %s: %s — retrying in %ds",
                    attempt + 1, 1 + SSH_RETRIES, device["host"], e, SSH_RETRY_DELAY,
                )
                await asyncio.sleep(SSH_RETRY_DELAY)
    raise last_exc


async def push_ssh(device: dict, dev_name: str, commands: list[str]) -> tuple[str, dict]:
    """Push configuration commands via Scrapli SSH.

    Retries up to SSH_RETRIES times on transient connection failures.
    """
    last_exc = None
    for attempt in range(1 + SSH_RETRIES):
        try:
            async with AsyncScrapli(**_connection_params(device)) as conn:
                response = await conn.send_configs(commands)
            return dev_name, {"transport_used": "asyncssh", "result": response.result}
        except Exception as e:
            last_exc = e
            if attempt < SSH_RETRIES:
                log.warning(
                    "SSH push attempt %d/%d failed for %s: %s — retrying in %ds",
                    attempt + 1, 1 + SSH_RETRIES, device["host"], e, SSH_RETRY_DELAY,
                )
                await asyncio.sleep(SSH_RETRY_DELAY)
    raise last_exc
