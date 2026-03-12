"""UT-018 — push_config approval gate tests.

Tests for the code-level approval gate in tools/config.py.
No real device connectivity required — transport layer and approval record are mocked.

Validates:
- push_config blocked when no approval record exists (file absent)
- push_config blocked when approval record has wrong status (REJECTED)
- push_config blocked when approval record has wrong status (EXPIRED)
- push_config blocked when approval record is already EXECUTED (replay prevention)
- push_config blocked when approved devices don't match push devices (exact match required)
- push_config blocked when approved devices are a superset of push devices (strict match)
- push_config succeeds when APPROVED record with exact device match exists
- push_config marks approval record as EXECUTED after successful push
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.config import push_config
from input_models.models import ConfigCommand


# ── Mock data ──────────────────────────────────────────────────────────────────

MOCK_DEVICES = {
    "E1C": {"host": "172.20.20.209", "platform": "cisco_c8000v", "transport": "restconf", "cli_style": "ios"},
    "C1C": {"host": "172.20.20.207", "platform": "cisco_c8000v", "transport": "restconf", "cli_style": "ios"},
}

MOCK_RISK = {"risk": "low", "devices": 1, "reasons": ["Minor configuration change"]}

SAFE_CMD = "ip ospf hello-interval 10"
SAFE_PUSH_RESULT = ("E1C", {"transport_used": "ssh", "result": "ok"})


def run(coro):
    return asyncio.run(coro)


def _approval_record(status: str, devices: list[str]) -> dict:
    return {
        "request_id": "test-uuid",
        "devices": devices,
        "status": status,
        "risk_level": "low",
        "summary": "test fix",
    }


# ── No approval record ─────────────────────────────────────────────────────────

def test_push_blocked_when_no_approval_file(tmp_path):
    """push_config must return error when no approval record file exists."""
    absent = tmp_path / "pending_approval.json"  # does not exist
    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config._APPROVAL_FILE", absent):
        result = run(push_config(params))

    assert "error" in result
    assert "approval" in result["error"].lower() or "request_approval" in result["error"]


# ── Wrong approval status ──────────────────────────────────────────────────────

@pytest.mark.parametrize("bad_status", ["REJECTED", "EXPIRED", "PENDING", "ERROR", "SKIPPED"])
def test_push_blocked_when_status_not_approved(tmp_path, bad_status):
    """push_config must return error when record status is not APPROVED."""
    record = _approval_record(bad_status, ["E1C"])
    approval_file = tmp_path / "pending_approval.json"
    approval_file.write_text(json.dumps(record))

    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config._APPROVAL_FILE", approval_file):
        result = run(push_config(params))

    assert "error" in result
    assert bad_status in result["error"] or "approval" in result["error"].lower()


# ── Replay prevention ──────────────────────────────────────────────────────────

def test_push_blocked_when_record_already_executed(tmp_path):
    """push_config must return error when record is EXECUTED (replay prevention)."""
    record = _approval_record("EXECUTED", ["E1C"])
    approval_file = tmp_path / "pending_approval.json"
    approval_file.write_text(json.dumps(record))

    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config._APPROVAL_FILE", approval_file):
        result = run(push_config(params))

    assert "error" in result
    assert "EXECUTED" in result["error"] or "consumed" in result["error"].lower()


# ── Device mismatch ────────────────────────────────────────────────────────────

def test_push_blocked_when_devices_dont_match(tmp_path):
    """push_config must return error when push devices differ from approved devices."""
    record = _approval_record("APPROVED", ["C1C"])  # approved for C1C
    approval_file = tmp_path / "pending_approval.json"
    approval_file.write_text(json.dumps(record))

    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])  # pushing to E1C

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config._APPROVAL_FILE", approval_file):
        result = run(push_config(params))

    assert "error" in result
    assert "mismatch" in result["error"].lower() or "match" in result["error"].lower()


def test_push_blocked_when_approved_superset_of_requested(tmp_path):
    """push_config must require exact device match — approved superset is not sufficient."""
    record = _approval_record("APPROVED", ["E1C", "C1C"])  # approved for 2 devices
    approval_file = tmp_path / "pending_approval.json"
    approval_file.write_text(json.dumps(record))

    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])  # pushing to only 1

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config._APPROVAL_FILE", approval_file):
        result = run(push_config(params))

    assert "error" in result
    assert "mismatch" in result["error"].lower() or "match" in result["error"].lower()


# ── Successful push with valid approval ────────────────────────────────────────

def test_push_succeeds_with_valid_approval(tmp_path):
    """push_config must succeed when APPROVED record with exact matching device list exists."""
    record = _approval_record("APPROVED", ["E1C"])
    approval_file = tmp_path / "pending_approval.json"
    approval_file.write_text(json.dumps(record))

    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=SAFE_PUSH_RESULT)), \
         patch("tools.config._APPROVAL_FILE", approval_file):
        result = run(push_config(params))

    assert "error" not in result
    assert "rollback_advisory" in result


def test_push_marks_record_executed_after_success(tmp_path):
    """push_config must update the approval record status to EXECUTED after a successful push."""
    record = _approval_record("APPROVED", ["E1C"])
    approval_file = tmp_path / "pending_approval.json"
    approval_file.write_text(json.dumps(record))

    params = ConfigCommand(devices=["E1C"], commands=[SAFE_CMD])

    with patch("tools.config.devices", MOCK_DEVICES), \
         patch("tools.config.assess_risk", new=AsyncMock(return_value=MOCK_RISK)), \
         patch("tools.config.push_ssh", new=AsyncMock(return_value=SAFE_PUSH_RESULT)), \
         patch("tools.config._APPROVAL_FILE", approval_file):
        run(push_config(params))

    updated = json.loads(approval_file.read_text())
    assert updated["status"] == "EXECUTED", "Approval record must be marked EXECUTED after push"
