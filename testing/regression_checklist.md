## Regression Checklist (Manual Tests Performed by User)

Run this checklist after any significant change to `MCPServer.py`, `oncall/watcher.py`,
`platforms/platform_map.py`, `tools/`, `transport/`, or any skill file:

| # | Check | Tier | Method |
|---|-------|------|--------|
| 1 | All unit tests pass | — | `./run_tests.sh unit` |
| 2 | Integration tests pass (lab required) | — | `./run_tests.sh integration` |
| 3 | OSPF adjacency diagnosis — EOS | 1 | ST-001A |
| 4 | EIGRP passive-interface diagnosis | 1 | ST-002 |
| 5 | Redistribution diagnosis | 1 | ST-003 |
| 6 | BGP timer mismatch diagnosis | 1 | ST-006 |
| 7 | Full On-Call pipeline (passive-interface) | 1 | OC-001 Primary |
| 8 | OSPF adjacency diagnosis — RouterOS | 2 | ST-001B |
| 9 | EIGRP stub configuration | 2 | ST-005 |
| 10 | OSPF area type change (multi-device) | 2 | ST-007 |
| 11 | Maintenance window blocks push_config | 2 | MW-001 |
| 12 | PBR investigation (diagnostic only) | 3 | ST-004 |
| 13 | Watcher event filtering and recovery logging | 3 | WB-001 – WB-004 |

**NOTE:** On-Call cases are documented as Jira tickets (see Jira project SUP). Standalone mode has no Jira integration.

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
| `test_maintenance_window.py` | check_maintenance_window inside/outside window; push_config blocked outside |
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

**MW-001 verification**: `push_config` enforces the maintenance window — it returns an error dict when `check_maintenance_window` returns `allowed: false`. To test: temporarily narrow the window in `MAINTENANCE.json` to exclude current time, submit a Standalone prompt, approve the proposed fix, and confirm the agent reports a maintenance window block. Restore `MAINTENANCE.json` after testing.
