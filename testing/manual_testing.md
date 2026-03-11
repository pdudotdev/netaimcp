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
tail -f /home/mcp/mcp-project/logs/oncall_watcher.log
```

---

### OC-001 — Full On-Call Pipeline (SLA Failure → Diagnosis → Fix → Deferred Queue)

**Tests**: Full watcher pipeline, agent investigation, fix verification, deferred queue, Jira documentation

Run this test manually for Tier 1 regression and full pipeline validation.

---

#### OSPF Passive Interface Break (A1C)

**SLA Path**: `A1C_TO_IAN` | **Break device**: A1C | **SLA source**: A1C (172.20.20.205)
**Implicit**: A1C has a second SLA probe (SLA 2) that also fires — validates deferred queue with concurrent failures

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
8. Asks user approval (displayed in the agent session)
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

#### Recovered Path Handling

**Purpose**: Validate the 2-option prompt when a deferred path has already recovered by the time it's investigated.

After the first case is resolved and the deferred session starts:
- If the deferred path has recovered (traceroute completes, interfaces up, neighbors present), the agent must present:
  ```
  A) Skip — path recovered, no action needed
  B) Investigate anyway — run full diagnostics despite recovery
  ```
- Pick **A**: verify the agent says "Path recovered, skipping." and immediately returns to the remaining deferred failures list (no Jira update, no lessons evaluation for this item)
- Pick **B**: verify the agent proceeds with full Step 2.5 diagnostics

---

#### Deferred Queue Handling

**Purpose**: Validate that concurrent SLA events during an active session are deferred and surfaced in a follow-up review session.

**Reason**: The setup above breaks at least two SLA paths at once. The agent is invoked for the **first failure only**. If a second failure occurs during the investigation of the first, the watcher skips it — this prevents agent storms during outages.

11. After the fix for the first failure is applied and documentation written, type `/exit`
12. Check second event logged as `SKIPPED (deferred - occurred during active session)` in `logs/oncall_watcher.log`:
```
[2026-03-01 07:53:52 UTC] SKIPPED (deferred - occurred during active session) - A1C (172.20.20.205): BOM%TRACK-6-STATE: 2 ip sla 2 reachability Up -> Down
```
13. After first agent session closes, a **second agent session** opens automatically with the deferred review prompt:
```
During the previous On-Call session the following SLA path failures were detected but could not be investigated at the time (logged as SKIPPED in logs/oncall_watcher.log):

1. A1C (172.20.20.205): BOM%TRACK-6-STATE: 2 ip sla 2 reachability Up -> Down (at 2026-03-01T07:26:09.841Z)

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

### WB-004 — Service Mode (tmux Session) ★ Primary Mode

**This is the primary production deployment mode. Always verify this first.**

The watcher is installed as a systemd service (`oncall-watcher.service`) which passes `--service` to
`watcher.py`. In service mode, every agent session runs in a detached tmux window so the watcher
process is never blocked by user interaction.

#### A) Manual invocation (dev/testing)

Start the watcher manually in service mode:
```bash
python3 oncall/watcher.py --service
```

Expected at startup: `Watcher started in SERVICE mode` in `logs/oncall_watcher.log`.

Inject an SLA Down event:
```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.205","msg":"%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down"}' | sudo tee -a /var/log/network.json
```

Verify:
1. A tmux session named `oncall-*` is created: `tmux list-sessions | grep oncall`
2. `logs/oncall_watcher.log` shows: `Agent invoked in tmux session: oncall-<timestamp>`
3. A notification is written to all open terminals and a desktop popup appears (if `notify-send` is available)
4. Attach to the session: `tmux attach -t oncall-<timestamp>`
5. Agent session is running with the SLA failure prompt
6. **Scrollback**: press `Ctrl+B` then `[` to enter scroll mode (arrow keys or mouse scroll), `q` to exit scroll mode
7. Type `/exit` in the agent session — tmux session closes
8. Watcher resumes monitoring: `Agent session ended.` in log, no dangling lock file

#### B) Systemd service

```bash
sudo systemctl status oncall-watcher.service
```
Expected: `Active: active (running)` and `ExecStart` shows `watcher.py --service`.

To restart after code changes:
```bash
sudo systemctl restart oncall-watcher.service
sudo journalctl -u oncall-watcher -f
```

#### C) Deferred queue in service mode

Run the OC-001 break scenario (passive-interface on A1C) to generate concurrent SLA failures.
Verify:
1. First failure → agent in `oncall-<ts>` tmux session
2. Second failure → logged as `SKIPPED (deferred)` in watcher log
3. After first session closes → deferred review in `oncall-deferred-<ts>` tmux session
4. User presented with list of deferred failures, options to investigate or `/exit`

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
