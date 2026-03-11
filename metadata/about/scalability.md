# aiNOC Scalability Guide

## Purpose

This document is a reference for contributors adding new protocols or vendors.
It describes the exact files to touch, the order to touch them, and architectural
bottlenecks to be aware of as the system grows.

---

## Adding a New Protocol

Protocols supported today: OSPF, BGP, routing policies.

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

Core vendor today: Cisco IOS-XE (`ios`) — all 9 lab devices. Module vendors (available as consultancy/extension builds): Arista EOS (`eos`), Juniper JunOS (`junos`), MikroTik RouterOS (`routeros`), VyOS (`vyos`), Aruba AOS-CX (`aos`).

Candidate vendors for future core expansion: SONiC.

### Recipe (~10 files, ~1-2 days)

| Step | File | Action |
|------|------|--------|
| 1 | `transport/<vendor>.py` (new) | Implement the transport module: `execute_<vendor>(device, cmd_or_action) → (raw, parsed)`. Mirror the structure of `transport/ssh.py`. Handle authentication, timeouts, and error cases. |
| 2 | `transport/__init__.py` | Add the new `transport` type to the `if/elif` dispatch chain in `execute_command()`. |
| 3 | `tools/config.py` | Add the new `cli_style` to `_push_to_device()`. Map to the correct push mechanism (REST PUT/PATCH, CLI commit, etc.). |
| 4 | `platforms/platform_map.py` | Add `"<cli_style>": { "ospf": {...}, "bgp": {...}, ... }` with all protocol→query→command mappings. |
| 5 | `input_models/models.py` | Extend `ShowCommand` field_validator: add appropriate show-command restrictions for the new vendor (e.g. `show ` prefix for IOS-style CLI, or `GET`-only for REST). |
| 6 | `inventory/NETWORK.json` | Add device entries with `"cli_style": "<vendor>"` and correct `"transport"` type. |
| 7 | `intent/INTENT.json` | Add device roles, AS assignments, and topology information. |
| 8 | `vendors/<vendor>_reference.md` (new) | Document API/CLI behavioral notes. Include: auth method, push command format, quirks, forbidden operations. |
| 9 | `platforms/mcp_tool_map.json` | Add `"<cli_style>"` entries for each tool's valid queries. |
| 10 | Tests | Add transport unit tests; add `cli_style="<vendor>"` assertions to `test_platform_map.py`. |

Step 1 (transport module) is the most work. Steps 2-3 are small additions to existing dispatch chains.

### Vendor Test Checklist

After adding a new vendor:
- `pytest testing/agent-testing/unit/test_platform_map.py -v` — add assertions for the new cli_style.
- `pytest testing/agent-testing/unit/test_input_validation.py -v` — add ShowCommand validation cases.
- `pytest testing/agent-testing/integration/test_transport.py -v` (lab required) — add a transport test class.
- Manually verify: `get_ospf(device="<new_device>", query="neighbors")` returns structured output.

---

## Architectural Bottlenecks

These are NOT blocking today. They become relevant when the system grows.

### 1. Transport Dispatch Duplication (LOW — at 3 core vendors)

**Current state:** Two if/elif chains keyed on `cli_style`/`transport`:
- `transport/__init__.py` → `execute_command()` dispatch (asyncssh / restconf + ActionChain)
- `tools/config.py` → `_push_to_device()` dispatch

At 1 core vendor (2 transports: asyncssh + restconf/ssh ActionChain) these are lean and manageable. At 6+ vendors, both files would need updating together on every addition, creating a maintenance burden.

**Future fix (when needed):** Extract a transport registry:
```python
# transport/registry.py
from transport.ssh      import SSHTransport
from transport.restconf import RESTCONFTransport

TRANSPORT_REGISTRY: dict[str, type] = {
    "asyncssh": SSHTransport,
    "restconf": RESTCONFTransport,
}
```
Each transport class implements `execute(device, cmd_or_action)` and `push(device, commands)`.
Registration replaces the if/elif chains. New vendor = new entry in `TRANSPORT_REGISTRY`.

### 2. Monolithic PLATFORM_MAP (LOW — at 3 core vendors)

**Current state:** All command mappings live in a single dict in `platforms/platform_map.py`.
At 1 core vendor × 2 sections (ios, ios_restconf) × ~5 protocols × ~6 queries each the file is well within readable size.
At 6+ vendors this could exceed maintainable size — per-vendor module split below should be planned.

**Future fix (when needed):** Per-vendor modules:
```
platforms/
    __init__.py    # merges dicts from all vendor modules
    ios.py         # PLATFORM_MAP["ios"] = {...}
    ios_restconf.py # PLATFORM_MAP["ios_restconf"] = {...}
    eos.py         # PLATFORM_MAP["eos"] = {...}
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
                         "ROUTE_REFLECTOR", "OSPF_AREA0_CORE",
                         "OSPF_AREA1_LEAF", "ISP_A_EDGE", "ISP_B_EDGE"]]
    igp_areas: dict[str, Any] = {}
    bgp: dict[str, Any] = {}
```
Load with `RouterIntent.model_validate(intent_data["routers"][dev])` in `assess_risk()`.
This would catch typos at startup and serve as authoritative documentation of valid roles.

---

## Current Scale Summary

| Dimension | Count | Headroom |
|-----------|-------|----------|
| Core vendors | 1 (Cisco) | ~6+ before bottleneck #1 becomes relevant |
| Transports | 2 (restconf, asyncssh) — 2-tier ActionChain for c8000v | Well under threshold |
| Protocols per vendor | 4-5 | ~10 before bottleneck #2 triggers |
| Unit tests | 307 | Each new protocol adds ~10-20 tests |
| Lines of Python | ~3,500 | Transport registry refactor relevant at 6+ vendors |

**Verdict:** The architecture is well within comfortable scaling bounds at 1 core vendor and 2 transports. Both dispatch bottlenecks are low priority — no refactoring needed until vendor count reaches 6+.
