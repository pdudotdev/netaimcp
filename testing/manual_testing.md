# aiNOC Manual Testing Strategy

End-to-end test scenarios for validating On-Call agent functionality.
Run these after significant codebase changes to confirm correct agent behavior.

---

## When to Run What

### Tier 1 — Core Regression (~2 min) | Run after every change

Run automated tests first:
```bash
cd /home/mcp/mcp-project/testing/agent-testing
./run_tests.sh unit         # run only unit tests
./run_tests.sh integration  # requires running lab
./run_tests.sh all          # run unit and integration
```

Then these manual scenarios:
- **OC-001** — Full On-Call Pipeline (Primary Setup + Deferred)

### Tier 2 — Targeted (~15 min) | Run when touching related code

- **WB-001–004** — Watcher Behavior (partially covered by UT-001 + IT-002)

---

## Prerequisites

- Lab is up (`sudo clab redeploy -t lab.yml`) for each test
- All devices reachable (verify with `./run_tests.sh integration`)
- MCP server running and accessible (check with `claude mcp list`)

---

---

## On-Call Mode Tests

These tests validate the full watcher → agent pipeline. The watcher monitors
`/var/log/network.json`, detects SLA Down events, and spawns a Claude agent session.

### Setup for all On-Call tests

In a separate terminal, start the watcher:
```bash
cd /home/mcp/mcp-project
python3 oncall/watcher.py
```

Also monitor `/var/log/network.json`:
```bash
tail -f /var/log/network.json
```

Monitor the watcher log in another terminal:
```bash
tail -f /home/mcp/mcp-project/logs/oncall_watcher.log
```

---

### OC-001 — Full On-Call Pipeline (SLA Failure → Diagnosis → Fix → Deferred Queue)

**Tests**: Full watcher pipeline, agent investigation, fix verification, deferred queue, Jira documentation

Run this test manually for Tier 1 regression and full pipeline validation.

---

#### OSPF Passive Interface Break (R3C)

**SLA Path**: `R4C_TO_R10C` | **Break device**: R3C | **SLA source**: R4C (172.20.20.204)
**Implicit**: `R9C_TO_R5C` also breaks — validates deferred queue with two concurrent failures

##### Setup (break)

SSH to R3C:
```
router ospf 1
  passive-interface Ethernet0/3
  passive-interface Ethernet1/0
```

##### Verify break

From R3C:
```
show ip ospf neighbor
```
Expected: R1A (via Ethernet0/3) **absent**. R2C (via Ethernet1/0) **absent**.

From R4C:
```
show ip route 10.10.10.10
```
Expected: Route to R10C loopback `10.10.10.10` **absent**.

##### Check /var/log/network.json

Two IP SLA paths fail as a result of the misconfiguration:
```
{"device":"172.20.20.204","facility":"local7","msg":"BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down","severity":"info","ts":"2026-02-25T07:26:05.065Z"}
{"device":"172.20.20.209","facility":"local7","msg":"BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down","severity":"info","ts":"2026-02-25T07:26:09.841Z"}
```

##### Check logs/oncall_watcher.log

Agent starts working on the first failure (reported by R4C):
```
[2026-02-25 07:26:06 UTC] Agent invoked for event on R4C: BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down
```
Claude Code session opens automatically in the terminal where `oncall/watcher.py` runs.

##### Expected agent behavior

1. Reads `skills/oncall/SKILL.md`
2. Looks up `R4C_TO_R10C` in `sla_paths/paths.json` → scope: R4C, R3C, R1A, R10C
3. Traceroutes from R4C to `10.10.10.10` → stops at R3C
4. Reads `skills/ospf/SKILL.md`
5. Calls `get_ospf(R3C, "neighbors")` → R1A missing
6. Calls `get_ospf(R3C, "config")` → passive-interface on Ethernet0/3 and Ethernet1/0
7. Proposes removing passive-interface on R3C Ethernet0/3 and Ethernet1/0
8. Asks user approval (displayed in the agent session)
9. Applies fix, verifies R4C route to 10.10.10.10 returns
10. Documents the issue to the Jira ticket (if Jira is configured)

**NOTE: Keep the session open and see Deferred Queue steps below after verifying the fix!**

##### Verify fix

From R3C:
```
show ip ospf neighbor
```
Expected: R1A and R2C FULL.

In `/var/log/network.json`:
```
{"device":"172.20.20.204","facility":"local7","msg":"BOM%TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up","severity":"info","ts":"2026-02-25T07:33:45.102Z"}
```

From R4C:
```
show ip route 10.10.10.10
show ip sla statistics
```
Expected: Route present; latest operation return code: OK.

##### Documentation check

- Jira ticket updated with findings and resolution (if Jira is configured)
- `Verification: PASSED`
- `Case Status: FIXED`

##### Teardown (if agent did not fix)

```
router ospf 1
  no passive-interface Ethernet0/3
  no passive-interface Ethernet1/0
```

---

#### Deferred Queue Handling

**Purpose**: Validate that concurrent SLA events during an active session are deferred and surfaced in a follow-up review session.

**Reason**: The setup above breaks at least two SLA paths at once. The agent is invoked for the **first failure only**. If a second failure occurs during the investigation of the first, the watcher skips it — this prevents agent storms during outages.

11. After the fix for the first failure is applied and documentation written, type `/exit`
12. Check second event logged as `SKIPPED (deferred - occurred during active session)` in `logs/oncall_watcher.log`:
```
[2026-02-25 07:53:52 UTC] SKIPPED (deferred - occurred during active session) - R9C (172.20.20.209): BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down
```
13. After first agent session closes, a **second agent session** opens automatically with the deferred review prompt:
```
During the previous On-Call session the following SLA path failures were detected but could not be investigated at the time (logged as SKIPPED in logs/oncall_watcher.log):

1. R9C (172.20.20.209): BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down (at 2026-02-25T07:26:09.841Z)

Would you like to investigate any of these? Reply with a number, 'all', or 'none'.
```
14. If multiple SLA path failures occurred during the initial investigation, they are all listed. The user can enter a number to investigate a specific one, `all`, or `/exit` to skip.
15. After the deferred review session closes, watcher resumes monitoring:
```
[Watcher] Deferred review session ended. Resuming monitoring
```

---

---

## Watcher Behavior Validation

These checks can be done without breaking lab config.

### WB-001 — Non-SLA Events Are Ignored

Inject a syslog message that is NOT an SLA Down event:
```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.201","msg":"%SYS-5-CONFIG_I: Configured from console"}' | sudo tee -a /var/log/network.json
```
Expected: Watcher does **not** invoke agent. Log shows no new `Agent invoked` entry.

### WB-002 — SLA Up (Recovery) Events Are Logged Without Agent Invocation

```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.204","msg":"%TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up"}' | sudo tee -a /var/log/network.json
```
Expected: **No agent invocation.** The watcher detects the Up event, logs a recovery entry,
and resumes monitoring without starting a Claude session.

In `logs/oncall_watcher.log`:
```
SLA RECOVERY: <device-name> (172.20.20.204): %TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up
```

Verify: no new `Agent invoked` entry appears in the log after the Up event.

### WB-003 — MikroTik Netwatch Event Detected

```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.218","msg":"netwatch,info event down [ type: simple, host: 10.0.0.1 ]"}' | sudo tee -a /var/log/network.json
```
Expected: Watcher **does** invoke agent (MikroTik format matched).

### WB-004 — Service Mode (tmux Session)

Start the watcher in service mode:
```bash
python3 oncall/watcher.py --service
```

Expected at startup: `Watcher started in SERVICE mode` in `logs/oncall_watcher.log`.

Inject an SLA Down event:
```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.204","msg":"%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down"}' | sudo tee -a /var/log/network.json
```

Verify:
1. A tmux session named `oncall-*` is created: `tmux list-sessions | grep oncall`
2. `logs/oncall_watcher.log` shows: `Agent invoked in tmux session: oncall-<timestamp>`
3. A `wall` broadcast message appears on your terminal with the session name and attach command
4. Attach to the session: `tmux attach -t oncall-<timestamp>`
4. Agent session is running with the SLA failure prompt
5. Type `/exit` in the agent session — tmux session closes
6. Watcher resumes monitoring: `Agent session ended.` in log and `logs/oncall_watcher.log` shows no dangling lock

---

---

## Case Documentation Checks

After any On-Call test run (Jira must be configured):

1. **Jira ticket updated with findings**:
   Check the Jira ticket (SUP project) for a comment with the full case structure from `case_format.md`.

2. **Case comment contains required fields**:
   All fields described in `cases/case_format.md` are present: Commands Used, Proposed Fixes, Verification.

3. **Lessons learned** (check if `cases/lessons.md` was updated - not always the case, the agent decides).
