"""UT-014 — Config push guardrail tests.

Tests for push_config() guardrails in tools/config.py.
No real device connectivity required — transport layer is mocked.

Validates:
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

# Bypass the approval gate for all tests in this file — the gate is tested in test_config_approval_gate.py
_NO_APPROVAL_ERROR = patch("tools.config._check_approval", return_value=None)


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


def run(coro):
    return asyncio.run(coro)


# ── Forbidden command guardrail ───────────────────────────────────────────────

def test_push_config_forbidden_command_returns_error():
    """push_config must return error dict when a command matches the FORBIDDEN set."""
    params = ConfigCommand(devices=["E1C"], commands=["reload"])

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         _NO_APPROVAL_ERROR:
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
    params = ConfigCommand(devices=["E1C"], commands=cmds)

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=("E1C", {"transport_used": "asyncssh", "result": "ok"}))), \
         _NO_APPROVAL_ERROR:
        result = run(push_config(params))

    assert "rollback_advisory" in result, "push_config result must contain rollback_advisory"
    assert isinstance(result["rollback_advisory"], list)
    assert result["rollback_advisory"] == ["no ip ospf hello-interval 10"]


def test_push_config_rollback_inverts_no_commands():
    """rollback_advisory must strip 'no ' prefix to invert 'no ...' commands."""
    cmds = ["no ip ospf hello-interval 10"]
    params = ConfigCommand(devices=["E1C"], commands=cmds)

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=("E1C", {"transport_used": "asyncssh", "result": "ok"}))), \
         _NO_APPROVAL_ERROR:
        result = run(push_config(params))

    assert result["rollback_advisory"] == ["ip ospf hello-interval 10"]


# ── Mixed cli_style guard ─────────────────────────────────────────────────────

def test_push_config_mixed_cli_styles_rejected():
    """push_config must reject device lists that mix different cli_style values."""
    params = ConfigCommand(devices=["E1C", "R1"], commands=["description test"])

    with patch("tools.config.devices", MOCK_DEVICES_MIXED), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         _NO_APPROVAL_ERROR:
        result = run(push_config(params))

    assert "error" in result, "push_config must error on mixed cli_style device list"
    assert "cli_style" in result["error"] or "mixed" in result["error"].lower()
