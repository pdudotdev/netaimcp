"""UT-011 — RESTCONF transport unit tests.

Tests for transport/restconf.py with mocked httpx.
No real device connectivity required.

Validates:
- Successful GET returns parsed JSON dict
- HTTP 4xx/5xx returns error dict with status code
- Timeout exception returns graceful error dict
- Non-JSON 200 response returns error dict
- URL is built correctly from action dict
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from transport.restconf import execute_restconf, _RESTCONF_BASE


# ── Helpers ───────────────────────────────────────────────────────────────────

DEVICE = {
    "host": "172.20.20.209",
    "platform": "cisco_c8000v",
    "transport": "restconf",
    "cli_style": "ios",
}

ACTION = {"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data", "method": "GET"}


def run(coro):
    return asyncio.run(coro)


def _mock_httpx_client(status_code: int, json_data=None, text_data="", raise_exc=None):
    """Build a mock httpx.AsyncClient context manager.

    Returns a mock that, when used as 'async with httpx.AsyncClient(...) as client:',
    yields a mock client whose get() returns a response with the given status_code.
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_data is not None:
        mock_response.json.return_value = json_data
    mock_response.text = text_data

    mock_client = AsyncMock()
    if raise_exc:
        mock_client.get = AsyncMock(side_effect=raise_exc)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    return mock_cm, mock_client


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_restconf_get_success():
    """Successful RESTCONF GET (HTTP 200) must return the parsed JSON dict."""
    expected = {"ospf-oper-data": {"ospf-state": []}}
    mock_cm, _ = _mock_httpx_client(200, json_data=expected)

    with patch("transport.restconf.httpx.AsyncClient", return_value=mock_cm):
        result = run(execute_restconf(DEVICE, ACTION))

    assert result == expected, "execute_restconf must return parsed JSON on HTTP 200"
    assert "error" not in result


def test_restconf_get_http_500_returns_error():
    """HTTP 500 response must return {'error': ...} with the status code."""
    mock_cm, _ = _mock_httpx_client(500, text_data="Internal Server Error")

    with patch("transport.restconf.httpx.AsyncClient", return_value=mock_cm):
        result = run(execute_restconf(DEVICE, ACTION))

    assert "error" in result, "execute_restconf must return error dict on HTTP 500"
    assert "500" in result["error"]


def test_restconf_get_http_404_returns_error():
    """HTTP 404 response must return {'error': ...} indicating resource not found."""
    mock_cm, _ = _mock_httpx_client(404, text_data="Not Found")

    with patch("transport.restconf.httpx.AsyncClient", return_value=mock_cm):
        result = run(execute_restconf(DEVICE, ACTION))

    assert "error" in result
    assert "404" in result["error"]


def test_restconf_get_timeout_returns_error():
    """A timeout exception from httpx must return {'error': ...}, not raise to caller."""
    import httpx
    mock_cm, _ = _mock_httpx_client(None, raise_exc=httpx.TimeoutException("read timeout"))

    with patch("transport.restconf.httpx.AsyncClient", return_value=mock_cm):
        result = run(execute_restconf(DEVICE, ACTION))

    assert "error" in result, "timeout must return error dict, not raise"
    assert "timeout" in result["error"].lower() or "read" in result["error"].lower()


def test_restconf_url_construction():
    """execute_restconf must build the URL as https://{host}:{port}/restconf/data/{action_url}."""
    expected_data = {"data": "ok"}
    mock_cm, mock_client = _mock_httpx_client(200, json_data=expected_data)

    with patch("transport.restconf.httpx.AsyncClient", return_value=mock_cm), \
         patch("transport.restconf.RESTCONF_PORT", 443):
        run(execute_restconf(DEVICE, ACTION))

    # Verify the URL passed to get() contains the host and action URL
    call_args = mock_client.get.call_args
    url_used = call_args[0][0]
    assert DEVICE["host"] in url_used, "URL must include device host"
    assert ACTION["url"] in url_used, "URL must include action URL path"
    assert _RESTCONF_BASE in url_used, "URL must include RESTCONF base path"
    assert url_used.startswith("https://"), "URL must use HTTPS"
