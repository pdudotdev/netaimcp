"""Operational tools: get_interfaces, ping, traceroute, run_show."""
import json
from core.inventory import devices
from core.settings import SSH_TIMEOUT_OPS_LONG
from platforms.platform_map import get_action
from transport import execute_command
from input_models.models import InterfacesQuery, PingInput, TracerouteInput, ShowCommand
from tools import _error_response


async def get_interfaces(params: InterfacesQuery) -> dict:
    """
    Retrieve interface status and IP information from a device.

    Use this tool to verify interface state, IP assignments, and operational
    status during connectivity and routing investigations.

    Notes:
    - Command syntax is vendor-specific and resolved via PLATFORM_MAP.
    - Returns a summary view of interfaces.

    Recommended usage:
    - Use when troubleshooting down links or missing adjacencies.
    - Use to confirm IP addressing and interface operational state.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    try:
        action = get_action(device, "interfaces", "interface_status")
    except KeyError:
        return _error_response(params.device, f"Interface status not supported on {device['cli_style'].upper()}")

    return await execute_command(params.device, action, transport=params.transport)


async def ping(params: PingInput) -> dict:
    """
    Test reachability from a device to a destination IP.

    Use this tool to verify connectivity, validate routing decisions,
    and detect packet loss or reachability failures.

    Notes:
    - All devices use SSH CLI for ping (resolved via PLATFORM_MAP tools.ping).

    Recommended usage:
    - Use after verifying routing to confirm data-plane reachability.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    cli_style = device["cli_style"]
    try:
        base = get_action(device, "tools", "ping", vrf=params.vrf)
    except KeyError:
        return _error_response(params.device, f"Ping not supported on {cli_style.upper()}")

    # CLI string → SSH via transport dispatcher
    action = f"{base} {params.destination}"
    if params.source and cli_style == "ios":
        action += f" source {params.source}"

    return await execute_command(params.device, action)


async def traceroute(params: TracerouteInput) -> dict:
    """
    Trace the path from a device to a destination IP.

    Use this tool to identify routing paths, loops, asymmetric routing,
    or where traffic is being dropped.

    Notes:
    - All devices use SSH CLI for traceroute (resolved via PLATFORM_MAP tools.traceroute).

    Recommended usage:
    - Use when ping succeeds but path is unexpected.
    - Use to locate where packets are dropped.
    - Provide source=<ip> (from sla_paths source_ip field) to force traceroute on the monitored path.
    - Use only when necessary.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    cli_style = device["cli_style"]
    try:
        base = get_action(device, "tools", "traceroute", vrf=params.vrf)
    except KeyError:
        return _error_response(params.device, f"Traceroute not supported on {cli_style.upper()}")

    # CLI string → SSH via transport dispatcher
    action = f"{base} {params.destination}"
    if params.source and cli_style == "ios":
        action += f" source {params.source}"

    return await execute_command(params.device, action, timeout_ops=SSH_TIMEOUT_OPS_LONG)


async def run_show(params: ShowCommand) -> dict:
    """Run a show command against a network device."""
    command = params.command.strip()
    try:
        parsed = json.loads(command)
        if isinstance(parsed, dict):
            command = parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return await execute_command(params.device, command)
