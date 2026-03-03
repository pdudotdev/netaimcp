## Regression Checklist (Manual Tests Performed by User)

Run this checklist after any significant change to `MCPServer.py`, `oncall/watcher.py`,
`platforms/platform_map.py`, `tools/`, `transport/`, or any skill file:

| # | Check | Tier | Method |
|---|-------|------|--------|
| 1 | All unit tests pass | — | `./run_tests.sh unit` |
| 2 | Integration tests pass (lab required) | — | `./run_tests.sh integration` |
| 3 | Full On-Call pipeline (passive-interface) | 1 | OC-001 Primary |
| 4 | Watcher event filtering and recovery logging | 2 | WB-001 – WB-004 |

**NOTE:** On-Call cases are documented as Jira tickets (see Jira project SUP).

---

**Unit test coverage by file (run `./run_tests.sh unit`):**

| Test File | What It Covers |
|-----------|----------------|
| `test_drain_mechanism.py` | tail_follow drain flag and line-yield logic |
| `test_platform_map.py` | PLATFORM_MAP command lookups for all vendors/queries |
| `test_sla_patterns.py` | SLA_DOWN_RE and SLA_UP_RE regex matching (all vendor formats) |
| `test_input_validation.py` | Literal enum rejection, ShowCommand read-only enforcement |
| `test_cache.py` | Bounded LRU eviction, TTL expiry, cache hit/miss |
| `test_command_validation.py` | FORBIDDEN CLI list, RouterOS JSON path/method validation, rollback advisory |
| `test_maintenance_window.py` | check_maintenance_window inside/outside window; push_config blocked outside; on_call bypass |
| `test_risk_assessment.py` | Risk scoring: role/SLA-path/keyword/device-count escalation |
| `test_syslog_sanitize.py` | sanitize_syslog_msg: non-printable stripping, truncation at 500 chars |

**Integration test coverage (requires running lab):**

| Test File | What It Covers |
|-----------|----------------|
| `test_mcp_connectivity.py` | Basic device reachability via MCP tools |
| `test_mcp_tools.py` | All protocol/routing/operational tools against live devices |
| `test_transport.py` | SSH/eAPI/REST transport layer: structured output, cache hit/miss, timeout |
| `test_watcher_events.py` | Watcher helpers: event detection, lock management, deferred scan |

---
