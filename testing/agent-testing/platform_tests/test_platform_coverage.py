"""
IT-005 — Platform Map Full Coverage

Tests every relevant entry in PLATFORM_MAP against 2 representative devices:
  A1C — Cisco IOS-XE IOL (asyncssh / SSH-only)
  E1C — Cisco c8000v    (restconf / 2-tier: RESTCONF → SSH)

For A1C: all queries run via the normal MCP tool path (SSH).
For E1C: each query is tested 2 times — once per transport tier — using
         the transport override parameter added to all structured query tools.

Result classification:
  PASS  — valid data returned
  EMPTY — transport succeeded but no data (feature not configured on device)
  FAIL  — transport error, device error, or unexpected empty when data was expected

Strong validation: tests distinguish EMPTY from FAIL and enforce that queries
known to have configured data (e.g. OSPF on A1C) return PASS, not EMPTY.

Requires live device access (NO_LAB=0).
"""

import asyncio
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

pytestmark = pytest.mark.skipif(
    os.environ.get("NO_LAB", "0") == "1",
    reason="Lab not running — set NO_LAB=0 to enable integration tests",
)

from platforms.platform_map import PLATFORM_MAP
from tools.protocol import get_ospf, get_bgp
from tools.routing import get_routing, get_routing_policies
from tools.operational import get_interfaces, ping, traceroute
from input_models.models import (
    OspfQuery, BgpQuery, RoutingQuery, RoutingPolicyQuery,
    InterfacesQuery, PingInput, TracerouteInput,
)


# ── inventory (2 representative devices) ──────────────────────────────────────

INVENTORY = {
    "A1C": {"host": "172.20.20.205", "platform": "cisco_iol",    "transport": "asyncssh",
             "cli_style": "ios", "location": "Access"},
    "E1C": {"host": "172.20.20.209", "platform": "cisco_c8000v", "transport": "restconf",
             "cli_style": "ios", "location": "Edge"},
}

DEVICE_LABELS = {
    "A1C": "A1C — Cisco IOS-XE IOL (asyncssh)",
    "E1C": "E1C — Cisco c8000v (RESTCONF/SSH)",
}

DEVICE_ORDER = ["A1C", "E1C"]

# Ping/traceroute destination reachable from all devices via the data plane.
PING_DEST = "10.0.0.33"


# ── expected data map (queries that MUST return real data, not empty) ──────────
#
# Key: (device, category, query)
# If present: test fails on EMPTY (means transport worked but expected data missing).
# If absent: EMPTY is acceptable (feature may not be configured on the device).

MUST_HAVE_DATA = {
    ("A1C", "ospf",          "neighbors"),
    ("A1C", "ospf",          "database"),
    ("A1C", "ospf",          "config"),
    ("A1C", "ospf",          "interfaces"),
    ("A1C", "ospf",          "details"),
    ("A1C", "routing_table", "ip_route"),
    ("A1C", "interfaces",    "interface_status"),
    ("E1C", "ospf",          "neighbors"),
    ("E1C", "ospf",          "database"),
    ("E1C", "ospf",          "config"),
    ("E1C", "ospf",          "interfaces"),
    ("E1C", "ospf",          "details"),
    ("E1C", "bgp",           "summary"),
    ("E1C", "bgp",           "table"),
    ("E1C", "bgp",           "config"),
    ("E1C", "bgp",           "neighbors"),
    ("E1C", "routing_table", "ip_route"),
    ("E1C", "interfaces",    "interface_status"),
}


# ── result classification ─────────────────────────────────────────────────────

EMPTY_DATA_PATTERNS = [
    "no data",
]


def classify_result(result) -> tuple[str, str]:
    """Classify a tool result as PASS, EMPTY, or FAIL.

    PASS  — valid (non-error) data returned.
    EMPTY — transport succeeded but returned no data (feature not configured).
    FAIL  — transport or device error.
    """
    if result is None:
        return "FAIL", "Tool returned None"

    if "error" in result and "raw" not in result:
        err = str(result["error"]).strip()
        if not err:
            return "EMPTY", ""
        return "FAIL", err

    raw = result.get("raw")

    if isinstance(raw, str) and "% Invalid input" in raw:
        return "FAIL", raw.strip()

    # IOS "% <msg>" prefix indicates feature not active / not configured — treat as EMPTY
    # (distinct from "% Invalid input" above which means bad command syntax → FAIL)
    if isinstance(raw, str) and raw.strip().startswith("% "):
        return "EMPTY", ""

    if isinstance(raw, dict) and "error" in raw:
        err = str(raw["error"]).strip()
        if not err:
            return "EMPTY", ""
        for pattern in EMPTY_DATA_PATTERNS:
            if pattern in err:
                return "EMPTY", ""
        return "FAIL", err

    if isinstance(raw, dict) and raw.get("data") is None and "note" in raw:
        return "EMPTY", ""

    if isinstance(raw, dict) and raw:
        non_meta = {k: v for k, v in raw.items()
                    if k not in ("op", "path", "endpoint", "note")}
        if non_meta and all(v is None for v in non_meta.values()):
            return "EMPTY", ""

    return "PASS", ""


def assert_result(device: str, category: str, query: str,
                  status: str, error_msg: str, transport_tier: str):
    """Assert test outcome with strict validation — no silent passes."""
    key = (device, category, query)

    if status == "FAIL":
        pytest.fail(f"[{transport_tier.upper()}] {device} {category}/{query}: {error_msg}")

    if key in MUST_HAVE_DATA and status == "EMPTY":
        pytest.fail(
            f"[{transport_tier.upper()}] {device} {category}/{query}: "
            f"Expected data but got EMPTY — protocol may not be configured or transport returned no data"
        )

    # status == PASS or (status == EMPTY and not in MUST_HAVE_DATA) → acceptable


# ── results collection ────────────────────────────────────────────────────────

RESULTS: list[dict] = []
RESULTS_FILE = Path(__file__).parent / "platform_coverage_results.md"


def truncate_output(output, max_lines: int = 100) -> str:
    if output is None:
        return "(no output)"
    if isinstance(output, (dict, list)):
        try:
            text = json.dumps(output, indent=2, default=str)
        except Exception:
            text = str(output)
    else:
        text = str(output)
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + "\n(truncated)"


def record(device: str, transport: str, category: str, query: str,
           status: str, output, error: str | None, transport_used: str | None = None) -> None:
    RESULTS.append({
        "device":         device,
        "transport":      transport,      # requested tier (or "ssh" for SSH-only tools)
        "transport_used": transport_used, # actual tier from _transport_used field (ActionChain)
        "category":       category,
        "query":          query,
        "status":         status,
        "output":         output,
        "error":          error,
    })


# ── Markdown report writer ────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def write_results_file():
    yield

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Group by (device, transport)
    groups: dict[tuple, list[dict]] = OrderedDict()
    for entry in RESULTS:
        key = (entry["device"], entry["transport"])
        groups.setdefault(key, []).append(entry)

    total_tests = len(RESULTS)
    total_pass  = sum(1 for r in RESULTS if r["status"] == "PASS")
    total_empty = sum(1 for r in RESULTS if r["status"] == "EMPTY")
    total_fail  = sum(1 for r in RESULTS if r["status"] == "FAIL")

    lines = [
        "# Platform Map Coverage Test Results",
        f"*Generated: {timestamp} UTC*",
        "",
        "## Summary",
        "",
        "| Device | Platform | Transport | Tests | Passed | Empty | Failed |",
        "|--------|----------|-----------|-------|--------|-------|--------|",
    ]

    for dev in DEVICE_ORDER:
        label = DEVICE_LABELS[dev]
        platform_part = label.split(" — ", 1)[1]
        for tier in (["ssh"] if dev == "A1C" else ["restconf", "ssh", "tools"]):
            entries = groups.get((dev, tier), [])
            if not entries:
                continue
            n = len(entries)
            p = sum(1 for e in entries if e["status"] == "PASS")
            e = sum(1 for e in entries if e["status"] == "EMPTY")
            f = sum(1 for e in entries if e["status"] == "FAIL")
            lines.append(f"| {dev} | {platform_part} | {tier.upper()} | {n} | {p} | {e} | {f} |")

    lines.append(
        f"| **Total** | | | **{total_tests}** | **{total_pass}** | **{total_empty}** | **{total_fail}** |"
    )
    lines.append("")
    lines.append("## Detailed Results")
    lines.append("")

    for dev in DEVICE_ORDER:
        lines.append(f"### {DEVICE_LABELS[dev]}")
        lines.append("")
        tier_order = ["ssh"] if dev == "A1C" else ["restconf", "ssh", "tools"]
        for tier in tier_order:
            entries = groups.get((dev, tier), [])
            if not entries:
                continue
            lines.append(f"#### Transport: {tier.upper()}")
            lines.append("")
            for i, entry in enumerate(entries, 1):
                status_label = entry["status"]
                transport_note = ""
                if entry["transport_used"] and entry["transport_used"] != tier:
                    transport_note = f" (actual: {entry['transport_used']})"
                lines.append(
                    f"##### {i}. [{tier.upper()}] {entry['category']} — {entry['query']} — {status_label}{transport_note}"
                )
                if entry["error"]:
                    lines.append(f"**Error:** {entry['error']}")
                else:
                    lines.append("**Result:**")
                    lines.append("```")
                    lines.append(truncate_output(entry["output"]))
                    lines.append("```")
                lines.append("")

    RESULTS_FILE.write_text("\n".join(lines), encoding="utf-8")


# ── helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


def _transport_used_from(result) -> str | None:
    if isinstance(result, dict):
        return result.get("_transport_used")
    return None


# ── parametrize data ──────────────────────────────────────────────────────────

# A1C: all categories and queries from PLATFORM_MAP["ios"] (SSH-only device)
# Note: policy_based_routing IS in ios section ("show ip policy") — include it
_IOS_CATEGORIES = ["ospf", "bgp", "routing_table", "routing_policies", "interfaces"]

A1C_CASES = []
for _cat in _IOS_CATEGORIES:
    for _q in PLATFORM_MAP["ios"].get(_cat, {}):
        A1C_CASES.append((_cat, _q))

# E1C: all categories/queries from ios_restconf × 2 transport tiers
# ios_restconf has the authoritative query list for c8000v structured queries
_RESTCONF_CATEGORIES = ["ospf", "bgp", "routing_table", "routing_policies", "interfaces"]
E1C_TRANSPORT_CASES = []
for _cat in _RESTCONF_CATEGORIES:
    for _q in PLATFORM_MAP["ios_restconf"].get(_cat, {}):
        for _tier in ["restconf", "ssh"]:
            E1C_TRANSPORT_CASES.append((_tier, _cat, _q))

# Tool tests (ping + traceroute) — SSH only for both devices
TOOL_CASES = [
    ("A1C", "ping"),
    ("A1C", "traceroute"),
    ("E1C", "ping"),
    ("E1C", "traceroute"),
]


# ── IT-005a: A1C — SSH queries ────────────────────────────────────────────────

@pytest.mark.parametrize("category,query", A1C_CASES)
def test_a1c_ssh(category, query):
    """Test all PLATFORM_MAP queries on A1C via SSH (the only transport for IOL devices)."""
    result = error_msg = None
    status = "FAIL"
    try:
        if category == "ospf":
            result = run(get_ospf(OspfQuery(device="A1C", query=query)))
        elif category == "bgp":
            result = run(get_bgp(BgpQuery(device="A1C", query=query)))
        elif category == "routing_table":
            result = run(get_routing(RoutingQuery(device="A1C")))
        elif category == "routing_policies":
            result = run(get_routing_policies(RoutingPolicyQuery(device="A1C", query=query)))
        elif category == "interfaces":
            result = run(get_interfaces(InterfacesQuery(device="A1C")))

        status, err = classify_result(result)
        if err:
            error_msg = err
        assert_result("A1C", category, query, status, error_msg or "", "ssh")
    except (AssertionError, pytest.fail.Exception):
        status = "FAIL"
        raise
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)
        pytest.fail(f"[SSH] A1C {category}/{query}: {e}")
    finally:
        tu = _transport_used_from(result)
        record("A1C", "ssh", category, query, status, result, error_msg, tu)


# ── IT-005b: E1C — per-transport-tier queries ─────────────────────────────────

@pytest.mark.parametrize("transport_tier,category,query", E1C_TRANSPORT_CASES)
def test_e1c_transport(transport_tier, category, query):
    """Test all PLATFORM_MAP queries on E1C, one tier at a time, using transport override."""
    result = error_msg = None
    status = "FAIL"
    try:
        if category == "ospf":
            result = run(get_ospf(OspfQuery(device="E1C", query=query, transport=transport_tier)))
        elif category == "bgp":
            result = run(get_bgp(BgpQuery(device="E1C", query=query, transport=transport_tier)))
        elif category == "routing_table":
            result = run(get_routing(RoutingQuery(device="E1C", transport=transport_tier)))
        elif category == "routing_policies":
            result = run(get_routing_policies(
                RoutingPolicyQuery(device="E1C", query=query, transport=transport_tier)))
        elif category == "interfaces":
            result = run(get_interfaces(InterfacesQuery(device="E1C", transport=transport_tier)))

        status, err = classify_result(result)
        if err:
            error_msg = err
        assert_result("E1C", category, query, status, error_msg or "", transport_tier)
    except (AssertionError, pytest.fail.Exception):
        status = "FAIL"
        raise
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)
        pytest.fail(f"[{transport_tier.upper()}] E1C {category}/{query}: {e}")
    finally:
        tu = _transport_used_from(result)
        record("E1C", transport_tier, category, query, status, result, error_msg, tu)


# ── IT-005c: ping + traceroute ────────────────────────────────────────────────

@pytest.mark.parametrize("device,tool_name", TOOL_CASES)
def test_tools(device, tool_name):
    """Test ping and traceroute on both devices (always SSH)."""
    result = error_msg = None
    status = "FAIL"
    try:
        if tool_name == "ping":
            result = run(ping(PingInput(device=device, destination=PING_DEST)))
        else:
            result = run(traceroute(TracerouteInput(device=device, destination=PING_DEST)))

        status, err = classify_result(result)
        if err:
            error_msg = err

        if status == "FAIL":
            pytest.fail(f"[SSH] {device} {tool_name}: {error_msg}")
        # ping/traceroute must return data (can't be EMPTY — response is always a string)
        if status == "EMPTY":
            pytest.fail(f"[SSH] {device} {tool_name}: returned empty (expected CLI output)")

    except (AssertionError, pytest.fail.Exception):
        status = "FAIL"
        raise
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)
        pytest.fail(f"[SSH] {device} {tool_name}: {e}")
    finally:
        record(device, "tools", "tools", tool_name, status, result, error_msg)
