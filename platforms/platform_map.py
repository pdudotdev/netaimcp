PLATFORM_MAP = {
    # ── Cisco IOS (asyncssh — CLI strings, Genie-parsed) ──────────────────────
    # Used by IOL devices: A1C, A2C, IAN, IBN (SSH-only, no NETCONF/RESTCONF).
    # Also used as the SSH fallback tier for all c8000v devices in ActionChain.
    # VRF-sensitive queries use dual-entry: {"default": "<global cmd>", "vrf": "<vrf cmd>"}
    "ios": {
        "ospf": {
            "neighbors":  "show ip ospf neighbor",
            "database":   "show ip ospf database",
            "borders":    "show ip ospf border-routers",
            "config":     "show running-config | section ospf",
            "interfaces": "show ip ospf interface",
            "details":    "show ip ospf",
        },
        "bgp": {
            "summary":   {"default": "show ip bgp summary",               "vrf": "show ip bgp vpnv4 vrf {vrf} summary"},
            "table":     {"default": "show ip bgp",                       "vrf": "show ip bgp vpnv4 vrf {vrf}"},
            "config":    {"default": "show running-config | section bgp", "vrf": "show running-config | section bgp"},
            "neighbors": {"default": "show ip bgp neighbors",             "vrf": "show ip bgp vpnv4 vrf {vrf} neighbors"},
        },
        "routing_table": {
            "ip_route":  {"default": "show ip route",                     "vrf": "show ip route vrf {vrf}"},
        },
        "routing_policies": {
            "redistribution":       "show run | section redistribute",
            "route_maps":           "show route-map",
            "prefix_lists":         "show ip prefix-list",
            "policy_based_routing": "show ip policy",
            "access_lists":         "show ip access-lists",
        },
        "interfaces": {
            "interface_status": "show ip interface brief"
        },
        "tools": {
            "ping":       {"default": "ping",        "vrf": "ping vrf {vrf}"},
            "traceroute": {"default": "traceroute",  "vrf": "traceroute vrf {vrf}"},
        },
    },

    # ── Cisco IOS-XE via RESTCONF (primary tier for c8000v) ───────────────────
    # Used by: C1C, C2C, E1C, E2C, X1C (restconf transport, primary ActionChain tier).
    # HTTP GET to /restconf/data/{url}. Returns all-VRF data; agent filters by VRF.
    # ping/traceroute have no RESTCONF equivalent — tools section falls back to ios CLI.
    "ios_restconf": {
        "ospf": {
            "neighbors":  {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data/ospf-state",      "method": "GET"},
            "database":   {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data/ospfv2-instance", "method": "GET"},
            "borders":    {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data/ospfv2-instance", "method": "GET"},
            "interfaces": {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data/ospf-state",      "method": "GET"},
            "details":    {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data/ospf-state",      "method": "GET"},
            "config":     {"url": "Cisco-IOS-XE-native:native/router/router-ospf",          "method": "GET"},
        },
        "bgp": {
            "summary":   {"url": "Cisco-IOS-XE-bgp-oper:bgp-state-data/address-families", "method": "GET"},
            "table":     {"url": "Cisco-IOS-XE-bgp-oper:bgp-state-data/bgp-route-vrfs",   "method": "GET"},
            "neighbors": {"url": "Cisco-IOS-XE-bgp-oper:bgp-state-data/neighbors",        "method": "GET"},
            "config":    {"url": "Cisco-IOS-XE-native:native/router/bgp",                  "method": "GET"},
        },
        "routing_table": {
            "ip_route": {"url": "Cisco-IOS-XE-fib-oper:fib-oper-data", "method": "GET"},
        },
        "routing_policies": {
            "redistribution":       {"url": "Cisco-IOS-XE-native:native/router",            "method": "GET"},
            "route_maps":           {"url": "Cisco-IOS-XE-native:native/route-map",         "method": "GET"},
            "prefix_lists":         {"url": "Cisco-IOS-XE-native:native/ip/prefix-list",    "method": "GET"},
            "policy_based_routing": {"url": "Cisco-IOS-XE-native:native/ip/local/policy",   "method": "GET"},
            "access_lists":         {"url": "Cisco-IOS-XE-native:native/ip/access-list",    "method": "GET"},
        },
        "interfaces": {
            "interface_status": {"url": "ietf-interfaces:interfaces", "method": "GET"},
        },
    },

}


class ActionChain:
    """Ordered fallback chain for 2-tier transport (RESTCONF → SSH).

    actions: list of (transport_type, action) pairs tried in order by the dispatcher.
    The first tier that returns a result without an 'error' key wins.
    """
    __slots__ = ("actions",)

    def __init__(self, actions: list):
        self.actions = actions

    def __repr__(self):
        return f"ActionChain({self.actions!r})"


def _apply_vrf(action, vrf_name: str | None):
    """Apply VRF substitution to an action entry."""
    # Dual-entry CLI format: {"default": "...", "vrf": "..."}
    if isinstance(action, dict) and "default" in action and "vrf" in action:
        template = action["vrf"] if vrf_name else action["default"]
        return template.replace("{vrf}", vrf_name) if vrf_name else template

    # Plain CLI string with {vrf} template
    if isinstance(action, str) and vrf_name and "{vrf}" in action:
        return action.replace("{vrf}", vrf_name)

    return action


def get_action(device: dict, category: str, query: str, vrf: str | None = None):
    """Look up command/action from PLATFORM_MAP.

    For ``restconf`` transport devices (c8000v): returns an ``ActionChain`` with
    two tiers — RESTCONF (primary) → SSH (fallback).
    The dispatcher tries each in order; first success wins.

    Exception: ``tools`` (ping/traceroute) always returns a plain CLI string
    since those have no RESTCONF equivalent.

    For ``asyncssh`` devices (IOL): returns a plain CLI string or dual-entry
    dict (resolved to a string via VRF logic).

    Args:
        device:   Inventory entry dict (must have 'cli_style' and 'transport' keys).
        category: Top-level PLATFORM_MAP section (e.g. 'ospf', 'interfaces', 'tools').
        query:    Sub-key within that section (e.g. 'neighbors', 'interface_status').
        vrf:      Optional VRF name. If None, global routing table is used.

    Returns:
        ActionChain for restconf structured queries; plain CLI string otherwise.

    Raises:
        KeyError: If the platform or category/query is not found in PLATFORM_MAP.
    """
    vrf_name = vrf or device.get("vrf")

    if device["transport"] == "restconf":
        # tools (ping/traceroute): no RESTCONF tier — return plain CLI string from ios
        if category == "tools":
            action = PLATFORM_MAP["ios"][category][query]
            return _apply_vrf(action, vrf_name)

        rc_action  = PLATFORM_MAP["ios_restconf"][category][query]
        ssh_action = _apply_vrf(PLATFORM_MAP["ios"][category][query], vrf_name)
        return ActionChain([
            ("restconf", rc_action),
            ("ssh",      ssh_action),
        ])

    # asyncssh devices: direct platform map lookup with VRF resolution
    override_key = f"{device['cli_style']}_{device['transport']}"
    map_entry = PLATFORM_MAP.get(override_key) or PLATFORM_MAP.get(device["cli_style"])
    if not map_entry:
        raise KeyError(f"No platform map entry for cli_style={device['cli_style']!r}")

    action = map_entry[category][query]
    return _apply_vrf(action, vrf_name)
