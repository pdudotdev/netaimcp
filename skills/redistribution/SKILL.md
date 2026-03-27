---
name: Redistribution Troubleshooting
description: "Cross-protocol redistribution (OSPF↔EIGRP) — seed metrics, subnets keyword, loop risk, route-map filtering"
---

> **SHOWCASE ARTIFACT** — This skill was written for a previous topology that included EIGRP.
> The current topology (v5.0+) is OSPF+BGP only. EIGRP was removed and there is no `get_eigrp`
> MCP tool. Retained as a reference for cross-protocol redistribution methodology only.
> **Do not follow this skill for the current topology.**

> **PREREQUISITE**: Before investigating redistribution, you MUST have verified that interfaces are Up/Up and OSPF and/or EIGRP adjacencies are healthy on BOTH sides of the redistribution point. Run `get_interfaces(device)`, `get_ospf(device, "neighbors")`, and `get_eigrp(device, "neighbors")`. If any interface is down or any adjacency is missing, fix that first (see `skills/ospf/SKILL.md` or `skills/eigrp/SKILL.md` Adjacency/Neighbor Checklist). Redistribution cannot work if the source protocol's adjacencies are down.

# Redistribution Troubleshooting Skill

## Scope
Cross-protocol redistribution troubleshooting at the redistribution point: E1C (EIGRP AS10 ↔ OSPF bidirectional, route-map filtered).

**Administrative Distance:** Connected 0 · Static 1 · EIGRP internal 90 · OSPF 110 · EIGRP external 170 · iBGP 200

**Critical asymmetry:** EIGRP internal (AD 90) < OSPF (AD 110). If a prefix is learned via both protocols natively, EIGRP wins — even if OSPF has the shorter path. This is the #1 cause of suboptimal routing in mutual redistribution topologies.

## Redistribution Points in This Network

| Device | Direction | Notes |
|--------|-----------|-------|
| E1C | EIGRP AS10 ↔ OSPF (bidirectional) | Both ways: EIGRP→OSPF (via route-map OSPF-TO-EIGRP) and OSPF→EIGRP (metric-type 1). A1C/A2C use EIGRP to reach E1C as default gateway. Loop risk — mitigated by route-map on the OSPF→EIGRP redistribute statement. |

---

## Symptom: Missing Redistributed Routes

When routes should appear after redistribution but don't:

```
get_routing_policies(device, "redistribution")   → active redistribution statements
get_ospf(device, "database")                      → check for Type 5/7 LSAs on ASBR
get_eigrp(device, "topology")                     → check for redistributed routes (D EX entries)
```

### Common Failures

1. **No seed metric (EIGRP)** → EIGRP silently drops routes with infinite metric
   - Fix: add `metric <bw> <delay> <reliability> <load> <mtu>` to the redistribute statement

2. **Missing `subnets` keyword (OSPF)** → `redistribute eigrp X` without `subnets` drops all classless subnets
   - Fix: add `subnets` keyword

3. **Route-map filtering** → redistribution may use a route-map that filters routes
   - Check with `get_routing_policies(device, "route_maps")`

4. **Metric-type E2 vs E1** → E2 (default) = fixed external cost from ASBR; E1 = cumulative (internal + external)
   - Check which is configured: `get_ospf(device, "config")`

---

## Symptom: Routing Loop Risk (Bidirectional Redistribution)

When a device redistributes in both directions (OSPF↔EIGRP), routes learned from one protocol can be re-injected back, creating a loop.

```
get_routing_policies(device, "redistribution")   → check for route-map on the redistribute statement
get_routing_policies(device, "route_maps")       → verify the route-map logic filters appropriately
```

### Loop Prevention Analysis

- **AD protection (partial):** OSPF internal/IA (AD 110) beats EIGRP external (AD 170) — re-injected EIGRP external routes won't displace OSPF routes on the OSPF side. But always verify with `get_routing(device)`.
- **Dangerous case:** EIGRP internal routes (AD 90) beat OSPF (AD 110). If a prefix redistributed from OSPF into EIGRP at C1C propagates to C2C as an EIGRP internal route, C2C will prefer it (AD 90) over the OSPF-learned version (AD 110) — creating suboptimal paths or loops.
- **Route-map filtering (preferred):** route-map on the redistribute statement is the most reliable prevention — it explicitly controls which routes are admitted in each direction.

### Route Tagging for Loop Prevention

Route tagging is the standard mechanism to prevent redistributed routes from re-entering their originating protocol at the other redistribution point.

**Pattern at each redistribution point:**
1. Redistributing OSPF → EIGRP: add `set tag 10` in the route-map
2. Redistributing EIGRP → OSPF: add `match tag 10` with a deny sequence in the route-map

This prevents an OSPF-originated route from being redistributed into EIGRP at C1C and then back into OSPF at C2C.

**Diagnosis:** `get_routing_policies(device, "route_maps")` — check for `set tag` and `match tag` clauses on C1C and C2C. If absent, loop prevention relies on AD alone (fragile).

---

## Seed Metric Reference

| Direction | Requirement | Guidance |
|-----------|------------|---------|
| OSPF → EIGRP | **Explicit seed metric required** | `redistribute ospf 1 metric 10000 100 255 1 1500` (bandwidth in kbps, delay in 10μs units, reliability, load, MTU). EIGRP silently drops routes with no metric. |
| EIGRP → OSPF | Optional (defaults to 20 if omitted) | `redistribute eigrp 10 subnets metric-type 1` — use E1 if downstream OSPF cost should influence path selection; use E2 (default) for a fixed cost regardless of internal topology. |

---

## Diagnostic: One Direction Works, Other Doesn't

1. `get_routing_policies(device, "redistribution")` — confirm BOTH `redistribute` statements exist on C1C or C2C
2. Check each direction independently:
   - OSPF → EIGRP: `get_eigrp(device, "topology")` — is the OSPF prefix present as `D EX` (EIGRP external)?
   - EIGRP → OSPF: `get_ospf(device, "database")` — is the EIGRP prefix present as a Type 5 (or Type 7 in NSSA) LSA?
3. **If present in topology/LSDB but absent from RIB:** check AD conflict — a lower-AD source may be winning. Check `get_routing(device, prefix=<X>)` to see which protocol installed it.

---

## Verification Checklist (Post-Fix)

- [ ] `get_ospf(asbr_device, "database")` shows Type 5 or Type 7 LSAs for redistributed routes
- [ ] `get_eigrp(receiving_device, "topology")` shows redistributed routes as D EX (external)
- [ ] `get_routing(device)` shows redistributed prefixes with expected next-hops
- [ ] No routing loops: verify EIGRP external routes are not displacing OSPF routes on the redistributing device

---

**References:** Cisco redistribution configuration guide · RFC 2328 §16.4 (OSPF external route calculation)
