---
name: On-Call SLA Troubleshooting
description: "SLA path failure workflow — read sla_paths.json, traceroute-first localization, ECMP handling, protocol triage"
---

# On-Call SLA Troubleshooting Skill

## Scope
On-Call mode investigation guide — reading sla_paths.json, traceroute-first localization, ECMP handling, protocol triage order.

### Terminology
- **Primary On-Call session**: Triggered directly by a new SLA failure event. Full workflow: Steps 0 through 3, session closure, Jira, lessons. Runs in non-interactive print mode — exits autonomously after presenting the summary.
- **Deferred failures**: SLA Down events that arrive while a primary session is active. After the session ends, `watcher.py` documents them automatically (Jira comment + Discord embed). No second agent session is spawned.

> **Before starting**: Read `cases/lessons.md` per CLAUDE.md guidelines — past lessons often shortcut diagnosis.

---

## Step 0: Read the sla_paths.json Entry for the Failed Path

Use the **Read** tool to read the file `sla_paths/paths.json` (this is a local file — do NOT use `readMcpResource`).

Locate the path entry matching the source device from the log event. Extract these key fields:

- **`source_device`**: the device that generated the SLA failure event
- **`destination_ip`**: IP being pinged by the SLA
- **`scope_devices`**: ALL devices you may need to investigate
- **`ecmp`**: if true, TWO paths exist — both must be checked
- **`ecmp_node`**: the device where the path splits
- **`ecmp_next_hops`**: the two next-hop devices after the split

---

## Step 1: Traceroute from Source Device (Always First)

If `source_ip` is available in the paths.json entry, always pass it:

```
traceroute(device=<source_device>, destination=<destination_ip>, source=<source_ip>)
```

Using `source_ip` forces the traceroute onto the monitored path. If the source interface is down, the traceroute fails immediately at the source device — correctly localizing the issue without alternate-path confusion.

**MANDATORY scope check — do this before applying any outcome below:**

Compare EVERY hop in the traceroute output against the `scope_devices` list from Step 0. Resolve IP addresses to device names using the inventory or context you already have. If ANY intermediate hop is a device NOT in `scope_devices`, this is an **off-path transit** — even if the traceroute reached the destination. The path is using an alternate route, NOT the monitored path. Apply the third outcome below.

Do NOT treat a completed traceroute as "successful" if it transited an off-scope device.

Read the output:

- **Path stops at hop N (or fails at source)**: issue is on or before that hop → proceed to Step 2.5
- **Timeout at first hop**: issue is on the source device itself (interface down, OSPF/BGP neighbor lost, no default route) → proceed to Step 2.5
- **Path transits a device NOT in scope_devices**: routing anomaly on the last in-scope hop. Do NOT investigate the off-path device. Identify the last hop that IS in scope_devices, run `get_routing(<that_device>, prefix=<destination_ip>)` to confirm it is routing toward the off-path device. Whether the route is present or absent, treat that in-scope device as the breaking hop and proceed immediately to Step 2.5.
- **Full path to destination AND all hops within scope_devices**: do NOT conclude "transient" yet — go to Step 1a

### Step 1a: Source-Device Sanity Check (when traceroute succeeds)

Even if the traceroute completes, the SLA was triggered for a reason. Verify the source device's local state with exactly two queries:

```
get_interfaces(device=<source_device>)
get_ospf(device=<source_device>, query="neighbors")   ← run on source_device, NOT the next-hop
```

> **Critical**: Always query routing protocol neighbors on the **source_device** first. Querying the next-hop device may show healthy adjacencies even when the source-side interface is down.

**Branch A — Traceroute completed, source state healthy** (source interface Up/Up AND source device's expected routing neighbors present AND all traceroute hops within scope_devices):

A completed traceroute does NOT automatically mean the path is recovered. The SLA may have recovered via a **failover/alternate route** while the primary defined path still has a failure. Determine which case applies:

**Compare the observed traceroute hops against the expected path from Principle 1 (INTENT.json + paths.json):**

| Case | Traceroute Result | Action |
|------|-----------------|--------|
| **Truly transient** | Hops follow the expected path exactly (same transit devices as the expected path) | Present summary table below, log to Jira as transient/self-resolved (resolution="Won't Fix"), proceed to session closure |
| **Failover recovery** | Hops reach the destination but via different devices than the expected path (alternate ABR, alternate ISP, different next-hops) | Primary path still broken — treat the first device where the trace diverges from the expected path as the breaking hop. Proceed to Step 2.5 to investigate why traffic is bypassing the expected path |

Present this summary table (fill in actual values):

```
| Check | Result | Status |
|-------|--------|--------|
| Traceroute to <destination_ip> | Full path, all hops respond | ✓ |
| Source interface (<source_interface>) | Up/Up | ✓ |
| Source device routing neighbors | All expected neighbors present | ✓ |
| Path follows expected route | <Yes — transient / No — via <alternate_device> — investigate> | ✓/✗ |
```

**Branch B — Issue still present** (source interface down OR expected neighbor missing):

This is the root cause. Proceed directly to Step 2.5.

---

## Step 2: ECMP Handling

If the path entry has `"ecmp": true`, the traceroute shows ONE of the two paths. The other may also be broken.

1. **Both paths broken?** If the path still fails after a fix, re-run traceroute with `source=<source_ip>`. If it still fails or takes a different failing path, an independent failure exists on the alternate path — return to Step 1 with the new traceroute result.
2. **One path fixed — verify alternate:** `get_routing(ecmp_node, prefix=<destination>)` — expect 2 equal-cost entries. If only 1 entry, the alternate path is not restored.
3. **Path identification:** The SLA probe may use either ECMP path. Always use `source=<source_ip>` in traceroute to force the probe's perspective and avoid alternate-path confusion.

Proceed to Step 2.5 after identifying the breaking hop via traceroute. If the traceroute from Step 1 completed to the destination, at least one ECMP path is functional — then proceed to Step 2.5 to investigate the alternate path's devices if ECMP verification shows only one RIB entry.

---

## Step 2.5: Basic Operational Checks (Mandatory — Run Before Anything Else)

**A missing route on the breaking hop is NOT a reason to investigate other devices.**
It is a reason to check the breaking hop's own state first.

```
get_interfaces(device=<breaking_hop>)
get_ospf(device=<breaking_hop>, query="neighbors")    ← or get_bgp per Step 3 triage table
```

**Decision gate:**

| Result | Action |
|--------|--------|
| Interface down (admin or line-protocol) | Root cause found. Present findings table. Stop. |
| No neighbors / fewer neighbors than expected | Go directly to the **Adjacency Checklist** in the protocol skill. Do NOT investigate downstream devices. |
| All neighbors FULL, all interfaces Up/Up | Proceed to Step 3. Issue is in LSDB, RIB, or policy layer. |

> **Do not leave the breaking hop to investigate downstream devices in the path.**
> Missing adjacencies on the breaking hop explain missing routes everywhere downstream.
> Investigating downstream only confirms the problem cascaded — it never finds the root cause.
> Timer mismatch, passive interface, and area mismatch are caught in one query.

> **One fix per layer (Principle 7):** If the decision gate above identifies an interface-layer issue (admin-down, line-protocol down), propose **only** the interface fix — even if investigation also revealed higher-layer issues (missing BGP config, wrong route-maps, etc.). Verify first. If the SLA path is still broken after the interface fix, re-run traceroute and start a new investigation cycle for the next layer.

---

## Step 3: Protocol Triage — Which Skill to Read Next

Map the breaking hop to its protocol:

| Breaking Hop Device | Protocol to Investigate | Skill to Read |
|--------------------|------------------------|---------------|
| A1C, A2C (source) | OSPF Area 1 stub (to C1C or C2C ABR) | `skills/ospf/SKILL.md` |
| C1C, C2C | OSPF Area 0 core + ABR | `skills/ospf/SKILL.md` |
| E1C, E2C | OSPF Area 0 + BGP AS1010 + NAT | If OSPF neighbors down → `skills/ospf/SKILL.md`; if BGP to ISP down → `skills/bgp/SKILL.md`; NAT issue → `skills/routing/SKILL.md` |
| X1C | BGP AS2020 (to IAN + IBN) | `skills/bgp/SKILL.md` |
| IAN, IBN | BGP AS4040/AS5050 (ISP edge — fully managed) | `skills/bgp/SKILL.md` |

---

## Time Efficiency Rules

- **Localize first, don't investigate all**: traceroute narrows to 1-2 devices max before running protocol tools
- **ECMP: check both paths** before concluding the issue is fixed
- **Don't re-check devices that are not on the scope_devices list**: out-of-scope devices won't affect this SLA path
- **Non-scope hop in traceroute: stay in scope**: if traceroute exits scope_devices, do NOT query or investigate the off-path device. Find the last in-scope hop, run `get_routing` on it, then go to Step 2.5.
- **No route on breaking hop → check its neighbors, not downstream devices**: a missing route means "run Step 2.5 on this device now". Missing adjacencies on the breaking hop explain missing routes across the entire downstream path.
- **Step 2.5 before any protocol skill section**: zero neighbors is an adjacency problem (timers, passive, area, auth). Resolve it on the breaking hop before consulting LSDB, redistribution, or area-type sections.

---

## Presenting Findings

Always present your analysis summary in a Markdown table before proposing a fix:

| Finding | Detail | Status |
|---------|--------|--------|
| Traceroute result | Stopped at hop N — device X | ✗ |
| Interface / neighbor state | e.g. Ethernet3 admin down | ✗ |
| Root cause | Brief description | ✗ |

Use ✓ for healthy items and ✗ for the identified issues. This lets the user scan the summary instantly before approving any configuration change.

---

## Step 4: Approval, Remediation & Session Closure

After presenting findings, follow this sequence exactly:

1. **Call `assess_risk`** — `assess_risk(devices=<affected>, commands=<fix_commands>)`. Include the risk level in the findings table.

2. **Call `request_approval`** — `request_approval(issue_key, summary, findings, commands, devices, risk_level)`. This posts an approval embed to Discord (if configured) and writes an audit record that `push_config` requires before it will execute.

3. **Handle the return value:**

   | Decision | Action |
   |----------|--------|
   | `"approved"` | Proceed to push |
   | `"rejected"` | Call `post_approval_outcome(message_id=..., decision="rejected", decided_by=<username>)`, log to Jira, go to session closure |
   | `"expired"` | Call `post_approval_outcome(message_id=..., decision="expired")` to post expiry outcome to Discord. Log to Jira that the fix could not be applied (approval expired), then go to session closure. Never push. |
   | `"skipped"` | Discord not configured. The code-level gate blocks `push_config` (no APPROVED record). Log to Jira that no approval channel is configured and go to session closure. Never push. |

4. **NEVER call `push_config` without approval** — `push_config` enforces this at the code level and will return an error if no approved record exists or if the device list does not match the approval.

5. **After approval:** call `push_config(devices=..., commands=...)`, then verify the fix resolved the issue (run traceroute and/or `get_<protocol>` to confirm). Then call `post_approval_outcome(message_id=..., decision="approved", decided_by=<username>, verified=<True|False>, verification_detail=<brief_result>)`.

5a. **Push failure retry** — when `push_config` returns errors on one or more devices:
   - Diagnose the error. Common causes: wrong AS/area number, syntax error, transport failure.
   - For partial failures (some devices succeeded, some failed), scope the retry to only the failed devices.
   - Call `post_approval_outcome(message_id=..., decision="approved", decided_by=<username>, verified=False, verification_detail="push failed: <brief error>")` for the failed attempt.
   - Correct the commands and call `request_approval` again with corrected commands and the failed-device list only.
   - On approval, call `push_config` with the corrected commands and failed devices only. Continue to verification.
   - **Cap**: 2 retries max (3 total push attempts). After the third failure, log to Jira and go to session closure.
   - Each retry cycle produces its own Discord outcome embed — expected behavior.

6. **Session closure:** follow CLAUDE.md **On-Call Session Closure** — log to Jira, evaluate `cases/lessons.md`, present summary, then exit autonomously. The watcher resumes monitoring immediately. Deferred failures (if any) are documented by the watcher — no agent action required.

---

## Jira Updates (On-Call)

Follow the Jira comment workflow in **CLAUDE.md → Case Management**. Use the `cases/case_format.md` structure for all comments. If no issue key is present, skip all Jira calls silently.
