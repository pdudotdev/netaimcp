"""Unit tests for check_maintenance_window() and push_config maintenance gate."""
import asyncio
from datetime import datetime, time as dt_time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz

from input_models.models import EmptyInput, ConfigCommand
from tools.state import check_maintenance_window


# UTC timezone used in MAINTENANCE.json
_UTC = pytz.utc

# A weekday (Wednesday) inside the 05:00–20:00 window
_INSIDE_WINDOW  = datetime(2026, 3, 4, 12, 0, 0, tzinfo=_UTC)   # Wed 12:00 UTC
_OUTSIDE_BEFORE = datetime(2026, 3, 4,  3, 0, 0, tzinfo=_UTC)   # Wed 03:00 UTC (before 05:00)
_OUTSIDE_AFTER  = datetime(2026, 3, 4, 21, 0, 0, tzinfo=_UTC)   # Wed 21:00 UTC (after 20:00)
_WEEKEND        = datetime(2026, 3, 7, 12, 0, 0, tzinfo=_UTC)   # Sat 12:00 UTC


def _run(coro):
    return asyncio.run(coro)


# ── check_maintenance_window ───────────────────────────────────────────────────

def test_inside_window_allowed():
    """A weekday timestamp within 05:00-20:00 UTC must return allowed=True.
    Configuration pushes during the window must proceed without blocking.
    """
    with patch("tools.state.datetime") as mock_dt:
        mock_dt.now.return_value = _INSIDE_WINDOW
        result = _run(check_maintenance_window(EmptyInput()))
    assert result["allowed"] is True
    assert "Within maintenance window" in result["reason"]


def test_outside_window_before_start_blocked():
    """A weekday timestamp before 05:00 UTC must return allowed=False.
    Early-morning changes outside the window must be blocked by push_config.
    """
    with patch("tools.state.datetime") as mock_dt:
        mock_dt.now.return_value = _OUTSIDE_BEFORE
        result = _run(check_maintenance_window(EmptyInput()))
    assert result["allowed"] is False
    assert "Outside maintenance window" in result["reason"]


def test_outside_window_after_end_blocked():
    """A weekday timestamp after 20:00 UTC must return allowed=False.
    Late-evening changes outside the window must be blocked by push_config.
    """
    with patch("tools.state.datetime") as mock_dt:
        mock_dt.now.return_value = _OUTSIDE_AFTER
        result = _run(check_maintenance_window(EmptyInput()))
    assert result["allowed"] is False


def test_weekend_blocked():
    """A Saturday or Sunday timestamp must return allowed=False regardless of time.
    Weekend changes are outside the Mon-Fri maintenance policy.
    """
    with patch("tools.state.datetime") as mock_dt:
        mock_dt.now.return_value = _WEEKEND
        result = _run(check_maintenance_window(EmptyInput()))
    assert result["allowed"] is False


# ── push_config maintenance gate ───────────────────────────────────────────────

def test_push_config_blocked_outside_window():
    """push_config must return an error dict when the maintenance window is closed.
    The gate must be enforced inside push_config, not just by the caller.
    """
    from tools.config import push_config

    blocked_mw = {
        "allowed": False,
        "current_time": "2026-03-07T12:00:00+00:00",
        "reason": "Outside maintenance window",
    }

    params = ConfigCommand(
        devices=["E1C"],
        commands=["ip ospf hello-interval 10"],
    )

    with patch("tools.config.check_maintenance_window", new=AsyncMock(return_value=blocked_mw)):
        result = _run(push_config(params))

    assert "error" in result
    assert "maintenance window" in result["error"].lower()


def test_push_config_proceeds_inside_window():
    """push_config must attempt device calls when the maintenance window is open.
    Confirms the gate allows changes through — not just blocks them.
    """
    from tools.config import push_config

    open_mw = {"allowed": True, "reason": "Within maintenance window"}
    mock_push_result = ("E1C", {"output": "ok"})

    params = ConfigCommand(
        devices=["E1C"],
        commands=["ip ospf hello-interval 10"],
    )

    with patch("tools.config.check_maintenance_window", new=AsyncMock(return_value=open_mw)), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value={"risk": "low", "devices": 1, "reasons": []})), \
         patch("tools.config._push_to_device_safe", new=AsyncMock(return_value=mock_push_result)):
        result = _run(push_config(params))

    assert "error" not in result
    assert result.get("E1C") == {"output": "ok"}


def test_push_config_on_call_bypasses_maintenance_window():
    """push_config must skip the maintenance window check when on_call=True.
    On-Call fixes must be applicable at any time — the window blocks scheduled changes only.
    """
    from tools.config import push_config

    blocked_mw = {
        "allowed": False,
        "current_time": "2026-03-07T12:00:00+00:00",
        "reason": "Outside maintenance window",
    }
    mock_push_result = ("E1C", {"output": "ok"})

    params = ConfigCommand(
        devices=["E1C"],
        commands=["ip ospf hello-interval 10"],
        on_call=True,
    )

    with patch("tools.config.check_maintenance_window", new=AsyncMock(return_value=blocked_mw)), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value={"risk": "low", "devices": 1, "reasons": []})), \
         patch("tools.config._push_to_device_safe", new=AsyncMock(return_value=mock_push_result)):
        result = _run(push_config(params))

    assert "error" not in result
    assert result.get("E1C") == {"output": "ok"}
