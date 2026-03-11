"""Unit tests for assess_risk() — role-based risk, SLA path impact, command keyword escalation.

UT-008 — Risk Assessment
"""
import asyncio
import io
import json
from unittest.mock import patch

import pytest

from input_models.models import RiskInput
from tools.state import assess_risk


# ── Minimal mock data ─────────────────────────────────────────────────────────

MOCK_INTENT = {
    "routers": {
        "R_ABR":  {"roles": ["ABR", "ASBR", "NAT_EDGE"]},   # critical control-plane node
        "R_LEAF": {"roles": ["OSPF_LEAF"]},                   # non-critical leaf
        "R_BARE": {"roles": ["OSPF_LEAF"]},                   # no SLA paths either
    }
}

# R_ABR and R_LEAF each appear in paths; R_BARE appears in none.
# R_ABR: 3 paths (→ high). R_LEAF: 1 path (→ medium). R_BARE: 0 paths.
MOCK_PATHS = {
    "paths": [
        {"id": "P1", "scope_devices": ["R_LEAF_SRC", "R_ABR", "R_DEST"]},
        {"id": "P2", "scope_devices": ["R_LEAF_SRC", "R_ABR", "R_DEST2"]},
        {"id": "P3", "scope_devices": ["R_LEAF_SRC", "R_ABR", "R_DEST3"]},
        {"id": "P4", "scope_devices": ["R_LEAF", "R_DEST"]},
    ]
}


def _run(coro):
    return asyncio.run(coro)


def _open_mock(path, *args, **kwargs):
    """Return in-memory StringIO for INTENT.json or paths.json, error for anything else."""
    p = str(path)
    if "INTENT" in p:
        return io.StringIO(json.dumps(MOCK_INTENT))
    if "paths" in p:
        return io.StringIO(json.dumps(MOCK_PATHS))
    raise FileNotFoundError(path)


def _assess(devices, commands):
    """Helper: run assess_risk with mocked file system."""
    params = RiskInput(devices=devices, commands=commands)
    with patch("builtins.open", side_effect=_open_mock):
        return _run(assess_risk(params))


# ── Role-based risk ───────────────────────────────────────────────────────────

def test_abr_role_triggers_high():
    """A device with ABR/ASBR/NAT_EDGE role must escalate to high regardless of command.
    Critical control-plane devices carry inherent high risk for any change.
    """
    result = _assess(["R_ABR"], ["description WAN-link"])
    assert result["risk"] == "high"
    assert any(
        any(role in r for role in ("ABR", "ASBR", "NAT_EDGE"))
        for r in result["reasons"]
    )


def test_low_role_no_paths_no_keyword_is_low():
    """A non-critical device with no SLA paths and a minor command must stay low risk.
    Establishes the baseline: not everything is high.
    """
    result = _assess(["R_BARE"], ["description WAN-link"])
    assert result["risk"] == "low"


# ── SLA path impact ───────────────────────────────────────────────────────────

def test_three_sla_paths_triggers_high():
    """Three or more affected SLA monitoring paths must escalate risk to high.
    SLA paths represent customer-visible reachability — broad impact = high risk.
    """
    # R_ABR appears in 3 paths; we use non-critical command to isolate the path trigger
    # (R_ABR's role also → high, so test with a path-only device via MOCK_PATHS P1-P3)
    # Use R_LEAF_SRC which appears in P1/P2/P3 but has no INTENT entry → no role escalation
    result = _assess(["R_LEAF_SRC"], ["description test"])
    assert result["risk"] == "high"
    assert any("3" in r or "SLA" in r or "sla" in r.lower() for r in result["reasons"])


def test_one_sla_path_triggers_medium():
    """A single SLA path affected on a non-critical device must escalate to medium.
    Some impact exists, but it is bounded.
    """
    result = _assess(["R_LEAF"], ["description test"])
    assert result["risk"] == "medium"
    assert any("1" in r or "SLA" in r or "sla" in r.lower() for r in result["reasons"])


def test_zero_sla_paths_no_path_escalation():
    """A device with no SLA paths must not gain a medium/high rating from path counting alone."""
    result = _assess(["R_BARE"], ["description test"])
    assert result["risk"] == "low"


# ── Command keyword escalation ────────────────────────────────────────────────

def test_ospf_keyword_triggers_high():
    """Commands containing 'ospf' touch the routing control plane and must escalate to high.
    OSPF misconfiguration can cause network-wide adjacency failures.
    """
    result = _assess(["R_BARE"], ["ip ospf hello-interval 10"])
    assert result["risk"] == "high"
    assert any("control plane" in r.lower() for r in result["reasons"])


def test_bgp_keyword_triggers_high():
    """Commands containing 'bgp' touch the routing control plane and must escalate to high.

    'neighbor' alone does not contain a routing keyword and must stay low.
    'router bgp' contains 'bgp' and 'router ' — both trigger high risk.
    """
    result = _assess(["R_BARE"], ["neighbor 10.0.0.1 remote-as 65001"])
    assert result["risk"] == "low", "bare 'neighbor' command without bgp keyword must be low risk"
    result2 = _assess(["R_BARE"], ["router bgp 65001"])
    assert result2["risk"] == "high"


def test_shutdown_keyword_triggers_high():
    """Commands containing 'shutdown' can disrupt interfaces and must escalate to high.
    Interface disruption affects all protocols and traffic on that link.
    """
    result = _assess(["R_BARE"], ["shutdown"])
    assert result["risk"] == "high"
    assert any("disruption" in r.lower() for r in result["reasons"])


# ── Device count escalation ───────────────────────────────────────────────────

def test_three_devices_triggers_high():
    """Three or more devices in a single change must escalate to high.
    Blast radius grows with device count.
    """
    result = _assess(["R_BARE", "R_BARE", "R_BARE"], ["description test"])
    assert result["risk"] == "high"
    assert any("3" in r for r in result["reasons"])


def test_two_devices_triggers_medium():
    """Two devices in a single change must escalate to at least medium.
    Multiple-device changes increase coordination risk.
    """
    result = _assess(["R_BARE", "R_BARE"], ["description test"])
    assert result["risk"] == "medium", "exactly 2 devices with benign commands must be exactly medium risk"
    assert any("multiple" in r.lower() or "2" in r for r in result["reasons"])


# ── Result structure ──────────────────────────────────────────────────────────

def test_result_has_required_keys():
    """assess_risk must always return a dict with risk, devices, and reasons keys."""
    result = _assess(["R_BARE"], ["description test"])
    assert "risk" in result
    assert "devices" in result
    assert "reasons" in result


def test_risk_value_is_valid_literal():
    """risk field must always be one of 'low', 'medium', or 'high'."""
    result = _assess(["R_BARE"], ["description test"])
    assert result["risk"] in ("low", "medium", "high")


def test_low_risk_returns_default_reason():
    """When no escalation triggers fire, reasons must contain a default fallback message."""
    result = _assess(["R_BARE"], ["description test"])
    assert len(result["reasons"]) >= 1
    # Default message is used when no specific reason was added
    if result["risk"] == "low":
        assert any("minor" in r.lower() for r in result["reasons"])


# ── Command keyword edge cases ─────────────────────────────────────────────────

def test_no_shutdown_excluded_from_high_risk():
    """'no shutdown' must NOT trigger the interface-disruption high risk escalation.

    The disruption check explicitly guards against false-positives from 'no shutdown'
    (which brings interfaces UP, not down). Only bare 'shutdown' must trigger high.
    """
    result_no_shut = _assess(["R_BARE"], ["no shutdown"])
    result_shut    = _assess(["R_BARE"], ["shutdown"])

    assert result_no_shut["risk"] != "high" or not any(
        "disruption" in r.lower() for r in result_no_shut["reasons"]
    ), "'no shutdown' must not trigger interface disruption escalation"
    assert result_shut["risk"] == "high", "bare 'shutdown' must escalate to high risk"


def test_empty_commands_returns_low():
    """assess_risk with an empty command list must default to low risk.

    No keywords can match an empty string, so the result must be the base low risk.
    """
    result = _assess(["R_BARE"], [])
    assert result["risk"] == "low", "empty command list must result in low risk"
