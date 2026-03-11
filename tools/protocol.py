"""Protocol diagnostic tools: get_ospf, get_bgp."""
import ipaddress

from core.inventory import devices
from platforms.platform_map import get_action
from transport import execute_command
from input_models.models import OspfQuery, BgpQuery
from tools import _error_response

_OSPF_OPER_KEY = "Cisco-IOS-XE-ospf-oper:ospf-oper-data"
_BGP_OPER_KEY  = "Cisco-IOS-XE-bgp-oper:bgp-state-data"

# Per-path noise in bgp-path-entry: always empty/zero/disabled in this topology.
# Agent needs: nexthop, metric, local-pref, weight, as-path, origin,
#              path-status, path-id, path-origin.
_BGP_PATH_NOISE = frozenset({
    "rpki-status", "community", "mpls-in", "mpls-out",
    "sr-profile-name", "sr-binding-sid", "sr-label-indx",
    "as4-path", "atomic-aggregate", "aggr-as-number", "aggr-as4-number",
    "aggr-address", "originator-id", "cluster-list",
    "extended-community", "ext-aigp-metric",
})

# Fields in Cisco-IOS-XE-ospf-oper that encode IPv4 addresses as uint32.
# Includes both process-level fields (router-id, area-id, neighbor-id, dr/bdr)
# and LSDB fields (lsa-id, advertising-router, link-id, link-data).
_OSPF_IP_FIELDS = frozenset({
    "router-id", "area-id", "dr-address", "bdr-address", "neighbor-id",
    "lsa-id", "advertising-router", "link-id", "link-data",
})

# Fields in ospf-interface entries that have no diagnostic value and only add noise.
_OSPF_INTF_NOISE = frozenset({
    "fast-reroute", "ttl-security", "multi-area", "prefix-suppression",
    "lls", "demand-circuit", "node-flag", "enable", "wait-timer", "bfd",
})


def _uint32_to_ip(value):
    """Convert a uint32 (int or numeric str) to dotted-decimal. Pass through otherwise."""
    try:
        n = int(value)
        if 0 <= n <= 0xFFFFFFFF:
            return str(ipaddress.IPv4Address(n))
    except (ValueError, TypeError):
        pass
    return value


def _convert_ospf_ip_fields(data):
    """Recursively convert known uint32 IP fields to dotted-decimal strings."""
    if isinstance(data, dict):
        return {k: _uint32_to_ip(v) if k in _OSPF_IP_FIELDS else _convert_ospf_ip_fields(v)
                for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_ospf_ip_fields(item) for item in data]
    return data


def _recursive_strip(data, keys_to_remove: frozenset):
    """Recursively remove specific keys from any nested dict/list structure.

    Transport-agnostic — works on RESTCONF JSON output without caring about
    the outer wrapper format.
    """
    if isinstance(data, dict):
        return {k: _recursive_strip(v, keys_to_remove)
                for k, v in data.items() if k not in keys_to_remove}
    if isinstance(data, list):
        return [_recursive_strip(item, keys_to_remove) for item in data]
    return data


def _trim_ospf(result: dict, query: str) -> dict:
    """Post-process OSPF results for the RESTCONF transport tier.

    Two operations are performed, in order:
    1. Convert uint32-encoded IP fields to dotted-decimal.
       The Cisco-IOS-XE-ospf-oper YANG model encodes many IP addresses (router-id,
       area-id, lsa-id, etc.) as uint32 integers in RESTCONF JSON responses.
    2. Strip noise fields that are irrelevant to the query, reducing token cost.
       Uses recursive key-based stripping.
    """
    transport = result.get("_transport_used")
    raw = result.get("raw")
    if not isinstance(raw, dict) or "error" in raw:
        return result

    # 1. Convert uint32 IP fields (RESTCONF only)
    if transport == "restconf":
        result["raw"] = _convert_ospf_ip_fields(raw)
        raw = result["raw"]

    # 2. Structural trimming (RESTCONF only)
    if transport != "restconf" or query == "config":
        return result

    if query == "neighbors":
        # Strip per-interface noise; keep neighbor-relevant fields
        result["raw"] = _recursive_strip(raw, _OSPF_INTF_NOISE)
    elif query == "interfaces":
        # Strip ospf-neighbor entries and noise — interface params are the point of this query
        result["raw"] = _recursive_strip(raw, _OSPF_INTF_NOISE | {"ospf-neighbor"})
    elif query == "details":
        # Strip all per-interface data — keep process/area summary only
        result["raw"] = _recursive_strip(raw, {"ospf-interface"})
    # database, borders: IP conversion applied above; no structural strip needed

    return result


def _filter_bgp_ipv4_unicast(data):
    """Recursively filter bgp-route-af lists to ipv4-unicast entries only.

    BGP route tables include empty stubs for ipv4-mdt, ipv4-multicast, etc.
    This removes them to reduce noise without affecting diagnostic content.
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k == "bgp-route-af" and isinstance(v, list):
                result[k] = [_filter_bgp_ipv4_unicast(af) for af in v
                             if af.get("afi-safi") == "ipv4-unicast"]
            else:
                result[k] = _filter_bgp_ipv4_unicast(v)
        return result
    if isinstance(data, list):
        return [_filter_bgp_ipv4_unicast(item) for item in data]
    return data


def _trim_bgp(result: dict, query: str) -> dict:
    """Post-process BGP results for the RESTCONF transport tier.

    For the 'table' query: filters bgp-route-af lists to ipv4-unicast only,
    dropping empty ipv4-mdt/ipv4-multicast AF stubs.
    For the 'neighbors' query: strips configured-policies/inherited-policies
    from peer-policy (60+ mostly-empty boolean fields per neighbor).
    """
    transport = result.get("_transport_used")
    raw = result.get("raw")
    if not isinstance(raw, dict) or "error" in raw:
        return result
    if transport != "restconf" or query == "config":
        return result

    if query == "table":
        result["raw"] = _filter_bgp_ipv4_unicast(raw)
        result["raw"] = _recursive_strip(result["raw"], _BGP_PATH_NOISE)
    elif query == "neighbors":
        result["raw"] = _recursive_strip(raw, {"configured-policies", "inherited-policies"})
    # summary: already well-scoped by URL path, no trim needed

    return result


async def get_ospf(params: OspfQuery) -> dict:
    """
    Retrieve OSPF operational data from a network device.

    Use this tool to investigate OSPF adjacency, database, and configuration
    issues during troubleshooting.

    Supported queries:
    - neighbors   → Check OSPF neighbor state and adjacency health
    - database    → Inspect LSDB contents and LSA propagation
    - borders     → Identify ABRs/ASBRs and inter-area routing
    - config      → Review OSPF configuration on the device
    - interfaces  → Verify OSPF-enabled interfaces and parameters
    - details     → Vendor-specific detailed OSPF information (if available)

    Notes:
    - Not all queries are supported on all platforms.
    - c8000v RESTCONF devices return all-VRF data; agent filters by VRF.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    try:
        action = get_action(device, "ospf", params.query, vrf=params.vrf)
    except KeyError:
        return _error_response(params.device, f"OSPF query '{params.query}' not supported on platform {device['cli_style'].upper()}")

    result = await execute_command(params.device, action, transport=params.transport)
    return _trim_ospf(result, params.query)


async def get_bgp(params: BgpQuery) -> dict:
    """
    Retrieve BGP operational data from a network device.

    Use this tool to investigate BGP session state, route exchange,
    and configuration during routing issues.

    Supported queries:
    - summary    → Check neighbor state, uptime, and prefixes exchanged
    - table      → Inspect detailed BGP table and path attributes
    - config     → Review BGP configuration
    - neighbors  → Per-neighbor detail: negotiated timers, capabilities, address families

    Notes:
    - Supported queries vary by platform.
    - For "neighbors" on IOS asyncssh, provide neighbor=<ip> to scope output to a single peer.

    Recommended usage:
    - Start with "summary" to verify session health.
    - Use "table" when routes are missing or path selection is unexpected.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return _error_response(params.device, f"Unknown device: {params.device}")

    try:
        action = get_action(device, "bgp", params.query, vrf=params.vrf)
    except KeyError:
        return _error_response(params.device, f"BGP query '{params.query}' not supported on platform {device['cli_style'].upper()}")

    if params.query == "neighbors" and params.neighbor and isinstance(action, str):
        # IOS asyncssh: append neighbor IP to CLI command string for scoped output
        action = f"{action} {params.neighbor}"

    result = await execute_command(params.device, action, transport=params.transport)
    return _trim_bgp(result, params.query)
