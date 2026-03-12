# 📁 Project File & Directory Reference

A structured overview of the key files, services, and directories that power the troubleshooting environment.

---

## ✅ `lessons.md`

**Purpose:** Institutional memory file.

A curated list (maximum 10 entries) of lessons learned from past troubleshooting cases:

- Common gotchas  
- Recurring patterns  
- “We see this one a lot” issues  

After every On-Call session, the agent:
1. Reads this file  
2. Decides whether to add a new lesson  
3. Or replace an older one with something more broadly useful  

> Think of it as the team’s cheat sheet for avoiding the same mistake twice.

---

## ✅ `intent.json`

**Purpose:** Source of truth for network design.

Defines the big-picture architecture:

- Area Border Routers (ABRs)
- OSPF / BGP speakers
- Autonomous Systems
- OSPF areas  
- Peering relationships  
- NAT design expectations  

When troubleshooting, this is your starting point.  
It helps answer: *“Is this device supposed to be doing X?”*

---

## ✅ `network.json`  
*(inventory/NETWORK.json)*

**Purpose:** Device roster and connection metadata.

Stores management details for every device:

- SSH / API host  
- CLI style (Cisco IOS — all devices)
- Transport method (asyncssh for IOL, restconf for c8000v)
- Physical location  

When you want to talk to a device, this file tells the tools **how to connect**.

---

## ✅ `platform_map.py`

**Purpose:** Vendor command abstraction layer.

Acts as the translator between human intent and vendor-specific commands.

Example:
```
get_ospf(device="A1C", query="neighbors")
```

This file converts that generic call into:
- A plain Cisco IOS CLI string (asyncssh devices: A1C, A2C, IAN, IBN)
- Or an `ActionChain` (2-tier: RESTCONF → SSH) for c8000v devices

It lets you forget about transport differences within the same vendor.

---

## ✅ `mcp_tool_map.json`

**Purpose:** MCP tool capability reference.

Maps which MCP tool handles which command.

Instead of guessing whether to use `run_show`:
- Check if `get_ospf`, `get_routing`, or another specialized tool exists.

Important behavior:
- If a tool returns empty → the feature is not configured.
- It does **not** mean the query is unsupported.

Prevents unnecessary fallback commands.

**Tool parameter reference:**
- Input parameters for every MCP tool are defined as Pydantic models in `input_models/models.py`.
- Each model field includes a `description=` annotation — these are the authoritative parameter docs.
- Valid `query` values per tool per vendor are mapped in `mcp_tool_map.json`.
- Risk scoring rules are documented in `metadata/about/guardrails.md`.

---

## ✅ `skills/` (folder)

**Purpose:** Troubleshooting playbooks.

Each file contains a symptom-first decision tree for:

- OSPF
- BGP
- Routing policy
- On-Call mode

Written in plain language with:
- Checklists  
- Tables  
- Investigation flows  

Use after ruling out basic interface/neighbor issues.  
These guide deeper inspection (LSDB, route-maps, policies, etc.).

---

## ✅ `paths.json`  
*(located in `sla_paths/`)*

**Purpose:** IP SLA monitoring definitions.

Defines:

- Source IP  
- Destination IP  
- Expected device path  

When an SLA path fails:
1. `oncall/watcher.py` looks up details here
2. Determines what should be reachable  
3. Hands off investigation to you  

---

## ✅ `CLAUDE.md`

**Purpose:** The project bible.

Contains:

- 6-principle troubleshooting methodology
- On-Call workflow (primary mode)
- Complete MCP tool list (15 tools)
- Lessons curation process
- Case management workflow
- 17 common pitfalls to avoid

Everything the agent needs to operate lives here.

---

## ✅ `core/jira_client.py`

**Purpose:** Jira Service Management integration.

An async REST client that:

- Logs findings  
- Posts resolution comments  
- Updates Jira tickets  

It bridges troubleshooting sessions with the ticketing system.

---

## ✅ `MCPServer.py`

**Purpose:** FastMCP tool server entry point (~60 lines).

Imports and registers all tools from the decomposed module structure:

```
MCPServer.py          — tool registration and mcp.run()
transport/
    __init__.py       — transport dispatcher (execute_command)
    ssh.py            — Scrapli SSH (Cisco IOS-XE asyncssh: A1C, A2C, IAN, IBN)
    restconf.py       — httpx RESTCONF (Cisco c8000v primary transport)
tools/
    protocol.py       — get_ospf, get_bgp
    routing.py        — get_routing, get_routing_policies
    operational.py    — get_interfaces, ping, traceroute, run_show
    config.py         — push_config, validate_commands, FORBIDDEN, approval gate
    state.py          — get_intent, assess_risk
    jira_tools.py     — jira_add_comment, jira_resolve_issue
    approval.py       — request_approval, post_approval_outcome (MCP tools)
core/inventory.py         — device inventory loader (NETWORK.json)
core/settings.py          — credentials and transport configuration
core/logging_config.py    — JSONFormatter, ainoc.* logger hierarchy
core/jira_client.py       — async Jira REST v3 client
core/discord_approval.py  — Discord API: post_approval_request, poll_for_reaction, post_outcome, post_investigation_started, post_deferred_list
input_models/models.py — all Pydantic input models
```

Workflow:
1. Receives tool call
2. Uses `platform_map.py` for vendor translation
3. Executes command via transport layer
4. Parses output
5. Returns structured data

---

## ✅ `oncall/watcher.py`

**Purpose:** Automated SLA monitoring sentry.

Monitors Syslog for SLA failure alerts.

When triggered:
1. Creates a Jira ticket  
2. Injects issue key into Claude prompt  
3. Starts troubleshooting session  

Acts as the handoff from passive monitoring to active investigation.

---

## ✅ `logs/oncall_watcher.log` (gitignored)

**Purpose:** Watcher activity log.

Records:

- SLA failures detected
- Jira tickets created
- Sessions started

Useful for:
- Debugging watcher issues
- Reviewing historical alert patterns

---

## ✅ `logs/session-oncall-<timestamp>.md` (gitignored)

**Purpose:** Per-session agent output log.

Each On-Call session's full CLI output is streamed here via `tmux pipe-pane`. Captures everything the agent printed — investigation steps, tool results, findings table, summary.

Use for post-incident review when you weren't watching live:
```
tmux attach -t oncall-<timestamp>    # live observation (if session still open)
cat logs/session-oncall-<timestamp>.md   # post-incident review
```