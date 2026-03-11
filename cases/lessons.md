# Top Lessons Learned

Curated from resolved cases. Agent updates this file after each case closure.
Read this file at session start. For detailed case history, refer to Jira tickets.

Maximum 10 entries. Each entry: one actionable lesson in 1-2 lines.

### Promotion Criteria
A lesson belongs here if it: (1) applies broadly to future cases, (2) corrects a methodology mistake, and (3) isn't already captured above.

---

1. **Source-first on SLA failure**: When an SLA path fails, always run `get_interfaces(source_device)` immediately. A shutdown `source_interface` (from paths.json) is immediately identifiable and is the root cause — do not escalate to protocol-level investigation until source device interfaces are confirmed Up/Up.

2. **Always pass `source_ip` in traceroute for SLA paths**: Without a source IP, traceroute may succeed via an alternate path and mask the actual monitored-path failure. Always use `traceroute(source_device, destination_ip, source=source_ip)` when `source_ip` is defined in paths.json.

3. **OSPF timer and network-type mismatch prevents adjacency formation**: Mismatched hello/dead intervals or network types between OSPF neighbors prevent adjacency despite physical connectivity and L3 reachability. Cisco IOS defaults to hello 10/dead 40 on broadcast/point-to-point links — mismatches arise from explicit non-default configuration. Network-type mismatch (POINT_TO_MULTIPOINT vs POINT_TO_POINT) causes automatic timer divergence (hello 30/dead 120 vs 10/40). Zero neighbors on an Up/Up interface = suspect timers or network type; always inspect `get_ospf(device, "interfaces")` on both sides before investigating other causes. Fix the misconfigured side — never match the outlier. ABR special case: when inter-area routes suddenly vanish while Area 1 neighbors remain healthy, immediately check the ABR's Area 0 interface dead-intervals — non-standard values cascade to all downstream areas losing both inter-area and external routes.

4. **LSDB vs RIB mismatch → adjacency or config issue**: If LSAs present in database but routes missing from RIB, root cause is OSPF adjacency failure or config error, not LSA flooding. Check neighbor states before investigating SPF calculations.

5. **Administratively shutdown interfaces break SLA paths — check all scope devices, not just source**: Shutdown interfaces on any device in the path (source, transit, egress, or destination) break SLA reachability. Transit devices like E1C (NAT_EDGE/ASBR) are especially impactful — shutdown OSPF or BGP-facing interfaces kill all adjacencies and cascade failures across multiple SLA paths. When `get_interfaces` shows admin-down on a scope device, that's the root cause — no further protocol investigation needed. Always check `get_interfaces` on the breaking hop before diving into protocol tools.

6. **ABR is a critical single point of failure — detect via stale LSAs**: When an ABR loses backbone (Area 0) adjacencies, all downstream areas lose inter-area and external routes simultaneously. A single broken ABR cascades failures across multiple SLA paths. Monitor ABR backbone adjacencies aggressively. Diagnostic: check LSDB for Type 3 or Router LSAs with age 1500+ seconds — stale LSAs indicate the originating router (typically ABR) has broken inter-area adjacencies preventing LSA refresh. Compare LSA ages across neighbors; identical stale ages across multiple neighbors confirms the source ABR's failure.

7. **OSPF passive-interface silently blocks adjacencies**: Passive-interface prevents hello exchange but leaves the physical link and layer 3 connectivity appearing healthy. Result: interface Up/Up, layer 3 reachable, but neighbor count zero. Always inspect `get_ospf(device, "interfaces")` for `passive` flag when neighbors are absent despite correct parameters (timers, area, auth, network type). This is especially critical on ABRs where passive Area N interfaces prevent inter-area route propagation.

8. **Verify intent vs actual state before proposing a fix**: INTENT.json describes the desired network design, not the current device config. Attributes like `area_type`, `stub`, and `default_originate` may differ from the running configuration. Always verify with `get_<protocol>(device, "config")` before basing a fix on INTENT.json values — misreading intent as actual state leads to proposing a fix for a non-existent misconfiguration.

9. **Aggressive BGP hold timers cause dual-ISP session flapping**: When both ISP sessions on an ASBR flap simultaneously, check `get_bgp(device, "neighbors", neighbor=<ip>)` for mismatched "hold time" vs "Configured hold time" lines. Non-default `timers <keepalive> <hold>` on neighbor statements (e.g. 3/9 instead of 60/180) make sessions fragile — any network jitter causes hold expiry and teardown, which cascades to downstream default route loss. Fix: `no neighbor X timers <k> <h>` to restore defaults. No session reset required if the change is applied inline; IOS renegotiates on the next OPEN.

10. **Traceroute via unexpected ISP path = primary ISP link failure, not transient**: When traceroute succeeds but transits an alternate ISP (e.g., IBN instead of IAN), do not dismiss as transient. Check BGP prefix counts on the ASBR — a significant imbalance between ISP peers (e.g., 2 vs 7 prefixes) signals the primary ISP path is down. Trace the issue to the ISP device's interface toward the destination (admin-shutdown, link failure) or a failed BGP session. The alternate path masks the failure but introduces suboptimal routing.
