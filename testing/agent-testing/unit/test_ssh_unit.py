"""UT-013 — SSH transport unit tests.

Tests for transport/ssh.py with mocked Scrapli.
No real device connectivity required.

Validates:
- Successful show command returns (raw_output, parsed_output) tuple
- Connection refused raises after exhausting retries
- Genie parse failure falls back to None parsed_output (raw text still returned)
- push_ssh success returns (dev_name, result_dict)
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from transport.ssh import execute_ssh, push_ssh


# ── Fixtures ──────────────────────────────────────────────────────────────────

DEVICE = {
    "host": "172.20.20.205",
    "platform": "cisco_iol",
    "transport": "asyncssh",
    "cli_style": "ios",
}

RAW_OUTPUT = "Neighbor ID     Pri   State     Dead Time   Address    Interface\n10.0.0.1       1    FULL/DR    00:00:32  10.1.1.2  Gi1"


def run(coro):
    return asyncio.run(coro)


def _mock_scrapli(raw: str, genie_result=None, genie_raises=False):
    """Build a mock AsyncScrapli context manager.

    raw: text to return from response.result
    genie_result: dict to return from genie_parse_output() (or None)
    genie_raises: if True, genie_parse_output() raises Exception
    """
    mock_response = MagicMock()
    mock_response.result = raw
    if genie_raises:
        mock_response.genie_parse_output.side_effect = Exception("No parser for command")
    else:
        mock_response.genie_parse_output.return_value = genie_result

    mock_conn = AsyncMock()
    mock_conn.send_command = AsyncMock(return_value=mock_response)
    mock_conn.send_configs = AsyncMock(return_value=MagicMock(result=""))

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    return mock_cm, mock_conn


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_ssh_show_command_success():
    """Successful show command must return (raw_output, parsed_output) with raw text."""
    genie_data = {"ospf": {"neighbors": {"10.0.0.1": {"state": "FULL"}}}}
    mock_cm, _ = _mock_scrapli(RAW_OUTPUT, genie_result=genie_data)

    with patch("transport.ssh.AsyncScrapli", return_value=mock_cm):
        raw, parsed = run(execute_ssh(DEVICE, "show ip ospf neighbor"))

    assert raw == RAW_OUTPUT, "raw output must match Scrapli response.result"
    assert parsed == genie_data, "parsed output must match genie_parse_output() return value"


def test_ssh_connection_refused_raises():
    """When Scrapli raises on all retry attempts, execute_ssh must propagate the exception."""
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    # Patch SSH_RETRIES to 0 so there's no delay in the test
    with patch("transport.ssh.AsyncScrapli", return_value=mock_cm), \
         patch("transport.ssh.SSH_RETRIES", 0):
        with pytest.raises(ConnectionRefusedError):
            run(execute_ssh(DEVICE, "show ip ospf neighbor"))


def test_ssh_genie_parse_failure_returns_none_parsed():
    """When Genie parse raises, execute_ssh must still return raw text with parsed=None."""
    mock_cm, _ = _mock_scrapli(RAW_OUTPUT, genie_raises=True)

    with patch("transport.ssh.AsyncScrapli", return_value=mock_cm):
        raw, parsed = run(execute_ssh(DEVICE, "show ip ospf neighbor"))

    assert raw == RAW_OUTPUT, "raw output must be returned even when Genie parse fails"
    assert parsed is None, "parsed must be None when Genie parse fails"


def test_push_ssh_success_returns_dev_name_and_result():
    """push_ssh must return (dev_name, result_dict) on success."""
    mock_cm, mock_conn = _mock_scrapli(RAW_OUTPUT)
    mock_conn.send_configs = AsyncMock(return_value=MagicMock(result="configured"))

    with patch("transport.ssh.AsyncScrapli", return_value=mock_cm):
        dev_name, result = run(push_ssh(DEVICE, "E1C", ["ip ospf hello-interval 10"]))

    assert dev_name == "E1C", "push_ssh must return the device name as first element"
    assert isinstance(result, dict), "push_ssh must return a result dict as second element"
    assert "transport_used" in result
    assert result["transport_used"] == "asyncssh"
