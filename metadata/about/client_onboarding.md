# aiNOC Client Onboarding Guide

A structured, repeatable procedure for deploying aiNOC in a client's environment — from first contact to live production monitoring.

---

## Overview

Typical engagement timeline: **6–7 weeks** (Phase 1 to Phase 5).

| Phase | Name | Duration |
|-------|------|----------|
| 1 | Discovery & Scoping | Week 1–2 |
| 2 | Environment Preparation | Week 2–3 |
| 3 | Customization & Build | Week 3–5 |
| 4 | Testing & Validation | Week 5–6 |
| 5 | Deployment & Handoff | Week 6–7 |
| — | Burn-in (supervised) | +1–2 weeks |

---

## Phase 1 — Discovery & Scoping

**Goal**: Understand the client's environment well enough to define an accurate scope and surface any blockers before development begins.

1. **Kickoff meeting**
   - NOC pain points (what's being missed, what takes too long, what keeps waking people up)
   - SLA requirements and business-critical paths
   - Current escalation procedures (L1/L2/L3 thresholds, ISP contact process)
   - Existing monitoring stack (Grafana, LibreNMS, PRTG, etc.) — avoid duplicating alerts

2. **Network documentation collection**
   See the [Required Documentation](#required-documentation-from-client) section below for the full checklist.

3. **Scope definition**
   - Agree on which devices and sites are in scope for Phase 1.
   - Recommended starting point: a single site or a bounded set of critical paths (5–15 devices).
   - Define Phase 2+ expansion plan if applicable.

4. **Integration inventory**
   - Ticketing system: Jira Cloud, Jira Server, ServiceNow, or other?
   - Syslog infrastructure: existing syslog server, format, transport (UDP/TCP/TLS)?
   - Authentication backend: RADIUS, TACACS+, or local credentials per device?
   - Secrets management: HashiCorp Vault, CyberArk, AWS Secrets Manager, or `.env`?

---

## Phase 2 — Environment Preparation

**Goal**: Server provisioned and all management-plane connectivity validated before development starts.

5. **Server provisioning**
   - Dedicated server or VM with reachability to the management network
   - Requirements: Python 3.11+, pip, systemd
   - Optional: Docker (for Containerlab lab environment if a test topology is needed)
   - Network: aiNOC server must reach device management IPs on all required ports (see table below)

   | Transport | Port | Protocol |
   |-----------|------|----------|
   | SSH (all platforms) | 22 | TCP |
   | RESTCONF (IOS-XE) | 443 | HTTPS |
   | eAPI (Arista EOS) | 443 | HTTPS |
   | NETCONF (Junos) | 830 | SSH |
   | REST API (MikroTik) | 443 | HTTPS |

6. **Secrets & credentials setup**
   - **Without Vault**: Create `.env` from `.env.example`. Set `ROUTER_USERNAME` / `ROUTER_PASSWORD`. For multi-vendor environments, per-platform credentials can be added (see `core/settings.py`).
   - **With HashiCorp Vault**: Provide Vault address, auth method (AppRole recommended), secret engine path, and secret schema. `core/settings.py` will be extended to call `get_credentials(device)` at tool execution time instead of reading globals at import.

7. **Inventory setup**
   - **Without NetBox**: Author `inventory/NETWORK.json` from the device inventory spreadsheet provided by the client. See `metadata/about/file_roles.md` for the schema.
   - **With NetBox**: Provide NetBox URL and API token. Custom fields required on each device in NetBox: `transport` (asyncssh / restconf / eapi / netconf) and `cli_style` (ios / eos / junos / routeros). `core/inventory.py` will be extended to sync from NetBox API.

8. **Transport validation**
   For each platform in scope, verify management plane connectivity from the aiNOC server to at least one representative device before writing any platform map entries. A failed SSH or RESTCONF connection at this stage is a firewall/ACL/credential issue — fix it now, not during testing.

---

## Phase 3 — Customization & Build

**Goal**: aiNOC configured for the client's specific topology, vendors, and operational context.

9. **Platform map extension** (`platforms/platform_map.py`)
   Add `PLATFORM_MAP` sections for each new vendor/transport combination. This is the core development work. See `metadata/about/scalability.md` for the step-by-step guide. Effort per new vendor: 2–7 days depending on transport complexity (see [Vendor Effort Estimates](#vendor-effort-estimates)).

10. **INTENT.json authoring** (`intent/INTENT.json`)
    Build the network intent schema from client documentation:
    - Router roles: ABR, ASBR, route reflector, NAT gateway
    - AS assignments and BGP peering matrix
    - IGP area assignments and area types
    - NAT boundaries (inside/outside interfaces)
    - SLA path definitions (sources, destinations, expected device paths)

11. **SLA path definitions** (`sla_paths/paths.json`)
    Define one entry per monitored path:
    - `source_device`: device generating IP SLA probes
    - `destination_ip`: probe target
    - `scope_devices`: all devices that may need investigation if the path fails
    - `ecmp`: true if two equal-cost paths exist
    - `ecmp_node` / `ecmp_next_hops`: where the path splits

12. **CLAUDE.md customization**
    Update topology-anchored sections:
    - Protocol triage table in `skills/oncall/SKILL.md` (device → protocol → skill mapping)
    - Scope sections in `skills/ospf/SKILL.md` and `skills/bgp/SKILL.md` (device names, area assignments)
    - Any vendor-specific pitfalls for the client's platform mix

13. **Skill files** (`skills/`)
    Generic RFC-based protocol theory applies to all vendors without modification. Add vendor-specific notes where CLI syntax differs:
    - Junos: `show ospf neighbor` (not `show ip ospf neighbor`)
    - Arista EOS: structured output via eAPI (JSON responses, not Genie-parsed)
    - MikroTik: `/routing ospf neighbor print` syntax

14. **Syslog / watcher integration** (`oncall/watcher.py`)
    - Configure Vector pipeline (`metadata/about/vector.yaml`) for the client's syslog format and SLA probe notification syntax.
    - Update `watcher.py` SLA trigger patterns if the client uses a different mechanism: Junos RPM probes, Arista IP SLA, IPSLA track objects.

15. **Ticketing integration** (`core/jira_client.py`)
    - Jira Cloud / Server: update `JIRA_BASE_URL`, `JIRA_PROJECT_KEY`, and auth (API token vs username:password).
    - ServiceNow: `jira_client.py` will need adaptation to ServiceNow REST API (incident creation, comment, resolve endpoints differ).

---

## Phase 4 — Testing & Validation

**Goal**: Full On-Call workflow validated in a safe environment before touching production.

16. **Unit test extension** (`testing/agent-testing/unit/`)
    Add test files for new vendor command maps, transport executor behavior, and input validation edge cases. See `testing/agent-testing/README.md` for the test file naming convention (UT-xxx).
    Run: `cd /home/mcp/aiNOC/testing/agent-testing && ./run_tests.sh unit`

17. **Integration testing** (`testing/agent-testing/integration/`)
    Run against a lab or staging environment mirroring the client topology (Containerlab, EVE-NG, or physical lab with `NO_LAB=0`).

18. **Acceptance testing** (manual E2E)
    Execute the full On-Call workflow end-to-end at least once per SLA path:
    - Inject SLA failure (shut an interface, fail a BGP neighbor)
    - Verify watcher triggers and creates a Jira ticket
    - Agent diagnoses, presents findings table, proposes fix
    - Apply fix (with user approval), verify resolution
    - Confirm lessons.md evaluation and Jira resolution

19. **Client walkthrough**
    - Live demo of the On-Call workflow
    - Train NOC staff: how to approve/deny fixes, interpret findings tables, use `/exit` to close sessions
    - Review on-call behavior and session lifecycle (single active session, deferred events, drain mechanism)

---

## Phase 5 — Deployment & Handoff

**Goal**: Production deployment stable, client team self-sufficient.

20. **Production deployment**
    - Install and enable `oncall/oncall-watcher.service` systemd unit
    - Configure log rotation for `logs/oncall_watcher.log`
    - Verify syslog source → Vector → `/var/log/network.json` → watcher pipeline end-to-end

21. **Burn-in period (1–2 weeks)**
    - Client NOC approves all fix proposals (no autonomous changes during burn-in)
    - aiNOC team reviews `cases/lessons.md` entries for quality after each case
    - Track false positive rate; tune watcher patterns if necessary

22. **Handoff documentation**
    Commit to client's repository:
    - Updated `CLAUDE.md`, `intent/INTENT.json`, `sla_paths/paths.json`, `skills/` files
    - Runbook for common operations:
      - Restart watcher: `systemctl restart oncall-watcher`
      - Update device inventory: edit `inventory/NETWORK.json` (or sync from NetBox)
      - Add new SLA path: add entry to `sla_paths/paths.json`, update `intent/INTENT.json`
      - Update troubleshooting model: edit `.claude/settings.json` (model, effortLevel)

---

## Required Documentation from Client

### Must-Have (Blocks Implementation)

| Document | Format | Used By | Key Fields |
|----------|--------|---------|-----------|
| **Device inventory** | Spreadsheet or NetBox export | `NETWORK.json` / NetBox sync | Hostname, management IP, platform, OS version, transport method |
| **Credentials** | Vault path or secure handoff | `.env` / Vault integration | Per-device or per-role; transport-specific (SSH user, RESTCONF user, eAPI token) |
| **Network topology diagram** | Visio / draw.io / text | `INTENT.json`, SLA paths | Physical + logical: links, areas, AS numbers, redistribution points |
| **IGP design document** | Document or config extracts | `INTENT.json`, skills | OSPF areas + types, IS-IS levels, EIGRP AS numbers, passive interfaces |
| **BGP design document** | Document or config extracts | `INTENT.json`, skills | AS numbers, peering matrix, route-policy names, communities in use |
| **Management plane access** | Firewall rules / VPN details | Server setup | aiNOC server must reach mgmt IPs on SSH 22, RESTCONF/eAPI 443, NETCONF 830 |
| **SLA definitions** | Business requirements | `sla_paths/paths.json` | Business-critical paths, source/destination IPs, acceptable latency/loss |
| **Ticketing system access** | API endpoint + credentials | `core/jira_client.py` | Jira project key, ServiceNow instance URL, API token |

### Should-Have (Improves Quality)

| Document | Format | Used By | Notes |
|----------|--------|---------|-------|
| **Sanitized running configs** | Text files (sensitive values removed) | Platform map validation | Verify command syntax matches platform_map entries before writing them |
| **OS version matrix** | Spreadsheet | Transport selection | Determines RESTCONF support (IOS-XE 16.6+), eAPI availability, NETCONF capability |
| **Change management policy** | Document | CLAUDE.md, Discord approval | Emergency change procedure, change approval SLA |
| **Escalation matrix** | Document | Skills, CLAUDE.md | Who to page for ISP issues, hardware failures, security incidents |
| **Existing monitoring** | Dashboard URLs | Reference | Avoid duplicating Grafana/LibreNMS/PRTG alerts — complement, don't overlap |
| **Known recurring issues** | Wiki or runbook pages | `cases/lessons.md` | Seed the lessons file; shortcut diagnosis from day one |
| **NAT/PAT design** | Config extracts | Skills, INTENT.json | Inside/outside interfaces, NAT ACLs, pool definitions, overload rules |
| **Route policy inventory** | Route-maps, prefix-lists | Skills reference | What policies exist and their business purpose (PBR, redistribution filters) |

### Nice-to-Have (Future Phases)

| Item | Format | Used By |
|------|--------|---------|
| **NetBox instance access** | URL + API token | Automated inventory sync (upcoming) |
| **HashiCorp Vault access** | Address + AppRole | Per-device credential management (upcoming) |
| **IPAM data** | NetBox/Infoblox export | Prefix validation in INTENT.json |
| **Interface utilization reports** | Monitoring export | SLA path prioritization |

---

## Codebase Readiness: Current State & Coupling Points

The codebase has solid abstraction layers (`platform_map.py`, `cli_style`, transport dispatcher, ActionChain) designed for multi-vendor from the start. Five specific coupling points require work when adding a new vendor:

### Hard Coupling Points

| # | Issue | File | Fix | Effort |
|---|-------|------|-----|--------|
| 1 | `PLATFORM_MAP["ios_restconf"]` is hardcoded (line 139) — RESTCONF section key not dynamically constructed | `platforms/platform_map.py` | Add explicit RESTCONF branch: `f"{cli_style}_{transport}"` key lookup for non-IOS restconf devices | Low (1–2 h) |
| 2 | Config push always uses SSH (`push_ssh()`) for all devices | `tools/config.py` | Add `config_push` category to PLATFORM_MAP; select push transport per `cli_style` | Medium (½ day) |
| 3 | FORBIDDEN set is 21 IOS CLI patterns only | `tools/config.py` | Make FORBIDDEN a dict keyed by `cli_style`; each vendor has its own pattern set | Low (2–3 h) |
| 4 | `_execute_single()` has hard `if/elif` for `asyncssh` / `restconf` only | `transport/__init__.py` | Registry pattern: `TRANSPORT_REGISTRY = {"asyncssh": fn, "restconf": fn, "eapi": fn, ...}` | Low (2–3 h) |
| 5 | Single global credentials (`ROUTER_USERNAME` / `ROUTER_PASSWORD` at import time) | `core/settings.py` | Per-platform env var fallback (short-term); `get_credentials(device)` → Vault (with Vault integration) | Medium (Vault is separate feature) |

### What's Already Vendor-Agnostic

- **MCP tool interface** (`get_ospf`, `get_bgp`, etc.): callers are unaware of transport — no changes needed
- **Input models** (`input_models/models.py`): Pydantic validation is protocol-based, not vendor-based
- **ActionChain pattern**: already supports multi-tier transport fallback for any vendor
- **On-Call workflow**: traceroute → localize → basics → protocol skill — fully vendor-agnostic
- **Skills** (BGP, OSPF, routing, oncall): RFC-based theory, topology-anchored scope sections
- **Jira / ticketing integration**: vendor-independent
- **Watcher / SLA monitoring**: only syslog format regex needs updating per vendor

### Vendor Effort Estimates

| Vendor | Transport | Parser | Total Effort |
|--------|-----------|--------|-------------|
| **Cisco IOS-XR** | SSH (Scrapli) | Genie / TTP | 2–3 days |
| **Arista EOS** | eAPI (httpx JSON) | Native JSON (structured) | 3–4 days |
| **Juniper Junos** | NETCONF (ncclient) or SSH | PyEZ / TTP | 5–7 days |
| **MikroTik RouterOS** | REST API (httpx) | Native JSON | 3–4 days |
| **Palo Alto PAN-OS** | REST API / SSH | XML / JSON | 4–5 days |

For detailed step-by-step guidance on adding a new vendor, see `metadata/about/scalability.md`.

### Upcoming Integration Impact

**NetBox** (inventory sync — upcoming):
- Changes needed: `core/inventory.py` (add `sync_from_netbox()`) + `oncall/watcher.py` (use NetBox API for device lookup on alert)
- Client prerequisite: Custom fields on NetBox device objects for `transport` and `cli_style`
- Effort: 2–3 days

**HashiCorp Vault** (credentials — upcoming):
- Changes needed: `core/settings.py` (add `get_credentials(device_name)` → Vault KV lookup)
- For per-device creds: transport layer must accept credentials per call (currently uses module-level globals)
- Effort: 2–3 days (global cred from Vault), 4–5 days (per-device creds)

---

## Quick Reference: Key Files to Customize per Client

| File | What to Customize |
|------|------------------|
| `inventory/NETWORK.json` | Device roster, management IPs, transport, cli_style |
| `intent/INTENT.json` | Router roles, AS assignments, IGP areas, BGP peers, NAT |
| `sla_paths/paths.json` | SLA monitoring path definitions |
| `.claude/settings.json` | Default model and effort level |
| `CLAUDE.md` | Protocol triage table, topology-specific pitfalls |
| `skills/oncall/SKILL.md` | Breaking-hop-to-protocol mapping table (Step 3) |
| `skills/ospf/SKILL.md` | Scope section (device names, area assignments) |
| `skills/bgp/SKILL.md` | Scope section (AS numbers, peering topology) |
| `cases/lessons.md` | Seed with client's known recurring issues |
| `platforms/platform_map.py` | New `cli_style` sections for non-Cisco vendors |
| `transport/` | New executor modules for non-SSH/RESTCONF transports |
| `.env` | Credentials, Vault/NetBox endpoints, TLS settings |
