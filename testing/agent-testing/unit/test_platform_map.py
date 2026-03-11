"""
UT-002 — Platform Map Commands

Verifies that PLATFORM_MAP returns the correct commands for each
section (ios, ios_restconf) and all relevant query types.
Also verifies the get_action() helper including:
- ActionChain construction (2-tier: RESTCONF → SSH) for restconf transport devices
- VRF resolution via dual-entry CLI format and {vrf} substitution
- Restconf tools (ping/traceroute) fall back to plain CLI strings
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "platforms"))
from platform_map import PLATFORM_MAP, ActionChain, get_action


# ── IOS ───────────────────────────────────────────────────────────────────────

class TestIOS:
    """Verify PLATFORM_MAP command strings for Cisco IOS (cli_style='ios').

    IOS OSPF entries are plain strings (show commands cover all VRFs automatically).
    BGP/routing_table entries use dual-entry format for VRF support.
    VRF-agnostic entries (routing_policies, interfaces) remain plain strings.
    """

    def test_ospf_neighbors(self):
        """OSPF neighbors must be a plain CLI string."""
        entry = PLATFORM_MAP["ios"]["ospf"]["neighbors"]
        assert entry == "show ip ospf neighbor"

    def test_ospf_database(self):
        """OSPF database must be a plain CLI string."""
        entry = PLATFORM_MAP["ios"]["ospf"]["database"]
        assert entry == "show ip ospf database"

    def test_ospf_interfaces(self):
        """OSPF interfaces must be a plain CLI string."""
        entry = PLATFORM_MAP["ios"]["ospf"]["interfaces"]
        assert entry == "show ip ospf interface"

    def test_ospf_config(self):
        """OSPF config must be a plain CLI string containing 'ospf'."""
        entry = PLATFORM_MAP["ios"]["ospf"]["config"]
        assert isinstance(entry, str)
        assert "ospf" in entry

    def test_ospf_borders(self):
        """OSPF borders must be a plain CLI string."""
        entry = PLATFORM_MAP["ios"]["ospf"]["borders"]
        assert entry == "show ip ospf border-routers"

    def test_ospf_details(self):
        """OSPF details must be a plain CLI string."""
        entry = PLATFORM_MAP["ios"]["ospf"]["details"]
        assert entry == "show ip ospf"

    def test_bgp_summary(self):
        """Summary dual-entry: default must be the IOS BGP summary show command."""
        entry = PLATFORM_MAP["ios"]["bgp"]["summary"]
        assert entry["default"] == "show ip bgp summary"

    def test_bgp_summary_vrf(self):
        """Summary dual-entry: vrf template must include 'vpnv4 vrf' for IOS."""
        entry = PLATFORM_MAP["ios"]["bgp"]["summary"]
        assert "vpnv4" in entry["vrf"]
        assert "{vrf}" in entry["vrf"]

    def test_bgp_neighbors(self):
        """Neighbors dual-entry: default must be the IOS BGP neighbors show command."""
        entry = PLATFORM_MAP["ios"]["bgp"]["neighbors"]
        assert entry["default"] == "show ip bgp neighbors"

    def test_routing_table(self):
        """ip_route dual-entry: default must be the IOS routing table show command."""
        entry = PLATFORM_MAP["ios"]["routing_table"]["ip_route"]
        assert entry["default"] == "show ip route"

    def test_routing_table_vrf(self):
        """ip_route dual-entry: vrf template must include 'vrf {vrf}'."""
        entry = PLATFORM_MAP["ios"]["routing_table"]["ip_route"]
        assert "vrf" in entry["vrf"]
        assert "{vrf}" in entry["vrf"]

    def test_redistribution(self):
        """Redistribution query must remain a plain string (VRF-agnostic)."""
        assert "redistribute" in PLATFORM_MAP["ios"]["routing_policies"]["redistribution"]

    def test_interfaces(self):
        """Interface status query must remain a plain string (VRF-agnostic)."""
        assert PLATFORM_MAP["ios"]["interfaces"]["interface_status"] == "show ip interface brief"

    def test_ping(self):
        """Ping dual-entry: default must be 'ping'."""
        entry = PLATFORM_MAP["ios"]["tools"]["ping"]
        assert entry["default"] == "ping"

    def test_ping_vrf(self):
        """Ping dual-entry: vrf template must prepend 'ping vrf {vrf}'."""
        entry = PLATFORM_MAP["ios"]["tools"]["ping"]
        assert entry["vrf"] == "ping vrf {vrf}"

    def test_traceroute(self):
        """Traceroute dual-entry: default must be 'traceroute'."""
        entry = PLATFORM_MAP["ios"]["tools"]["traceroute"]
        assert entry["default"] == "traceroute"

    def test_traceroute_vrf(self):
        """Traceroute dual-entry: vrf template must prepend 'traceroute vrf {vrf}'."""
        entry = PLATFORM_MAP["ios"]["tools"]["traceroute"]
        assert entry["vrf"] == "traceroute vrf {vrf}"


# ── IOS RESTCONF ───────────────────────────────────────────────────────────────

class TestIOSRestconf:
    """Verify PLATFORM_MAP RESTCONF action dicts for Cisco c8000v (ios_restconf).

    ios_restconf devices use RESTCONF GET to Cisco-IOS-XE YANG endpoints.
    All entries are {"url": "...", "method": "GET"} dicts.
    Tools (ping/traceroute) are not present — get_action() falls back to ios CLI strings.
    """

    def test_ospf_neighbors_is_restconf_get(self):
        """OSPF neighbors must be a RESTCONF GET dict with Cisco ospf-oper YANG URL."""
        entry = PLATFORM_MAP["ios_restconf"]["ospf"]["neighbors"]
        assert "url" in entry
        assert entry["method"] == "GET"
        assert "ospf" in entry["url"].lower()

    def test_ospf_config_is_restconf_get(self):
        """OSPF config must be a RESTCONF GET dict pointing to native/router/router-ospf."""
        entry = PLATFORM_MAP["ios_restconf"]["ospf"]["config"]
        assert "url" in entry
        assert entry["method"] == "GET"
        assert "ospf" in entry["url"].lower()

    def test_bgp_summary_is_restconf_get(self):
        """BGP summary must be a RESTCONF GET dict with Cisco bgp-oper YANG URL."""
        entry = PLATFORM_MAP["ios_restconf"]["bgp"]["summary"]
        assert "url" in entry
        assert entry["method"] == "GET"
        assert "bgp" in entry["url"].lower()

    def test_routing_table_is_restconf_get(self):
        """Routing table must be a RESTCONF GET dict with Cisco fib-oper YANG URL."""
        entry = PLATFORM_MAP["ios_restconf"]["routing_table"]["ip_route"]
        assert "url" in entry
        assert entry["method"] == "GET"
        assert "fib" in entry["url"].lower()

    def test_interfaces_is_restconf_get(self):
        """Interface status must be a RESTCONF GET dict with ietf-interfaces YANG URL."""
        entry = PLATFORM_MAP["ios_restconf"]["interfaces"]["interface_status"]
        assert "url" in entry
        assert entry["method"] == "GET"
        assert "interface" in entry["url"].lower()

    def test_routing_policies_all_are_restconf_get(self):
        """All routing policy queries must be RESTCONF GET dicts."""
        for qname in ["redistribution", "route_maps", "prefix_lists",
                      "policy_based_routing", "access_lists"]:
            entry = PLATFORM_MAP["ios_restconf"]["routing_policies"][qname]
            assert "url" in entry, f"{qname} must have 'url' key"
            assert entry["method"] == "GET", f"{qname} must use GET method"

    def test_no_tools_section(self):
        """ios_restconf must not define a tools section — ping/traceroute use ios CLI fallback."""
        assert "tools" not in PLATFORM_MAP["ios_restconf"]


# ── Removed sections must not exist ───────────────────────────────────────────

class TestRemovedSections:
    """Confirm that removed platform map sections are not present."""

    def test_ios_netconf_section_not_present(self):
        """ios_netconf section must not exist (NETCONF tier removed)."""
        assert "ios_netconf" not in PLATFORM_MAP

    def test_eos_section_not_present(self):
        """Arista EOS section must not exist in Cisco-only platform map."""
        assert "eos" not in PLATFORM_MAP

    def test_junos_section_not_present(self):
        """JunOS section must not exist in Cisco-only platform map."""
        assert "junos" not in PLATFORM_MAP


# ── get_action() helper ────────────────────────────────────────────────────────

class TestGetAction:
    """Verify get_action() returns ActionChain for restconf devices and plain strings
    for asyncssh devices. VRF resolution must work for both.
    """

    # ── asyncssh (IOL) devices ─────────────────────────────────────────────────

    def test_ios_asyncssh_ospf_no_vrf_returns_plain_string(self):
        """IOS asyncssh OSPF without VRF returns plain string."""
        device = {"cli_style": "ios", "transport": "asyncssh"}
        result = get_action(device, "ospf", "neighbors")
        assert result == "show ip ospf neighbor"

    def test_ios_asyncssh_bgp_with_device_vrf_returns_vrf_string(self):
        """IOS asyncssh BGP with device vrf field resolves to VRF-qualified CLI string."""
        device = {"cli_style": "ios", "transport": "asyncssh", "vrf": "VRF1"}
        result = get_action(device, "bgp", "summary")
        assert isinstance(result, str)
        assert "VRF1" in result
        assert "vrf" in result.lower()

    def test_ios_asyncssh_explicit_vrf_overrides_device_vrf(self):
        """Explicit vrf param must take precedence over device's vrf field."""
        device = {"cli_style": "ios", "transport": "asyncssh", "vrf": "VRF1"}
        result = get_action(device, "bgp", "summary", vrf="VRF2")
        assert "VRF2" in result
        assert "VRF1" not in result

    def test_ios_asyncssh_ping_with_vrf(self):
        """IOS asyncssh ping with VRF must return 'ping vrf VRF1'."""
        device = {"cli_style": "ios", "transport": "asyncssh", "vrf": "VRF1"}
        result = get_action(device, "tools", "ping")
        assert result == "ping vrf VRF1"

    def test_ios_asyncssh_ping_no_vrf(self):
        """IOS asyncssh ping without VRF must return plain 'ping'."""
        device = {"cli_style": "ios", "transport": "asyncssh"}
        result = get_action(device, "tools", "ping")
        assert result == "ping"

    def test_ios_asyncssh_routing_policies_plain_string(self):
        """IOS asyncssh routing_policies must remain plain strings (VRF-agnostic)."""
        device = {"cli_style": "ios", "transport": "asyncssh", "vrf": "VRF1"}
        result = get_action(device, "routing_policies", "redistribution")
        assert isinstance(result, str)
        assert "redistribute" in result

    # ── restconf (c8000v) devices ──────────────────────────────────────────────

    def test_restconf_ospf_returns_action_chain(self):
        """c8000v restconf OSPF must return an ActionChain (2-tier fallback)."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "ospf", "neighbors")
        assert isinstance(result, ActionChain)

    def test_restconf_action_chain_has_two_tiers(self):
        """ActionChain for restconf device must have exactly 2 tiers."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "ospf", "neighbors")
        assert len(result.actions) == 2

    def test_restconf_action_chain_tier_order(self):
        """ActionChain tiers must be ordered: restconf → ssh."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "ospf", "neighbors")
        tiers = [t for t, _ in result.actions]
        assert tiers == ["restconf", "ssh"]

    def test_restconf_tier_is_url_dict(self):
        """ActionChain restconf tier must be a RESTCONF URL dict."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "ospf", "neighbors")
        _, rc_action = result.actions[0]
        assert "url" in rc_action
        assert rc_action["method"] == "GET"

    def test_ssh_tier_is_cli_string(self):
        """ActionChain SSH tier (tier 1) must be a plain CLI string."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "ospf", "neighbors")
        _, ssh_action = result.actions[1]
        assert isinstance(ssh_action, str)
        assert "show" in ssh_action.lower()

    def test_restconf_tools_returns_plain_string_not_action_chain(self):
        """Restconf device tools (ping) must return plain CLI string, not ActionChain."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "tools", "ping")
        assert isinstance(result, str)
        assert not isinstance(result, ActionChain)

    def test_restconf_tools_ping_with_vrf(self):
        """Restconf device ping with VRF must return VRF-qualified string."""
        device = {"cli_style": "ios", "transport": "restconf", "vrf": "VRF1"}
        result = get_action(device, "tools", "ping")
        assert "VRF1" in result

    def test_restconf_bgp_returns_action_chain(self):
        """c8000v restconf BGP must return an ActionChain."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "bgp", "summary")
        assert isinstance(result, ActionChain)

    def test_restconf_interfaces_returns_action_chain(self):
        """c8000v restconf interfaces must return an ActionChain."""
        device = {"cli_style": "ios", "transport": "restconf"}
        result = get_action(device, "interfaces", "interface_status")
        assert isinstance(result, ActionChain)

    # ── edge cases ─────────────────────────────────────────────────────────────

    def test_unknown_cli_style_raises_key_error(self):
        """An unknown cli_style with no PLATFORM_MAP entry must raise KeyError."""
        device = {"cli_style": "unknown_vendor", "transport": "asyncssh"}
        with pytest.raises(KeyError):
            get_action(device, "ospf", "neighbors")
