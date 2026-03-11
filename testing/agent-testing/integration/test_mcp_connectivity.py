"""
IT-001 — MCP Tool Connectivity

Verifies that the MCP server tools can reach real devices and return
meaningful data across all transport types. No configuration changes are made.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Skip all tests in this module if NO_LAB is set (e.g. in CI without a running lab)
pytestmark = pytest.mark.skipif(
    os.environ.get("NO_LAB", "0") == "1",
    reason="Lab not running — set NO_LAB=0 to enable integration tests",
)

from tools.operational import get_interfaces, ping
from tools.protocol    import get_ospf
from input_models.models import InterfacesQuery, OspfQuery, PingInput


# ── helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_get_interfaces_a1c():
    """IT-001a: A1C (IOS asyncssh) interfaces should be non-empty and include Ethernet0."""
    result = run(get_interfaces(InterfacesQuery(device="A1C")))
    assert result, "Expected non-empty result from get_interfaces(A1C)"
    text = str(result)
    assert "Ethernet0" in text or "eth" in text.lower(), (
        f"Expected interface data in result, got: {text[:200]}"
    )


def test_get_ospf_neighbors_c2c():
    """IT-001b: C2C (Cisco c8000v RESTCONF) should have valid OSPF neighbor data."""
    result = run(get_ospf(OspfQuery(device="C2C", query="neighbors")))
    assert result, "Expected non-empty OSPF neighbor result from C2C"
    text = str(result)
    assert "error" not in text.lower(), f"Unexpected error in OSPF neighbors: {text[:200]}"


def test_ping_a1c_to_loopback():
    """IT-001c: Ping from A1C to its own loopback should succeed."""
    result = run(ping(PingInput(device="A1C", destination="10.1.1.1")))
    assert result, "Expected non-empty ping result"
    text = str(result)
    assert "success" in text.lower() or "!" in text or "bytes" in text.lower(), (
        f"Ping appears to have failed: {text[:200]}"
    )
