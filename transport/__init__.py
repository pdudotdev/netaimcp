"""Transport dispatcher — routes execute_command calls to the correct transport.

Two branches (Cisco-only 2-tier stack):
  - asyncssh:  Scrapli SSH for IOL devices (A1C, A2C, IAN, IBN) + SSH fallback.
  - restconf:  2-tier ActionChain for c8000v devices (C1C, C2C, E1C, E2C, X1C).
               RESTCONF (primary) → SSH (fallback).
               Plain CLI strings (ping/traceroute) → SSH directly.
"""
import logging

from core.inventory import devices
from platforms.platform_map import ActionChain
from transport.ssh     import execute_ssh
from transport.restconf import execute_restconf

log = logging.getLogger("ainoc.transport")


async def _execute_single(device: dict, transport_type: str, sub_action,
                          timeout_ops: int | None = None) -> tuple:
    """Execute one tier of an ActionChain. Returns (raw_output, parsed_output)."""
    if transport_type == "restconf":
        raw = await execute_restconf(device, sub_action)
        return raw, None
    elif transport_type == "ssh":
        return await execute_ssh(device, sub_action, timeout_ops=timeout_ops)
    else:
        err = {"error": f"Unknown ActionChain tier: {transport_type}"}
        return err, err


async def execute_command(device_name: str, cmd_or_action,
                          timeout_ops: int | None = None,
                          transport: str | None = None) -> dict:
    """Execute a read command on a device and return a structured result dict."""
    device = devices.get(device_name)
    if not device:
        return {"error": "Unknown device"}

    cli_style     = device["cli_style"]
    dev_transport = device["transport"]

    log.info("dispatch: %s via %s", device_name, dev_transport)

    # Filter ActionChain to a single tier if transport override is requested
    if isinstance(cmd_or_action, ActionChain) and transport:
        filtered = [(t, a) for t, a in cmd_or_action.actions if t == transport]
        if not filtered:
            return {"device": device_name, "cli_style": cli_style,
                    "error": f"Transport '{transport}' not available for this device"}
        cmd_or_action = ActionChain(filtered)

    transport_used = None
    command_used = None

    try:
        if dev_transport == "asyncssh":
            if isinstance(cmd_or_action, dict):
                return {
                    "device": device_name, "cli_style": cli_style,
                    "error": "RESTCONF JSON commands are not supported on SSH-only devices. Use a CLI 'show' command.",
                }
            raw_output, parsed_output = await execute_ssh(device, cmd_or_action,
                                                          timeout_ops=timeout_ops)
            command_used = cmd_or_action

        elif dev_transport == "restconf":
            if isinstance(cmd_or_action, ActionChain):
                # 2-tier fallback: RESTCONF → SSH
                raw_output, parsed_output = None, None
                for tier, sub_action in cmd_or_action.actions:
                    raw_output, parsed_output = await _execute_single(
                        device, tier, sub_action, timeout_ops=timeout_ops)
                    if not (isinstance(raw_output, dict) and "error" in raw_output):
                        transport_used = tier
                        if tier == "restconf":
                            command_used = f"GET /restconf/data/{sub_action['url']}"
                        else:
                            command_used = sub_action
                        break
                    log.warning("%s tier failed for %s: %s", tier, device_name,
                                raw_output.get("error", "unknown"))
                # raw_output/parsed_output hold last attempt (success or final error)
            elif isinstance(cmd_or_action, dict) and "url" in cmd_or_action:
                # Raw RESTCONF action dict (from run_show) — route directly to RESTCONF
                raw_output = await execute_restconf(device, cmd_or_action)
                parsed_output = None
                transport_used = "restconf"
                command_used = f"GET /restconf/data/{cmd_or_action['url']}"
            else:
                # Plain CLI string (tools: ping/traceroute) → SSH
                raw_output, parsed_output = await execute_ssh(device, cmd_or_action,
                                                              timeout_ops=timeout_ops)
                transport_used = "ssh"
                command_used = cmd_or_action

        else:
            log.error("unknown transport: %s for device %s", dev_transport, device_name)
            return {
                "device": device_name, "cli_style": cli_style,
                "error":  f"Unknown transport: {dev_transport}",
            }

    except Exception as e:
        log.error("command failed: %s — %s", device_name, e)
        return {"device": device_name, "cli_style": cli_style, "error": str(e)}

    # Log transport-level errors (returned as dicts, not exceptions)
    if isinstance(raw_output, dict) and "error" in raw_output:
        log.error("transport error: %s — %s", device_name, raw_output["error"])

    result = {
        "device":    device_name,
    }
    if command_used:
        result["_command"] = command_used
    result["cli_style"] = cli_style
    if transport_used:
        result["_transport_used"] = transport_used

    result["raw"] = raw_output
    if parsed_output is not None:
        result["parsed"] = parsed_output

    return result
