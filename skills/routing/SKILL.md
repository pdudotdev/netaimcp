---
name: Routing Policy & Path Selection
description: "Path selection investigation — PBR, route-map and prefix-list policy influence, ECMP behavior, routing table verification"
---

> **PREREQUISITE**: Before investigating path selection or routing policy, you MUST have verified that interfaces are Up/Up and protocol neighbors are healthy on the device in question. Run `get_interfaces(device)` and `get_<protocol>(device, "neighbors")`. If any interface is down or any neighbor is missing, fix that first — path selection issues cannot be the root cause if basic adjacency prerequisites are missing.

# Routing Policy & Path Selection Skill

## Scope
Path selection troubleshooting for all devices. Read this skill when traffic takes an unexpected or consistently asymmetric path and protocol adjacency/route presence are confirmed correct.

## Start Here: Policy Check Sequence

When traffic consistently takes an unexpected path, check in this order — do not skip steps:

> **Step 0 — Longest-prefix-match override:** Before checking any policy, verify no more-specific route exists: `get_routing(device, prefix=<exact_destination>)`. A /32 host route or a more-specific subnet overrides ALL policy, cost, and AD calculations. If an unexpected specific route is present, that is the root cause — stop here.

    get_routing_policies(device, "policy_based_routing")
    get_routing_policies(device, "route_maps")
    get_routing_policies(device, "prefix_lists")
    get_routing(device, prefix="<destination>")

> **PBR must be checked before any protocol cost math.** PBR overrides the routing table entirely — OSPF and BGP best-path calculations are irrelevant if a `ip policy route-map` is applied on the ingress interface.

| Finding | Root Cause |
|---------|-----------|
| Interface has `ip policy route-map X` | PBR is active — inspect the route-map and ACL before anything else |
| Route-map `set metric` biasing a redistributed path | Redistribution policy is skewing path preference |
| Prefix-list `deny` at a redistribution or distribution point | Route blocked from being advertised upstream — missing from downstream RIBs |
| Single RIB entry when two equal-cost paths are expected | PBR, cost asymmetry, `maximum-paths 1`, or distribute-list filtering |
| Two equal-cost RIB entries but one path always selected | Normal CEF per-destination hashing — not a Router ID tie-breaker |

---

## Symptom: Policy-Based Routing

`policy_based_routing` returns only the **interface binding** — which interface has `ip policy route-map X` applied. It does not show the route-map logic. Always follow with two more queries:

    get_routing_policies(device, "policy_based_routing")   → identifies which interface has PBR
    get_routing_policies(device, "route_maps")             → shows match/set clauses for that route-map
    get_routing_policies(device, "access_lists")           → shows ACL referenced in the match clause

### What to look for in route-map output

- `match ip address <ACL>` — which traffic is matched (source/destination criteria)
- `set ip next-hop <IP>` — matched traffic is forwarded here, bypassing the RIB
- `set interface <intf>` — matched traffic exits a specific interface regardless of routing
- `deny` sequence with no `set` — traffic in a deny sequence falls through to the RIB (not PBR-forwarded)

> **Never conclude "PBR is not the cause" from `policy_based_routing` alone.** If an interface shows `ip policy`, always fetch both `route_maps` and `access_lists` before forming a conclusion. The three queries work as a chain: binding → logic → match criteria.

---

## Symptom: Route Filtering by Route Map or Prefix List

Route-maps applied at redistribution points can modify metrics, biasing path preference on downstream devices. Prefix-lists used as distribute-lists or in redistribution route-maps can block routes from being accepted into or advertised from the RIB — making them absent on downstream routers.

    get_routing_policies(device, "route_maps")     → check for set metric or deny sequences
    get_routing_policies(device, "prefix_lists")   → check permit/deny entries for the affected prefix
    get_ospf(device, "config")                     → check for distribute-list under router ospf

**Direction matters:** filters are applied either inbound (blocking routes from entering the local RIB from a neighbor/protocol) or outbound (blocking routes from being advertised). The filter is configured on the device doing the filtering — the downstream device is where the route will be absent.

**Implicit deny:** every prefix-list ends with an implicit `deny any`. Routes not explicitly permitted are silently dropped.

**Distribute-list filtering** (`distribute-list` under `router ospf`) is a special case: it blocks routes from entering the RIB without removing them from the LSDB. Symptom: `get_ospf(device, "database")` shows the LSA but `get_routing(device, prefix=<X>)` returns no route. See the OSPF skill's "Distribute-List Filtering" section for the full investigation flow — use `get_routing_policies(device, "access_lists")` or `get_routing_policies(device, "prefix_lists")` to inspect the filter logic.

> For BGP attribute manipulation (`set local-preference`, `set weight`, `set as-path prepend`), see `skills/bgp/SKILL.md` — Wrong Best Path section.

---

## Symptom: ECMP — Traffic Always Takes One Path

When two equal-cost paths are expected but traffic consistently uses the same one:

    get_routing(device, prefix="<destination>")   → must show 2+ equal-cost entries for true ECMP
    traceroute(device, destination="<dest>")      → confirms actual forwarding path for that flow

| RIB result | Interpretation |
|-----------|---------------|
| Two entries, equal cost | True ECMP. CEF uses per-destination hashing — a single src/dst IP pair always takes the same path. This is normal, not a misconfiguration. |
| One entry only | ECMP never established — investigate below. |

> **On Cisco IOS with CEF, per-destination load balancing means a single flow always takes the same path.** This is deterministic CEF hashing of the src/dst IP pair — it is NOT a Router ID tie-breaker. Attributing consistent path selection to "higher Router ID wins" is incorrect for IOS OSPF ECMP.

If only one path is installed when two are expected:

1. **Check cost symmetry** — unequal costs mean only the better path is installed:

        get_ospf(device, "database")     → compare LSA costs on both candidate paths

2. **Check `maximum-paths`** — default is 4 on IOS-XE for OSPF; if set to 1, only one path installs:

        get_ospf(device, "config")       → look for maximum-paths under router ospf

3. **Check BGP `maximum-paths`** — BGP defaults to 1 path (no ECMP). Unlike OSPF (default 4), BGP requires explicit configuration:

        get_bgp(device, "config")   → look for maximum-paths under address-family ipv4

4. **Check PBR** — a route-map on the ingress interface can force one path regardless of the RIB:

        get_routing_policies(device, "policy_based_routing")

---

## Symptom: Route From Wrong Protocol (AD Conflict)

When traffic takes a path that doesn't match the expected routing protocol (e.g., iBGP instead of OSPF, or a static route unexpectedly active):

```
get_routing(device, prefix=<destination>)   → check [AD/metric] field in RIB output
```

The RIB entry format `[AD/metric]` identifies the source. When multiple protocols have routes for the same prefix, lowest AD wins:

| Protocol | Default AD |
|----------|-----------|
| Connected | 0 |
| Static | 1 |
| eBGP | 20 |
| OSPF | 110 |
| iBGP | 200 |

**Floating static route:** A static route with AD > 1 (e.g., `ip route X Y Z 254`) acts as a backup — it activates only when all lower-AD routes for that prefix are withdrawn. If a floating static unexpectedly becomes active, the primary dynamic route has been lost — investigate the routing protocol, not the static itself.

---

## Symptom: NAT/PAT Translation Issues

> **Low priority** — only investigate NAT after all routing, adjacency, and policy checks pass. NAT issues are rare root causes in this network.

When the breaking hop is a **NAT_EDGE** device (E1C, E2C per INTENT.json) and all of the following are true:
- All interfaces Up/Up
- All protocol neighbors FULL
- Routes present in RIB with correct next-hops
- No PBR, route-map, or prefix-list anomalies

Then check NAT translations via `run_show`:

    run_show(device, "show ip nat translations")
    run_show(device, "show ip nat statistics")

| Finding | Root Cause |
|---------|-----------|
| Empty translation table | No traffic is being NATed — check `ip nat inside`/`ip nat outside` interface designations and NAT ACL/route-map |
| Translations present but destination unreachable | NAT is working; issue is upstream (ISP) or return-path related |
| Only inside→outside entries, no outside→inside | One-way NAT — return traffic may be blocked by ISP or missing reverse route |

Look for: inside/outside interface counts, active translations, expired translations, and pool exhaustion.

---

## Query Reference

| Query | What it returns |
|-------|----------------|
| `policy_based_routing` | Interfaces with `ip policy route-map X` applied |
| `route_maps` | All route-map definitions (match/set clauses, sequences) |
| `prefix_lists` | Prefix-list definitions (permit/deny per range) |
| `access_lists` | ACL definitions — used to identify PBR match criteria |
| `redistribution` | Active redistribution statements |

---

## Verification Checklist (Post-Fix)

- [ ] `get_routing_policies(device, "policy_based_routing")` — no unexpected `ip policy` bindings on ingress interfaces
- [ ] `get_routing_policies(device, "route_maps")` — no `deny` sequences or `set metric` clauses unexpectedly biasing the path
- [ ] `get_routing_policies(device, "prefix_lists")` — affected prefix is covered by `permit`, not `deny`
- [ ] `get_routing(device, prefix="<destination>")` — correct number of next-hops installed in RIB
- [ ] `traceroute(device, destination="<dest>")` — actual forwarding path matches expected topology
- [ ] `run_show(device, "show ip nat translations")` — if NAT_EDGE device (E1C, E2C): translations present (check only when relevant)
