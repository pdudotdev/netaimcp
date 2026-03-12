# Changelog

All notable changes to this project are documented in this file.

---

## [v5.2.0]

### 📟 Discord Remote Approval
- New `core/discord_approval.py` module — Discord bot API integration: `post_approval_request()`, `poll_for_reaction()`, `post_outcome()`
- New `tools/approval.py` — two MCP tools registered:
  - `request_approval`: posts a rich embed to a configured Discord channel with findings, commands, devices, and risk level. Adds ✅/❌ reactions and polls for operator response. Returns `"approved"` / `"rejected"` / `"expired"` / `"skipped"` decision.
  - `post_approval_outcome`: posts the final outcome (approved+verified, rejected, expired) as a Discord reply after fix + verification
- **Discord-primary**: when Discord is configured, the operator approves via Discord embed. When Discord is not configured, the agent logs to Jira that no approval channel is available and exits without pushing config.
- **No Discord = no push**: if Discord not configured (`DISCORD_BOT_TOKEN` / `DISCORD_CHANNEL_ID` absent), `request_approval` returns `"skipped"` — the agent must proceed to Session Closure without applying any fix
- **Audit trail**: every approval request and outcome written to `data/pending_approval.json` (runtime state, gitignored)
- New env vars: `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, `APPROVAL_TIMEOUT_MINUTES` (default 10)
- Setup guide: `metadata/discord/discord_setup.md`
- 13 → 15 MCP tools registered

### 🔒 push_config Code-Level Approval Gate
- `push_config` now verifies `data/pending_approval.json` before executing any commands — architectural enforcement independent of prompt instructions
- Requirements: record must exist with `status: "APPROVED"` and device list must **exactly match** the push targets (sorted comparison). Pushing to unapproved devices is blocked even if an approval record exists for different devices.
- Blocks with a descriptive error: no record, wrong status (`REJECTED`, `EXPIRED`, `PENDING`, `SKIPPED`), device mismatch, or `EXECUTED` replay
- After a successful push, record is marked `EXECUTED` — a second push on the same approval is blocked; a new `request_approval` call is required
- When Discord is not configured, `request_approval` writes a `SKIPPED` record — `push_config` is blocked at the code gate, enforcing the same policy as the prompt instructions
- Previously: approval was prompt-level only (CLAUDE.md Pitfall #16). Now: two independent enforcement layers — code gate (architectural) + prompt instructions (behavioral)

### 🔄 Session Lifecycle — Service-Only Mode + Auto-Exit
- **Interactive mode removed** — the watcher always runs Claude in tmux + print mode (`-p`). Claude processes its prompt, uses MCP tools, and exits automatically when done. No `/exit` needed, no operator at the CLI required.
- **Single code path**: `--service` flag removed from `watcher.py` and systemd `ExecStart`. tmux is now a hard requirement checked at startup.
- **Session output logging**: each session's full output is streamed via `tmux pipe-pane` to `logs/session-oncall-<timestamp>.md` for post-incident review.
- **Watcher resumes monitoring immediately** after Claude exits — `_wait_for_tmux_process_exit()` polls `pane_dead` so `remain-on-exit on` sessions don't block the watcher.
- **tmux session persists** after Claude exits (`remain-on-exit on`) so operators can attach later to review the full investigation history.

### 🗑️ Deferred Investigation Sessions Removed
- `invoke_deferred_review()` deleted — no second agent session is spawned for deferred failures.
- **Deferred documentation**: after the primary session ends, `watcher.py` scans for concurrent failures, adds a Jira comment to the original ticket, and posts an informational Discord embed. No agent cost, no autonomous investigation.
- New `_document_deferred_events()` helper in `watcher.py`. New `post_deferred_list()` in `core/discord_approval.py`.
- Removed: `PENDING_EVENTS_FILE`, `DEFERRED_FILE`, `save_pending_events()`, stale file cleanup at startup.
- `.gitignore`: removed `oncall/pending_events.json` + `oncall/deferred.json`; added `logs/session-*.md`.

### 🧠 Oncall Skill & Agent Guidance
- Added **Step 4: Approval, Remediation & Session Closure** to `skills/oncall/SKILL.md` — the skill is now a complete end-to-end workflow. Previously it ended at "Presenting Findings" with no bridge to the approval/remediation lifecycle (CLAUDE.md steps 4–6). An agent following the skill alone could skip Discord approval entirely.
- Updated CLAUDE.md: "user is supervising the workflow via the Claude Code console" → "operator supervises via the Claude Code console and/or Discord remote approval" (accurate for remote approval scenarios)
- Added CLAUDE.md Pitfall #16 (never call `push_config` without approval) and Pitfall #17 (always call `post_approval_outcome` after resolution)

### 📚 Documentation
- `metadata/about/guardrails.md` — expanded **Agent Autonomy Approval** section: documents code-level gate, Discord-primary approval model, exact device match requirement, and replay prevention. Replaces the single-line "no-auto-push rule" with a full three-layer description.

### 🧪 Testing
- **UT-018** (`test_config_approval_gate.py`): 10 unit tests covering all gate scenarios — no record, bad status (4 variants), replay, device mismatch, superset mismatch, successful push, EXECUTED marking
- **UT-014** (`test_config_push.py`): updated to bypass approval gate via `_NO_APPROVAL_ERROR` mock (gate tested separately in UT-018)
- 408 → 430 unit tests

---

## [v5.1.0]

### 🗑️ Removed
- **Maintenance window feature** removed entirely — aiNOC runs fully in on-call context (interactive or service mode), so time-gated change control was functionally inert
  - Deleted `policy/MAINTENANCE.json`
  - Deleted `tools/state.check_maintenance_window()` and `pytz` dependency
  - Removed `on_call` parameter from `ConfigCommand` model and `push_config()`
  - Unregistered `check_maintenance_window` MCP tool (13 tools now)
  - Deleted `testing/agent-testing/unit/test_maintenance_window.py` (UT-007)
  - 415 → 401 unit tests

### 🧹 Cleanup
- Deleted `metadata/transports/transports.txt` (orphaned reference note)
- Deleted empty `vendors/` directory placeholder
- Deleted `transport/pool.py` (no-op stub — `async def close_sessions(): pass`); simplified `MCPServer.py` lifespan to none
- Removed NETCONF legacy acceptance branch from `ShowCommand.must_be_read_only` (`{"filter":...}` / `{"get":...}`) — NETCONF was removed in v5.0; these forms are now rejected like any other unknown JSON key
- Removed dead constants `_OSPF_OPER_KEY` / `_BGP_OPER_KEY` from `tools/protocol.py` — leftover YANG path strings from before platform_map.py owned URL building
- Deleted `testing/agent-testing/cookie.txt` (libcurl artifact) and stale `.pyc` bytecache files
- Added 3 missing MCP tool allow rules to `.claude/settings.local.json` / `.claude/settings.local.example.json`: `get_routing_policies`, `run_show`, `get_intent`
- Updated `skills/redistribution/SKILL.md` device names to current topology (D1C/R3C/R8C/B1C/B2C → E1C/C1C/C2C/A1C/A2C)
- Fixed stale label in `test_mcp_tools.py`: `test_push_config_ios_netconf` → `test_push_config_ios_restconf`
- Rewrote `metadata/about/scalability.md` — comprehensive contributor guide for adding protocols/vendors, synchronized with current implementation
- Added scalability guide link to `README.md`; fixed pitfall count in `file_roles.md` (15→14); added IT-005 to test tables

### 📚 Skills & Agent Guidance Quality Audit
- **BGP skill** (`skills/bgp/SKILL.md`): Added OpenConfirm state (RFC 4271 §8); fixed Active/Connect state descriptions; reordered Session Checklist (AS numbers before timers — more fundamental); added "Session Established but Zero Prefixes" section (address-family activation); added "Session Flapping / Reset Reasons" table; updated iBGP/RR section scope note (current topology is eBGP-only); added community handling omission note; fixed RR cluster-id explanation (RFC 4456 §8 accuracy); documented `clear ip bgp` FORBIDDEN limitation in Verification Checklist
- **OSPF skill** (`skills/ospf/SKILL.md`): Added LOADING state to neighbor table; added P2MP timers (Hello 30s/Dead 120s); added NSSA Totally Stubby area type; added ABR route summarization (`area range`) section; added distribute-list filtering section (LSA-present/route-absent symptom); enhanced INIT state description (asymmetric link cause); added RFC 3101 §2.3 inline reference
- **Routing skill** (`skills/routing/SKILL.md`): Removed misleading "ios only" annotations; added distribute-list cross-reference to OSPF skill; added BGP `maximum-paths` default note (defaults to 1 — no ECMP without explicit config); cleaned up Query Reference table (removed redundant Platform support column)
- **On-Call skill** (`skills/oncall/SKILL.md`): Added Terminology section defining primary vs deferred review session (anchors `pending_events.json` concept); clarified Step 2 ECMP precondition; added `lessons.md` read reminder before Step 0
- **CLAUDE.md**: Added Pitfall #15 (`clear` commands FORBIDDEN); added redistribution showcase entry to Skills Library table
- **`metadata/about/file_roles.md`**: Removed stale `pool.py` reference; updated pitfall count (14→15)

---

## [v5.0.0]

> Cisco-only architecture with 2-tier transport (RESTCONF→SSH). 9 devices, all Cisco IOS/IOS-XE. Other vendors available as customizable modules per client need.

### 🌐 Topology
- 9-device Cisco IOS/IOS-XE topology (2 platforms: cisco_iol, cisco_c8000v)
- OSPF Area 0 + Area 1 stub, BGP dual-ISP (AS1010↔AS4040/AS5050), BGP AS2020 at X1C
- 5 SLA paths: OSPF cost-based primary/backup ABR selection (A1C/A2C via C1C/C2C)
- Full redundancy across the Access, Collapsed Core, Edge-to-ISP layers

### 🔌 Transports
- **2-tier for c8000v**: RESTCONF (primary, httpx/JSON) → SSH (fallback, Scrapli/CLI)
- **SSH-only for IOL**: A1C, A2C, IAN, IBN
- `ActionChain` class in `platform_map.py` for ordered transport fallback
- Config push: all devices use SSH CLI

### 🏗️ Architecture
- Clear separation between **Interactive** and **Service** modes
- `PLATFORM_MAP` with 2 distinct sections: `ios`, `ios_restconf`
- `transport/restconf.py` — httpx AsyncClient for RESTCONF reads; 
- RESTCONF now has dedicated BGP/OSPF trim functions to reduce token cost
- Transport dispatcher with ActionChain fallback iteration + `_transport_used` tag

### 🔧 Fixes
- Deferred-event scanner deduplicates by `(device, msg)` — SLA oscillation (Down→Up→Down) no longer triggers false deferred sessions
- Jira client: module-level globals replaced with `_config()` helper that reads env vars at call time (fixes stale-config under systemd)
- `oncall-watcher.service`: EnvironmentFile commented out — systemd doesn't strip inline comments from `.env`, corrupting values that python-dotenv handles correctly

### 📡 Transport Visibility
- Result dict includes `_command` field (actual CLI command or RESTCONF URL) right after `device` for inline visibility in Claude Code
- Debug logging added to SSH and RESTCONF executors

### 🧪 Testing
- 416 unit + watcher-events tests (up from 244)
- 16 unit test files, covering: transport dispatch, RESTCONF/SSH executors, config push, tool layer, Jira tools
- New integration tests: full MCP tool coverage, transport layer, platform coverage
- New test: deferred excludes trigger device's repeated SLA oscillation events

---

## [v4.5.0]

> On-Call-first architecture. Standalone mode retired as an official mode. Tool set simplified.

### 🏗 Architecture
- Retired Standalone Mode as an official workflow — On-Call is now the primary mode; ad-hoc console troubleshooting remains supported via the 6 Core Principles
- Removed `snapshot_state` tool and all snapshot infrastructure (feature was write-only — no programmatic reader existed)
- Added `on_call: bool` parameter to `push_config` — bypasses the maintenance window when `True` (On-Call fixes apply at any hour)
- Risk assessment (`assess_risk`) now surfaced before user approval: agent calls it in On-Call step 4 and includes risk level in the findings table

### 🧪 Testing
- 281 tests: removed 6 snapshot input validation tests, added 3 on_call model/bypass tests
- Manual E2E: retired ST-00x Standalone test suite; OC-001, MW-001, and WB-001–004 remain
- 15 MCP tools registered (snapshot_state removed)

---

## [v4.0.0]

> Major **quality, reliability, and security** release.
> No new protocols or vendors — hardened foundation for v4.5.

### 🔐 Security & Safety
- Enforced maintenance windows in `push_config` (blocked outside policy)
- Restricted `run_show` to read-only commands (no config bypass)
- RouterOS REST validation (forbidden paths blocked, POST rejected)
- Syslog prompt injection mitigation (sanitize + delimiter)
- Expanded forbidden command set (5 → 14 patterns)
- Configurable TLS/SSL per transport:
  - `VERIFY_TLS`
  - `ROUTEROS_USE_HTTPS`
  - `SSH_STRICT_HOST_KEY`

### 🏗 Architecture
- Decomposed monolithic `MCPServer.py` (798 lines) into:
  - `tools/`
  - `transport/`
  - `core/`
  - `input_models/`
- Implemented bounded LRU cache (256 entries, TTL-based eviction)
- Added connection pooling for eAPI and REST transports
- Enforced HTTP timeouts on all device and Jira connections
- Added structured JSON logging with configurable levels

### 🧠 Troubleshooting Methodology
- Introduced **6 Core Troubleshooting Principles** (mandatory, ordered) — see `CLAUDE.example.md`
- Rewrote Standalone Mode into 10 deterministic steps with decision gates
- Added protocol skill prerequisite gates (interfaces + neighbors verified before deep investigation)
- Implemented role-aware risk assessment using `INTENT.json` and SLA paths

### 🚨 On-Call & Operational
- SLA recovery (Up) event detection and logging
- Added service mode (`--service` flag, renamed from `-d`/`--daemon`) with tmux session support and `wall` notification
- Added systemd service file (`oncall/oncall-watcher.service`) for production deployment
- ~~Added pre-change snapshot support in `push_config`~~ *(removed in v4.5 — feature was write-only)*
- Generated rollback advisory for all config changes

### 🧪 Testing
- 230 unit tests across 9 test files (up from 3 in v3.0) *(229 in v4.5 after snapshot tests removed)*
- 4 integration test files with `NO_LAB` skip guards
- 12 manual E2E scenarios:
  - 7 standalone
  - 1 on-call
  - 1 maintenance window
  - 3 watcher
- Enforced Pydantic `Literal` validation on all query parameters

---

## [v3.0.0]

> Focus: Multi-mode operations, improved diagnosis flow, optimized AI performance, reduced hallucinations and costs.

### 🧠 AI & Workflow Improvements
- Added `mcp_tool_map.json` for improved MCP tool selection
- Updated `INTENT.json` for cleaner network context
- Added `CLAUDE.md` with defined workflows and guidance
- Added troubleshooting skills for improved coherence
- Added `cases.md` and `lessons.md` (see `/cases.example`)
- aiNOC now documents cases and curates reusable lessons

### 🧪 Testing & Quality
- Well-defined test suites
- Regression test checklist

### 🌐 Enhancements
- Added MikroTik API reference
- Minor bug fixes

---

## [v2.0.0]

> Focus: Topology expansion, MCP toolset improvements, optimized AI performance, reduced hallucinations and costs, beyond SSH connectivity.

### 🧠 AI & Tooling Improvements
- Structured outputs:
  - Cisco: Genie
  - Arista: eAPI
  - MikroTik: REST API
- Strict command determinism:
  - `platform_map`
  - Query enums in input models
  - Platform-aware commands
- Tool caching to prevent duplicate commands and troubleshooting loops
- Protocol-specific MCP tools
- Targeted config sections (avoiding full `show run` dumps)
- Updated `INTENT.json` and `NETWORK.json`
- Legacy `run_show` tool now fallback-only
- Improved tool docstrings

### 🌐 Platform & Protocol Expansion
- Routers: 20
- MCP tools: 14
- New vendor: MikroTik
- New protocol: BGP
- Cisco: Genie parsing
- Arista: eAPI (replacing SSH)
- MikroTik: REST API queries
- Platform command map
- Improved topology diagram

### 🏗 Architecture & Code Quality
- Cleaner, modular codebase
- Enhanced `INTENT.json`
- Minor bug fixes

---

## [v1.0.0]

### 🚀 Initial Release
- Routers: 11
- Protocols: 2 (OSPF, EIGRP)
- Vendors: 2 (Arista, Cisco)
- MCP server tools: 6