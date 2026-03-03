# aiNOC Manual Testing Strategy

End-to-end test scenarios for validating Standalone and On-Call agent functionality.
Run these after significant codebase changes to confirm correct agent behavior.

---

## When to Run What

### Tier 1 — Core Regression (~40 min) | Run after every change

Run automated tests first:
```bash
cd /home/mcp/mcp-project/testing/agent-testing
./run_tests.sh unit
./run_tests.sh integration  # requires running lab
```

Then these manual scenarios:
- **ST-001A** — OSPF Timer Mismatch (EOS)
- **ST-002** — EIGRP Passive Interface
- **ST-003** — Redistribution Break
- **ST-006** — BGP Timer Mismatch
- **OC-001** — Full On-Call Pipeline (Primary Setup)

### Tier 2 — Extended Coverage (~40 min) | Run for significant changes

- **ST-001B** — OSPF Timer Mismatch (RouterOS) — same pattern, different vendor
- **ST-005** — EIGRP Stub/Summary Misconfiguration
- **ST-007** — OSPF Area Type Change (multi-device)
- **MW-001** — Maintenance Window Blocking

### Tier 3 — Targeted (~15 min) | Run when touching related code

- **ST-004** — PBR Investigation (diagnostic only — no fix applied)
- **WB-001–003** — Watcher Behavior (partially covered by UT-001 + IT-002)

---

## Prerequisites

- Lab is up (`sudo clab redeploy -t lab.yml`) for each test
- All devices reachable (verify with `./run_tests.sh integration`)
- MCP server running or accessible (check with `claude mcp list`)

---

## Standalone Mode Tests

These tests validate the agent's diagnostic and remediation workflow when a user
submits a network problem description directly at the Claude Code prompt.

Launch with:
```bash
cd /home/mcp/mcp-project
claude
```

---

### ST-001 — OSPF Timer Mismatch (Multi-Vendor)

**Protocol**: OSPF | **Symptom**: Adjacency down due to dead-interval mismatch

Run at least **Variant A** for Tier 1; run **both** for release validation.

#### Variant A — R1A (Arista EOS)

**Device**: R1A (Arista EOS)

##### Setup (break)

Connect to R1A via SSH and apply:
```
interface Ethernet3
  ip ospf dead-interval 7
interface Ethernet4
  ip ospf dead-interval 7
```

##### Verify break

From R1A:
```
show ip ospf neighbor
```
Expected: R2C and R3C are **absent** from Area 0 neighbors (Ethernet3/Ethernet4).

##### Agent prompt
```
OSPF adjacencies are down on R1A. R1A shows no OSPF neighbors in Area 0. Please investigate.
```

##### Expected agent behavior

1. Reads `skills/ospf/SKILL.md`
2. Calls `get_ospf(R1A, "neighbors")` → no Area 0 neighbors
3. Calls `get_ospf(R1A, "interfaces")` → dead-interval 7 on Ethernet3/Ethernet4
4. Identifies timer mismatch (EOS default dead-interval = 40s)
5. Proposes removing the dead-interval override on R1A Ethernet3 and Ethernet4
6. Asks user approval before applying
7. Applies fix, verifies R2C and R3C return to FULL state

##### Verify fix

```
show ip ospf neighbor
```
Expected: R2C and R3C present, state FULL.

##### Teardown (if agent did not fix)

```
interface Ethernet3
  no ip ospf dead-interval
interface Ethernet4
  no ip ospf dead-interval
```

---

#### Variant B — R18M (MikroTik RouterOS)

**Devices**: R18M, R20M (both MikroTik RouterOS)

##### Setup (break)

SSH to R18M and set a non-default hello interval:
```
/routing ospf interface-template set [find] hello-interval=5s
```

Or via REST API:
```json
{"method": "PATCH", "path": "/rest/routing/ospf/interface-template/<id>", "body": {"hello-interval": "5s"}}
```

##### Verify break

From R18M:
```
/routing ospf neighbor print
```
Expected: R20M absent (dead-interval mismatch prevents adjacency).

##### Agent prompt
```
OSPF adjacency between R18M and R20M is down. R20M cannot reach prefixes advertised by R18M. Please investigate.
```

##### Expected agent behavior

1. Reads `skills/ospf/SKILL.md`
2. Calls `get_ospf(R18M, "neighbors")` → R20M absent
3. Calls `get_ospf(R18M, "interfaces")` → hello-interval 5s (non-default)
4. Calls `get_ospf(R20M, "interfaces")` → hello-interval 10s (default)
5. Identifies R18M as the misconfigured side (RouterOS defaults: hello 10s / dead 40s)
6. Proposes resetting R18M hello-interval to default via REST PATCH
7. Asks approval, applies, verifies adjacency returns

##### Teardown (if agent did not fix)

Reset R18M hello-interval to default:
```json
{"method": "PATCH", "path": "/rest/routing/ospf/interface-template/<id>", "body": {"hello-interval": "10s"}}
```

---

### ST-002 — EIGRP Passive Interface (R8C)

**Protocol**: EIGRP | **Device**: R8C (Cisco IOS) | **Symptom**: Neighbor down

#### Setup (break)

SSH to R8C and apply:
```
router eigrp 20
  passive-interface Ethernet0/3
```

#### Verify break

From R8C:
```
show ip eigrp neighbors
```
Expected: R9C is **absent**.

From R9C:
```
show ip eigrp neighbors
```
Expected: R8C is **absent**.

#### Agent prompt
```
R9C has lost EIGRP connectivity. R9C cannot reach any OSPF-learned destinations. Please investigate.
```

#### Expected agent behavior

1. Reads `skills/eigrp/SKILL.md`
2. Calls `get_eigrp(R8C, "neighbors")` → no neighbors
3. Calls `get_eigrp(R8C, "interfaces")` → Ethernet0/3 is passive
4. Proposes removing passive-interface Ethernet0/3 on R8C
5. Asks approval, applies, verifies R9C neighbor returns FULL

#### Verify fix

```
show ip eigrp neighbors
```
On R8C: R9C present. On R9C: R8C present.

#### Teardown (if agent did not fix)

```
router eigrp 20
  no passive-interface Ethernet0/3
```

---

### ST-003 — Redistribution Break (R3C)

**Protocol**: Redistribution | **Device**: R3C (Cisco IOS) | **Symptom**: Routes missing

#### Setup (break)

SSH to R3C and remove OSPF→EIGRP redistribution:
```
router eigrp 10
  no redistribute ospf 1 route-map OSPF-TO-EIGRP
```

#### Verify break

From R4C:
```
show ip route
```
Expected: No `D EX` routes for `172.16.0.0/24` (OSPF Area 2 subnet) or other OSPF-originated prefixes.

#### Agent prompt
```
R4C is missing routes to the 172.16.0.0/24 subnet (Area 2 stub network). Please investigate.
```

#### Expected agent behavior

1. Reads `skills/redistribution/SKILL.md`
2. Calls `get_eigrp` and `get_ospf` tools
3. Calls `get_routing(R4C, "172.16.0.0/24")` → route missing
4. Calls `get_routing_policies(R3C, "redistribution")` → redistribute statement absent
5. Proposes restoring: `redistribute ospf 1 metric 1000 1 255 1 1500` under `router eigrp 10`
6. Asks approval, applies, verifies route returns on R4C

#### Verify fix

From R4C:
```
show ip route 172.16.0.0
```
Expected: `D EX 172.16.0.0/24` present.

#### Teardown (if agent did not fix)

```
router eigrp 10
  redistribute ospf 1 metric 1000 1 255 1 1500
```

---

### ST-004 — Policy-Based Routing Investigation (R8C)

**Protocol**: Routing Policy | **Device**: R8C (Cisco IOS) | **Symptom**: Traffic from R9C to 2.2.2.66 follows asymmetric path

**Tier 3** — Diagnostic only, no fix applied.

#### Setup (break)

SSH to R8C and apply PBR configuration:
```
ip access-list extended 100
 10 permit ip host 192.168.20.2 host 2.2.2.66
route-map ACCESS-R2-LO permit 10
 match ip address 100
 set ip next-hop 10.1.1.6
interface Ethernet0/3
 ip policy route-map ACCESS-R2-LO
```

**NOTE:** This configuration is already default on R8C in this lab.

#### Verify break

From R9C toward R2A loopback:
```
traceroute 2.2.2.66
```
Expected: Path goes through `10.1.1.6` (R7A), not R6A.

#### Agent prompt

```
Why are R9C's packets destined for 2.2.2.66 forwarded by R8C to R7A every time?
```

#### Expected agent behavior

1. Reads routing policy skills
2. Calls `get_routing(R8C, "2.2.2.66")` → shows normal ECMP paths (R6A 10.1.1.2 and R7A 10.1.1.6 equal cost)
3. Calls `get_routing_policies(R8C, "route_maps")` → finds `ACCESS-R2-LO` with `set ip next-hop 10.1.1.6`
4. Calls `get_routing_policies(R8C, "access_lists")` → finds ACL 100 matching host 192.168.20.2 → host 2.2.2.66
5. Identifies PBR on Et0/3 overriding normal routing decisions
6. Correctly diagnoses root cause with explanation of ACL match and next-hop override

#### Verify (diagnostic only)

Agent correctly identified:
- PBR as root cause
- The specific ACL and route-map involved
- The forced next-hop (10.1.1.6 = R7A)

#### Teardown

N/A

---

### ST-005 — EIGRP Stub/Summary Misconfiguration (R9C)

**Protocol**: EIGRP | **Device**: R9C (Cisco IOS) | **Symptom**: Individual loopback /24 routes advertised instead of /22 summary

#### Setup (break)

SSH to R9C and change stub from `connected summary` to `connected`:
```
router eigrp 20
  eigrp stub connected
```

#### Verify break

From R1A:
```
show ip route | include 9.9
```
Expected: Three separate `O E1 9.9.x.0/24` entries visible instead of a single `O E1 9.9.0.0/22`.

#### Agent prompt

```
Why are all routers in the network (e.g. R1A) showing individual routes to R9C's loopbacks.
Check this and give me some solutions.
```

#### Expected agent behavior

1. Reads `skills/eigrp/SKILL.md`
2. Calls `get_routing()` and/or `get_routing_policies`
3. Calls `get_eigrp(R9C, "config")` → finds `eigrp stub connected` (no `summary` keyword)
4. Calls `get_eigrp(R9C, "interfaces")` → identifies summary-address on Et0/1
5. Identifies conflict: stub `connected` without `summary` overrides and advertises individual connected routes
6. Presents multiple fix options (change stub to include `summary`, modify interface summary, summarize at R8C, etc.)
7. User selects option that configures `eigrp stub summary` on R9C
8. Applies fix, verifies /22 summary now present and individual /24s suppressed on R1A

#### Verify fix

```
show ip route | include 9.9
```
Expected: Single `O E1 9.9.0.0/22` present.

#### Teardown (if agent did not fix)

```
router eigrp 20
  eigrp stub connected summary
```

---

### ST-006 — BGP Timer Mismatch → Default Route Lost (R2C)

**Protocol**: BGP | **Device**: R2C (Cisco IOS) | **Symptom**: BGP sessions flapping, default route missing

#### Setup (break)

SSH to R2C and apply non-default BGP timers:
```
router bgp 1010
  neighbor 200.40.40.2 timers 3 9
  neighbor 200.50.50.2 timers 3 9
```

#### Verify break

From R2C:
```
show ip bgp summary
```
Expected: ISP_A and ISP_B neighbors in Idle/Active state (session flapping due to timer mismatch with ISP peers).

From R3C or R4C:
```
show ip route 0.0.0.0
```
Expected: Default route absent or unstable.

#### Agent prompt
```
R2C is losing its BGP sessions to both ISP_A and ISP_B. Default route is flapping or absent on downstream devices. Please investigate.
```

#### Expected agent behavior

1. Reads `skills/bgp/SKILL.md`
2. Calls `get_bgp(R2C, "summary")` → neighbors in Idle/Active
3. Calls `get_bgp(R2C, "config")` → identifies `timers 3 9` (non-default)
4. BGP default timers: keepalive 60s / hold-time 180s; ISP peers use defaults
5. Proposes removing non-default timers: `no neighbor 200.40.40.2 timers` and `no neighbor 200.50.50.2 timers`
6. Asks approval, applies, verifies sessions return to Established
7. Verifies default route returns on downstream devices

#### Teardown (if agent did not fix)

```
router bgp 1010
  no neighbor 200.40.40.2 timers
  no neighbor 200.50.50.2 timers
```

---

### ST-007 — OSPF Area 1 Type Change → External Routes Lost (R2C + R6A)

**Protocol**: OSPF | **Devices**: R2C (Cisco IOS), R6A (Arista EOS) | **Symptom**: External routes missing in Area 1

#### Setup (break)

SSH to R2C and change Area 1 from NSSA to normal:
```
router ospf 1
  no area 1 nssa
```

#### Verify break

From R6A:
```
show ip route
```
Expected: External routes (type O E1 or O N1) for EIGRP-redistributed prefixes are **absent** from R6A's routing table.

From R9C:
```
show ip route 172.16.0.0
```
Expected: Route to Area 2 prefix absent (inter-area route cascade failure).

#### Agent prompt
```
R6A and R9C have lost external routes. OSPF routes to EIGRP-side prefixes (192.168.x.x) and inter-area routes are missing. Please investigate.
```

#### Expected agent behavior

1. Reads `skills/ospf/SKILL.md`
2. Reads INTENT.json → Area 1 intended type: NSSA
3. Calls `get_ospf(R2C, "config")` → Area 1 shows no NSSA configuration (changed to normal)
4. Calls `get_ospf(R6A, "config")` → R6A still configured as NSSA; mismatch detected
5. R2C is the ABR → the config was removed from R2C; R2C deviates from intent
6. Proposes restoring `area 1 nssa` on R2C (the ABR side is the authoritative side)
7. Asks approval, applies, verifies external routes return on R6A and R9C

#### Teardown (if agent did not fix)

```
router ospf 1
  area 1 nssa
```

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
tail -f /home/mcp/mcp-project/oncall_watcher.log
```

---

### OC-001 — Full On-Call Pipeline (SLA Failure → Diagnosis → Fix → Deferred Queue)

**Tests**: Full watcher pipeline, agent investigation, fix verification, deferred queue, Jira documentation

Run the **Primary Setup** for Tier 1 regression and full pipeline validation.

---

#### Primary Setup — OSPF Passive Interface Break (R3C)

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

##### Check oncall_watcher.log

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

**Reason**: Both setups above break two SLA paths at once. The agent is invoked for the **first failure only**. If a second failure occurs during the investigation of the first, the watcher skips it — this prevents agent storms during outages.

11. After the fix for the first failure is applied and documentation written, type `/exit`
12. Check second event logged as `SKIPPED (deferred - occurred during active session)` in `oncall_watcher.log`:
```
[2026-02-25 07:53:52 UTC] SKIPPED (deferred - occurred during active session) - R9C (172.20.20.209): BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down
```
13. After first agent session closes, a **second agent session** opens automatically with the deferred review prompt:
```
During the previous On-Call session the following SLA path failures were detected but could not be investigated at the time (logged as SKIPPED in oncall_watcher.log):

1. R9C (172.20.20.209): BOM%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down (at 2026-02-25T07:26:09.841Z)

Would you like to investigate any of these? Reply with a number, 'all', or 'none'.
```
14. If multiple SLA path failures occurred during the initial investigation, they are all listed. The user can enter a number to investigate a specific one, `all`, or `/exit` to skip.
15. After the deferred review session closes, watcher resumes monitoring:
```
[Watcher] Deferred review session ended. Resuming monitoring
```

---

## Watcher Behavior Validation

These checks can be done without breaking lab config.

### WB-001 — Non-SLA Events Are Ignored

Inject a syslog message that is NOT an SLA Down event:
```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.201","msg":"%SYS-5-CONFIG_I: Configured from console"}' >> /var/log/network.json
```
Expected: Watcher does **not** invoke agent. Log shows no new `Agent invoked` entry.

### WB-002 — SLA Up (Recovery) Events Are Logged Without Agent Invocation

```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.204","msg":"%TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up"}' >> /var/log/network.json
```
Expected: **No agent invocation.** The watcher detects the Up event, logs a recovery entry,
and resumes monitoring without starting a Claude session.

In `oncall_watcher.log`:
```
SLA RECOVERY: <device-name> (172.20.20.204): %TRACK-6-STATE: 1 ip sla 1 reachability Down -> Up
```

Verify: no new `Agent invoked` entry appears in the log after the Up event.

### WB-003 — MikroTik Netwatch Event Detected

```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.218","msg":"netwatch,info event down [ type: simple, host: 10.0.0.1 ]"}' >> /var/log/network.json
```
Expected: Watcher **does** invoke agent (MikroTik format matched).

### WB-004 — Daemon Mode (tmux Session)

Start the watcher in daemon mode:
```bash
python3 oncall/watcher.py -d
```

Expected at startup: `Watcher started in DAEMON mode` in `oncall_watcher.log`.

Inject an SLA Down event:
```bash
echo '{"ts":"2026-01-01T00:00:00Z","device":"172.20.20.204","msg":"%TRACK-6-STATE: 1 ip sla 1 reachability Up -> Down"}' >> /var/log/network.json
```

Verify:
1. A tmux session named `oncall-*` is created: `tmux list-sessions | grep oncall`
2. `oncall_watcher.log` shows: `Agent invoked in tmux session: oncall-<timestamp>`
3. Attach to the session: `tmux attach -t oncall-<timestamp>`
4. Agent session is running with the SLA failure prompt
5. Type `/exit` in the agent session — tmux session closes
6. Watcher resumes monitoring: `Agent session ended.` in log and `oncall_watcher.log` shows no dangling lock

---

## Case Documentation Checks

After any On-Call test run (Jira must be configured):

1. **Jira ticket updated with findings**:
   Check the Jira ticket (SUP project) for a comment with the full case structure from `case_format.md`.

2. **Case comment contains required fields**:
   All fields described in `cases/case_format.md` are present: Commands Used, Proposed Fixes, Verification.

3. **Lessons learned** (check if `cases/lessons.md` was updated):

---

## Maintenance Window Policy

The agent must refuse config pushes outside the maintenance window defined in
`policy/MAINTENANCE.json` (UTC Mon–Fri 05:00–20:00).

### MW-001 — Change Blocked Outside Window

To test this, temporarily edit the maintenance window to exclude the current time
(or run this test after 20:00 UTC on a weekday / any time on weekend).

Apply a break, submit a Standalone prompt, and confirm:
- Agent diagnoses the issue correctly
- Agent proposes the fix
- When user approves, `push_config` returns an error about maintenance window
- Agent reports the block to the user without retrying

**Do not modify `MAINTENANCE.json` permanently** - restore after testing.
