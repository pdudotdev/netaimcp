"""Configuration push tool: push_config, validate_commands, and forbidden command sets."""
import asyncio
import json
import logging
import time

from core.inventory import devices

log = logging.getLogger("ainoc.tools.config")
from transport.ssh  import push_ssh
from transport.eapi import push_eapi
from transport.rest import push_rest
from tools.state import check_maintenance_window, assess_risk, snapshot_state
from tools import _error_response
from input_models.models import ConfigCommand, EmptyInput, RiskInput, SnapshotInput

# Forbidden CLI command substrings — matched case-insensitively against any CLI command.
FORBIDDEN = {
    # Device-level destructive operations
    "reload", "write erase", "erase", "format", "delete", "boot",
    "crypto key zeroize",
    # Routing process removal (high blast-radius in multi-area/multi-AS environments)
    "no router",
    # Interface reset — clears all sub-config
    "default interface",
    # State-clearing commands that cause temporary outages
    "clear ip ospf", "clear ip bgp", "clear ip eigrp", "clear ip route",
    # Diagnostic overload — can saturate CPU on production devices
    "debug all",
}

# RouterOS REST paths that must never be targeted by push_config automation.
FORBIDDEN_REST_PATHS = {
    "/rest/system/reset",
    "/rest/system/reboot",
    "/rest/system/shutdown",
    "/rest/system/backup",
    "/rest/file",
    "/rest/user",
    "/rest/system/identity",
    "/rest/certificate",
    "/rest/ip/firewall/filter",
}

# Valid HTTP methods for RouterOS push_config (POST excluded: fails on RouterOS 7.x).
VALID_REST_PUSH_METHODS = {"PUT", "PATCH", "DELETE"}


def _generate_rollback_advisory(commands: list[str]) -> list[str]:
    """Generate advisory rollback commands (not automatically applied).

    CLI commands: invert "no" prefix.
    RouterOS JSON actions: note that manual rollback is required (original IDs needed).
    """
    rollback = []
    for cmd in commands:
        stripped = cmd.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                method = parsed.get("method", "").upper()
                path   = parsed.get("path", "")
                rollback.append(f"# RouterOS {method} rollback requires manual action: {path}")
                continue
        except json.JSONDecodeError:
            pass
        if stripped.lower().startswith("no "):
            rollback.append(stripped[3:].strip())
        else:
            rollback.append(f"no {stripped}")
    return rollback


def validate_commands(cmds: list[str]) -> None:
    """Raise ValueError if any command matches a forbidden pattern.

    RouterOS JSON-encoded actions: validated against FORBIDDEN_REST_PATHS and
    VALID_REST_PUSH_METHODS. PUT=create, PATCH=modify, DELETE=remove.

    IOS/EOS CLI commands: validated against the FORBIDDEN substring set.
    """
    for c in cmds:
        is_json_action = False
        try:
            parsed = json.loads(c)
            if isinstance(parsed, dict):
                is_json_action = True
                method = parsed.get("method", "").upper()
                path   = parsed.get("path", "").lower()
                if method not in VALID_REST_PUSH_METHODS:
                    raise ValueError(
                        f"Invalid REST method {method!r} in push_config action. "
                        f"Allowed: {', '.join(sorted(VALID_REST_PUSH_METHODS))}. "
                        f"Use run_show for GET queries."
                    )
                if any(path.startswith(fp) for fp in FORBIDDEN_REST_PATHS):
                    raise ValueError(
                        f"Forbidden REST path in push_config action: {path!r}. "
                        f"This path is protected and must not be modified via automation."
                    )
        except json.JSONDecodeError:
            pass  # Not JSON — fall through to CLI check

        if is_json_action:
            continue

        if any(bad in c.lower() for bad in FORBIDDEN):
            log.error("forbidden command blocked: %r", c)
            raise ValueError(f"Forbidden command detected: {c}")


async def _push_to_device(dev_name: str, device: dict, commands: list[str]) -> tuple[str, dict]:
    """Dispatch config push to the correct transport."""
    transport = device["transport"]
    if transport == "eapi":
        return await push_eapi(device, dev_name, commands)
    elif transport == "asyncssh":
        return await push_ssh(device, dev_name, commands)
    elif transport == "rest":
        return await push_rest(device, dev_name, commands)
    else:
        raise NotImplementedError(f"push_config not supported for transport: {transport}")


async def _push_to_device_safe(dev_name: str, device: dict, commands: list[str]) -> tuple[str, object]:
    try:
        return await _push_to_device(dev_name, device, commands)
    except Exception as e:
        return dev_name, _error_response(dev_name, f"ERROR: {e}")


async def push_config(params: ConfigCommand) -> dict:
    """
    Push configuration commands to one or more devices.

    IMPORTANT:
    - This tool enforces maintenance window policy.
    - If changes are outside the approved window, the tool will refuse to run.
    - Maintenance policy files (e.g. MAINTENANCE.json) MUST NOT be modified
    by Claude or by any automation workflow.
    - If a change is blocked, Claude should inform the user and stop.
    - Risk assessment is advisory only and does not block changes.
    """
    log.info("push_config START: devices=%s commands=%s", params.devices, params.commands)

    mw_result = await check_maintenance_window(EmptyInput())
    if not mw_result.get("allowed", True):
        log.warning("push_config BLOCKED: outside maintenance window at %s", mw_result.get("current_time"))
        return {
            "error":        "Configuration changes blocked: outside maintenance window",
            "current_time": mw_result.get("current_time", "unknown"),
            "reason":       mw_result.get("reason", "Outside maintenance window"),
        }

    # Guard: all devices must share the same cli_style — commands are vendor-specific
    # and will fail or corrupt state if sent to the wrong transport.
    known_devices = {d: devices[d]["cli_style"] for d in params.devices if d in devices}
    cli_styles_present = set(known_devices.values())
    if len(cli_styles_present) > 1:
        return {
            "error":       "Mixed cli_style in device list. Push to each vendor group separately.",
            "cli_styles":  known_devices,
        }

    risk = await assess_risk(RiskInput(devices=params.devices, commands=params.commands))

    # Pre-change snapshot (optional, profile auto-selected from commands)
    pre_snapshot_id = None
    if params.snapshot_before:
        cmd_text = " ".join(params.commands).lower()
        if "eigrp" in cmd_text:
            snap_profile = "eigrp"
        elif "bgp" in cmd_text:
            snap_profile = "bgp"
        else:
            snap_profile = "ospf"
        snap = await snapshot_state(SnapshotInput(devices=params.devices, profile=snap_profile))
        pre_snapshot_id = snap.get("snapshot_id")
        log.info("pre-change snapshot taken: id=%s profile=%s", pre_snapshot_id, snap_profile)

    start = time.perf_counter()
    validate_commands(params.commands)

    tasks   = []
    results = {}
    for dev_name in params.devices:
        device = devices.get(dev_name)
        if not device:
            results[dev_name] = _error_response(dev_name, "Unknown device")
            continue
        tasks.append(
            asyncio.create_task(
                _push_to_device_safe(dev_name, device, params.commands)
            )
        )

    for dev_name, result in await asyncio.gather(*tasks):
        results[dev_name] = result

    end = time.perf_counter()
    log.info("push_config RESULT: %s", json.dumps({k: v for k, v in results.items()}, default=str))
    results["execution_time_seconds"] = round(end - start, 2)
    results["risk_assessment"] = risk
    results["rollback_advisory"] = _generate_rollback_advisory(params.commands)
    if pre_snapshot_id:
        results["pre_change_snapshot"] = pre_snapshot_id
    return results
