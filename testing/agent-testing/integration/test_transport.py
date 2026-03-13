"""IT-004 — Transport Layer: integration tests for transport layer (asyncssh, RESTCONF).

These tests require a running lab (`sudo clab redeploy -t AINOC-TOPOLOGY.yml`).
Run with: ./run_tests.sh integration

Each test verifies:
  - The transport can connect to its target device
  - execute_command returns a structured result dict (no "error" key)
  - The result contains either "parsed" or "raw" output

Skip markers prevent CI failures when the lab is not available.
"""
import asyncio
import os
import pytest

# Skip all tests in this module if NO_LAB is set (e.g. in CI without a running lab)
pytestmark = pytest.mark.skipif(
    os.environ.get("NO_LAB", "0") == "1",
    reason="Lab not running — set NO_LAB=0 to enable integration tests",
)


from transport import execute_command


def _run(coro):
    return asyncio.run(coro)


def _assert_ok(result: dict):
    """Assert the result dict is a successful transport response."""
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "error" not in result, f"Transport error: {result.get('error')}"
    assert "parsed" in result or "raw" in result, "Result must have 'parsed' or 'raw'"


# ── asyncssh (Cisco IOS-XE IOL) ───────────────────────────────────────────────

class TestSSHTransport:
    """A1C is a Cisco IOS-XE IOL device via Scrapli asyncssh."""

    def test_ssh_execute_show_version(self):
        result = _run(execute_command("A1C", "show version"))
        _assert_ok(result)
        assert result["cli_style"] == "ios"

    def test_ssh_execute_ospf_neighbors(self):
        result = _run(execute_command("A1C", "show ip ospf neighbor"))
        _assert_ok(result)

    def test_ssh_device_field_in_result(self):
        """Device field must be present in result."""
        result = _run(execute_command("A1C", "show ip route"))
        assert result.get("device") == "A1C"


# ── RESTCONF (Cisco c8000v) ───────────────────────────────────────────────────

class TestRESTCONF:
    """E1C and C1C are Cisco c8000v devices via 2-tier ActionChain (RESTCONF→SSH)."""

    def test_restconf_execute_interfaces_e1c(self):
        """E1C RESTCONF — interfaces via ActionChain."""
        from platforms.platform_map import get_action
        from core.inventory import devices
        device = devices.get("E1C")
        action = get_action(device, "interfaces", "interface_status")
        result = _run(execute_command("E1C", action))
        _assert_ok(result)
        assert result["cli_style"] == "ios"

    def test_restconf_execute_ospf_neighbors_c1c(self):
        """C1C RESTCONF — OSPF neighbors via ActionChain."""
        from platforms.platform_map import get_action
        from core.inventory import devices
        device = devices.get("C1C")
        action = get_action(device, "ospf", "neighbors")
        result = _run(execute_command("C1C", action))
        _assert_ok(result)

    def test_restconf_execute_interfaces_c2c(self):
        """C2C RESTCONF — interfaces via ActionChain."""
        from platforms.platform_map import get_action
        from core.inventory import devices
        device = devices.get("C2C")
        action = get_action(device, "interfaces", "interface_status")
        result = _run(execute_command("C2C", action))
        _assert_ok(result)
        assert result["cli_style"] == "ios"

    def test_restconf_transport_used_field(self):
        """ActionChain result must include _transport_used field."""
        from platforms.platform_map import get_action
        from core.inventory import devices
        device = devices.get("E1C")
        action = get_action(device, "interfaces", "interface_status")
        result = _run(execute_command("E1C", action))
        _assert_ok(result)
        assert "_transport_used" in result, "Expected _transport_used field in ActionChain result"
