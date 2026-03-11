"""
UT-001 — SLA Pattern Detection

Tests the SLA_DOWN_RE regex from oncall/watcher.py against all expected
log message formats (match) and non-SLA messages (no match).
"""

import sys
from pathlib import Path

import pytest

# Import the regex directly from oncall.watcher without running main()
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from oncall.watcher import SLA_DOWN_RE, SLA_UP_RE


# ── Messages that MUST match ──────────────────────────────────────────────────

SHOULD_MATCH = [
    # Cisco IOS standard
    "%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down",
    # Cisco IOS with BOM prefix
    "BOM%TRACK-6-STATE: 2 ip sla 2 reachability Up -> Down",
    # Cisco IOS — different track/sla numbers
    "%TRACK-3-STATE: 10 ip sla 10 reachability Up -> Down",
    # Cisco alternate phrasing
    "ip sla 1 changed state reachable to down",
    "ip sla 3 transition up to down",
    # Case-insensitive variants
    "%TRACK-6-STATE: 1 ip sla 1 reachability Up -> DOWN",
]

# ── Messages that must NOT match ─────────────────────────────────────────────

SHOULD_NOT_MATCH = [
    # SLA going Up (not Down)
    "%TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up",
    "ip sla 1 changed state down to reachable",
    # Unrelated syslog messages
    "%SYS-5-CONFIG_I: Configured from console",
    "%LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet0/1, changed state to up",
    "BGP neighbor 10.0.0.1 state changed to Established",
    # Empty and whitespace
    "",
    "   ",
]


@pytest.mark.parametrize("msg", SHOULD_MATCH)
def test_matches_sla_down(msg):
    """SLA_DOWN_RE must match all known Cisco IOS/IOS-XE Down event log formats.
    Parametrized across Cisco IOS standard, alternate phrasing, and case variants.
    """
    assert SLA_DOWN_RE.search(msg), f"Expected match for: {msg!r}"


@pytest.mark.parametrize("msg", SHOULD_NOT_MATCH)
def test_no_match_non_sla(msg):
    """SLA_DOWN_RE must not match Up events or unrelated syslog messages.
    A false positive would trigger spurious agent invocations for non-failure events.
    """
    assert not SLA_DOWN_RE.search(msg), f"Expected no match for: {msg!r}"


# ── SLA_UP_RE: Messages that MUST match ───────────────────────────────────────

UP_SHOULD_MATCH = [
    # Cisco IOS standard recovery
    "%TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up",
    # Cisco IOS with BOM prefix
    "BOM%TRACK-6-STATE: 2 ip sla 2 reachability Down -> Up",
    # Cisco IOS — different track/sla numbers
    "%TRACK-3-STATE: 10 ip sla 10 reachability Down -> Up",
    # Cisco alternate phrasing
    "ip sla 1 changed state down to reachable",
    "ip sla 3 transition unreachable to up",
    # Case-insensitive variants
    "%TRACK-6-STATE: 1 ip sla 1 reachability Down -> UP",
]

# ── SLA_UP_RE: Messages that must NOT match ───────────────────────────────────

UP_SHOULD_NOT_MATCH = [
    # SLA going Down (not Up)
    "%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down",
    "ip sla 1 changed state reachable to down",
    # Unrelated syslog messages
    "%SYS-5-CONFIG_I: Configured from console",
    "%LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet0/1, changed state to up",
    "BGP neighbor 10.0.0.1 state changed to Established",
    # Empty and whitespace
    "",
    "   ",
]


@pytest.mark.parametrize("msg", UP_SHOULD_MATCH)
def test_matches_sla_up(msg):
    """SLA_UP_RE must match all known recovery event log formats.
    Recovery detection drives watcher behavior (log without spawning agent).
    """
    assert SLA_UP_RE.search(msg), f"Expected match for: {msg!r}"


@pytest.mark.parametrize("msg", UP_SHOULD_NOT_MATCH)
def test_no_match_non_sla_up(msg):
    """SLA_UP_RE must not match Down events or unrelated messages.
    A false positive would suppress legitimate Down-event agent invocations.
    """
    assert not SLA_UP_RE.search(msg), f"Expected no match for: {msg!r}"
