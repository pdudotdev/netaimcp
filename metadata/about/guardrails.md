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

# 🔒 v5.0 Security Controls

## ✅ Credential & Destructive Command Protection (Permission Deny Rules)
- `.env` files blocked from `Read` and `Bash(cat)` — prevents credential exposure (router creds, Jira token)
- `Bash(ssh *)` denied — enforces Pitfall #5 at permission level, not just prompt level
- `Bash(rm -rf *)` denied — prevents catastrophic file deletion
- `git push --force` and `git reset --hard` denied — prevents irreversible git operations
- Defined in `.claude/settings.local.json` deny list

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

# 🔒 Security Controls

## ✅ `run_show` Read-Only Enforcement (Pitfall #13)
- `ShowCommand` Pydantic model validates at MCP boundary
- CLI commands (IOS): must start with `show ` (case-insensitive)
- RESTCONF JSON actions: must have `url` key with `method=GET` only
- Any other input raises `ValidationError` before execution
- Prevents config bypass via `run_show`

## ✅ Syslog Prompt Injection Mitigation (Strengthened in v5.0)
- Syslog messages sanitized via character allowlist (alphanumeric + safe network punctuation only) — all other characters replaced with spaces
- Applied to all event fields before injection into the agent prompt and before writing to deferred/pending event files
- Delimiter markers isolate log content from instructions
- **Known residual risk**: No sanitizer can fully prevent LLM prompt injection from adversarial ASCII text; this is a defense-in-depth measure

## ✅ Expanded Forbidden Command Set (Updated in v5.0)
- 23 blocked patterns in `tools/config.py`
- Covers: reload, erase, write erase, format, delete, copy run, write mem, configure replace, username manipulation, enable secret/password, snmp-server community, crypto key ops, transport input none, and others
- Applied before any `push_config` execution
- **Known residual risk**: IOS abbreviations (e.g. `wr er` instead of `write erase`) bypass substring matching; a full IOS parser would be required to close this gap completely

## ✅ Input Parameter Validation (v5.0)
- `ping`/`traceroute` `destination`: validated with `ipaddress.ip_address()` — rejects CLI injection via append (e.g. `"8.8.8.8 repeat 999999"`)
- `ping`/`traceroute` `source`: validated as IP address or interface name regex — rejects arbitrary string injection
- `get_bgp` `neighbor`: validated with `ipaddress.ip_address()` — rejects `"1.2.3.4 | include password"` style injection
- `get_routing` `prefix`: validated as IPv4 address or CIDR regex
- All `vrf` fields: validated as alphanumeric + underscore/dash, max 32 chars — rejects newline injection in VRF substitution
- Jira `issue_key`: validated as `^[A-Z][A-Z0-9]+-\d+$` — prevents URL path traversal in Jira REST calls
- Implemented in `input_models/models.py` at the Pydantic model layer

## ✅ Maintenance Window Fail-Closed (v5.0)
- If `MAINTENANCE.json` is missing or deleted, `check_maintenance_window` returns `allowed: False`
- Previously failed open (allowed all changes when policy file was absent)
- Implemented in `tools/state.py`

## ✅ TLS/SSL Configuration (Env-Var Only, Pitfall #12)
- Controlled by: `RESTCONF_VERIFY_TLS`, `SSH_STRICT_HOST_KEY`
- Read once at import time — not runtime-configurable
- Agent cannot toggle or bypass TLS settings mid-session
- **Lab vs. production note**: Both default to `false` for lab convenience. For production deployments, set both to `true` in `.env`. No startup warning is emitted — rely on deployment documentation.

## ✅ Credential & Destructive Command Protection (Permission Deny Rules, v5.0)
- `.env` and common secret file variants blocked from `Read` — prevents credential exposure (router creds, Jira token)
- `Bash(env)`, `Bash(printenv *)`, `Bash(less .env*)`, `Bash(head .env*)` denied — closes common bypass vectors
- `Bash(ssh *)`, `Bash(sshpass *)` denied — enforces Pitfall #5 at permission level, not just prompt level
- `Bash(rm -rf *)` denied — prevents catastrophic file deletion
- `git push --force` and `git reset --hard` denied — prevents irreversible git operations
- `nc`, `curl`, `sudo docker`, `docker exec` removed from allow list — require explicit user approval each use
- Defined in `.claude/settings.local.json` deny list
- **Known residual risk**: `Bash(python3:*)` is broadly allowed and cannot be restricted without breaking test/tool execution; a `python3 -c` invocation reading `.env` would succeed. Mitigated by prompt-level instructions only.

## ✅ Rollback Advisory (`push_config`)
- Rollback advisory generated for every config change (inverting "no" prefixes for IOS CLI strings)

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
| Command content | Commands contain: `router`, `ospf`, `bgp`, or `isis` | high |
| Command content | Commands contain: `shutdown` (but NOT `no shutdown` — restoration is excluded) | high |

`assess_risk` is advisory only — it does not block changes. The user decides whether to proceed regardless of risk level.

