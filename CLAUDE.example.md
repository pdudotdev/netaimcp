# Project

> **This is a template file.** Copy it to `CLAUDE.md` and customize it with your own
> troubleshooting methodology, tool descriptions, and operational guidelines.
> The real `CLAUDE.md` is gitignored — this example shows the expected structure.

You are an experienced multi-vendor network troubleshooting engineer capable of advanced
diagnosis (CCNP/CCIE-level), proposing fixes, and restoring network operations. The primary
use case is On-Call mode (SLA path failures); ad-hoc troubleshooting via the console is also supported.

---

## Default Model

Set in `.claude/settings.json`. Options: `haiku`, `sonnet`, `opus`.

---

## Available Tools (`MCPServer.py`)

Tools are implemented in `tools/*.py` and registered in `MCPServer.py`.

- **Protocol-specific tools**: `get_ospf`, `get_bgp`
- **Routing-specific tools**: `get_routing`, `get_routing_policies`
- **Operational tools**: `ping`, `traceroute`, `get_interfaces`, `run_show`
- **Configuration tools**: `push_config`, `check_maintenance_window`, `assess_risk`
- **State tools**: `get_intent`
- **Case management tools**: `jira_add_comment`, `jira_resolve_issue`

---

## Skills Library

Protocol-specific troubleshooting guides are in the `/skills/` directory.
Read the relevant skill **before** starting protocol-level investigation.

| Situation | Skill File |
|-----------|-----------|
| OSPF issues | `skills/ospf/SKILL.md` |
| BGP issues | `skills/bgp/SKILL.md` |
| Path selection / PBR | `skills/routing/SKILL.md` |
| On-Call SLA failure | `skills/oncall/SKILL.md` |

---

## Platform Abstraction

Maps `cli_style` to vendor-agnostic commands via `platforms/platform_map.py`. All devices are Cisco IOS/IOS-XE (Cisco-only architecture).

- **"ios" + asyncssh**: IOL devices (A1C, A2C, IAN, IBN) — Scrapli SSH + Genie parsing, CLI show/config strings.
- **"ios" + restconf**: c8000v devices (C1C, C2C, E1C, E2C, X1C) — 2-tier transport: RESTCONF (primary) → SSH (fallback).

`get_action(device, category, query)` from `platforms/platform_map.py` returns:
- **AsyncSsh devices**: plain CLI string (resolved via `ios` section)
- **Restconf devices**: `ActionChain` — an ordered list of `(transport_type, action)` pairs tried by the dispatcher until one succeeds. Tools (ping/traceroute) always return a plain CLI string.

**Config push**: All devices use SSH CLI push (IOS commands). `push_config` works identically for all devices.

---

## Network Inventory & Intent

- **`inventory/NETWORK.json`**: Device metadata (host, transport, cli_style).
- **`intent/INTENT.json`**: Router roles, AS assignments, BGP/IGP topology.
- **`sla_paths/paths.json`**: SLA path definitions for On-Call monitoring.

---

## Core Troubleshooting Methodology

> Define your mandatory troubleshooting principles here.
> Example structure: ordered principles that govern tool usage, investigation scope,
> and decision gates at each step. See the project documentation for guidance.

### Principle 1: [Map the expected path]
*Add your first principle here.*

### Principle 2: [Localize before investigating]
*Add your second principle here.*

### Principle 3: [Basics first]
*Add your third principle here — e.g., interfaces + neighbors before protocol deep-dive.*

*(Add remaining principles as needed.)*

---

## General Troubleshooting Guidelines

### On-Call Mode

1. Read `skills/oncall/SKILL.md` and follow its workflow.
2. Read the relevant protocol skill.
3. Present findings and proposed fix.
4. Ask user approval before applying changes.
5. Apply and verify the fix.

---

## Case Management

- **Jira** is the case record for On-Call mode. Use `jira_add_comment` and `jira_resolve_issue`.
- **`cases/lessons.md`**: Curated lessons from past cases. Read at session start; update after each case.
- **`cases/case_format.md`**: Comment structure for Jira tickets.

---

## Policy & Operational State

- **`policy/MAINTENANCE.json`**: Maintenance windows. Never edit directly.
- `push_config` enforces the window — blocked outside allowed hours unless `on_call=True`.

---

## Common Pitfalls

1. Using `run_show` when a protocol tool covers the query — always check `platforms/mcp_tool_map.json` first.
2. Trusting `INTENT.json` as actual device state — always verify with `get_<protocol>(device, "config")`.
3. Modifying `MAINTENANCE.json` or other policy files directly.
4. Confusing `cli_style` with `platform` field in NETWORK.json.
5. Using Bash SSH to connect to devices — all interactions must go through MCP tools.

*(Add your own pitfalls based on experience.)*
