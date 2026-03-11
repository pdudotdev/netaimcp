"""UT-014 — Config push guardrail tests.

Tests for push_config() guardrails in tools/config.py.
No real device connectivity required — transport layer is mocked.

Validates:
- push_config blocked outside maintenance window (on_call=False)
- push_config with on_call=True skips the maintenance window check entirely
- Forbidden commands are rejected and return an error dict
- rollback_advisory is present in every successful push result
- Mixed cli_style device list is rejected
- validate_commands raises ValueError for each FORBIDDEN substring
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.config import push_config, validate_commands, FORBIDDEN
from input_models.models import ConfigCommand


# ── Mock data ─────────────────────────────────────────────────────────────────

MOCK_DEVICES = {
    "E1C": {"host": "172.20.20.209", "platform": "cisco_c8000v", "transport": "restconf", "cli_style": "ios"},
    "E2C": {"host": "172.20.20.210", "platform": "cisco_c8000v", "transport": "restconf", "cli_style": "ios"},
}

MOCK_DEVICES_MIXED = {
    "E1C": {"host": "172.20.20.209", "platform": "cisco_c8000v", "transport": "restconf", "cli_style": "ios"},
    "R1":  {"host": "172.20.20.100", "platform": "arista_ceos",  "transport": "asyncssh", "cli_style": "eos"},
}

MOCK_RISK = {"risk": "low", "devices": 1, "reasons": ["Minor configuration change"]}

MW_BLOCKED  = {"allowed": False, "current_time": "2026-03-10T02:00:00+00:00", "reason": "Outside maintenance window"}
MW_ALLOWED  = {"allowed": True,  "current_time": "2026-03-10T10:00:00+00:00", "reason": "Within maintenance window"}


def run(coro):
    return asyncio.run(coro)


# ── Maintenance window guardrail ───────────────────────────────────────────────

def test_push_config_outside_window_blocked():
    """push_config without on_call=True must return error when outside maintenance window."""
    params = ConfigCommand(devices=["E1C"], commands=["description test-link"])
    with patch("tools.config.check_maintenance_window", new=AsyncMock(return_value=MW_BLOCKED)):
        result = run(push_config(params))

    assert "error" in result, "push_config must return error dict when blocked by maintenance window"
    assert "maintenance window" in result["error"].lower()


def test_push_config_on_call_bypasses_window_check():
    """push_config with on_call=True must never call check_maintenance_window."""
    params = ConfigCommand(devices=["E1C"], commands=["description test-link"], on_call=True)
    mw_mock = AsyncMock(return_value=MW_BLOCKED)

    with patch("tools.config.check_maintenance_window", mw_mock), \
         patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=("E1C", {"transport_used": "asyncssh", "result": "ok"}))):
        run(push_config(params))

    mw_mock.assert_not_called(), "check_maintenance_window must not be called when on_call=True"


# ── Forbidden command guardrail ───────────────────────────────────────────────

def test_push_config_forbidden_command_returns_error():
    """push_config must return error dict when a command matches the FORBIDDEN set."""
    params = ConfigCommand(devices=["E1C"], commands=["reload"], on_call=True)

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)):
        result = run(push_config(params))

    assert "error" in result, "push_config must return error when forbidden command is present"
    assert "forbidden" in result["error"].lower() or "Forbidden" in result["error"]


@pytest.mark.parametrize("bad_cmd", list(FORBIDDEN))
def test_validate_commands_rejects_each_forbidden(bad_cmd):
    """validate_commands must raise ValueError for each substring in the FORBIDDEN set."""
    with pytest.raises(ValueError, match="Forbidden"):
        validate_commands([bad_cmd])


# ── Rollback advisory ─────────────────────────────────────────────────────────

def test_push_config_rollback_advisory_present():
    """push_config must include rollback_advisory in the result for every successful push."""
    cmds = ["ip ospf hello-interval 10"]
    params = ConfigCommand(devices=["E1C"], commands=cmds, on_call=True)

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=("E1C", {"transport_used": "asyncssh", "result": "ok"}))):
        result = run(push_config(params))

    assert "rollback_advisory" in result, "push_config result must contain rollback_advisory"
    assert isinstance(result["rollback_advisory"], list)
    assert result["rollback_advisory"] == ["no ip ospf hello-interval 10"]


def test_push_config_rollback_inverts_no_commands():
    """rollback_advisory must strip 'no ' prefix to invert 'no ...' commands."""
    cmds = ["no ip ospf hello-interval 10"]
    params = ConfigCommand(devices=["E1C"], commands=cmds, on_call=True)

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=("E1C", {"transport_used": "asyncssh", "result": "ok"}))):
        result = run(push_config(params))

    assert result["rollback_advisory"] == ["ip ospf hello-interval 10"]


# ── Mixed cli_style guard ─────────────────────────────────────────────────────

def test_push_config_mixed_cli_styles_rejected():
    """push_config must reject device lists that mix different cli_style values."""
    params = ConfigCommand(devices=["E1C", "R1"], commands=["description test"], on_call=True)

    with patch("tools.config.devices", MOCK_DEVICES_MIXED), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)):
        result = run(push_config(params))

    assert "error" in result, "push_config must error on mixed cli_style device list"
    assert "cli_style" in result["error"] or "mixed" in result["error"].lower()
