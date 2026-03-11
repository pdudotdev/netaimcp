"""
UT-007 — Transport Dispatcher: 2-Tier ActionChain Fallback

Tests that the execute_command() dispatcher correctly handles ActionChain
fallback for restconf transport devices (c8000v).

Validates:
- RESTCONF success → SSH never called
- RESTCONF fail → SSH tried and succeeds
- Both tiers fail → error dict returned
- asyncssh device → plain SSH, no ActionChain
- _transport_used tag set correctly in result
- ActionChain construction via get_action()
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from platforms.platform_map import ActionChain, get_action
from transport import execute_command


# ── Fixtures ──────────────────────────────────────────────────────────────────

RESTCONF_DEVICE = {
    "host": "172.20.20.209",
    "platform": "cisco_iosxe",
    "transport": "restconf",
    "cli_style": "ios",
}

SSH_DEVICE = {
    "host": "172.20.20.205",
    "platform": "cisco_iosxe",
    "transport": "asyncssh",
    "cli_style": "ios",
}

RESTCONF_ACTION = {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data/ospf-state", "method": "GET"}
SSH_ACTION      = "show ip ospf neighbor"

TEST_CHAIN = ActionChain([
    ("restconf", RESTCONF_ACTION),
    ("ssh",      SSH_ACTION),
])

SUCCESS_RC  = {"Cisco-IOS-XE-ospf-oper:ospf-state": {"ospf-instance": []}}
SUCCESS_SSH = ("Neighbor ID  ...", {"parsed": True})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _patch_devices(device_name, device):
    """Patch core.inventory.devices so execute_command can look up the device."""
    return patch("transport.devices", {device_name: device})


def run(coro):
    return asyncio.run(coro)


# ── ActionChain construction ───────────────────────────────────────────────────

def test_action_chain_construction_for_restconf_device():
    """get_action() must return an ActionChain for restconf transport devices."""
    result = get_action(RESTCONF_DEVICE, "ospf", "neighbors")
    assert isinstance(result, ActionChain)


def test_action_chain_has_two_tiers():
    """ActionChain must contain exactly 2 (transport_type, action) pairs."""
    chain = get_action(RESTCONF_DEVICE, "ospf", "neighbors")
    assert len(chain.actions) == 2


def test_action_chain_tier_names_in_order():
    """ActionChain tiers must be ordered: restconf → ssh."""
    chain = get_action(RESTCONF_DEVICE, "ospf", "neighbors")
    tiers = [t for t, _ in chain.actions]
    assert tiers == ["restconf", "ssh"]


def test_action_chain_not_for_asyncssh_device():
    """get_action() must return a plain string (not ActionChain) for asyncssh devices."""
    result = get_action(SSH_DEVICE, "ospf", "neighbors")
    assert isinstance(result, str)
    assert not isinstance(result, ActionChain)


def test_action_chain_not_for_tools_even_on_restconf():
    """get_action() for tools (ping/traceroute) on restconf devices must return plain string."""
    result = get_action(RESTCONF_DEVICE, "tools", "ping")
    assert isinstance(result, str)
    assert not isinstance(result, ActionChain)


# ── Fallback chain execution ───────────────────────────────────────────────────

def test_restconf_success_no_fallback():
    """When RESTCONF succeeds, SSH must never be called."""
    with _patch_devices("E1C", RESTCONF_DEVICE), \
         patch("transport.execute_restconf", new=AsyncMock(return_value=SUCCESS_RC)) as rc_mock, \
         patch("transport.execute_ssh",      new=AsyncMock()) as ssh_mock:

        result = run(execute_command("E1C", TEST_CHAIN))

    rc_mock.assert_called_once()
    ssh_mock.assert_not_called()
    assert result.get("_transport_used") == "restconf"
    assert "error" not in result
    # RESTCONF returns (raw, None) — parsed must not be set in result
    assert "parsed" not in result


def test_restconf_fail_ssh_success():
    """When RESTCONF fails with error, SSH must be tried and succeed."""
    with _patch_devices("E1C", RESTCONF_DEVICE), \
         patch("transport.execute_restconf", new=AsyncMock(return_value={"error": "HTTP 503"})) as rc_mock, \
         patch("transport.execute_ssh",      new=AsyncMock(return_value=SUCCESS_SSH)) as ssh_mock:

        result = run(execute_command("E1C", TEST_CHAIN))

    rc_mock.assert_called_once()
    ssh_mock.assert_called_once()
    assert result.get("_transport_used") == "ssh"
    assert "error" not in result


def test_all_tiers_fail_returns_error():
    """When all tiers fail, execute_command must return a result with an error in raw.

    All mocks return error dicts so the ActionChain loop exhausts all tiers.
    The final raw output must contain an error key, and _transport_used must be absent
    (no tier succeeded, so none can be tagged as the transport used).
    """
    with _patch_devices("E1C", RESTCONF_DEVICE), \
         patch("transport.execute_restconf", new=AsyncMock(return_value={"error": "HTTP 503"})), \
         patch("transport.execute_ssh",      new=AsyncMock(return_value=({"error": "SSH refused"}, None))):

        result = run(execute_command("E1C", TEST_CHAIN))

    assert isinstance(result["raw"], dict), "result['raw'] must be a dict when all tiers fail"
    assert "error" in result["raw"], "result['raw'] must contain an error key when all tiers fail"
    assert "_transport_used" not in result, "_transport_used must not be set when no tier succeeds"


def test_asyncssh_device_uses_ssh_directly():
    """asyncssh devices must call execute_ssh directly without ActionChain iteration."""
    with _patch_devices("A1C", SSH_DEVICE), \
         patch("transport.execute_ssh",      new=AsyncMock(return_value=SUCCESS_SSH)) as ssh_mock, \
         patch("transport.execute_restconf", new=AsyncMock()) as rc_mock:

        result = run(execute_command("A1C", "show ip ospf neighbor"))

    ssh_mock.assert_called_once()
    rc_mock.assert_not_called()
    assert "_transport_used" not in result  # asyncssh doesn't set _transport_used


def test_transport_used_tag_in_result():
    """Result dict must contain _transport_used when ActionChain is resolved."""
    with _patch_devices("E1C", RESTCONF_DEVICE), \
         patch("transport.execute_restconf", new=AsyncMock(return_value=SUCCESS_RC)), \
         patch("transport.execute_ssh",      new=AsyncMock()):

        result = run(execute_command("E1C", TEST_CHAIN))

    assert "_transport_used" in result
    assert result["_transport_used"] in ("restconf", "ssh")


def test_restconf_plain_string_routes_to_ssh():
    """A plain CLI string on a restconf device (ping/traceroute) must route to SSH."""
    with _patch_devices("E1C", RESTCONF_DEVICE), \
         patch("transport.execute_ssh",      new=AsyncMock(return_value=("ping ok", None))) as ssh_mock, \
         patch("transport.execute_restconf", new=AsyncMock()) as rc_mock:

        result = run(execute_command("E1C", "ping 10.0.0.1"))

    ssh_mock.assert_called_once()
    rc_mock.assert_not_called()
