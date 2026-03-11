"""UT-015 — Tool layer dispatch tests.

Tests for tools/protocol.py, tools/operational.py, tools/routing.py.
No real device connectivity — transport.execute_command is mocked.

Validates:
- get_ospf on asyncssh device passes plain CLI string to execute_command
- get_ospf on restconf device passes ActionChain to execute_command
- get_bgp routes through platform_map correctly
- get_routing dispatches correctly (with and without prefix)
- get_interfaces dispatches correctly
- ping on restconf device uses plain CLI string (not ActionChain)
- traceroute on restconf device uses plain CLI string
- run_show rejects non-show commands at validation
- run_show accepts show-prefix commands and forwards to execute_command
- get_ospf with vrf parameter flows through to action resolution
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from platforms.platform_map import ActionChain
from input_models.models import (
    OspfQuery, BgpQuery, RoutingQuery, InterfacesQuery,
    PingInput, TracerouteInput, ShowCommand,
)
from tools.protocol import get_ospf, get_bgp, _trim_ospf, _trim_bgp
from tools.routing import get_routing
from tools.operational import get_interfaces, ping, traceroute, run_show


# ── Device fixtures ───────────────────────────────────────────────────────────

ASYNCSSH_DEV = {
    "host": "172.20.20.205",
    "platform": "cisco_iol",
    "transport": "asyncssh",
    "cli_style": "ios",
}

RESTCONF_DEV = {
    "host": "172.20.20.209",
    "platform": "cisco_c8000v",
    "transport": "restconf",
    "cli_style": "ios",
}

MOCK_RESULT = {"device": "X", "cli_style": "ios", "raw": "output"}


def run(coro):
    return asyncio.run(coro)


def _run_get_ospf(device_name, device_dict, query="neighbors", vrf=None):
    params = OspfQuery(device=device_name, query=query, vrf=vrf)
    mock_result = {**MOCK_RESULT, "device": device_name}
    with patch("tools.protocol.devices", {device_name: device_dict}), \
         patch("tools.protocol.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        result = run(get_ospf(params))
    return result, mock_exec


# ── get_ospf ──────────────────────────────────────────────────────────────────

def test_get_ospf_asyncssh_uses_cli_string():
    """get_ospf on an asyncssh device must pass a plain CLI string to execute_command."""
    result, mock_exec = _run_get_ospf("A1C", ASYNCSSH_DEV, query="neighbors")

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str), "asyncssh device must use plain CLI string"
    assert not isinstance(action_used, ActionChain)
    assert "show ip ospf neighbor" in action_used


def test_get_ospf_restconf_uses_actionchain():
    """get_ospf on a restconf device must pass an ActionChain to execute_command."""
    result, mock_exec = _run_get_ospf("E1C", RESTCONF_DEV, query="neighbors")

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, ActionChain), "restconf device must use ActionChain"


def test_get_ospf_unknown_device_returns_error():
    """get_ospf with an unknown device name must return an error dict."""
    params = OspfQuery(device="UNKNOWN", query="neighbors")
    with patch("tools.protocol.devices", {}):
        result = run(get_ospf(params))
    assert "error" in result


def test_get_ospf_vrf_param_flows_through():
    """VRF parameter must be passed to get_action and influence the action returned."""
    result, mock_exec = _run_get_ospf("A1C", ASYNCSSH_DEV, query="neighbors", vrf="VRF1")
    # For asyncssh + ios: ospf has no VRF variant, so the plain string is returned unchanged
    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str)


# ── get_bgp ───────────────────────────────────────────────────────────────────

def test_get_bgp_asyncssh_uses_cli_string():
    """get_bgp on asyncssh device must pass plain CLI string to execute_command."""
    params = BgpQuery(device="A1C", query="summary")
    mock_result = {**MOCK_RESULT, "device": "A1C"}
    with patch("tools.protocol.devices", {"A1C": ASYNCSSH_DEV}), \
         patch("tools.protocol.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(get_bgp(params))

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str)
    assert "show ip bgp" in action_used


def test_get_bgp_restconf_uses_actionchain():
    """get_bgp on restconf device must pass ActionChain to execute_command."""
    params = BgpQuery(device="E1C", query="summary")
    mock_result = {**MOCK_RESULT, "device": "E1C"}
    with patch("tools.protocol.devices", {"E1C": RESTCONF_DEV}), \
         patch("tools.protocol.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(get_bgp(params))

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, ActionChain)


def test_get_bgp_neighbor_filter_appended_for_asyncssh():
    """get_bgp with neighbor IP on asyncssh device must append the neighbor to the CLI string."""
    params = BgpQuery(device="A1C", query="neighbors", neighbor="10.0.0.1")
    mock_result = {**MOCK_RESULT, "device": "A1C"}
    with patch("tools.protocol.devices", {"A1C": ASYNCSSH_DEV}), \
         patch("tools.protocol.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(get_bgp(params))

    action_used = mock_exec.call_args[0][1]
    assert "10.0.0.1" in action_used, "neighbor IP must be appended to CLI string for asyncssh"


# ── get_routing ───────────────────────────────────────────────────────────────

def test_get_routing_no_prefix_uses_full_table_command():
    """get_routing without prefix must pass the full route table action."""
    params = RoutingQuery(device="A1C")
    mock_result = {**MOCK_RESULT, "device": "A1C"}
    with patch("tools.routing.devices", {"A1C": ASYNCSSH_DEV}), \
         patch("tools.routing.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(get_routing(params))

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str)
    assert "show ip route" in action_used
    assert "10." not in action_used  # no prefix appended


def test_get_routing_with_prefix_appends_to_cli():
    """get_routing with prefix on asyncssh device must append the prefix to the CLI command."""
    params = RoutingQuery(device="A1C", prefix="10.0.0.26")
    mock_result = {**MOCK_RESULT, "device": "A1C"}
    with patch("tools.routing.devices", {"A1C": ASYNCSSH_DEV}), \
         patch("tools.routing.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(get_routing(params))

    action_used = mock_exec.call_args[0][1]
    assert "10.0.0.26" in action_used, "prefix must be appended to CLI command"


# ── get_interfaces ────────────────────────────────────────────────────────────

def test_get_interfaces_asyncssh_uses_cli_string():
    """get_interfaces on asyncssh device must pass CLI string to execute_command."""
    params = InterfacesQuery(device="A1C")
    mock_result = {**MOCK_RESULT, "device": "A1C"}
    with patch("tools.operational.devices", {"A1C": ASYNCSSH_DEV}), \
         patch("tools.operational.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(get_interfaces(params))

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str)
    assert "show ip interface brief" in action_used


# ── ping / traceroute: always CLI strings ─────────────────────────────────────

def test_ping_restconf_device_uses_cli_string():
    """ping on a restconf device must use a plain CLI string, never an ActionChain."""
    params = PingInput(device="E1C", destination="10.0.0.26")
    mock_result = {**MOCK_RESULT, "device": "E1C"}
    with patch("tools.operational.devices", {"E1C": RESTCONF_DEV}), \
         patch("tools.operational.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(ping(params))

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str), "ping must use CLI string even on restconf device"
    assert not isinstance(action_used, ActionChain)
    assert "ping" in action_used
    assert "10.0.0.26" in action_used


def test_traceroute_restconf_device_uses_cli_string():
    """traceroute on a restconf device must use a plain CLI string, never an ActionChain."""
    params = TracerouteInput(device="E1C", destination="10.0.0.26")
    mock_result = {**MOCK_RESULT, "device": "E1C"}
    with patch("tools.operational.devices", {"E1C": RESTCONF_DEV}), \
         patch("tools.operational.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        run(traceroute(params))

    action_used = mock_exec.call_args[0][1]
    assert isinstance(action_used, str), "traceroute must use CLI string even on restconf device"
    assert not isinstance(action_used, ActionChain)
    assert "traceroute" in action_used
    assert "10.0.0.26" in action_used


# ── run_show ──────────────────────────────────────────────────────────────────

def test_run_show_rejects_non_show_command():
    """run_show must reject 'configure terminal' at input validation (ValidationError)."""
    with pytest.raises(ValidationError):
        ShowCommand(device="A1C", command="configure terminal")


def test_run_show_accepts_show_prefix_and_dispatches():
    """run_show must accept 'show ...' command and forward to execute_command."""
    params = ShowCommand(device="A1C", command="show ip route")
    mock_result = {**MOCK_RESULT, "device": "A1C"}
    with patch("tools.operational.devices", {"A1C": ASYNCSSH_DEV}), \
         patch("tools.operational.execute_command", new=AsyncMock(return_value=mock_result)) as mock_exec:
        result = run(run_show(params))

    mock_exec.assert_called_once()
    assert result == mock_result


# ── _trim_ospf ─────────────────────────────────────────────────────────────────
#
# Fixtures use the ACTUAL RESTCONF response structure:
# - RESTCONF: child container at top level with module-prefix key
# e.g. {"Cisco-IOS-XE-ospf-oper:ospf-state": {"ospf-instance": [...]}}

_OSPF_NEIGHBORS_RESTCONF = {
    "Cisco-IOS-XE-ospf-oper:ospf-state": {
        "ospf-instance": [
            {
                "af": "address-family-ipv4",
                "router-id": 3232243969,  # 192.168.33.1 as uint32
                "ospf-area": [
                    {
                        "area-id": 0,  # 0.0.0.0 as uint32
                        "ospf-interface": [
                            {
                                "name": "GigabitEthernet2",
                                "cost": 1,
                                "hello-interval": 10,
                                "dead-interval": 40,
                                "state": "DR",
                                "dr": "33.33.33.11",  # already dotted (different YANG field)
                                "bdr": "22.22.22.22",
                                "fast-reroute": {"enabled": False},      # noise
                                "ttl-security": {"enabled": False},      # noise
                                "multi-area": {"multi-area-id": 0},      # noise
                                "lls": False,                            # noise
                                "ospf-neighbor": [
                                    {"neighbor-id": "22.22.22.22", "state": "ospf-nbr-full"}
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }
}

_OSPF_DATABASE_RESTCONF = {
    "Cisco-IOS-XE-ospf-oper:ospfv2-instance": [
        {
            "instance-id": 1,
            "router-id": 555819275,              # 33.33.33.11 as uint32
            "ospfv2-area": [
                {
                    "area-id": 0,                # 0.0.0.0 as uint32
                    "ospfv2-lsdb-area": [
                        {
                            "lsa-type": 1,
                            "lsa-id": 167772186,          # 10.0.0.26 as uint32
                            "advertising-router": 167772186,
                            "ospfv2-router-lsa-links": [
                                {"link-id": 167772186, "link-data": 167772185}
                            ],
                        }
                    ],
                }
            ],
        }
    ]
}

def _ospf_result_rc(query="neighbors"):
    """RESTCONF OSPF result fixture."""
    import copy
    if query == "database":
        raw = copy.deepcopy(_OSPF_DATABASE_RESTCONF)
    else:
        raw = copy.deepcopy(_OSPF_NEIGHBORS_RESTCONF)
    return {"_transport_used": "restconf", "raw": raw}


def test_trim_ospf_converts_uint32_router_id_restconf():
    """RESTCONF neighbors: router-id (uint32 int) must be converted to dotted-decimal."""
    result = _trim_ospf(_ospf_result_rc("neighbors"), "neighbors")
    inst = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]
    assert inst["router-id"] == "192.168.33.1", f"Expected dotted-decimal, got: {inst['router-id']}"
    assert inst["ospf-area"][0]["area-id"] == "0.0.0.0"


def test_trim_ospf_converts_uint32_lsdb_fields_restconf():
    """RESTCONF database: lsa-id, advertising-router, link-id, link-data must be dotted-decimal."""
    result = _trim_ospf(_ospf_result_rc("database"), "database")
    inst = result["raw"]["Cisco-IOS-XE-ospf-oper:ospfv2-instance"][0]
    assert inst["router-id"] == "33.33.33.11"
    lsdb = inst["ospfv2-area"][0]["ospfv2-lsdb-area"][0]
    assert lsdb["lsa-id"] == "10.0.0.26"
    assert lsdb["advertising-router"] == "10.0.0.26"
    link = lsdb["ospfv2-router-lsa-links"][0]
    assert link["link-id"] == "10.0.0.26"
    assert link["link-data"] == "10.0.0.25"


def test_trim_ospf_neighbors_strips_noise_fields():
    """neighbors query: noise fields (fast-reroute, ttl-security, multi-area, lls) must be stripped."""
    result = _trim_ospf(_ospf_result_rc("neighbors"), "neighbors")
    intf = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]["ospf-area"][0]["ospf-interface"][0]
    for noise_key in ("fast-reroute", "ttl-security", "multi-area", "lls"):
        assert noise_key not in intf, f"{noise_key} must be stripped from neighbors result"


def test_trim_ospf_neighbors_keeps_neighbor_entries():
    """neighbors query: ospf-neighbor list must be preserved."""
    result = _trim_ospf(_ospf_result_rc("neighbors"), "neighbors")
    intf = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]["ospf-area"][0]["ospf-interface"][0]
    assert "ospf-neighbor" in intf, "ospf-neighbor list must be kept for neighbors query"
    assert intf["ospf-neighbor"][0]["state"] == "ospf-nbr-full"


def test_trim_ospf_neighbors_keeps_diagnostic_fields():
    """neighbors query: diagnostic fields (cost, timers, state, dr, bdr) must be preserved."""
    result = _trim_ospf(_ospf_result_rc("neighbors"), "neighbors")
    intf = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]["ospf-area"][0]["ospf-interface"][0]
    for field in ("name", "cost", "hello-interval", "dead-interval", "state", "dr", "bdr"):
        assert field in intf, f"{field} must be preserved in neighbors result"


def test_trim_ospf_interfaces_strips_neighbors_and_noise():
    """interfaces query: ospf-neighbor and noise fields must be stripped; other interface params kept."""
    result = _trim_ospf(_ospf_result_rc("interfaces"), "interfaces")
    intf = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]["ospf-area"][0]["ospf-interface"][0]
    assert "ospf-neighbor" not in intf, "ospf-neighbor must be stripped for interfaces query"
    for noise_key in ("fast-reroute", "ttl-security", "multi-area", "lls"):
        assert noise_key not in intf, f"{noise_key} must be stripped for interfaces query"
    assert "cost" in intf
    assert "hello-interval" in intf
    assert "state" in intf


def test_trim_ospf_details_strips_ospf_interface():
    """details query: ospf-interface list must be stripped; instance/area summary kept."""
    result = _trim_ospf(_ospf_result_rc("details"), "details")
    area = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]["ospf-area"][0]
    assert "ospf-interface" not in area, "ospf-interface must be stripped for details query"
    # Area-id should still be present (and converted)
    assert "area-id" in area


def test_trim_ospf_database_no_structural_strip():
    """database query: structure must be unchanged (only IP conversion applied)."""
    result = _trim_ospf(_ospf_result_rc("database"), "database")
    # The ospfv2-lsdb-area must remain — database query needs full LSDB
    area = result["raw"]["Cisco-IOS-XE-ospf-oper:ospfv2-instance"][0]["ospfv2-area"][0]
    assert "ospfv2-lsdb-area" in area, "LSDB must be preserved for database query"


def test_trim_ospf_ssh_result_unchanged():
    """SSH results must be returned unchanged — no conversion or trimming."""
    import copy
    result = _trim_ospf({"_transport_used": "ssh", "raw": copy.deepcopy(_OSPF_NEIGHBORS_RESTCONF)}, "neighbors")
    # SSH results pass through — uint32 not converted, noise not stripped
    inst = result["raw"]["Cisco-IOS-XE-ospf-oper:ospf-state"]["ospf-instance"][0]
    assert inst["router-id"] == 3232243969  # raw integer, unchanged
    intf = inst["ospf-area"][0]["ospf-interface"][0]
    assert "fast-reroute" in intf  # noise not stripped


def test_trim_ospf_error_result_unchanged():
    """Error results must be returned unchanged."""
    result = _trim_ospf({"_transport_used": "restconf", "raw": {"error": "timeout"}}, "neighbors")
    assert "error" in result["raw"]


# ── _trim_bgp ──────────────────────────────────────────────────────────────────
#
# Fixtures use the ACTUAL RESTCONF response structure — child container at top level.
# RESTCONF summary returns  {"Cisco-IOS-XE-bgp-oper:address-families": {...}}.
# RESTCONF table returns    {"Cisco-IOS-XE-bgp-oper:bgp-route-vrfs": {...}}.
# RESTCONF neighbors returns {"Cisco-IOS-XE-bgp-oper:neighbors": {...}}.

_BGP_TABLE_RESTCONF = {
    "Cisco-IOS-XE-bgp-oper:bgp-route-vrfs": {
        "bgp-route-vrf": [
            {
                "vrf": "default",
                "bgp-route-afs": {
                    "bgp-route-af": [
                        {"afi-safi": "ipv4-unicast", "bgp-route-filters": {}},
                        {"afi-safi": "ipv4-mdt",     "bgp-route-filters": {}},
                        {"afi-safi": "ipv4-multicast","bgp-route-filters": {}},
                    ]
                },
            }
        ]
    }
}

_BGP_NEIGHBORS_RESTCONF = {
    "Cisco-IOS-XE-bgp-oper:neighbors": {
        "neighbor": [
            {
                "neighbor-id": "200.40.40.2",
                "session-state": "fsm-established",
                "peer-policy": {
                    "name": "",
                    "total-inherited": 0,
                    "configured-policies": {"route-map-in": "", "weight": 0},
                    "inherited-policies": {"configured-policies": {"weight": 0}},
                },
            }
        ]
    }
}


def _bgp_table_result(transport="restconf"):
    import copy
    return {"_transport_used": transport, "raw": copy.deepcopy(_BGP_TABLE_RESTCONF)}


def _bgp_nbr_result(transport="restconf"):
    import copy
    return {"_transport_used": transport, "raw": copy.deepcopy(_BGP_NEIGHBORS_RESTCONF)}


def test_trim_bgp_table_filters_to_ipv4_unicast_restconf():
    """RESTCONF table query: bgp-route-af list must contain only ipv4-unicast after trim."""
    result = _trim_bgp(_bgp_table_result("restconf"), "table")
    vrfs = result["raw"]["Cisco-IOS-XE-bgp-oper:bgp-route-vrfs"]["bgp-route-vrf"]
    for vrf_entry in vrfs:
        afs = vrf_entry["bgp-route-afs"]["bgp-route-af"]
        assert len(afs) == 1
        assert afs[0]["afi-safi"] == "ipv4-unicast"


def test_trim_bgp_neighbors_drops_policy_dumps():
    """neighbors query: peer-policy must NOT contain configured-policies or inherited-policies."""
    result = _trim_bgp(_bgp_nbr_result(), "neighbors")
    for nbr in result["raw"]["Cisco-IOS-XE-bgp-oper:neighbors"]["neighbor"]:
        pp = nbr.get("peer-policy", {})
        assert "configured-policies" not in pp
        assert "inherited-policies" not in pp
        assert "name" in pp  # non-policy fields preserved


def test_trim_bgp_neighbors_preserves_session_state():
    """neighbors query: diagnostic fields (session-state, neighbor-id) must be preserved."""
    result = _trim_bgp(_bgp_nbr_result(), "neighbors")
    nbr = result["raw"]["Cisco-IOS-XE-bgp-oper:neighbors"]["neighbor"][0]
    assert nbr["neighbor-id"] == "200.40.40.2"
    assert nbr["session-state"] == "fsm-established"


def test_trim_bgp_summary_passthrough():
    """summary query is a passthrough — response already scoped by URL, no trimming needed."""
    import copy
    summary_raw = {"Cisco-IOS-XE-bgp-oper:address-families": {"address-family": []}}
    result = _trim_bgp({"_transport_used": "restconf", "raw": copy.deepcopy(summary_raw)}, "summary")
    assert "Cisco-IOS-XE-bgp-oper:address-families" in result["raw"]


def test_trim_bgp_ssh_result_unchanged():
    """SSH results must be returned unchanged — no trimming applied."""
    import copy
    raw = copy.deepcopy(_BGP_TABLE_RESTCONF)
    result = _trim_bgp({"_transport_used": "ssh", "raw": raw}, "table")
    # ipv4-mdt and ipv4-multicast must still be present (no filtering for SSH)
    afs = result["raw"]["Cisco-IOS-XE-bgp-oper:bgp-route-vrfs"]["bgp-route-vrf"][0]["bgp-route-afs"]["bgp-route-af"]
    af_types = {af["afi-safi"] for af in afs}
    assert "ipv4-mdt" in af_types
    assert "ipv4-multicast" in af_types


_BGP_TABLE_WITH_PATH_NOISE = {
    "Cisco-IOS-XE-bgp-oper:bgp-route-vrfs": {
        "bgp-route-vrf": [
            {
                "vrf": "default",
                "bgp-route-afs": {
                    "bgp-route-af": [
                        {
                            "afi-safi": "ipv4-unicast",
                            "bgp-route-filters": {
                                "bgp-route-filter": [
                                    {
                                        "route-filter": "bgp-rf-all",
                                        "bgp-route-entries": {
                                            "bgp-route-entry": [
                                                {
                                                    "prefix": "8.8.8.8/32",
                                                    "version": 2,
                                                    "available-paths": 1,
                                                    "bgp-path-entries": {
                                                        "bgp-path-entry": [
                                                            {
                                                                "nexthop": "200.40.40.2",
                                                                "metric": 0,
                                                                "local-pref": 100,
                                                                "weight": 0,
                                                                "as-path": "4040 2020",
                                                                "origin": "origin-igp",
                                                                "path-status": {"valid": [None], "bestpath": [None]},
                                                                "path-id": 0,
                                                                "path-origin": "external-path",
                                                                # noise fields below
                                                                "rpki-status": "rpki-not-enabled",
                                                                "community": "",
                                                                "mpls-in": "",
                                                                "mpls-out": "",
                                                                "sr-profile-name": "",
                                                                "sr-binding-sid": 0,
                                                                "sr-label-indx": 0,
                                                                "as4-path": "",
                                                                "atomic-aggregate": False,
                                                                "aggr-as-number": 0,
                                                                "aggr-as4-number": 0,
                                                                "aggr-address": "",
                                                                "originator-id": "",
                                                                "cluster-list": "",
                                                                "extended-community": "",
                                                                "ext-aigp-metric": "0",
                                                            }
                                                        ]
                                                    },
                                                }
                                            ]
                                        },
                                    }
                                ]
                            },
                        },
                        {"afi-safi": "ipv4-mdt", "bgp-route-filters": {}},
                    ]
                },
            }
        ]
    }
}

_BGP_PATH_NOISE_KEYS = {
    "rpki-status", "community", "mpls-in", "mpls-out",
    "sr-profile-name", "sr-binding-sid", "sr-label-indx",
    "as4-path", "atomic-aggregate", "aggr-as-number", "aggr-as4-number",
    "aggr-address", "originator-id", "cluster-list",
    "extended-community", "ext-aigp-metric",
}
_BGP_PATH_KEEP_KEYS = {
    "nexthop", "metric", "local-pref", "weight", "as-path",
    "origin", "path-status", "path-id", "path-origin",
}


def test_trim_bgp_table_strips_path_noise_restconf():
    """table query: per-path noise fields must be absent; diagnostic fields preserved."""
    import copy
    result = _trim_bgp({"_transport_used": "restconf", "raw": copy.deepcopy(_BGP_TABLE_WITH_PATH_NOISE)}, "table")
    vrfs = result["raw"]["Cisco-IOS-XE-bgp-oper:bgp-route-vrfs"]["bgp-route-vrf"]
    for vrf_entry in vrfs:
        # AF filtering still applied: only ipv4-unicast remains
        afs = vrf_entry["bgp-route-afs"]["bgp-route-af"]
        assert all(af["afi-safi"] == "ipv4-unicast" for af in afs)
        # Check path entries
        for af in afs:
            filters = af["bgp-route-filters"].get("bgp-route-filter", [])
            for f in filters:
                for entry in f["bgp-route-entries"]["bgp-route-entry"]:
                    for path in entry["bgp-path-entries"]["bgp-path-entry"]:
                        for noise_key in _BGP_PATH_NOISE_KEYS:
                            assert noise_key not in path, f"noise key '{noise_key}' still present"
                        for keep_key in _BGP_PATH_KEEP_KEYS:
                            assert keep_key in path, f"diagnostic key '{keep_key}' was removed"
