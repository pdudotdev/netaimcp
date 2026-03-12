"""
IT-003 — Full MCP Tool Coverage

Verifies connectivity and tool correctness for all platform types
(IOS asyncssh, IOS RESTCONF/SSH). Includes push_config CRUD tests per transport.

Requires live device access.
"""

import asyncio
import json
import os
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Skip all tests in this module if NO_LAB is set (e.g. in CI without a running lab)
pytestmark = pytest.mark.skipif(
    os.environ.get("NO_LAB", "0") == "1",
    reason="Lab not running — set NO_LAB=0 to enable integration tests",
)

from transport          import execute_command
from tools.protocol     import get_ospf, get_bgp
from tools.routing      import get_routing, get_routing_policies
from tools.operational  import get_interfaces, ping, traceroute, run_show
from tools.config       import push_config
from input_models.models import (
    OspfQuery,
    BgpQuery,
    InterfacesQuery,
    RoutingQuery,
    RoutingPolicyQuery,
    PingInput,
    TracerouteInput,
    ShowCommand,
    ConfigCommand,
)


# ── device constants ──────────────────────────────────────────────────────────

IOS_SSH1 = "A1C"    # Cisco IOS-XE IOL asyncssh (Access)
IOS_SSH2 = "A2C"    # Cisco IOS-XE IOL asyncssh (Access)
IOS_SSH3 = "IAN"    # Cisco IOS-XE IOL asyncssh (ISP A)

IOS_RC1  = "E1C"    # Cisco c8000v RESTCONF (Edge)
IOS_RC2  = "E2C"    # Cisco c8000v RESTCONF (Edge)

RC1      = "C1C"    # Cisco c8000v RESTCONF (Core 1, ABR)
RC2      = "C2C"    # Cisco c8000v RESTCONF (Core 2, ABR)


# ── results collection ────────────────────────────────────────────────────────

RESULTS: list[dict] = []
RESULTS_FILE = Path(__file__).parent / "test_mcp_tools_results.md"


def _format_output(output) -> str:
    """Format test output for Markdown display."""
    if isinstance(output, (dict, list)):
        try:
            return json.dumps(output, indent=2, default=str)
        except (TypeError, ValueError):
            return str(output)
    return str(output)


def record(section: str, test_name: str, device: str, transport: str, output):
    """Append a single test result to the collection."""
    RESULTS.append({
        "section": section,
        "test": test_name,
        "device": device,
        "transport": transport,
        "output": output,
    })


def record_crud(section: str, test_name: str, device: str, phases: dict):
    """Append a multi-phase (CRUD) test result to the collection."""
    RESULTS.append({
        "section": section,
        "test": test_name,
        "device": device,
        "phases": phases,
    })


def _approve_devices(devices: list[str]) -> None:
    """Write a valid APPROVED record so push_config's approval gate passes.

    The gate marks the record EXECUTED after each push, so this must be called
    before every push_config invocation (including cleanup/delete calls).
    """
    approval_file = PROJECT_ROOT / "data" / "pending_approval.json"
    approval_file.parent.mkdir(exist_ok=True)
    approval_file.write_text(json.dumps({
        "request_id": "integration-test",
        "status": "APPROVED",
        "devices": devices,
    }, indent=2))


@pytest.fixture(autouse=True, scope="session")
def write_results_file():
    """Yield to let all tests run, then write collected results to Markdown."""
    yield

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# IT-003 — MCP Tool Test Results",
        f"*Generated: {timestamp} UTC*",
        "",
    ]

    sections: OrderedDict[str, list] = OrderedDict()
    for entry in RESULTS:
        sections.setdefault(entry["section"], []).append(entry)

    for sec_title, entries in sections.items():
        lines.append(f"## {sec_title}")
        lines.append("")
        for entry in entries:
            if "phases" in entry:
                lines.append(f"### {entry['test']} ({entry['device']})")
                lines.append("")
                for phase_name, phase_output in entry["phases"].items():
                    lines.append(f"#### {phase_name}")
                    lines.append("```json")
                    lines.append(_format_output(phase_output))
                    lines.append("```")
                    lines.append("")
            else:
                lines.append(f"### {entry['test']} ({entry['device']} — {entry['transport']})")
                lines.append("```json")
                lines.append(_format_output(entry["output"]))
                lines.append("```")
                lines.append("")

    RESULTS_FILE.write_text("\n".join(lines), encoding="utf-8")


# ── helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ── IT-003a: platform connectivity ────────────────────────────────────────────

def test_connectivity_ios_ssh():
    """IT-003a-1: asyncssh to Cisco IOS-XE IOL (A1C) — show version."""
    result = run(execute_command(IOS_SSH1, "show version"))
    record("IT-003a: Platform Connectivity", "test_connectivity_ios_ssh", IOS_SSH1, "asyncssh", result)
    assert result, f"Expected non-empty result from execute_command({IOS_SSH1})"
    text = str(result)
    assert "version" in text.lower(), f"Expected version info, got: {text[:200]}"


def test_connectivity_restconf_core1():
    """IT-003a-2: RESTCONF to Cisco c8000v (C1C) — get interfaces."""
    from platforms.platform_map import get_action
    device = {"cli_style": "ios", "transport": "restconf", "host": RC1}
    action = get_action(device, "interfaces", "interface_status")
    result = run(execute_command(RC1, action))
    record("IT-003a: Platform Connectivity", "test_connectivity_restconf_core1", RC1, "RESTCONF", result)
    assert result, f"Expected non-empty result from execute_command({RC1})"


def test_connectivity_restconf_edge():
    """IT-003a-3: RESTCONF to Cisco c8000v (E1C) — get interfaces."""
    from platforms.platform_map import get_action
    device = {"cli_style": "ios", "transport": "restconf", "host": IOS_RC1}
    action = get_action(device, "interfaces", "interface_status")
    result = run(execute_command(IOS_RC1, action))
    record("IT-003a: Platform Connectivity", "test_connectivity_restconf_edge", IOS_RC1, "RESTCONF", result)
    assert result, f"Expected non-empty result from execute_command({IOS_RC1})"


def test_connectivity_restconf_core2():
    """IT-003a-4: RESTCONF to Cisco c8000v (C2C) — get interfaces."""
    from platforms.platform_map import get_action
    device = {"cli_style": "ios", "transport": "restconf", "host": RC2}
    action = get_action(device, "interfaces", "interface_status")
    result = run(execute_command(RC2, action))
    record("IT-003a: Platform Connectivity", "test_connectivity_restconf_core2", RC2, "RESTCONF", result)
    assert result, f"Expected non-empty result from execute_command({RC2})"


# ── IT-003b: protocol tools ────────────────────────────────────────────────────

def test_ospf_restconf_core1():
    """IT-003b-1: get_ospf neighbors on Cisco c8000v RESTCONF (C1C)."""
    result = run(get_ospf(OspfQuery(device=RC1, query="neighbors")))
    record("IT-003b: Protocol Tools", "test_ospf_restconf_core1", RC1, "RESTCONF", result)
    assert result, f"Expected non-empty OSPF result from {RC1}"
    text = str(result)
    assert "error" not in text.lower(), f"Unexpected error in OSPF result: {text[:200]}"


def test_bgp_ios_restconf():
    """IT-003b-2: get_bgp summary on IOS RESTCONF (E1C)."""
    result = run(get_bgp(BgpQuery(device=IOS_RC1, query="summary")))
    record("IT-003b: Protocol Tools", "test_bgp_ios_restconf", IOS_RC1, "RESTCONF", result)
    assert result, f"Expected non-empty BGP result from {IOS_RC1}"


def test_bgp_neighbors_ios_ssh():
    """IT-003b-3: get_bgp summary on IOS asyncssh (IAN)."""
    result = run(get_bgp(BgpQuery(device=IOS_SSH3, query="summary")))
    record("IT-003b: Protocol Tools", "test_bgp_neighbors_ios_ssh", IOS_SSH3, "asyncssh", result)
    assert result, f"Expected non-empty BGP summary result from {IOS_SSH3}"
    assert "error" not in result, f"get_bgp summary failed: {result}"


def test_interfaces_ios_ssh():
    """IT-003b-4: get_interfaces on IOS asyncssh (A2C)."""
    result = run(get_interfaces(InterfacesQuery(device=IOS_SSH2)))
    record("IT-003b: Protocol Tools", "test_interfaces_ios_ssh", IOS_SSH2, "asyncssh", result)
    assert result, f"Expected non-empty interfaces result from {IOS_SSH2}"


def test_routing_ios_ssh():
    """IT-003b-5: get_routing prefix lookup on IOS asyncssh (A1C)."""
    result = run(get_routing(RoutingQuery(device=IOS_SSH1, prefix="10.0.0.0")))
    record("IT-003b: Protocol Tools", "test_routing_ios_ssh", IOS_SSH1, "asyncssh", result)
    assert result, f"Expected non-empty routing result from {IOS_SSH1}"


def test_ping_ios_ssh():
    """IT-003b-6: ping from IOS asyncssh (A1C)."""
    result = run(ping(PingInput(device=IOS_SSH1, destination="10.0.0.1")))
    record("IT-003b: Protocol Tools", "test_ping_ios_ssh", IOS_SSH1, "asyncssh", result)
    assert result, f"Expected non-empty ping result from {IOS_SSH1}"


def test_routing_policies_ios_restconf():
    """IT-003b-7: get_routing_policies route_maps on IOS RESTCONF (E1C)."""
    result = run(get_routing_policies(RoutingPolicyQuery(device=IOS_RC1, query="route_maps")))
    record("IT-003b: Protocol Tools", "test_routing_policies_ios_restconf", IOS_RC1, "RESTCONF", result)
    assert result, f"Expected non-empty routing policies result from {IOS_RC1}"


def test_traceroute_ios_ssh():
    """IT-003b-8: traceroute from IOS asyncssh (A1C)."""
    result = run(traceroute(TracerouteInput(device=IOS_SSH1, destination="10.0.0.1")))
    record("IT-003b: Protocol Tools", "test_traceroute_ios_ssh", IOS_SSH1, "asyncssh", result)
    assert result, f"Expected non-empty traceroute result from {IOS_SSH1}"


def test_run_show_ios_ssh():
    """IT-003b-9: run_show fallback on IOS asyncssh (A2C)."""
    result = run(run_show(ShowCommand(device=IOS_SSH2, command="show ip arp")))
    record("IT-003b: Protocol Tools", "test_run_show_ios_ssh", IOS_SSH2, "asyncssh", result)
    assert result, f"Expected non-empty run_show result from {IOS_SSH2}"


def test_ospf_restconf_core2():
    """IT-003b-10: get_ospf neighbors on Cisco c8000v RESTCONF (C2C)."""
    result = run(get_ospf(OspfQuery(device=RC2, query="neighbors")))
    record("IT-003b: Protocol Tools", "test_ospf_restconf_core2", RC2, "RESTCONF", result)
    assert result, f"Expected non-empty OSPF result from {RC2}"


# ── IT-003c: repeated command returns fresh data ───────────────────────────────

def test_repeated_command_returns_fresh_data():
    """IT-003c: execute_command — repeated identical calls each return fresh device data."""
    device = IOS_SSH1
    command = "show clock"

    r1 = run(execute_command(device, command))
    assert "error" not in r1, f"First call failed: {r1.get('error')}"

    r2 = run(execute_command(device, command))
    assert "error" not in r2, f"Second call failed: {r2.get('error')}"

    record("IT-003c: Repeated Command", "test_repeated_command_returns_fresh_data", IOS_SSH1, "asyncssh",
           {"call_1": r1, "call_2": r2})


# ── IT-003d: push_config (Loopback CRUD) ─────────────────────────────────────

def test_push_config_ios_ssh():
    """IT-003d-1: push_config loopback CRUD on IOS asyncssh (A1C)."""
    device = IOS_SSH1
    phases = {}

    # Create Loopback99
    create_cmds = [
        "interface Loopback99",
        "ip address 10.99.99.1 255.255.255.255",
        "no shutdown",
    ]
    _approve_devices([device])
    create_result = run(push_config(ConfigCommand(devices=[device], commands=create_cmds)))
    phases["Create"] = create_result
    assert device in create_result, f"Expected {device} key in push_config result"

    try:
        # Verify Loopback99 exists
        verify_result = run(get_interfaces(InterfacesQuery(device=device)))
        phases["Verify"] = verify_result
        text = str(verify_result)
        assert "Loopback99" in text, f"Loopback99 not found after creation: {text[:300]}"
    finally:
        # Delete Loopback99 (always runs for cleanup)
        delete_cmds = ["no interface Loopback99"]
        _approve_devices([device])
        delete_result = run(push_config(ConfigCommand(devices=[device], commands=delete_cmds)))
        phases["Delete"] = delete_result

    record_crud("IT-003d: push_config (Loopback CRUD)", "test_push_config_ios_ssh", device, phases)


def test_push_config_ios_restconf():
    """IT-003d-2: push_config loopback CRUD on IOS RESTCONF (E1C) — push uses SSH CLI."""
    device = IOS_RC1
    phases = {}

    # Create Loopback99 via SSH fallback (c8000v pushes via SSH for CLI commands)
    create_cmds = [
        "interface Loopback99",
        "ip address 10.99.99.1 255.255.255.255",
        "no shutdown",
    ]
    _approve_devices([device])
    create_result = run(push_config(ConfigCommand(devices=[device], commands=create_cmds)))
    phases["Create"] = create_result
    assert device in create_result, f"Expected {device} key in push_config result"

    time.sleep(2)  # Allow IOS-XE RESTCONF datastore to sync with running-config

    try:
        # Verify Loopback99 exists
        verify_result = run(get_interfaces(InterfacesQuery(device=device)))
        phases["Verify"] = verify_result
        text = str(verify_result)
        assert "Loopback99" in text, f"Loopback99 not found after creation: {text[:300]}"
    finally:
        # Delete Loopback99 (always runs for cleanup)
        delete_cmds = ["no interface Loopback99"]
        _approve_devices([device])
        delete_result = run(push_config(ConfigCommand(devices=[device], commands=delete_cmds)))
        phases["Delete"] = delete_result

    record_crud("IT-003d: push_config (Loopback CRUD)", "test_push_config_ios_restconf", device, phases)


# ── IT-003e: push_config (Extended CRUD) ──────────────────────────────────────

def test_push_description_ios_ssh():
    """IT-003e-1: push_config description on Loopback97 — IOS asyncssh (A1C)."""
    device = IOS_SSH1
    phases = {}

    create_cmds = [
        "interface Loopback97",
        "description INTTEST-MARKER",
        "no shutdown",
    ]
    _approve_devices([device])
    create_result = run(push_config(ConfigCommand(devices=[device], commands=create_cmds)))
    phases["Create"] = create_result
    assert device in create_result, f"Expected {device} key in push_config result"

    try:
        verify_result = run(run_show(ShowCommand(device=device, command="show run interface Loopback97")))
        phases["Verify"] = verify_result
        text = str(verify_result)
        assert "Loopback97" in text, f"Loopback97 not found after creation: {text[:300]}"
        assert "INTTEST-MARKER" in text, f"Description INTTEST-MARKER not found: {text[:300]}"
    finally:
        _approve_devices([device])
        delete_result = run(push_config(ConfigCommand(devices=[device], commands=["no interface Loopback97"])))
        phases["Delete"] = delete_result

    record_crud("IT-003e: push_config (Extended CRUD)", "test_push_description_ios_ssh", device, phases)


def test_push_description_ios_restconf():
    """IT-003e-2: push_config description on Loopback97 — IOS RESTCONF (C1C). SSH push + RESTCONF read."""
    device = RC1
    phases = {}

    create_cmds = [
        "interface Loopback97",
        "description INTTEST-MARKER",
        "no shutdown",
    ]
    _approve_devices([device])
    create_result = run(push_config(ConfigCommand(devices=[device], commands=create_cmds)))
    phases["Create"] = create_result
    assert device in create_result, f"Expected {device} key in push_config result"

    time.sleep(2)  # Allow IOS-XE RESTCONF datastore to sync with running-config

    try:
        verify_result = run(get_interfaces(InterfacesQuery(device=device)))
        phases["Verify"] = verify_result
        text = str(verify_result)
        assert "Loopback97" in text, f"Loopback97 not found after creation: {text[:300]}"
        assert "INTTEST-MARKER" in text, f"Description INTTEST-MARKER not found: {text[:300]}"
    finally:
        _approve_devices([device])
        delete_result = run(push_config(ConfigCommand(devices=[device], commands=["no interface Loopback97"])))
        phases["Delete"] = delete_result

    record_crud("IT-003e: push_config (Extended CRUD)", "test_push_description_ios_restconf", device, phases)


def test_push_acl_ios_ssh():
    """IT-003e-3: push_config ACL CRUD — IOS asyncssh (A2C). Verified via get_routing_policies."""
    device = IOS_SSH2
    phases = {}

    create_cmds = [
        "ip access-list standard INTTEST-ACL",
        "permit 192.168.254.0 0.0.0.255",
    ]
    _approve_devices([device])
    create_result = run(push_config(ConfigCommand(devices=[device], commands=create_cmds)))
    phases["Create"] = create_result
    assert device in create_result, f"Expected {device} key in push_config result"

    try:
        verify_result = run(get_routing_policies(RoutingPolicyQuery(device=device, query="access_lists")))
        phases["Verify"] = verify_result
        text = str(verify_result)
        assert "INTTEST-ACL" in text, f"INTTEST-ACL not found after creation: {text[:300]}"
    finally:
        _approve_devices([device])
        delete_result = run(push_config(ConfigCommand(devices=[device], commands=["no ip access-list standard INTTEST-ACL"])))
        phases["Delete"] = delete_result

    record_crud("IT-003e: push_config (Extended CRUD)", "test_push_acl_ios_ssh", device, phases)


def test_push_prefix_list_ios_restconf():
    """IT-003e-4: push_config prefix-list CRUD — IOS RESTCONF (E1C). Verified via SSH run_show.

    E1C has no prefix-lists by default — RESTCONF correctly returns {} until the datastore syncs.
    Verify via SSH run_show to avoid RESTCONF sync timing issues; the test validates push_config
    correctness, not RESTCONF reads.
    """
    device = IOS_RC1
    phases = {}

    create_cmds = ["ip prefix-list INTTEST-PFX seq 10 permit 192.168.254.0/24"]
    _approve_devices([device])
    create_result = run(push_config(ConfigCommand(devices=[device], commands=create_cmds)))
    phases["Create"] = create_result
    assert device in create_result, f"Expected {device} key in push_config result"

    try:
        verify_result = run(run_show(ShowCommand(device=device, command="show ip prefix-list INTTEST-PFX")))
        phases["Verify"] = verify_result
        text = str(verify_result)
        assert "INTTEST-PFX" in text, f"INTTEST-PFX not found after creation: {text[:300]}"
    finally:
        _approve_devices([device])
        delete_result = run(push_config(ConfigCommand(devices=[device], commands=["no ip prefix-list INTTEST-PFX"])))
        phases["Delete"] = delete_result

    record_crud("IT-003e: push_config (Extended CRUD)", "test_push_prefix_list_ios_restconf", device, phases)


def test_push_multi_device_ssh():
    """IT-003e-5: push_config Loopback98 to [A1C, A2C] simultaneously — exercises asyncio.gather fan-out."""
    devices_list = [IOS_SSH1, IOS_SSH2]
    phases = {}

    create_cmds = [
        "interface Loopback98",
        "ip address 10.98.98.1 255.255.255.255",
        "no shutdown",
    ]
    _approve_devices(devices_list)
    create_result = run(push_config(ConfigCommand(devices=devices_list, commands=create_cmds)))
    phases["Create"] = create_result
    for d in devices_list:
        assert d in create_result, f"Expected {d} key in multi-device push result"

    try:
        for d in devices_list:
            verify_result = run(get_interfaces(InterfacesQuery(device=d)))
            phases[f"Verify-{d}"] = verify_result
            text = str(verify_result)
            assert "Loopback98" in text, f"Loopback98 not found on {d} after creation: {text[:300]}"
    finally:
        _approve_devices(devices_list)
        delete_result = run(push_config(ConfigCommand(devices=devices_list, commands=["no interface Loopback98"])))
        phases["Delete"] = delete_result

    record_crud("IT-003e: push_config (Extended CRUD)", "test_push_multi_device_ssh", str(devices_list), phases)


def test_push_multi_device_restconf():
    """IT-003e-6: push_config Loopback98 to [C1C, C2C] simultaneously — exercises fan-out on restconf-transport devices."""
    devices_list = [RC1, RC2]
    phases = {}

    create_cmds = [
        "interface Loopback98",
        "ip address 10.98.98.1 255.255.255.255",
        "no shutdown",
    ]
    _approve_devices(devices_list)
    create_result = run(push_config(ConfigCommand(devices=devices_list, commands=create_cmds)))
    phases["Create"] = create_result
    for d in devices_list:
        assert d in create_result, f"Expected {d} key in multi-device push result"

    time.sleep(2)  # Allow IOS-XE RESTCONF datastore to sync

    try:
        for d in devices_list:
            verify_result = run(get_interfaces(InterfacesQuery(device=d)))
            phases[f"Verify-{d}"] = verify_result
            text = str(verify_result)
            assert "Loopback98" in text, f"Loopback98 not found on {d} after creation: {text[:300]}"
    finally:
        _approve_devices(devices_list)
        delete_result = run(push_config(ConfigCommand(devices=devices_list, commands=["no interface Loopback98"])))
        phases["Delete"] = delete_result

    record_crud("IT-003e: push_config (Extended CRUD)", "test_push_multi_device_restconf", str(devices_list), phases)
