# Top Lessons Learned

Curated from resolved cases. Agent updates this file after each case closure.
Read this file at session start. For detailed case history, refer to Jira tickets.

Maximum 10 entries. Each entry: one actionable lesson in 1-2 lines.

### Promotion Criteria
A lesson belongs here if it: (1) applies broadly to future cases, (2) corrects a methodology mistake, and (3) isn't already captured above.

---

1. **Source-first on SLA failure**: When an SLA path fails, always run `get_interfaces(source_device)` immediately. A shutdown `source_interface` (from paths.json) is immediately identifiable and is the root cause — do not escalate to protocol-level investigation until source device interfaces are confirmed Up/Up.

2. **Always pass `source_ip` in traceroute for SLA paths**: Without a source IP, traceroute may succeed via an alternate path and mask the actual monitored-path failure. Always use `traceroute(source_device, destination_ip, source=source_ip)` when `source_ip` is defined in paths.json.

3. **OSPF timer and network-type mismatch prevents adjacency formation**: Mismatched hello/dead intervals or network types between OSPF neighbors prevent adjacency despite physical connectivity and L3 reachability. Both Arista EOS and Cisco IOS default to hello 10/dead 40 on broadcast/point-to-point links — mismatches arise from explicit non-default configuration. Network-type mismatch (POINT_TO_MULTIPOINT vs POINT_TO_POINT) causes automatic timer divergence (hello 30/dead 120 vs 10/40). Zero neighbors on an Up/Up interface = suspect timers or network type; always inspect `get_ospf(device, "interfaces")` on both sides before investigating other causes. Fix the misconfigured side — never match the outlier. ABR special case: when inter-area routes suddenly vanish while Area 1 neighbors remain healthy, immediately check the ABR's Area 0 interface dead-intervals — non-standard values cascade to all downstream areas losing both inter-area and external routes.

4. **LSDB vs RIB mismatch → adjacency or config issue**: If LSAs present in database but routes missing from RIB, root cause is OSPF adjacency failure or config error, not LSA flooding. Check neighbor states before investigating SPF calculations.

5. **Administratively shutdown interfaces on egress/destination devices break SLA paths silently**: When ISP-facing or egress interfaces are shut down on the destination device, the SLA source receives explicit rejection (host unreachable) rather than timeout. This localizes the issue to the destination device quickly. Always check interface status on egress_devices in paths.json, not just the source device. Both source and destination interfaces must be Up/Up for SLA paths to work.

6. **ABR is a critical single point of failure — detect via stale LSAs**: When an ABR loses backbone (Area 0) adjacencies, all downstream areas lose inter-area and external routes simultaneously. A single broken ABR cascades failures across multiple SLA paths. Monitor ABR backbone adjacencies aggressively. Diagnostic: check LSDB for Type 3 or Router LSAs with age 1500+ seconds — stale LSAs indicate the originating router (typically ABR) has broken inter-area adjacencies preventing LSA refresh. Compare LSA ages across neighbors; identical stale ages across multiple neighbors confirms the source ABR's failure.

7. **OSPF passive-interface silently blocks adjacencies**: Passive-interface prevents hello exchange but leaves the physical link and layer 3 connectivity appearing healthy. Result: interface Up/Up, layer 3 reachable, but neighbor count zero. Always inspect `get_ospf(device, "interfaces")` for `passive` flag when neighbors are absent despite correct parameters (timers, area, auth, network type). This is especially critical on ABRs where passive Area N interfaces prevent inter-area route propagation.

8. **RouterOS OSPF dynamic interfaces are read-only — use interface-template for config**: `get_ospf(device, "interfaces")` returns entries with `dynamic: true` that are auto-created by the OSPF process and cannot be PATCH'd directly (returns HTTP 400). To modify timer or configuration values (e.g. `hello-interval`), fetch `/rest/routing/ospf/interface-template` via `run_show` to get the template IDs, then `PATCH /rest/routing/ospf/interface-template/<id>`. The templates are the authoritative source; dynamic entries reflect the applied state.

9. **Aggressive BGP hold timers cause dual-ISP session flapping**: When both ISP sessions on an ASBR flap simultaneously, check `get_bgp(device, "neighbors", neighbor=<ip>)` for mismatched "hold time" vs "Configured hold time" lines. Non-default `timers <keepalive> <hold>` on neighbor statements (e.g. 3/9 instead of 60/180) make sessions fragile — any network jitter causes hold expiry and teardown, which cascades to downstream default route loss. Fix: `no neighbor X timers <k> <h>` to restore defaults. No session reset required if the change is applied inline; IOS renegotiates on the next OPEN.
