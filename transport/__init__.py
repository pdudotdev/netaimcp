"""Transport dispatcher — routes execute_command calls to the correct
vendor-specific transport module (SSH, eAPI, or REST).
"""
import logging

from core.cache import cache_get, cache_set, CMD_TTL
from core.inventory import devices
from transport.ssh  import execute_ssh
from transport.eapi import execute_eapi
from transport.rest import execute_rest

log = logging.getLogger("ainoc.transport")


async def execute_command(device_name: str, cmd_or_action, ttl: int = CMD_TTL) -> dict:
    """Execute a read command on a device and return a structured result dict.

    Uses a short-lived cache (ttl seconds) to avoid redundant network calls
    for repeated queries within a troubleshooting session. Pass ttl=0 to bypass.
    """
    device = devices.get(device_name)
    if not device:
        return {"error": "Unknown device"}

    cli_style = device["cli_style"]
    transport  = device["transport"]

    if ttl > 0:
        cached = cache_get(device_name, str(cmd_or_action), ttl)
        if cached:
            cached["cache_hit"] = True
            return cached

    log.info("dispatch: %s via %s", device_name, transport)

    try:
        if transport == "rest":
            raw_output    = await execute_rest(device, cmd_or_action)
            parsed_output = raw_output

        elif transport == "eapi":
            raw_output    = await execute_eapi(device, cmd_or_action)
            parsed_output = raw_output

        elif transport == "asyncssh":
            raw_output, parsed_output = await execute_ssh(device, cmd_or_action)

        else:
            log.error("unknown transport: %s for device %s", transport, device_name)
            return {
                "device": device_name, "cli_style": cli_style,
                "error":  f"Unknown transport: {transport}",
            }

    except Exception as e:
        log.error("command failed: %s — %s", device_name, e)
        return {"device": device_name, "cli_style": cli_style, "error": str(e)}

    # Log transport-level HTTP errors (returned as dicts, not exceptions)
    if isinstance(raw_output, dict) and "error" in raw_output:
        log.error("transport error: %s — %s", device_name, raw_output["error"])

    result = {
        "device":    device_name,
        "cli_style": cli_style,
        "cache_hit": False,
    }

    result["raw"] = raw_output
    if parsed_output:
        result["parsed"] = parsed_output

    if ttl > 0:
        cache_set(device_name, str(cmd_or_action), result)

    return result
