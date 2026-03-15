# aiNOC Scalability Guide

## Purpose

This document is a reference for architectural bottlenecks to be aware of as the system grows.

---

## Key Concepts

Read this section before moving further.

### `transport` vs `cli_style` are independent axes

`cli_style` drives **command syntax** — which section of `PLATFORM_MAP` to look up (e.g. `"ios"`).
`transport` drives **connection dispatch** — how to physically reach the device (e.g. `"asyncssh"` or `"restconf"`).

A device with `cli_style="ios"` and `transport="restconf"` uses IOS command syntax but is
queried over RESTCONF. They are not coupled.

### ActionChain (2-tier transport)

For `transport="restconf"` devices, `get_action(device, category, query)` returns an
`ActionChain([(restconf, url_dict), (ssh, cli_str)])` rather than a plain CLI string.
The transport dispatcher (`transport/__init__.py`) tries each tier in order and stops
at the first success. `result["_transport_used"]` records which tier won (`"restconf"` or `"ssh"`).

This is what allows c8000v devices to fall back to CLI seamlessly if the RESTCONF API
returns a non-200 status.

### VRF dual-entry format

`PLATFORM_MAP` entries that support VRF use a dict instead of a plain string:

```python
"bgp": {
    "summary": {"default": "show ip bgp summary", "vrf": "show ip bgp vpnv4 vrf {vrf} summary"},
}
```

`_apply_vrf(action, vrf_name)` in `platform_map.py` resolves the dict at lookup time.
Use this format for any query where the VRF changes the command. Plain strings are fine
for commands that are VRF-agnostic.

### `tools` category always returns CLI strings

`ping` and `traceroute` have no RESTCONF equivalent. `get_action()` always returns a plain
CLI string for the `"tools"` category — even for `restconf` devices — and the dispatcher
routes it to SSH. New operational tools without a RESTCONF endpoint should follow this pattern.

### RESTCONF post-processing (trimmer functions)

RESTCONF responses can contain uint32-encoded IP addresses, excess policy noise, and
multi-AF data that the agent doesn't need. Protocol tools include optional trimmer functions
that normalize the output before returning:

- `_trim_ospf(result, query)` — converts uint32 IP fields to dotted-decimal, strips interface noise
- `_trim_bgp(result, query)` — filters to IPv4 unicast, strips policy/path noise

New protocols with RESTCONF support should add a `_trim_<protocol>(result, query)` function
in `tools/protocol.py` following the same pattern.

### Skill file pattern

Each skill has two files:
- `SKILL.example.md` — template showing the expected structure, **checked into git**
- `SKILL.md` — the real network-specific decision tree, **gitignored**

Both files live in `skills/<protocol>/`. Always create both.

---

## Adding a New Protocol

Protocols supported today: OSPF, BGP, routing policies/table.

Candidate protocols: IS-IS, VRRP/HSRP, MSTP/STP, PIM/IGMP, LAG/LACP, VPN (L3VPN).

### Recipe (10 steps, ~2-4 hours)

| Step | File | Action |
|------|------|--------|
| 1 | `platforms/platform_map.py` | Add a new protocol key under `PLATFORM_MAP["ios"]` (CLI strings). If the protocol has a Cisco-IOS-XE YANG model, add it under `PLATFORM_MAP["ios_restconf"]` too (RESTCONF URL dicts). Use the VRF dual-entry format for any query that changes with a VRF. Omit the `ios_restconf` section entirely if no YANG model exists. |
| 2 | `input_models/models.py` | Add a `Literal` type for valid queries (e.g. `VrrpQuery = Literal["neighbors", "config", "detail"]`) and a Pydantic model class inheriting from `BaseParamsModel`. Add `vrf: str \| None = None` and `transport: str \| None = None` optional fields if the protocol supports VRF or transport override. |
| 3 | `tools/protocol.py` | Add a handler following the `get_ospf()` pattern: look up device → `get_action(device, "<protocol>", params.query, vrf=params.vrf)` → `execute_command(device, action)` → optional `_trim_<protocol>(result, query)` → return. If RESTCONF is supported and returns noisy output, add the trimmer function in the same file. |
| 4 | `MCPServer.py` | Register the tool: `mcp.tool(name="get_<protocol>")(get_<protocol>)`. |
| 5 | `platforms/mcp_tool_map.json` | Add a tool entry with `platform_map_section` and `queries` per `cli_style`. This drives the Pitfall #1 lookup that prevents agents from falling back to `run_show`. |
| 6 | `skills/<protocol>/SKILL.example.md` | Create the skill template: PREREQUISITE section (which MCP tools to run first) → Symptom sections (decision trees with exact tool calls) → Fix Guidance. Mirror the structure of `skills/ospf/SKILL.example.md`. |
| 7 | `skills/<protocol>/SKILL.md` | Create the real skill file (gitignored) with topology-specific decision trees and device-specific observations. |
| 8 | `skills/oncall/SKILL.md` | Add a row to the oncall triage table so on-call sessions route to the new skill for the right breaking-hop symptom. |
| 9 | `CLAUDE.md` | Add the tool to the Available Tools list (under the appropriate category bullet). Add a row to the Skills Library table. |
| 10 | Tests | See test checklist below. |

Steps 1–5 are code changes and independently testable. Steps 6–9 are documentation only.

### Protocol Test Checklist

After adding a new protocol, add/update tests in these files:

- **`test_platform_map.py`** — Add assertions within the `TestIOS` and `TestIOSRestconf` classes for each new query entry. Use direct string equality for CLI commands; use dict-key assertions (`assert entry["method"] == "GET"`) for RESTCONF URL dicts. Add `get_action()` tests in `TestGetAction` for both transport types.

- **`test_input_validation.py`** — Add module-level `VALID_<PROTOCOL>_QUERIES` and `INVALID_<PROTOCOL>_QUERIES` lists, then parametrized `test_<protocol>_query_valid(q)` and `test_<protocol>_query_invalid(q)` functions. Include injection-resistance cases (`;`, `\n`, `|`) for any string fields.

- **`run_tests.sh`** — If creating a new test file, register it with the next available UT number in **both** the `unit)` and `all)` case branches.

- **`test_mcp_tools.py`** (integration, lab required) — Add a smoke test that calls the new tool and asserts a non-error response.

### Notes

- Protocols spanning multiple vendors may need different query strings per vendor. The `PLATFORM_MAP` dict handles this — map the same query string to different commands/URLs per `cli_style`.
- If a vendor does not support a protocol, omit that key entirely. `get_ospf()` returns `{"error": "..."}` for unsupported combinations, which is expected behavior.
- Never add `run_show` fallbacks for new protocols. Implement in `platform_map.py` so the tool is vendor-agnostic and the agent uses the correct tool path.

---

## Adding a New Vendor

Core vendor today: Cisco IOS-XE (`ios`) — all 9 lab devices.
Module vendors (available as consultancy/extension builds): Arista EOS (`eos`), Juniper JunOS (`junos`), MikroTik RouterOS (`routeros`), VyOS (`vyos`), Aruba AOS-CX (`aos`), SONiC (`frr`).

### Recipe (~12 files, ~1-2 days)

| Step | File | Action |
|------|------|--------|
| 1 | `transport/<transport>.py` | Implement the transport module. For queries: `execute_<transport>(device: dict, cmd_or_action) → tuple[str, object]` returning `(raw_str, parsed_dict_or_None)`. For config push: `push_<transport>(device: dict, dev_name: str, commands: list[str]) → tuple[str, dict]`. Mirror `transport/ssh.py` structure — include retry logic, error handling, and auth from `core/settings.py`. |
| 2 | `transport/__init__.py` | Add the new `transport` type to the `if/elif` dispatch in `execute_command()`. If the vendor uses a 2-tier model (REST + SSH fallback), add ActionChain handling and register the new tier in `_execute_single()`. If the vendor uses a single transport, just add a direct `execute_<transport>(device, cmd_or_action)` call. |
| 3 | `tools/config.py` | Add a branch in `_push_to_device()` for the new `cli_style` (currently all devices delegate to `push_ssh`). If the new vendor uses SSH CLI push identically to IOS, the existing branch may cover it; add an explicit check to be safe. |
| 4 | `platforms/platform_map.py` | Add `PLATFORM_MAP["<cli_style>"]` with all protocol→query→command mappings (CLI strings). If the vendor uses a secondary REST transport, add `PLATFORM_MAP["<cli_style>_<transport>"]` with REST URL dicts. Use VRF dual-entry format for VRF-capable queries. |
| 5 | `input_models/models.py` | Extend `ShowCommand.must_be_read_only` validator for the new vendor's read-only command format. Currently accepts: CLI string starting with `show `, RESTCONF `{"url": "...", "method": "GET"}`, legacy filter/get JSON. Add an `elif` for any new format (e.g. gNMI path dict, JunOS `show` prefix variant). |
| 6 | `inventory/NETWORK.json` | Add device entries with the correct `cli_style`, `transport`, `platform`, `host`, and `location` fields. |
| 7 | `intent/INTENT.json` | Add device roles, AS assignments, IGP area config, BGP neighbors, direct links. |
| 8 | `vendors/<vendor>_reference.md` | Document: auth method, push command format, platform-specific quirks, forbidden operations, YANG model paths if REST is used. |
| 9 | `platforms/mcp_tool_map.json` | Add `"<cli_style>"` entries to each tool's `queries` object. |
| 10 | `skills/` | Create vendor-specific protocol skill files if the troubleshooting procedure differs from IOS (e.g. different show commands, different state representation). Update the oncall triage table for any new breaking-hop scenarios. |
| 11 | `CLAUDE.md` | Update the Available Tools list if new tools were added. Update the Skills Library table. Add any vendor-specific notes to the platform abstraction section. |
| 12 | Tests | See test checklist below. |

Step 1 (transport module) is the most work. Steps 2-3 are small additions to existing dispatch chains.

### Vendor Test Checklist

After adding a new vendor, add/update tests in these files:

- **`test_platform_map.py`** — Add a `Test<Vendor>` class (mirroring `TestIOS`) with per-query assertions for each protocol. Update `TestRemovedSections` if the vendor was previously excluded. Add `get_action()` tests in `TestGetAction` using a mock device with the new `cli_style` and `transport`.

- **`test_input_validation.py`** — Add `ShowCommand` validation cases for the new vendor's command format. Both valid examples (accepted) and invalid examples (rejected) should be tested.

- **`test_transport_dispatch.py`** — Add dispatch tests for the new transport type: ActionChain routing if 2-tier, direct routing if single-tier. Test error handling and the `_transport_used` field.

- **`test_<transport>_unit.py`** (new file) — Unit tests for the transport module: mock the underlying client (httpx, SSH, gRPC), assert correct request construction, assert error-dict returns on failure. Register with the next available UT number in `run_tests.sh` in both `unit)` and `all)` branches.

- **`test_transport.py`** (integration, lab required) — Add a transport test class for live-device verification.

- Manual verification: `get_ospf(device="<new_device>", query="neighbors")` returns structured output.

---

## Architectural Bottlenecks

These are NOT blocking today. They become relevant when the system grows.

### 1. Transport Dispatch Duplication (LOW — at 6+ core vendors)

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
At 1 core vendor × 2 sections (ios, ios_restconf) × ~4 protocols × ~6 queries each the file is well within readable size.
At 6+ vendors this could exceed maintainable size — per-vendor module split below should be planned.

**Future fix (when needed):** Per-vendor modules:
```
platforms/
    __init__.py      # merges dicts from all vendor modules
    ios.py           # PLATFORM_MAP["ios"] = {...}
    ios_restconf.py  # PLATFORM_MAP["ios_restconf"] = {...}
    eos.py           # PLATFORM_MAP["eos"] = {...}
    junos.py         # PLATFORM_MAP["junos"] = {...}
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
| Protocols per vendor | 4 (OSPF, BGP, routing table, routing policies) | ~10 before bottleneck #2 triggers |
| Unit tests | 556 | Each new protocol adds ~10-20 tests |
| Lines of Python | ~3,000 | Transport registry refactor relevant at 6+ vendors |

**Verdict:** The architecture is well within comfortable scaling bounds at 1 core vendor and 2 transports. Both dispatch bottlenecks are low priority — no refactoring needed until vendor count reaches 6+.
