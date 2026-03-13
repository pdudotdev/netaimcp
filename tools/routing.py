"""Routing table and policy tools: get_routing, get_routing_policies."""
from core.inventory import devices
from platforms.platform_map import get_action, ActionChain
from transport import execute_command
from input_models.models import RoutingQuery, RoutingPolicyQuery
from tools import _error_response


async def get_routing(params: RoutingQuery) -> dict:
    """
    Retrieve routing table information from a device.

    - If prefix is provided → targeted route lookup.
    - If prefix is omitted → full routing table.

    Use this tool to verify route presence, next-hop selection,
    and routing protocol contributions.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    try:
        base_cmd = get_action(device, "routing_table", "ip_route", vrf=params.vrf)
    except KeyError:
        return _error_response(params.device, f"Routing not supported on {device['cli_style'].upper()}")

    if not params.prefix:
        action = base_cmd
    elif isinstance(base_cmd, ActionChain):
        # RESTCONF devices: append prefix to the SSH fallback tier only.
        # The RESTCONF tier returns the full FIB table (no per-prefix URL filter).
        new_actions = []
        for tier, sub_action in base_cmd.actions:
            if tier == "ssh" and isinstance(sub_action, str):
                new_actions.append((tier, f"{sub_action} {params.prefix}"))
            else:
                new_actions.append((tier, sub_action))
        action = ActionChain(new_actions)
    else:
        # IOS CLI string (asyncssh devices): append prefix to the command
        action = f"{base_cmd} {params.prefix}"

    return await execute_command(params.device, action, transport=params.transport)


async def get_routing_policies(params: RoutingPolicyQuery) -> dict:
    """
    Retrieve routing policy configuration from a device.

    Use this tool to inspect route maps, prefix lists, access lists,
    and policy-based routing that may influence routing decisions.

    Supported queries:
    - redistribution         → View routing protocol redistribution
    - route_maps             → View route-map definitions
    - prefix_lists           → Inspect prefix filtering rules
    - policy_based_routing   → Verify PBR configuration (IOS asyncssh only)
    - access_lists           → Review ACLs affecting routing or filtering

    Notes:
    - Supported queries vary by platform.

    Recommended usage:
    - Use when routes are filtered, modified, or unexpectedly redirected.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    try:
        action = get_action(device, "routing_policies", params.query, vrf=params.vrf)
    except KeyError:
        return _error_response(params.device, f"Routing policy query '{params.query}' not supported on {device['cli_style'].upper()}")

    return await execute_command(params.device, action, transport=params.transport)
