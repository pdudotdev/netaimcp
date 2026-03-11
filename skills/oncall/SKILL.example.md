# On-Call Skill — SLA Path Failure Workflow

> **This is a template file.** Copy it to `SKILL.md` and replace the placeholder content
> with your On-Call investigation workflow.
> The real `SKILL.md` is gitignored — this example shows the expected structure.

---

## Overview

This skill governs the On-Call workflow when the watcher detects an SLA path failure
and invokes a Claude agent session. Follow the steps below in order.

---

## Step 1: Identify the Failed SLA Path

Read `sla_paths/paths.json` to find the path matching the failed device IP.

- Note: `source_ip`, `destination_ip`, and `scope_devices`
- The `scope_devices` list is your **investigation boundary** — do not query devices outside it

---

## Step 2: Map the Expected Path

Read `intent/INTENT.json` and construct the expected forwarding path from source to destination.

List it explicitly, e.g.:
> "Expected path: R4C → R3C → R1A → R10C (OSPF Area 0)"

Identify transit devices: ABRs, ASBRs, redistribution points.

---

## Step 2.5: Localize with Traceroute

Run a single traceroute from the SLA source to the destination:

```
traceroute(source_device, destination_ip, source=source_ip)
```

The **breaking hop** is the last device that responds. If traceroute completes, the issue
may be transient — verify with ping before proceeding.

---

## Step 3: Basics First at the Breaking Hop

At the breaking hop, run exactly:

1. `get_interfaces(breaking_hop)` — are all relevant interfaces Up/Up?
2. `get_<protocol>(breaking_hop, "neighbors")` — are expected neighbors present?

**Decision gate:**
- Interface down → root cause found. Present findings.
- Neighbors missing → read the protocol skill's **Adjacency Checklist only**.
- All healthy → proceed to deeper investigation.

---

## Step 4: Protocol-Specific Investigation

Based on the expected path's protocol, read the relevant skill:

| Protocol | Skill |
|----------|-------|
| OSPF | `skills/ospf/SKILL.md` |
| BGP | `skills/bgp/SKILL.md` |
| Redistribution | `skills/redistribution/SKILL.md` |

Follow the skill's symptom-driven sections.

---

## Step 5: Present Findings

Before presenting, call `assess_risk(devices=<affected_devices>, commands=<fix_commands>)` and include the risk level in the findings table.

Use a Markdown table (| Finding | Detail | Status |) with ✓/✗ for each check.
Include proposed remediation steps.

---

## Step 6: Apply Fix (After User Approval)

Never call `push_config` without explicit user confirmation.

When applying the fix, pass `on_call=True` to `push_config` — this bypasses the maintenance window so fixes apply at any hour.

After applying:
1. Verify the fix with the same tool that identified the problem.
2. Confirm the SLA path has recovered (check `/var/log/network.json` for Up event).

---

## Jira Updates

Follow the Jira comment workflow in **CLAUDE.md → Case Management**.
Use `cases/case_format.md` structure for all comments.
If no issue key is present, skip all Jira calls silently.

---

## Session Closure

After investigation is complete:
1. Log to Jira (findings comment, then resolution or declined note).
2. Evaluate and update `cases/lessons.md` if applicable.
3. Present a concise summary to the user.
4. Prompt: "Type `/exit` to close this On-Call session."
5. **Do NOT exit autonomously** — wait for the user to type `/exit`.
