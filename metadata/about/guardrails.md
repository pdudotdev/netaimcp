# 🛡️ System Safeguards & Operational Controls

A structured overview of the architectural protections that prevent unsafe automation, duplicate execution, hallucinations, runaway costs, and policy drift.

---

# 🤖 Agent Autonomy Approval

## ✅ Explicit No-Auto-Push Rule
- "Always ask the user whether to proceed before calling `push_config`"
- Mandatory rule (stated twice in `CLAUDE.md`)
- No configuration changes without explicit user approval

## ✅ Permission-Based Tool System
- User can deny any tool call:
  - Edit
  - Bash
  - `push_config`
- Agent must handle denial gracefully
- Skips blocked step without failure or escalation

## ✅ Maintenance Window Enforcement
- `push_config` checks `MAINTENANCE.json`
- Blocks out-of-window changes automatically
- File is read-only (agent cannot bypass or modify)

---

# ⚡ Agent Storms & Duplicate Invocations

## ✅ Lock File Mechanism (`oncall.lock`)
- Single-instance guard
- Prevents multiple agents from running simultaneously

## ✅ PID Liveness Check (`is_lock_stale()`)
- Detects dead processes
- Cleans stale locks automatically
- Prevents deadlocks

## ✅ Deferred Events Handling (`pending_events.json`)
- Events arriving during an active session:
  - Captured
  - Deferred for later review
- Not lost
- Not re-triggered mid-session

## ✅ Drain Mechanism (`drain[0]` flag)
- After session ends:
  - Watcher seeks to EOF
  - Skips buffered events
- Prevents re-processing the same failure N times

---

# 🔁 Command Repetition & Redundant Investigation

## ✅ Core Troubleshooting Methodology (6 Principles)

Ordered, deterministic workflow that prevents repetition:

### P1 — Map Expected Path
- Read `INTENT.json`
- Define investigation scope upfront

### P2 — Single Localization Step
- One traceroute only
- Prevents N traceroutes

### P3 — Mandatory Basics-First Gate
- `get_interfaces`
- `get_neighbors`
- Must pass before deeper tools

### P4 — Never Chase Downstream
- Missing route?
- Check source’s neighbors only

### P5 — One Device at a Time
- Fully resolve before moving on

### P6 — Simple Before Complex
- Ordered 10-item checklist
- Stop at first mismatch

---

## ✅ Decision Gates in Principle 3

- Interfaces down → STOP
- Neighbors missing → Go directly to Adjacency Checklist
- Skip:
  - LSDB analysis
  - Redistribution checks
  - Policy inspection

Prevents premature deep-dives.

---

# 🧠 Hallucinations & Off-Scope Investigation

## ✅ Explicit `scope_devices` List (`sla_paths/paths.json`)
- Each SLA path defines exact investigation boundary
- Pitfall #8 warns against touching out-of-scope devices

## ✅ `INTENT.json` Context Requirement
- Principle 1 mandates reading intent first
- Prevents:
  - Inventing device roles
  - Making up areas
  - Fabricating topology

## ✅ Skill Prerequisites
- Each protocol skill requires basics-first gate
- PREREQUISITE note blocks skipping steps

## ✅ Pitfall #10
- "Do not skip adjacency check before protocol skill deep-dive"
- Prevents premature LSDB reading

---

# 💰 Increased Costs & Tool Misuse

## ✅ MCP Tool Map (`platforms/mcp_tool_map.json`)
- Maps every tool to supported queries
- Pitfall #1 mandates checking this before using `run_show`
- Forces:
  - Cheaper
  - Targeted
  - Structured tools first

## ✅ No Task Subagents for MCP Calls
- Pitfall #6 forbids using subagents for network operations
- Subagents do not inherit MCP connection
- Forces direct main-session calls
- Faster and cheaper

## ✅ No Bash SSH to Devices
- Pitfall #5 forbids bypassing MCP abstraction layer
- Prevents uncontrolled SSH storms

---

# 📝 Case Documentation & Lesson Integrity

## ✅ Mandatory Case Documentation
- Every On-Call case documented as a Jira ticket comment (see `cases/case_format.md` for structure)
- `cases/cases.md` was replaced by Jira Service Management (removed in v4.0)
- Prevents duplicate documentation
- Enables lesson mining via `cases/lessons.md`

## ✅ Lessons Curation (`cases/lessons.md`)
- Pre-curated top 10 lessons
- Must be read at session start
- Agent must decide:
  - Add new lesson?
  - Promote over older one?
- Prevents invented lessons

## ✅ Case Format Structure (`cases/case_format.md`)
- Standardized schema
- Enforces consistent documentation
- Prevents ad-hoc notes

## ✅ Task Tracking for Documentation
- Documentation marked as final task
- Case cannot close without it

---

# 🔐 Policy Integrity

## ✅ Read-Only Policy Files
The following cannot be modified by the agent:

- `MAINTENANCE.json`
- `inventory/NETWORK.json`
- `intent/INTENT.json`

Prevents:
- Accidental drift
- Intentional policy modification

## ✅ External Vector Configuration
- Log pipeline (`/etc/vector/vector.yaml`)
- Managed outside the agent
- Cannot be corrupted or modified

---

# 📟 On-Call Mode Isolation

## ✅ Focus Enforcement
- "You will NOT be invoked or deviated from the current case"
- Prevents multitasking
- Prevents context loss

## ✅ Deferred Review Workflow
- Events during active session:
  - Become separate session
- Prevents abandoning deferred failures

---

# ⚙️ Command Caching (MCP Server)

## ✅ 5-Second Command-Level Cache
- Keyed by: `(device, command)`
- Prevents re-querying identical command within 5 seconds
- Reduces repetition and costs

## ✅ Cache Hit Skips Device Connection
- Identical device + command within 5 seconds:
  - Returns cached result
  - No device connection made
- `run_show` excluded (TTL = 0)

---

# 🔒 v4.0 Security Controls

## ✅ `run_show` Read-Only Enforcement (Pitfall #13)
- `ShowCommand` Pydantic model validates at MCP boundary
- CLI commands: must start with `show ` (case-insensitive)
- RouterOS actions: must use `method: GET`
- Any other input raises `ValidationError` before execution
- Prevents config bypass via `run_show`

## ✅ RouterOS REST Validation
- Forbidden REST paths blocked before any HTTP call
- POST method rejected (not supported on RouterOS 7.x)
- Config changes must use `push_config` with PUT / PATCH / DELETE

## ✅ Syslog Prompt Injection Mitigation
- Syslog messages sanitized before injection into agent prompt
- Delimiter markers isolate log content from instructions
- Prevents malicious log entries from hijacking agent behavior

## ✅ Expanded Forbidden Command Set
- Grown from 5 → 14 blocked patterns in `tools/config.py`
- Covers: reload, erase, write erase, format, delete, and others
- Applied before any `push_config` execution

## ✅ TLS/SSL Configuration (Env-Var Only, Pitfall #12)
- Controlled by: `VERIFY_TLS`, `ROUTEROS_USE_HTTPS`, `SSH_STRICT_HOST_KEY`
- Read once at import time — not runtime-configurable
- Agent cannot toggle or bypass TLS settings mid-session

## ✅ Pre-Change Snapshots (`push_config`)
- `snapshot_state` captures device state before applying changes
- Enables manual before/after diff review
- Rollback advisory generated for every config change

---

# 📊 Risk Assessment (`assess_risk`)

`assess_risk` assigns a **low / medium / high** risk level before any config push. Risk only escalates — it never de-escalates within a single assessment.

**Escalation rules (applied in order, highest wins):**

| Dimension | Condition | Risk |
|-----------|-----------|------|
| Device count | ≥ 3 devices | high |
| Device count | > 1 device | medium |
| Device role | Device has role ABR, ASBR, IGP_REDISTRIBUTOR, NAT_EDGE, or ROUTE_REFLECTOR (from `intent/INTENT.json`) | high |
| SLA path impact | ≥ 3 SLA paths in `scope_devices` include a target device | high |
| SLA path impact | 1–2 SLA paths affected | medium (upgrades from low only) |
| Command content | Commands contain: `router`, `ospf`, `bgp`, `isis`, or `eigrp` | high |
| Command content | Commands contain: `shutdown` or `no shutdown` | high |

`assess_risk` is advisory only — it does not block changes. The user decides whether to proceed regardless of risk level.

---

# 📸 Snapshot Profiles (`snapshot_state`)

`snapshot_state` accepts a `profile` parameter that selects which commands to run per device platform.

**Valid profiles:** `ospf` | `stp` | `eigrp` | `bgp`

| Profile | IOS commands captured | EOS commands captured | RouterOS commands captured |
|---------|----------------------|----------------------|--------------------------|
| `ospf` | running-config, OSPF config, OSPF neighbors | running-config, OSPF config, OSPF neighbors | IP addresses, OSPF instances, OSPF neighbors |
| `stp` | running-config, STP general, STP per-VLAN detail | running-config, STP general | *(not supported — no STP in RouterOS)* |
| `eigrp` | running-config, EIGRP neighbors, EIGRP topology | *(not supported — no EIGRP on EOS)* | *(not supported — no EIGRP on RouterOS)* |
| `bgp` | running-config, BGP summary, BGP table | running-config, BGP summary, BGP table | BGP connections, BGP sessions |

`push_config` with `snapshot_before=True` auto-selects the profile from the commands being pushed: `eigrp` if any command contains "eigrp", `bgp` if any contains "bgp", otherwise `ospf`.

Snapshots are written to the `snapshots/` directory (gitignored). Invalid profiles are rejected at the MCP boundary (`profile` is a validated enum).