# aiNOC Scalability Guide

## Purpose

This document is a reference for contributors adding new protocols or vendors.
It describes the exact files to touch, the order to touch them, and architectural
bottlenecks to be aware of as the system grows.

---

## Adding a New Protocol

Protocols supported today: OSPF, EIGRP, BGP, routing policies.

Candidate protocols: VRRP, HSRP, MSTP/STP, PIM/IGMP, LAG/LACP, IS-IS, VPN (L3VPN).

### Recipe (5-7 files, ~2-4 hours)

| Step | File | Action |
|------|------|--------|
| 1 | `platforms/platform_map.py` | Add a new protocol key (`"vrrp"`, `"stp"`, etc.) under each `cli_style` that supports it. Map query strings to CLI commands or REST paths. Leave the key absent (or `{}`) for vendors that don't support the protocol. |
| 2 | `input_models/models.py` | Add a `Literal` type for valid queries (e.g. `VrrpQuery = Literal["neighbors", "config", "detail"]`) and a Pydantic model class inheriting from `BaseParamsModel`. |
| 3 | `tools/protocol.py` | Add a handler function following the `get_ospf()` pattern: look up `PLATFORM_MAP[cli_style][protocol][query]`, call `execute_command()`, return the result. |
| 4 | `MCPServer.py` | Register the tool: `mcp.tool(name="get_vrrp")(get_vrrp)`. |
| 5 | `platforms/mcp_tool_map.json` | Add a tool entry mapping the tool name to its valid queries per `cli_style`. This drives the Pitfall #1 lookup before any `run_show` fallback. |
| 6 | `skills/vrrp/SKILL.md` | Write the troubleshooting skill (symptom-driven, decision tree). |
| 7 | `CLAUDE.md` | Add a row to the Available Tools table and Skills Library table. |

Steps 1-5 are isolated and independently testable. Step 6 (skill) and step 7 (CLAUDE.md) are documentation only.

### Protocol Test Checklist

After adding a new protocol:
- `pytest testing/agent-testing/unit/test_platform_map.py -v` — add query→command assertions for the new protocol.
- `pytest testing/agent-testing/unit/test_input_validation.py -v` — add valid/invalid query parametrize cases.
- `pytest testing/agent-testing/integration/test_mcp_tools.py -v` (lab required) — integration smoke test.

### Notes

- Protocols that span multiple vendors may need different query strings per vendor. The `PLATFORM_MAP` dict handles this — map the same query string to different commands per `cli_style`.
- If a vendor doesn't support a protocol (e.g. RouterOS doesn't have STP), omit that key entirely. `get_ospf()` will return `{"error": "..."}` for unsupported combos, which is the expected behavior.
- Avoid adding `run_show` fallbacks for new protocols — implement in `platform_map.py` so the tool is vendor-agnostic.

---

## Adding a New Vendor

Vendors supported today: Cisco IOS-XE (`ios`), Arista EOS (`eos`), MikroTik RouterOS (`routeros`).

Candidate vendors: Juniper JunOS, Aruba CX, SONiC.

### Recipe (~10 files, ~1-2 days)

| Step | File | Action |
|------|------|--------|
| 1 | `transport/junos.py` (new) | Implement the transport module: `execute_junos(device, cmd_or_action) → (raw, parsed)`. Mirror the structure of `transport/ssh.py` or `transport/eapi.py`. Handle authentication, timeouts, error cases, and `cache_hit`. |
| 2 | `transport/__init__.py` | Add the new `transport` type to the `if/elif` dispatch chain in `execute_command()`. |
| 3 | `tools/config.py` | Add the new `cli_style` to `_push_to_device_safe()`. Map to the correct push mechanism (REST PUT/PATCH, Netconf RPC, CLI commit, etc.). |
| 4 | `platforms/platform_map.py` | Add `"junos": { "ospf": {...}, "bgp": {...}, ... }` with all protocol→query→command mappings. |
| 5 | `input_models/models.py` | Extend `ShowCommand` field_validator: add `cli_style == "junos"` branch with JunOS-appropriate show-command restrictions (e.g. `show` prefix in JunOS CLI, or `GET`-only for REST). |
| 6 | `inventory/NETWORK.json` | Add device entries with `"cli_style": "junos"` and correct `"transport"` type. |
| 7 | `intent/INTENT.json` | Add device roles, AS assignments, and topology information. |
| 8 | `vendors/junos_reference.md` (new) | Document API/CLI behavioral notes — equivalent to `vendors/mikrotik_api_reference.md`. Include: auth method, push command format, quirks, forbidden operations. |
| 9 | `platforms/mcp_tool_map.json` | Add `"junos"` entries for each tool's valid queries. |
| 10 | Tests | Add transport unit tests; add `cli_style="junos"` assertions to `test_platform_map.py`. |

Step 1 (transport module) is the most work. Steps 2-3 are small additions to existing dispatch chains.

### Vendor Test Checklist

After adding a new vendor:
- `pytest testing/agent-testing/unit/test_platform_map.py -v` — add assertions for the new cli_style.
- `pytest testing/agent-testing/unit/test_input_validation.py -v` — add ShowCommand validation cases.
- `pytest testing/agent-testing/integration/test_transport.py -v` (lab required) — add a TestJunOSTransport class.
- Manually verify: `get_ospf(device="<junos_device>", query="neighbors")` returns structured output.

---

## Architectural Bottlenecks

These are NOT blocking today. They become relevant when the system grows.

### 1. Transport Dispatch Duplication (HIGH — at 5+ vendors)

**Current state:** Two if/elif chains keyed on `cli_style`/`transport`:
- `transport/__init__.py` → `execute_command()` dispatch
- `tools/config.py` → `_push_to_device_safe()` dispatch

At 3 vendors these are short and readable. At 5+ vendors, both files must be updated together on every new vendor addition, creating a maintenance burden.

**Future fix (when needed):** Extract a transport registry:
```python
# transport/registry.py
from transport.ssh  import SSHTransport
from transport.eapi import EAPITransport
from transport.rest import RESTTransport

TRANSPORT_REGISTRY: dict[str, type] = {
    "asyncssh": SSHTransport,
    "eapi":     EAPITransport,
    "rest":     RESTTransport,
}
```
Each transport class implements `execute(device, cmd_or_action)` and `push(device, commands)`.
Registration replaces the if/elif chains. New vendor = new entry in `TRANSPORT_REGISTRY`.

### 2. Monolithic PLATFORM_MAP (MEDIUM — at 5+ vendors)

**Current state:** All vendor command mappings live in a single dict in `platforms/platform_map.py`.
At 3 vendors × ~6 protocols × ~6 queries each the file is manageable (~100 lines).
At 5+ vendors this exceeds readable size.

**Future fix (when needed):** Per-vendor modules:
```
platforms/
    __init__.py    # merges dicts from all vendor modules
    ios.py         # PLATFORM_MAP["ios"] = {...}
    eos.py         # PLATFORM_MAP["eos"] = {...}
    routeros.py    # PLATFORM_MAP["routeros"] = {...}
    junos.py       # PLATFORM_MAP["junos"] = {...}
```
No change to consumers — they still `from platforms.platform_map import PLATFORM_MAP`.

### 3. No INTENT.json Schema Validation (MEDIUM)

**Current state:** `INTENT.json` is loaded as a free-form dict. Typos in role names
(`"asbr"` vs `"ASBR"`) silently produce wrong risk assessments and wrong scope lists.

**Future fix (when needed):** Pydantic model for INTENT.json:
```python
class RouterIntent(BaseModel):
    roles: list[Literal["ABR", "ASBR", "IGP_REDISTRIBUTOR", "NAT_EDGE",
                         "ROUTE_REFLECTOR", "EIGRP_LEAF", "EIGRP_HUB"]]
    igp_areas: dict[str, Any] = {}
    bgp: dict[str, Any] = {}
```
Load with `RouterIntent.model_validate(intent_data["routers"][dev])` in `assess_risk()`.
This would catch typos at startup and serve as authoritative documentation of valid roles.

---

## Current Scale Summary

| Dimension | Count | Headroom |
|-----------|-------|----------|
| Vendors | 3 | ~5 before bottleneck #1 triggers |
| Protocols per vendor | 5-6 | ~10 before bottleneck #2 triggers |
| Unit tests | 230 | Each new protocol adds ~10-20 tests |
| Lines of Python | ~2,300 | No refactoring needed until 5+ vendors |

**Verdict:** The architecture scales cleanly for the next 2-3 protocols and 1-2 vendors with zero refactoring. The bottlenecks above are future considerations only.
