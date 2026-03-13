# 🛡️ System Safeguards & Operational Controls

Architectural protections that prevent unsafe automation, duplicate execution, and unauthorized configuration changes. Organized by enforcement type: code-enforced (hard stops) → config-enforced (deny rules / env vars) → behavioral (prompt-level).

---

# 🔒 Code-Enforced Controls

These mechanisms are enforced in code — they block unsafe actions regardless of prompt instructions.

## ✅ Code-Level Approval Gate (v5.2)
`push_config` reads `data/pending_approval.json` before executing any configuration change. Requirements:
- Record must exist with `status: "APPROVED"`
- `devices` in the approval record must **exactly match** (sorted) the devices being pushed to — pushing to unapproved devices is blocked even if an approval record exists for different devices
- A record with `status: "EXECUTED"` (already consumed) blocks replay pushes
- A record with `status: "SKIPPED"` (Discord not configured) also blocks pushes — no Discord = no push

Without a valid approval record, `push_config` returns an error and no commands are sent to any device. This prevents config push even if prompt-level instructions are lost, ignored, or bypassed.

After a successful push, the record is marked `"EXECUTED"` — a second push requires a new `request_approval` call.

## ✅ Lock File + PID Liveness (`oncall/oncall.lock`)
- Single-instance guard — prevents multiple agents from running simultaneously
- `is_lock_stale()` detects dead processes and cleans stale locks automatically, preventing deadlocks from crashed processes

## ✅ Drain Mechanism (`drain[0]` flag)
After session ends, the watcher seeks to EOF and skips buffered events — prevents re-processing the same failure N times.

## ✅ `run_show` Read-Only Enforcement
`ShowCommand` Pydantic model validates at the MCP boundary before execution:
- CLI commands (IOS): must start with `show ` (case-insensitive)
- RESTCONF JSON actions: must have `url` key with `method=GET` only
- Any other input raises `ValidationError` — prevents config bypass via `run_show`

## ✅ Expanded Forbidden Command Set (Updated in v5.0)
21 blocked patterns in `tools/config.py`, applied before any `push_config` execution. Covers: reload, erase, write erase, format, delete, copy run, write mem, configure replace, username manipulation, enable secret/password, snmp-server community, crypto key ops, transport input none, and others.

**Known residual risk**: IOS abbreviations (e.g. `wr er` instead of `write erase`) bypass substring matching; a full IOS parser would be required to close this gap completely.

## ✅ Input Parameter Validation (v5.0)
Pydantic models in `input_models/models.py` validate all tool inputs at the MCP boundary:
- `destination`: validated as IP address; `source`: validated as IP address or interface name (alphanumeric + `/:.-`, max 50 chars) — rejects CLI injection via append (e.g. `"8.8.8.8 repeat 999999"`)
- `neighbor`: validated as IP address — rejects `"1.2.3.4 | include password"` style injection
- `prefix`: validated as IPv4 address or CIDR regex
- `vrf`: alphanumeric + underscore/dash, max 32 chars — rejects newline injection
- `issue_key`: `^[A-Z][A-Z0-9]+-\d+$` — prevents URL path traversal in Jira REST calls

## ✅ Syslog Prompt Injection Mitigation (Strengthened in v5.0)
Syslog messages sanitized by stripping non-printable characters (Python `str.isprintable()` filter) and collapsing whitespace. Applied to all event fields before injection into the agent prompt and before writing to deferred/pending event files. Delimiter markers isolate log content from instructions.

**Known residual risk**: No sanitizer can fully prevent LLM prompt injection from adversarial ASCII text; this is a defense-in-depth measure.

---

# ⚙️ Config-Enforced Controls

Enforced by `.claude/settings.local.json` deny rules or environment variables — cannot be changed at runtime.

## ✅ Credential & Destructive Command Protection
Deny rules in `.claude/settings.local.json`:
- `.env` and common secret file variants blocked from `Read` — prevents credential exposure
- `Bash(env)`, `Bash(printenv *)`, `Bash(less .env*)`, `Bash(head .env*)`, `Bash(tail .env*)`, `Bash(more .env*)` denied — closes common bypass vectors
- `Bash(ssh *)`, `Bash(sshpass *)` denied — enforces no-direct-SSH at permission level
- `Bash(rm -rf *)` denied — prevents catastrophic file deletion
- `git push --force` and `git reset --hard` denied — prevents irreversible git operations
- `nc`, `curl`, `sudo docker`, `docker exec` require explicit user approval each use

**Known residual risk**: `Bash(python3:*)` is broadly allowed and cannot be restricted without breaking test/tool execution; a `python3 -c` invocation reading `.env` would succeed. Mitigated by prompt-level instructions only.

## ✅ TLS/SSL Configuration (Env-Var Only)
Controlled by `RESTCONF_VERIFY_TLS` and `SSH_STRICT_HOST_KEY` — read once at import time, not runtime-configurable. Agent cannot toggle or bypass TLS settings mid-session.

**Lab vs. production note**: Both default to `false` for lab convenience. For production deployments, set both to `true` in `.env`.

---

# 🧠 Behavioral Controls

These depend on the LLM following prompt instructions. No code-level backstop — labeled here as behavioral.

## ✅ Discord-Primary Approval
When Discord is configured, `request_approval` is the mandatory gate before `push_config`. It posts a rich embed and polls for ✅/❌ emoji reaction. If Discord is not configured or approval expires, the agent logs to Jira and exits without pushing. The code-level approval gate (Section 1) independently enforces this — even if the agent skips `request_approval`, `push_config` will return an error.

## ✅ Read-Only Policy Files
`inventory/NETWORK.json` and `intent/INTENT.json` cannot be modified by the agent — both are instructed as read-only in CLAUDE.md and the deny rules limit write access.

## ✅ On-Call Focus Enforcement
Once invoked for an SLA failure, the agent focuses solely on that issue until completion. Deferred failures (arriving during an active session) are documented to Jira and Discord by the watcher after the session ends — no second agent session is spawned.
