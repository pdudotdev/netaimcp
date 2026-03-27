# Changelog

All notable changes to this project are documented in this file.

---

## [v5.5.1]

> Dashboard UX improvements, source visibility, manual test suite, and setup documentation hardening.

### 📊 Dashboard UX
- **COPY buttons**: per-panel clipboard buttons on AGENT REASONING and TOOL CALLS panels — copy full panel content as plain text
- **Session hold + DISMISS**: when a session ends, panels remain visible (status → "Completed — Monitoring"). A **✕ DISMISS** button returns to the idle overlay on demand. A new session auto-dismisses any held content.
- **MCP tool badge styling**: MCP tools (e.g. `get_ospf`, `traceroute`) rendered with a distinct `.tool-name.mcp` badge to visually distinguish them from built-in Claude tools (Read, Edit, Bash)
- **MCP params unwrapping**: tool input display strips the outer `{params: ...}` wrapper that MCP tools use internally, showing clean parameter key/value pairs
- **Font size**: bumped +1px across all UI elements for improved readability

### 🔍 Source Visibility
- New **SOURCE** meta-group in the dashboard header: shows `<inventory> · <credentials>` (e.g. `NetBox · Vault` or `NETWORK.json · .env`) when a session is active
- Same info added to the Discord "Investigation Started" embed (`📦 Inventory: X · 🔑 Credentials: Y` line)
- `core/inventory.py`: exposes `inventory_source` module-level string (`"NetBox"` or `"NETWORK.json"`)
- `core/vault.py`: new `credential_source()` — probes Vault for the `ainoc/router` secret if not yet cached, returns `"Vault"` or `".env"`. Self-sufficient in any process regardless of import order.
- `oncall/watcher.py`: passes both sources to `_write_dashboard_state()` and `post_investigation_started()` at session start; logs both at watcher startup

### 🧪 Manual Test Suite
- 55 OSPF/BGP troubleshooting scenarios added to `testing/manual_testing.md`:
  - **27 OSPF tests**: covers all 7 adjacency criteria (hello/dead timers, area ID/type, network type, authentication, passive interface, MTU, Router ID uniqueness)
  - **28 BGP tests**: covers all 6 session formation criteria + 11 path selection attributes (Weight through Neighbor IP tie-break)
- Operator applies break configs via SSH; agent diagnoses and proposes fix

### 📚 Documentation
- `metadata/vault/vault_setup.md`: added **Production: Initialization** section — switching vault.hcl to HTTP listener, `vault operator init`, `vault operator unseal`, KV engine enable, and unseal-on-reboot caveat
- `metadata/netbox/netbox_setup.md`: added **Production: Boot Persistence** section — restart policies for Docker Compose containers and optional systemd unit

### 🧪 Testing
- UT-026 schema guard updated for new `inventory_source` and `credential_source` fields in active session state
- 610 unit tests passing

---

## [v5.5.0]

> Real-time agent observability dashboard, session stop mechanism, SSH timeout optimizations.

### 📊 Real-Time Agent Dashboard
- New `dashboard/ws_bridge.py` — always-on WebSocket bridge: tail-follows the watcher's NDJSON session file (stream-json format), parses events, and broadcasts to browser clients. Serves HTTP + WebSocket on a single port (`DASHBOARD_PORT` env var, default 5555) using websockets 16.0's `process_request` callback — no separate HTTP server needed
- New `dashboard/index.html` — single-file browser UI (dark NOC theme): two panels — AGENT REASONING (markdown-rendered, streamed incrementally) and TOOL CALLS (collapsible timeline with tool name, inputs, and output). Auto-scroll with lock toggle, session header with live elapsed timer and cost display, idle overlay between sessions
- New `dashboard/oncall-dashboard.service` — systemd unit (independent of `oncall-watcher.service`; communication is filesystem-only via `data/dashboard_state.json` + session NDJSON files)
- Late-joining browser clients receive a full replay buffer (up to 200 events) on connect — no missed events
- WebSocket event types surfaced: `init`, `session_start`, `session_idle`, `reasoning`, `tool_start`, `tool_input_complete`, `tool_result`, `session_end`
- Tool input JSON streamed incrementally (`input_json_delta` chunks) and accumulated per content-block index before display
- Remote access: SSH tunnel (`ssh -L 5555:localhost:5555`) or direct LAN

### 🚨 Session Stop Mechanism
- Sentinel file pattern (`data/stop_session`): any actor creates it → watcher detects within 2s → kills agent tmux session and posts Discord error notification
- Dashboard "■ STOP" button (red, visible only during active sessions): sends `{"action": "stop"}` via WebSocket → bridge writes sentinel → watcher acts within 2s
- CLI stop: `touch /home/mcp/aiNOC/data/stop_session` during an active session — same effect
- Stale sentinel cleared automatically at session start so it never blocks the next session

### 🔄 Watcher Stream-JSON Migration
- Switched `--output-format json` → `stream-json --verbose --include-partial-messages` with `stdbuf -oL` (forces line-buffered stdout to file; prevents block-buffering delay that would stall the dashboard)
- `--verbose` is required — without it, no `stream_event` objects are emitted
- New `_write_dashboard_state()` helper — writes `data/dashboard_state.json` at session start (with `session_name`, `session_file`, `state: "active"`) and session end (`state: "idle"`)
- Cost parsing updated: reverse-scans NDJSON lines for `{"type": "result", "total_cost_usd": ...}` (was a single JSON object)
- `DASHBOARD_RETAIN_LOGS=1` env var — when set, session NDJSON files are kept after session end for post-mortem review (default: deleted)

### ⚡ SSH Timeout Optimization
- `SSH_TIMEOUT_TRANSPORT`: 30 → 15s — SSH handshake; devices respond in <5s or are unreachable
- `SSH_TIMEOUT_OPS_LONG`: 60 → 45s — traceroute; IOS XE completes in ~30s
- `SSH_RETRIES`: 2 → 1 — 2 total attempts instead of 3
- Worst-case per MCP call: 3 × 30s + 2 × 2s = **94s** → 2 × 15s + 1 × 2s = **32s**
- Per-command `timeout_ops` moved from Scrapli connection constructor (`_connection_params`) to `send_command(command, timeout_ops=timeout_ops)` — connection setup always uses `SSH_TIMEOUT_OPS` (30s); only the traceroute command execution uses the longer 45s timeout where it is actually needed

### 🧪 Testing
- **UT-026** (`testing/agent-testing/unit/test_ws_bridge.py`): 39 tests — `_strip_tool_prefix`, NDJSON parsing (malformed/empty input, result line, text_delta, full tool_use lifecycle via content_block_start/delta/stop, tool_result, incomplete partial JSON), event buffer ring behavior, session state broadcast
- Watcher stop-sentinel detection and dashboard state file tests added to existing watcher test files
- 472 → 577 total tests passing

### 📦 Dependencies
- New: `websockets>=16.0,<17.0`

---

## [v5.4.0]

### 🔐 HashiCorp Vault Integration
- New `core/vault.py` — thin Vault KV v2 client with `get_secret(path, key, fallback_env)`: reads secrets from Vault, caches per-path, falls back to `os.getenv()` when Vault is not configured or unreachable
- Vault paths: `ainoc/router` (username, password), `ainoc/jira` (api_token), `ainoc/discord` (bot_token)
- Consumers updated to use `get_secret()`:
  - `core/settings.py` — router credentials
  - `core/jira_client.py` — Jira API token
  - `core/discord_approval.py` — Discord bot token
- New env vars: `VAULT_ADDR`, `VAULT_TOKEN` (both optional — Vault is fully optional)
- New dependency: `hvac>=2.3,<3.0`
- Setup guide: `metadata/vault/vault_setup.md`

### 🌐 NetBox Device Inventory
- New `core/netbox.py` — NetBox device inventory loader via pynetbox: maps NetBox devices to the same `{host, platform, transport, cli_style, location}` schema as `NETWORK.json`
- `core/inventory.py` rewritten — tries NetBox first, falls back to `NETWORK.json` when NetBox is not configured, unreachable, or returns no valid devices
- NetBox custom fields on Device model: `transport` (asyncssh/restconf), `cli_style` (ios)
- New `metadata/netbox/populate_netbox.py` — idempotent pynetbox script that creates all prerequisite objects (custom fields, manufacturer, device types, platform, roles, sites) and 9 devices with management interfaces and IPs
- New dependency: `pynetbox>=7.4,<8.0`
- Setup guide: `metadata/netbox/netbox_setup.md`

### 📊 Source Logging
- `core/vault.py`: INFO log on first Vault read per path; DEBUG log when Vault not configured
- `core/netbox.py`: INFO log with device count on successful load
- `core/inventory.py`: INFO log showing which source loaded the inventory (NetBox vs NETWORK.json)

### 🧪 Testing
- **UT-019** (`test_vault.py`): 9 tests — env var fallback, Vault reads with mock hvac, caching, error fallback
- **UT-020** (`test_netbox.py`): 9 tests — None on missing config, pynetbox exceptions, schema mapping, CIDR stripping, field validation
- 454 → 472 total tests passing (includes test_watcher_discord_notifications.py now registered as UT-021)

---

## [v5.3.1]

### 🐛 Bug Fixes / Off-Path Detection
- **Transient false positive**: the agent incorrectly concluded "transient — recovered without intervention" when the SLA path recovered via an alternate ISP (IBN) rather than the expected path (IAN). IAN Eth0/3 was still admin-down. Root cause: LLM non-determinism in applying Principle 2 (off-path detection). Fixed by two complementary changes:
  - **Prompt enrichment**: `invoke_claude()` now looks up the SLA path in `sla_paths/paths.json` by source device and injects `scope_devices` + expected path description directly into the prompt. The agent has the scope list immediately, without needing to recall it from an earlier file read.
  - **Oncall skill**: Step 1 now includes an explicit mandatory scope check (between traceroute call and outcome bullets) that forces hop-by-hop comparison against `scope_devices`. Step 1a Branch A condition updated to explicitly require all hops within scope.

### 🗒️ Session Log Overhaul
- **`--output-format json`**: Claude is now invoked with `--output-format json`, with stdout redirected to `logs/session-oncall-<timestamp>.md`. This replaces all failed terminal-capture approaches (pipe-pane, capture-pane, capture-pane+alternate-screen-off). The JSON envelope contains `total_cost_usd`, `num_turns`, `usage`, and the full `result` text — reliable, no escape code issues.
- **Removed dead code**: `_ANSI_RE` regex and `_clean_session_log()` function removed (ANSI stripping was only needed for pipe-pane output). `set-option -g history-limit 50000` and `set-option alternate-screen off` removed from tmux setup.
- **tmux attach link removed**: the `📺 Session details: tmux attach -t <session>` line is removed from the Discord investigation-started embed. It was useless — shows empty terminal during investigation (alternate screen), "no sessions" after (killed in finally).

### 📊 Watcher Log Enrichment
- **Session duration and exit**: "Agent session ended." now includes duration and exit classification: `"Agent session ended. Duration: 2m46s, exit: normal"` (or `crash (code N)` / `timeout (force-killed)`).
- **Session cost**: after session end, `total_cost_usd` and `num_turns` are parsed from the JSON output file and logged: `"Session cost: $0.1141 | turns: 5"`.
- **Approval audit**: after `_post_discord_session_notification`, watcher reads `data/pending_approval.json` and logs approval status, decided_by, risk level, and devices. If no approval was requested, logs `"No approval requested this session (transient/recovered)"`.
- **Session cost in Discord embeds**: `post_session_complete` and `post_session_error` now accept `session_cost` and display a 💰 Cost inline field when available.

---

## [v5.3.0]

### 🐛 Bug Fixes
- **Duplicate Discord notifications**: fixed a `try/except/else` semantics bug in `invoke_claude()` that caused both a red "Agent Session Error" embed and a green "Session Complete — transient" embed to be posted when the agent crashed. Python's `try/except/else` fires the `else` whenever the `try` body raises no exception — not only when no `if/elif` branch matched. Fixed by moving `post_session_complete` into the `else` of the `if/elif` chain inside the `try`. The notification block is now extracted into `_post_discord_session_notification()` for testability.
- **Crash cooldown UnboundLocalError**: `main()` was missing `global _last_crash_ts` declaration. The `_last_crash_ts = None` assignment (cooldown expiry clear) caused Python to treat the variable as local throughout the function, crashing with `UnboundLocalError` on every SLA Down event. Recovery events were unaffected (they `continue` before the cooldown check). Result: watcher appeared to run but silently crashed on every Down event.

### 🔒 Agent Session Safety
- **Crash cooldown**: after an agent crash (non-zero exit code), new sessions are suppressed for `CRASH_COOLDOWN_MINUTES` (default 5) to prevent wasting API calls when the failure is systemic (e.g. API credit limits, authentication errors). The cooldown timestamp is cleared automatically once the window expires. The cooldown state is module-level and independent of Discord configuration.
- **Agent timeout**: `_wait_for_tmux_process_exit()` now enforces a deadline (default 30 min). If Claude doesn't exit within the timeout, the tmux session is force-killed via `tmux kill-session`, the watcher logs a warning, and the lock file is released so new sessions can proceed. Configurable via `AGENT_TIMEOUT_MINUTES` env var.
- **tmux session cleanup**: after the agent exits, the tmux session is explicitly killed (`tmux kill-session`). Sessions no longer accumulate indefinitely.

### 📢 Discord UX Improvements
- **Investigation-started notification**: when the watcher spawns an agent session, it immediately posts a blue informational embed to Discord ("🚨 NEW ISSUE: DEVICE {name} — Investigation Started") so the operator is notified before the investigation even begins.
- **Progress updates**: after 60 seconds of active investigation the watcher posts 🔍 "Still investigating network state..." and after 120 seconds 🔍 "Investigation ongoing, please wait..." to Discord. Each message only fires if the agent is still running at that mark — crashes before the threshold produce no progress message.
- **Acknowledgment messages**: after the operator reacts with ✅ or ❌, a confirmation reply is posted ("Approval received from @user — aiNOC is proceeding with the fix." / "Rejection received from @user — aiNOC will not apply the fix.").
- **Jira ticket in outcome embeds**: `post_approval_outcome` now reads the issue key from the approval state file and includes a "Ticket SUP-xx updated" field in the Discord outcome embed.
- **Removed duplicate expiry message**: `request_approval` no longer auto-posts an expiry outcome. All outcome posts (approved, rejected, expired) are handled by the agent via `post_approval_outcome`, which includes the Jira ticket reference. Previously, expiry caused two identical-looking Discord messages.

### 🔒 Approval Gate Hardening
- When Discord is not configured, `request_approval` writes `status: "SKIPPED"` (previously was writing `APPROVED`). The `push_config` gate rejects SKIPPED status — no Discord = no push, enforced at code level.
- Integration tests updated: `_approve_devices()` helper writes a valid APPROVED record before each `push_config` call so the gate passes in test context.
- New env var: `AGENT_TIMEOUT_MINUTES=30`

### 🧪 Testing
- UT-017 (`test_approval.py`): SKIPPED status assertion added; `post()` method added to MockSessions for ack message tests; `post_approval_outcome` tests updated for Jira `issue_key` param.
- UT-018 (`test_config_approval_gate.py`): SKIPPED added to bad-status parametrize list.
- UT-021 (`test_watcher_discord_notifications.py`): 10 tests covering Discord notification exclusivity (crash/timeout/watcher-exc → error only; normal exit → complete only; approval-requested → neither) and crash cooldown behaviour (timestamp set on crash, skips within window, clears after expiry, not set on normal exit).
- Integration tests (`test_mcp_tools.py`): all 8 push_config tests now call `_approve_devices()` before each push.
- 443 → 452 total tests passing.

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
- **tmux session cleanup**: after Claude exits and the session log is cleaned, the watcher kills the tmux session (`tmux kill-session`). Full session output is preserved in `logs/session-oncall-<timestamp>.md`. (Note: `remain-on-exit on` is still set to keep the pane alive until the watcher's cleanup runs.)

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
- Introduced **6 Core Troubleshooting Principles** (mandatory, ordered) — see `CLAUDE.md`
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
- Added `cases.md` and `lessons.md` (see `cases/`)
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