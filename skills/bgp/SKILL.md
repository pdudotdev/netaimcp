---
name: BGP Troubleshooting
description: "BGP session state, missing routes, prefix policy, default-originate, next-hop-self, route reflector — decision trees and checklists"
---

> **PREREQUISITE**: Before using this skill, you MUST have already run `get_interfaces(device)` and `get_bgp(device, "summary")` on the target device. If sessions are not Established, go directly to the **Session Checklist** below — do not read the full skill from the top. If all sessions are Established, proceed with the relevant symptom section.

# BGP Troubleshooting Skill

## Scope
BGP session state, missing routes, prefix policy, default-originate, next-hop-self, route reflector.
Covers: AS1010 (E1C, E2C), AS2020 (X1C), AS4040 (IAN), AS5050 (IBN).

**All BGP sessions in the current topology are eBGP.** The iBGP/Route Reflector section below is included as generic troubleshooting guidance for completeness.

**Defaults:** Keepalive 60s · Hold 180s · AD 20 (eBGP) / 200 (iBGP) · Weight 0 (received routes) / 32768 (locally originated)

## Start Here: Session State

When a BGP neighbor is not Established:

```
get_bgp(device, "summary")
```

| State | Root Cause | Fix |
|-------|-----------|-----|
| Established + count | Healthy | — |
| Idle | TCP failing or admin shutdown | Check reachability, check `neighbor X shutdown` |
| Connect | TCP SYN in progress | Reachability issue — peer unreachable or TCP 179 filtered |
| Active | TCP connect failed, retrying / listening for incoming | Check ACL on TCP 179, check update-source, ebgp-multihop for non-direct eBGP |
| OpenSent | OPEN sent, waiting reply | Usually transient, else hold-timer mismatch |
| OpenConfirm | OPEN exchanged, awaiting KEEPALIVE | Usually transient — if stuck, check hold-timer or capability negotiation failure |
| Idle (Admin) | `neighbor X shutdown` configured | Remove shutdown |

### Session Checklist

Run `get_bgp(device, "config")` and verify in order. Stop at the first mismatch — fix it first, then re-verify. If the issue persists after the fix, start a new investigation cycle for any remaining problems.
If `config` output is ambiguous (e.g., no explicit timers shown but sessions are flapping), run `get_bgp(device, "neighbors", neighbor=<ip>)` to see negotiated timers directly.

> **Note**: This checklist checks AS numbers before timers, which differs from CLAUDE.md Principle 6's generic ordering (timers before AS). In BGP, AS mismatch causes immediate OPEN rejection — it is more fundamental than a timer mismatch, which is negotiated after OPEN exchange.

1. **AS numbers correct?** (`local-as` on each side matches the peer's `remote-as`)
2. **Keepalive/hold timers match on both ends?** Defaults: keepalive=60s, hold=180s.
   Mismatch → root cause found, stop here.
   **Fix direction**: restore the non-standard side to defaults — never change a correctly-configured peer to match a misconfigured one.
   `neighbors` shows actual negotiated values — if they differ from defaults, check `config` for explicit `timers` statements on the local device. Trust the operational data; do not dismiss non-default negotiated values as parser artifacts.
3. **Neighbor IP reachable?** `ping(device, neighbor_ip, source=update_source_ip)` from the configured source address.
4. **`update-source` set correctly?** Required for iBGP sessions using Loopback addresses — verify both sides agree on source IP. *(Not applicable in current topology — all sessions are eBGP with physical interface peering.)*
5. **`ebgp-multihop` configured?** Required for non-directly-connected eBGP peers. Missing → stuck in Active.
6. **Authentication match?** MD5 password (key and type) must match on both sides if configured.

### Query Reference

| Query | Returns | When to use |
|-------|---------|-------------|
| `summary` | Neighbor list, state, uptime, prefixes received | First check — verify all sessions are Established and prefix counts non-zero |
| `table` | Full BGP table with path attributes (next-hop, AS-path, local-pref, MED, origin, weight) | Route missing, wrong best path selected, or next-hop investigation |
| `config` | BGP process config, neighbors, route-maps, prefix-lists, address-family, RR config | Verify neighbor config, policies, route-reflector-client, update-source |
| `neighbors` | Per-neighbor detail: negotiated timers, capabilities, address families, reset reasons | Timer mismatch diagnosis, capability issues, session flapping investigation. Use `neighbor=<ip>` on IOS to scope to a single peer. |

---

## Symptom: Session Established but Zero Prefixes

When `get_bgp(device, "summary")` shows a session as Established but with 0 prefixes received:

1. **Address-family activation**: Check `get_bgp(device, "config")` for `neighbor <ip> activate` under `address-family ipv4 unicast`. On IOS-XE, neighbors defined under the global `router bgp` process need explicit activation under the address-family to exchange IPv4 prefixes.
2. **Outbound filter on peer**: The remote peer may have an outbound route-map or prefix-list denying all prefixes. Check `get_routing_policies(peer_device, "route_maps")` on the sending side.
3. **No routes to advertise**: The peer may have no routes matching its `network` statements or redistribution config. Check `get_bgp(peer_device, "config")` and `get_bgp(peer_device, "table")`.

---

## Symptom: Session Flapping / Reset Reasons

When `get_bgp(device, "neighbors", neighbor=<ip>)` shows repeated resets:

| Reset Reason | Root Cause | Action |
|-------------|-----------|--------|
| Hold Timer Expired | Keepalives not arriving in time — aggressive timers, congested link, or CPU overload | Check `timers` in config — non-default values (e.g., keepalive 3 / hold 9) make sessions fragile on any jitter |
| Notification received (cease) | Peer sent administrative notification | Check peer for `neighbor X shutdown` or max-prefix limit reached |
| Peer closed session | TCP reset from peer | Check peer's BGP process health and interface stability |
| No route to peer | IGP route to peer's update-source lost | Check IGP adjacencies and `get_routing(device, prefix=<peer_ip>)` |

**Key diagnostic**: Compare "hold time" (negotiated) vs "Configured hold time" in `neighbors` output. If the negotiated hold time is under 30 seconds, any network jitter will cause flapping. Restore to defaults (keepalive 60 / hold 180) on the non-standard side.

---

## Symptom: Missing Routes

When a route should be in the BGP table but isn't:

```
get_bgp(device, "table")
get_bgp(device, "config")
```

### Route Presence Checklist

1. **Route in BGP table?** (`>` = best, `*` = valid, ` ` = not valid/no best path)
2. **Next-hop reachable?** → `get_bgp(device, "table")` — inspect the next-hop field. If the next-hop is an eBGP peer's IP (external address), iBGP peers may have no IGP route to it. Fix: apply `neighbor X next-hop-self` on the eBGP edge router so it rewrites the next-hop to its own interface before advertising to iBGP peers. Verify reachability: `get_routing(peer_device, prefix=<next_hop_ip>)`.
3. **Outbound policy blocking advertisement?** → `get_routing_policies(device, "route_maps")` and `get_routing_policies(device, "prefix_lists")` — check for deny clauses on the **sending** device. Remember: route-maps have an implicit `deny` at the end — any prefix not explicitly permitted is dropped.
4. **`network` statement matching exact route in RIB?** (must be exact — not aggregate unless `aggregate-address` is configured)
5. **`redistribute` configured?** Check metric-type and route-map filters
6. **Route in RIB but not in BGP?** → next-hop unreachable, route not valid (`*` missing from table output)
7. **Own AS in received AS_PATH?** BGP silently discards any route whose AS_PATH contains the receiving router's own AS number (loop prevention, RFC 4271 §9.1.2). Symptom: route visible in the sending peer's table but absent from yours — no NOTIFICATION is sent. Check `get_bgp(device, "table")` for the prefix; if absent, confirm via the peer that its path does not traverse your AS.
8. **Well-known community blocking propagation?** A route tagged `NO_EXPORT` (0xFFFFFF01) MUST NOT be advertised outside the AS; `NO_ADVERTISE` (0xFFFFFF02) MUST NOT be advertised to any peer. Either community causes a route to be silently withheld from outbound updates — route is present locally but invisible to peers. Check communities in `get_bgp(device, "table")` output for the affected prefix (RFC 1997 §3).

---

## Symptom: Default Route Missing

When ISP should be sending default but it's missing:

```
get_bgp(device, "table")    → look for 0.0.0.0/0 with a valid best path (>)
get_bgp(device, "summary")  → confirm session to ISP peer is Established
```

### Diagnosis

- **Default missing**: ISP may have `default-originate` only conditionally (e.g., `default-originate route-map`) — check ISP config
- **ISP policy**: ISPs in this topology filter customer-advertised defaults inbound (they send but don't accept)
- **Peer IPs**: Get ISP peer IPs from `INTENT.json` → each edge router has different ISP-facing IPs

---

## Symptom: iBGP Routes Not Propagating (Route Reflector)

*Generic guidance — not applicable to the current topology (all sessions are eBGP).*

When iBGP routes are missing on a peer:

```
get_bgp(device, "summary")    → verify iBGP session to RR is Established
get_bgp(rr_device, "config")  → verify peer has route-reflector-client configured
get_bgp(device, "table")      → check if route exists but isn't best path
```

### RR Checklist

- **iBGP routes not propagating** → confirm RR has `neighbor X route-reflector-client` for all clients
- **Next-hop still set to originator's IP (not RR)** → client needs `next-hop-self` or IGP must reach originator
- **Check RR cluster-id** if multiple RRs exist — RRs intended to be in the same cluster must share the same cluster-id (RFC 4456 §8). Different cluster-ids create separate clusters: inter-cluster loop detection does not apply, risking route duplication or suboptimal paths

---

## Symptom: Wrong Best Path Selected

When a route exists but the wrong next-hop is being used:

```
get_bgp(device, "table")      → see all paths for a prefix
get_bgp(device, "config")     → check for weight, local-pref, or AS-path manipulation
```

### Best Path Selection (11-attribute order)

1. Highest Weight (Cisco-local, not advertised)
2. Highest Local Preference (iBGP, default 100)
3. Locally originated (network/redistribute/aggregate)
4. Shortest AS-path
5. Lowest Origin (IGP < EGP < Incomplete)
6. Lowest MED (same AS neighbor only — RFC 4271 §9.1.2: MED is **only compared between routes received from the same neighboring AS**; routes from different ASes are not MED-compared unless `bgp always-compare-med` is configured)
7. eBGP over iBGP
8. Lowest IGP metric to next-hop
9. Oldest eBGP route
10. Lowest BGP Router ID
11. Lowest neighbor IP

---

## Verification Checklist (Post-Fix)

- [ ] `get_bgp(device, "summary")` shows all neighbors as Established
- [ ] `get_bgp(device, "table")` shows expected prefixes with `>` (best path)
- [ ] Default route `0.0.0.0/0` present from all ISP peers on each customer edge router (E1C, E2C, X1C)
- [ ] `get_routing(device)` shows BGP default route in RIB
- [ ] After any policy change (route-map, prefix-list): policy changes do **NOT** take effect on existing routes without a soft reset. The `clear ip bgp` command is in the FORBIDDEN set and cannot be executed via MCP tools — **advise the operator to run `clear ip bgp <neighbor> soft in` or `clear ip bgp <neighbor> soft out` manually on the device**.

---

**References:** RFC 4271 (BGP-4, FSM §8, best path §9.1.2, NEXT_HOP §5.1.3, MED scope §9.1.2) · RFC 4456 (BGP Route Reflection, cluster-id §8) · RFC 4760 (Multiprotocol Extensions) · RFC 1997 (BGP Communities, well-known §3)
