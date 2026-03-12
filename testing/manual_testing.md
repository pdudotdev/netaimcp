# aiNOC Manual Testing Strategy

End-to-end test scenarios for validating On-Call agent functionality.
Run these after significant codebase changes to confirm correct agent behavior.

---

## When to Run What

### Tier 1 — Core Regression (~2 min) | Run after every change

Run automated tests first:
```bash
cd /home/mcp/aiNOC/testing/agent-testing
./run_tests.sh unit         # run only unit tests
./run_tests.sh integration  # requires running lab
./run_tests.sh all          # run unit and integration
```

Then these manual scenarios:
- **WB-004** — Service Mode (primary deployment mode — always test in service mode)
- **OC-001** — Full On-Call Pipeline (Primary Setup + Deferred)

### Tier 2 — Targeted (~15 min) | Run when touching related code

- **WB-004** — Watcher Behavior edge cases (service mode sub-scenarios not covered in Tier 1)

---

## Prerequisites

- Lab is up (`sudo clab redeploy -t AINOC-TOPOLOGY.yml`) for each test
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
cd /home/mcp/aiNOC
python3 oncall/watcher.py
```

Also monitor `/var/log/network.json`:
```bash
tail -f /var/log/network.json
```

Monitor the watcher log in another terminal:
```bash
tail -f /home/mcp/aiNOC/logs/oncall_watcher.log
```

---

### OC-001 — Full On-Call Pipeline (SLA Failure → Diagnosis → Fix → Deferred Documentation)

**Tests**: Full watcher pipeline, agent investigation, fix verification, deferred documentation, Jira documentation

Run this test manually for Tier 1 regression and full pipeline validation.

---

#### OSPF Passive Interface Break (A1C)

**SLA Path**: `A1C_TO_IAN` | **Break device**: A1C | **SLA source**: A1C (172.20.20.205)
**Implicit**: A1C has a second SLA probe (SLA 2) that also fires — validates deferred documentation with concurrent failures

##### Setup (break)

First, identify A1C's OSPF interface(s) toward the core (C1C/C2C). Verify with:
```
get_ospf("A1C", "interfaces")
```
Note the interface name(s) where C1C and C2C neighbors are seen.

Push via `push_config` to A1C (adjust interface name as needed):
```
router ospf 1
  passive-interface <A1C_interface_toward_core>
```
(Making the OSPF-facing interface passive drops both Area 1 adjacencies — C1C and C2C neighbors lost.)

##### Verify break

From A1C:
```
show ip ospf neighbor
```
Expected: C1C and C2C **absent**.

From A1C:
```
show ip route 10.0.0.26
```
Expected: Route to E1C loopback `10.0.0.26` **absent** (no inter-area routes without ABR adjacency).

##### Check /var/log/network.json

Two IP SLA paths fail as a result of the misconfiguration:
```
{"device":"172.20.20.205","facility":"local7","msg":"BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down","severity":"info","ts":"2026-03-01T07:26:05.065Z"}
{"device":"172.20.20.205","facility":"local7","msg":"BOM%TRACK-6-STATE: 2 ip sla 2 reachability Up -> Down","severity":"info","ts":"2026-03-01T07:26:09.841Z"}
```

##### Check logs/oncall_watcher.log

Agent starts working on the first failure (reported by A1C):
```
[2026-03-01 07:26:06 UTC] Agent invoked for event on A1C: BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down
```
Claude Code session opens automatically in the terminal where `oncall/watcher.py` runs.

##### Expected agent behavior

1. Reads `skills/oncall/SKILL.md`
2. Looks up `A1C_TO_IAN` in `sla_paths/paths.json` → scope: A1C, C1C, C2C, E1C, E2C, IAN
3. Traceroutes from A1C (source 10.1.1.5) to `200.40.40.2` → fails at first hop (A1C has no route)
4. Reads `skills/ospf/SKILL.md`
5. Calls `get_ospf(A1C, "neighbors")` → C1C and C2C missing
6. Calls `get_ospf(A1C, "interfaces")` → shows `passive` on the core-facing interface
7. Proposes removing passive-interface on A1C
8. Requests operator approval via Discord (posts embed with ✅/❌ reactions)
9. Applies fix, verifies A1C route to 10.0.0.26 returns
10. Documents the issue to the Jira ticket (if Jira is configured)

**NOTE: Keep the session open and see Deferred Queue steps below after verifying the fix!**

##### Verify fix

From A1C:
```
show ip ospf neighbor
```
Expected: C1C and C2C FULL.

In `/var/log/network.json`:
```
{"device":"172.20.20.205","facility":"local7","msg":"BOM%TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up","severity":"info","ts":"2026-03-01T07:33:45.102Z"}
```

From A1C:
```
show ip route 10.0.0.26
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
  no passive-interface <A1C_interface_toward_core>
```

---

#### Deferred Failure Documentation

**Purpose**: Validate that concurrent SLA events during an active session are documented to Jira and Discord after the session ends.

**Reason**: The setup above breaks at least two SLA paths at once. The agent is invoked for the **first failure only**. If a second failure occurs during the investigation of the first, the watcher logs it as SKIPPED — no second agent session is spawned.

11. After the agent session completes (auto-exits in print mode), verify in `logs/oncall_watcher.log`:
```
SKIPPED (deferred - occurred during active session) - A1C (172.20.20.205): BOM%TRACK-6-STATE: 2 ip sla 2 reachability Up -> Down
Documenting 1 deferred failure(s) to Jira/Discord
Deferred failures documented to Jira ticket <key>
Deferred failures posted to Discord
Resuming monitoring.
```
12. Verify Jira: original ticket has a new comment titled "Deferred SLA Failures" listing the concurrent events
13. Verify Discord: an orange informational embed "⚠️ Deferred SLA Failures" appears in the channel with the event list

---

---

## Watcher Behavior Validation

These checks can be done without breaking lab config.

### WB-004 — tmux Session + Session Logging ★ Primary Mode

**This is the only mode. Always verify this first.**

The watcher always runs Claude in tmux + print mode (`-p`). Claude auto-exits when done. No interactive CLI or `--service` flag.

#### A) Manual invocation (dev/testing)

Start the watcher:
```bash
python3 oncall/watcher.py
```

Inject an SLA Down event:
```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.205","msg":"%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down"}' | sudo tee -a /var/log/network.json
```

Verify:
1. A tmux session named `oncall-<timestamp>` is created: `tmux list-sessions | grep oncall`
2. `logs/oncall_watcher.log` shows: `Agent invoked in tmux session: oncall-<timestamp>` and `Session log: logs/session-oncall-<timestamp>.md`
3. A notification is written to all open terminals and a desktop popup appears (if `notify-send` is available)
4. Agent completes and auto-exits — **no `/exit` needed**
5. Watcher resumes monitoring: `Agent session ended.` then `Resuming monitoring.` in log, no dangling lock file
6. Session log exists and contains agent output: `cat logs/session-oncall-<timestamp>.md`
7. tmux session is **killed** after cleanup — session log preserves all output for post-incident review

#### B) Systemd service

```bash
sudo systemctl status oncall-watcher.service
```
Expected: `Active: active (running)` and `ExecStart` shows `watcher.py` (no `--service` flag).

To restart after code changes:
```bash
sudo systemctl restart oncall-watcher.service
sudo journalctl -u oncall-watcher -f
```

#### C) Deferred documentation

Run the OC-001 break scenario (passive-interface on A1C) to generate concurrent SLA failures.
Verify:
1. First failure → agent in `oncall-<ts>` tmux session, auto-exits when done
2. Second failure → logged as `SKIPPED (deferred)` in watcher log
3. After first session → watcher logs `Documenting N deferred failure(s) to Jira/Discord` then `Resuming monitoring.`
4. No second tmux session spawned — deferred failures documented via Jira comment + Discord embed only

#### D) SSH retry transparency

If a transient SSH hiccup occurs during an on-call session, verify in `logs/oncall_watcher.log`:
```
SSH attempt 1/3 failed for <device_ip>: ... — retrying in 2s
```
The agent should recover automatically without reporting an error to the user.

---

---

## Case Documentation Checks

After any On-Call test run (Jira must be configured):

1. **Jira ticket updated with findings**:
   Check the Jira ticket (SUP project) for a comment with the full case structure from `case_format.md`.

2. **Case comment contains required fields**:
   All fields described in `cases/case_format.md` are present: Commands Used, Proposed Fixes, Verification.

3. **Lessons learned** (check if `cases/lessons.md` was updated - not always the case, the agent decides).
