---
name: OSPF Troubleshooting
description: "OSPF adjacency, LSDB, area types, authentication, route filtering, and redistribution — symptom-first decision trees with lookup tables"
---

> **PREREQUISITE**: Before using this skill, you MUST have already run `get_interfaces(device)` and `get_ospf(device, "neighbors")` on the target device. If neighbors are missing or fewer than expected, go directly to the **Adjacency Checklist** below — do not read the full skill from the top. If all neighbors are FULL and all interfaces Up/Up, proceed with the relevant symptom section.

# OSPF Troubleshooting Skill

## Scope
OSPF adjacency, LSDB, area types, authentication, route filtering, redistribution receipt.
Covers C1C, C2C, E1C, E2C (Area 0), A1C, A2C (Area 1 stub).

**Defaults:** Hello 10s · Dead 40s (broadcast/P2P) | Hello 30s · Dead 120s (NBMA/P2MP) · AD 110 · Reference BW 100 Mbps

## Start Here: Neighbor State

When an OSPF neighbor is not FULL or missing entirely:

```
get_ospf(device, "neighbors")
```

| State | Root Cause |
|-------|-----------|
| FULL | Healthy |
| EXSTART / EXCHANGE | **MTU mismatch** (most common) **or duplicate Router ID**. MTU: `get_interfaces(device)` on both sides — compare MTU. Router ID: if MTU matches, run `get_ospf(device, "details")` on both sides and compare Router IDs — a duplicate RID causes the DD master/slave election to deadlock permanently. |
| LOADING | LSA requests pending — retransmission failing (lossy link, CRC errors, congestion) or the requested LSA was prematurely aged out (MaxAge) before delivery. **RFC 2328 defines no Loading-state timeout** — a stuck Loading neighbor persists indefinitely. Check interface errors; if none, advise operator to `clear ip ospf process` on the stuck side. |
| INIT | Hello one-way (my RID not in their Hello): asymmetric link, ingress ACL blocking 224.0.0.5/224.0.0.6, or auth mismatch on one side |
| 2WAY | DR/BDR election only (non-DR/BDR on broadcast) — normal for non-DR routers |
| DOWN | No hellos received: interface down, passive interface, or wrong area |

### Query Reference
| Query | What it returns | Use when |
|-------|----------------|----------|
| `neighbors` | Neighbor state, router-id, interface | Checking adjacency health |
| `interfaces` | Timer values, auth type, passive flag, area, network type, cost | Verifying adjacency parameters (timers, auth, passive, area) |
| `config` | Process-level config (area definitions, redistribution, network statements) | Checking OSPF process config (area types, redistribution, network statements). |
| `database` | LSDB contents (LSA types, ages, router-ids) | Investigating missing routes |
| `details` | Process-level details (SPF stats, router-id, ABR/ASBR role) | Checking NSSA translation, SPF timers |

### Adjacency Checklist
Verify these items on each side in order. Most use `get_ospf(device, "interfaces")` — items that require a different query note this explicitly. Stop at the first mismatch — fix it first, then re-verify.

1. **Hello/dead timers match on both ends?** Read hello/dead values from
   `get_ospf(device, "interfaces")` on **each side** and compare them.
   Mismatch → root cause found, stop here.
   **Standard defaults** (broadcast/point-to-point): hello=10, dead=40. NBMA/point-to-multipoint: hello=30, dead=120. Any other dead interval (e.g. 7) is non-standard.
   **Fix direction**: restore the device with non-standard values to defaults — never change
   correctly-configured devices to match a misconfigured outlier.
2. **Area ID and type match?** Area number must be the same AND area type (normal / stub / NSSA) must agree on both sides. Check with `get_ospf(device, "config")` — look for `area X nssa`, `area X stub`. Mismatched type → adjacency rejected (NSSA sets N-bit in Hello options; normal sets E-bit — mismatch = hellos silently dropped) (RFC 3101 §2.3).
3. **Network type match?** (point-to-point vs broadcast → must match)
   - **Caution:** Network type is NOT exchanged in Hello packets — adjacency can form despite mismatch. But SPF breaks: the P2P side generates Router LSAs without DR info; the broadcast side expects DR-based LSAs. Routes appear in LSDB but next-hops become unreachable. Symptom: neighbors show FULL but routes are missing.
4. **Auth key and type match?** (key-id AND key string, case-sensitive). IOS shows auth keys in plaintext in the running config. Verify by checking whether other adjacencies using the same key are healthy.
5. **Interface passive?** (`passive-interface` disables hellos)
6. **MTU match?** (most common cause of EXSTART/EXCHANGE stuck)
   - **Diagnosis:** `get_interfaces(device)` on both sides — compare MTU values. OSPF includes interface MTU in DBD packets (RFC 2328 §10.6); if the received MTU exceeds the local interface MTU, the DBD is rejected and the adjacency stalls in EXSTART/EXCHANGE. The lower-MTU side logs "Nbr X has larger interface MTU".
   - **Fix:** Match MTU on both interfaces. Avoid `ip ospf mtu-ignore` — it masks the symptom and can cause oversized OSPF packets to be dropped in transit.
7. **Router IDs unique?** Run `get_ospf(device, "details")` on both sides and compare Router IDs. A duplicate RID (two routers with the same Router ID) causes DD master/slave election in ExStart to deadlock permanently — the adjacency never leaves ExStart. Fix the misconfigured device; the correct RID is typically the Loopback0 address. Note: this check uses `details`, not `interfaces`.

---

## Symptom: Missing Routes

When a route should be in the RIB but isn't:

```
get_ospf(device, "database")
get_routing(device, prefix="<expected-prefix>")
```

### Diagnosis Path

After running the two queries above, branch on the result:

**Is the expected LSA present in the LSDB?** (`get_ospf(device, "database")`)

| LSDB Result | RIB Result | Diagnosis Path |
|-------------|------------|----------------|
| LSA present | Route absent from RIB | **Filtering or forwarding problem on this device** — check Distribute-List Filtering below. For Type 5/7 LSAs, also check forwarding address reachability and E1/E2 metric type (see External Route Issues section). |
| LSA present | Route present, wrong metric/path | For Type 5/7: check E1/E2 metric type preference (see External Route Issues section). For intra/inter-area: check cost in LSDB. |
| LSA absent | Route absent | **Flooding scope or origination problem** — check Area-Type Route Presence Rules below. |

**LSA absent — after checking area-type rules:**

If the area type *should* allow this LSA type (e.g., Type 5 in Area 0, Type 3 in a non-totally-stubby area) and all neighbors on this device are FULL:
- **Type 5 absent** → the redistributing ASBR is not generating the LSA (missing or filtered `redistribute` statement on the ASBR).
- **Type 3 absent for a specific prefix** → the ABR in the source area may be suppressing it (`area range not-advertise` or outbound filtering).
- **Type 7 absent in NSSA** → see NSSA-Specific Issues section below.

If the area type *does not* allow this LSA type (e.g., Type 5 in a stub area), the absence is expected — the ABR should inject a default route (Type 3) instead.

---

### LSA Type Lookup
Understand what should be in the LSDB before diagnosing what's missing:

| Type | Name | Who generates | Flooded |
|------|------|---------------|---------|
| 1 | Router LSA | Every router | Within area |
| 2 | Network LSA | DR on broadcast | Within area |
| 3 | Summary LSA | ABR | Between areas |
| 4 | ASBR Summary | ABR | Other areas |
| 5 | External LSA | ASBR | All areas (except stub) |
| 7 | NSSA External | ASBR in NSSA | NSSA only → converted to Type 5 at ABR |

### Area-Type Route Presence Rules
Critical for interpreting the LSDB:

- **Stub**: No Type 5/7. ABR injects inter-area summaries (Type 3) + default. External routes blocked.
- **Totally stubby** (stub with `no-summary`): No Type 3/5/7. Only a single default (Type 3) from ABR. Know the difference — look for presence/absence of Type 3 LSAs.
- **NSSA**: Type 7 generated by ASBR internally. ABR translates to Type 5 for the backbone. Check both ends: Type 7 in NSSA area, Type 5 in backbone.
- **NSSA Totally Stubby** (`nssa no-summary`): No Type 3/5. Type 7 within area + single default (Type 3) from ABR. Combines NSSA external redistribution with totally stubby inter-area filtering.
- **Backbone Area 0**: All LSA types allowed.

### ABR Route Summarization (`area range`)

ABRs (C1C, C2C in this topology) can summarize inter-area routes using `area X range <network> <mask>`. When active, individual subnets within the range are suppressed and replaced with a single aggregate Type 3 LSA. Adding `not-advertise` suppresses even the aggregate.

**Symptom**: specific subnets from another area are missing, but an aggregate prefix is present.

```
get_ospf(device, "config")    → look for `area X range` on the ABR (C1C or C2C)
get_ospf(device, "database")  → verify the aggregate Type 3 LSA exists
```

This is intentional design, not a fault — verify against `INTENT.json` whether summarization is expected.

### Distribute-List Filtering (LSA present, route absent)

`distribute-list` under `router ospf` filters routes from the RIB **without** removing LSAs from the LSDB. This causes a confusing symptom: `get_ospf(device, "database")` shows the LSA but `get_routing(device, prefix=<X>)` returns no OSPF route.

```
get_ospf(device, "config")    → look for `distribute-list` under router ospf
```

If found, identify the referenced ACL or prefix-list, then inspect the filter logic:

```
get_routing_policies(device, "access_lists")    → if distribute-list references an ACL
get_routing_policies(device, "prefix_lists")    → if distribute-list references a prefix-list
```

This is a deliberate policy decision — not a flooding failure.

---

## Symptom: NSSA-Specific Issues

When redistributed routes are missing in an NSSA area:

1. **Type 7 LSA not generated** → check `redistribute` config on the ASBR
   ```
   get_ospf(device, "config")
   ```
   Look for the redistribute statement; if missing, that's the issue.

2. **Type 7 present in area but Type 5 missing in backbone** → NSSA ABR translation issue
   - Check ABR has `area X nssa` (not `area X nssa no-redistribution`)
   - Multiple NSSA ABRs? Only the one with highest RID translates; verify with `get_ospf(device, "details")`

3. **Default not propagating into NSSA** → ABR must have `area X nssa default-information-originate`

---

## Symptom: Authentication Failures

When neighbors are stuck in INIT with auth mismatch:

> **Before investigating auth keys**: confirm hello/dead timers match on both sides.
> Timer mismatch and auth key mismatch produce identical symptoms (interface Up/Up, L3
> reachable, neighbor count = 0). Timer values and auth type are both visible in
> `get_ospf(device, "interfaces")` output. Check timers first.

```
get_ospf(device, "interfaces")       → shows auth type, timer values, and all OSPF interface details
```

Check: key-id match, key-string match (case-sensitive), MD5 vs plain text type consistent on both ends.

---

## Symptom: Wrong DR/BDR or No DR Election

DR/BDR election occurs on broadcast/NBMA network types only. Highest priority wins (default 1); ties broken by highest Router ID. Priority 0 = ineligible for DR/BDR.

| Symptom | Cause | Check |
|---------|-------|-------|
| Wrong device is DR | Priority misconfiguration | `get_ospf(device, "interfaces")` — check OSPF priority per interface |
| No DR elected | All priorities set to 0 | Same — at least one device must have priority > 0 |
| DR does not change after reboot of old DR | Non-preemptive election | Expected behavior — current DR keeps role until it fails (RFC 2328 §9.4) |

**Note:** DR election is non-preemptive. A higher-priority router joining the segment later does NOT take over the DR role — it waits until the current DR goes down.

---

## Symptom: External Route Issues

When redistributed external routes appear in the LSDB but are not installed in the RIB:

### E1 vs. E2 Metric Types (RFC 2328 §16.4)

OSPF supports two external metric types for Type 5 / Type 7 LSAs:

| Type | Cost Calculation | Preference |
|------|-----------------|------------|
| E1 | External metric + internal OSPF cost to ASBR (cumulative) | Always preferred over E2 |
| E2 | External metric only — ignores internal distance | Default on Cisco IOS |

**Critical rule**: Type 1 **always beats** Type 2 for the same destination, regardless of numeric values. If both types exist for the same prefix, E1 wins even if its total cost is higher.

**Symptom**: Unexpected path taken to an external prefix → check metric type in `get_ospf(device, "database")`. If E1 and E2 both appear for the same destination, E1 wins unconditionally.

**Fix direction**: Redistribute with consistent metric type across all ASBRs. Mixing E1 and E2 for the same prefix causes unpredictable path selection.

### Forwarding Address in External LSAs (RFC 2328 §12.4.3)

A non-zero forwarding address in a Type 5 or Type 7 LSA instructs routers to send traffic **directly to that IP** rather than through the advertising ASBR.

```
get_ospf(device, "database")           → look for non-zero forwarding address in Type 5/7 LSAs
get_routing(device, prefix=<fwd_addr>) → verify forwarding address is reachable
```

**Symptom**: LSA present in LSDB but route not installed in RIB. If the forwarding address is not reachable via OSPF intra- or inter-area routes, the external route is **silently discarded** — it exists in the LSDB but cannot be used for forwarding.

**Fix**: Ensure the forwarding address is reachable via OSPF, or configure the ASBR to use forwarding address `0.0.0.0` (routes traffic through the ASBR itself).

---

## Verification Checklist (Post-Fix)

- [ ] All expected neighbors in FULL state
- [ ] `get_ospf(device, "database")` shows expected LSA types for the area type
- [ ] `get_routing(device)` shows all expected prefixes with correct next-hops
- [ ] For redistributed routes: Type 5 (from backbone) or Type 7 (from NSSA ASBR) present

---

**References:** RFC 2328 (OSPFv2: neighbor FSM §10, MTU §10.6, external metrics §16.4, forwarding address §12.4.3) · RFC 3101 (NSSA: P-bit §3, translator election §2.2) · RFC 5709 (OSPF HMAC-SHA auth)
