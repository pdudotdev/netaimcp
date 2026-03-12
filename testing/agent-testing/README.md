# aiNOC Agent Test Suite

Structured test framework for validating aiNOC agent behavior after codebase changes.

## Prerequisites

```bash
cd /home/mcp/aiNOC
pip install -r requirements.txt
```

Credentials are loaded from `/home/mcp/aiNOC/.env`:
```
ROUTER_USERNAME=admin
ROUTER_PASSWORD=admin
```

## Running Tests

```bash
chmod +x run_tests.sh

# Run all tests
./run_tests.sh all

# Run only unit tests (no device connectivity required)
./run_tests.sh unit

# Run integration tests (real devices, read-only)
./run_tests.sh integration
```

## Test Categories

### Unit Tests (no devices)
| ID | File | Description |
|----|------|-------------|
| UT-001 | unit/test_sla_patterns.py | SLA_DOWN_RE regex against all log formats |
| UT-002 | unit/test_platform_map.py | PLATFORM_MAP command mapping per cli_style |
| UT-003 | unit/test_drain_mechanism.py | tail_follow drain/EOF-seek logic |
| UT-004 | unit/test_input_validation.py | Literal enum rejection, ShowCommand read-only enforcement |
| UT-006 | unit/test_command_validation.py | FORBIDDEN CLI list, rollback advisory |
| UT-008 | unit/test_risk_assessment.py | Risk level logic (low/medium/high), keyword/device/path escalation |
| UT-009 | unit/test_syslog_sanitize.py | Syslog message sanitization |
| UT-010 | unit/test_transport_dispatch.py | ActionChain 2-tier fallback (RESTCONF→SSH), _transport_used tag, asyncssh routing |
| UT-011 | unit/test_restconf_unit.py | RESTCONF executor: HTTP 200/4xx/5xx/timeout, URL construction |
| UT-013 | unit/test_ssh_unit.py | SSH executor: Scrapli send_command, Genie fallback, push_ssh |
| UT-014 | unit/test_config_push.py | push_config: forbidden commands, rollback advisory, mixed cli_style guard |
| UT-015 | unit/test_tool_layer.py | Tool dispatch: protocol/routing/operational tools, ping/traceroute CLI enforcement |
| UT-016 | unit/test_jira_tools.py | Jira tools: add_comment/resolve_issue success/error/no-key paths |
| UT-017 | unit/test_approval.py | Discord approval: request_approval (configured/not), poll results, expiry, env timeout override, post_approval_outcome |
| UT-018 | unit/test_config_approval_gate.py | push_config approval gate: no record, bad status (incl. SKIPPED), replay, device mismatch, success, EXECUTED marking |

### Integration Tests (read-only, real devices)
| ID | File | Description |
|----|------|-------------|
| IT-001 | integration/test_mcp_connectivity.py | MCP tool reachability (requires lab, skip with NO_LAB=1) |
| IT-002 | integration/test_watcher_events.py | Watcher event parsing without agent spawn (no lab required) |
| IT-003 | integration/test_mcp_tools.py | Full MCP tool coverage — all transports (RESTCONF/SSH), push_config CRUD (requires lab, skip with NO_LAB=1) |
| IT-004 | integration/test_transport.py | SSH/RESTCONF transport layer: structured output, _transport_used tag, timeouts (requires lab, skip with NO_LAB=1) |
| IT-005 | platform_tests/test_platform_coverage.py | Platform map coverage: all devices × all query categories (requires lab, skip with NO_LAB=1) |

## End-to-End Testing

E2E tests (On-Call scenarios) are performed manually.
See `testing/manual_testing.md` for the full manual test strategy.
