# ✨ aiNOC

[![Latest Release](https://img.shields.io/badge/version-4.0.0-blue.svg)](https://github.com/pdudotdev/aiNOC/releases/tag/4.0.0)
[![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/aiNOC)](https://github.com/pdudotdev/aiNOCcommits/main/)

## 📖 **Table of Contents**
- 📜 **aiNOC Project**
  - [🔭 Overview](#-overview)
  - [♻️ Repository Lifecycle](#%EF%B8%8F-repository-lifecycle)
  - [🍀 Here's a Demo](#-heres-a-demo)
  - [⭐ What's New in v4.0](#-whats-new-in-v40)
  - [⚒️ Tech Stack](#%EF%B8%8F-tech-stack)
  - [📋 Supported Vendors](#-supported-vendors)
  - [🎓 Troubleshooting Scope](#-troubleshooting-scope)
  - [🛠️ Environment Setup](#%EF%B8%8F-environment-setup)
  - [🔄 Test Network Topology](#-test-network-topology)
  - [📞 On-Call Mode](#-on-call-mode)
  - [🌱 AI Automation 101](#-ai-automation-101)
  - [⬆️ Planned Upgrades](#%EF%B8%8F-planned-upgrades)
  - [📄 Disclaimer](#-disclaimer)
  - [📜 License](#-license)

## 🔭 Overview
aiNOC is a **network troubleshooting framework** for multi-vendor, multi-protocol, multi-area/multi-AS, OSI L2-L4 enterprise networks.

**Key characteristics:**
- [x] **Multi-vendor support**
- [x] **Multi-protocol, L2-L4**
- [x] **Multi-area/multi-AS**
- [x] **SSH/eAPI/REST API**
- [x] **Jira integration**

Operating modes of **aiNOC**:
- [x] **Standalone mode (ST)**
  - User specifies network issue and symptoms at the prompt
- [x] **On-Call mode (OC)**
  - Agent is invoked by SLA path failure, see [**On-Call Mode**](#-on-call-mode)

**Important files**:
- [x] See [**file_roles**](metadata/about/file_roles.md)

**Agent guardrails**:
- [x] See [**guardrails**](metadata/about/guardrails.md)

**Supported models**:
- [x] Haiku 4.5 (best for costs)
- [x] Sonnet 4.6
- [x] Opus 4.6

**High-level architecture:**

![arch](metadata/topology/ARCHv3.png)

## 🍀 Here's a Demo
- [x] ▶ See a [**DEMO HERE**](https://www.youtube.com/watch?v=oxSa25R6EgI) for v3.0.
  - *Next video demo coming with v5.0*

## ♻️ Repository Lifecycle
This repository is **NOT** static. **New features** are being added periodically (vendors, protocols, integrations, optimizations).

**Stay up-to-date**:
- [x] **Watch** and **Star** this repository

**Current version**:
- [x] **aiNOC v4.0**

## ⭐ What's New in v4.0

v4.0 is a major **quality, reliability, and security** release - no new protocols or vendors, but a hardened foundation for v5.0.

**Security & Safety:**
- [x] `push_config` now enforces maintenance windows (blocked outside policy)
- [x] `run_show` restricted to read-only commands (no config bypass)
- [x] RouterOS REST validation - forbidden paths blocked, POST rejected
- [x] Syslog prompt injection mitigation (sanitize + delimiter)
- [x] Expanded forbidden command set (5 → 14 patterns)
- [x] TLS/SSL configurable per transport (`VERIFY_TLS`, `ROUTEROS_USE_HTTPS`, `SSH_STRICT_HOST_KEY`)

**Architecture:**
- [x] Monolithic `MCPServer.py` (798 lines) decomposed into `tools/`, `transport/`, `core/`, `input_models/`
- [x] Bounded LRU cache (256 entries, TTL-based eviction)
- [x] Connection pooling for eAPI and REST transports
- [x] HTTP timeouts on all device and Jira connections
- [x] Structured JSON logging with configurable levels

**Troubleshooting Methodology:**
- [x] 6 Core Troubleshooting Principles (mandatory, ordered) - see `CLAUDE.example.md`
- [x] Standalone Mode rewritten - 10 deterministic steps with decision gates
- [x] Protocol skill prerequisite gates (interfaces + neighbors verified before deep investigation)
- [x] Role-aware risk assessment using `INTENT.json` and SLA paths

**On-Call & Operational:**
- [x] SLA recovery (Up) event detection and logging
- [x] Daemon mode (`-d` flag) with tmux session support
- [x] systemd service file (`oncall/oncall-watcher.service`) for production deployment
- [x] Pre-change snapshot support in `push_config`
- [x] Rollback advisory generation for all config changes

**Testing:**
- [x] 229 unit tests across 9 test files (up from 3 in v3.0)
- [x] 4 integration test files with `NO_LAB` skip guards
- [x] 13 manual E2E scenarios (8 standalone, 2 on-call, 3 watcher)
- [x] Pydantic `Literal` validation on all query parameters

## ⚒️ Tech Stack

| Tool | ✓ |
|------|---|
| Claude Code | ✓ |
| MCP (FastMCP) | ✓ |
| ContainerLab | ✓ |
| Python | ✓ |
| Scrapli | ✓ |
| Genie | ✓ |
| REST API | ✓ |
| EOS eAPI | ✓ |
| Jira API | ✓ |
| Vector | ✓ |
| Ubuntu | ✓ |
| VS Code | ✓ |
| VirtualBox/VMware | ✓ |

## 📋 Supported Vendors

| Vendor | Platform |
|--------|----------|
| Arista | EOS (cEOS) |
| Cisco | IOS/IOS-XE (IOL) |
| MikroTik | RouterOS |

## 🎓 Troubleshooting Scope
- [x] **OSPF multi-area**:
  - Basic protocol parameters:
    - Reference bandwidth
    - Point-to-point links
    - Passive interfaces
    - MD5 authentication
    - External type 1 routes
    - Default routes injected
  - Route summarization (ABR)
  - Route redistribution EIGRP-OSPF
  - Route filtering with prefix lists
  - Route filtering with distribute lists
  - Area types: normal, stubby, totally NSSA

- [x] **EIGRP**:
  - Basic protocol parameters:
    - Passive interfaces
    - MD5 authentication
    - EIGRP stub summary
  - Route redistribution OSPF-EIGRP
  - Default metric via route maps

- [x] **BGP**:
  - eBGP, dual-ISP mode
  - ISP default-originate
  - Prefix lists and route maps
  - Route reflectors and clients

- [x] **Services**:
  - Policy-Based Routing
  - IP SLA icmp-echo
  - MikroTik Netwatch
  - Arista Connectivity
  - NAT/PAT on ASBRs
  - Management APIs
  - Static routing
  - Syslog, NTP

## 🛠️ Environment Setup
**Installation**:
```
git clone https://github.com/pdudotdev/aiNOC/
cd aiNOC
python3 -m venv mcp
source mcp/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

⚠️ **NOTE:** The included **CLAUDE.md** and **skills** are templates. You can customize them with your own troubleshooting methodology, tool descriptions, and operational guidelines.

## 🔄 Test Network Topology
**Network diagram**:

![topology](metadata/topology/TOPOLOGY-v2.0.png)

**Connection types:**

| Vendor | Transport |
|--------|-----------|
| Cisco IOS | Scrapli SSH |
| Arista EOS | Arista eAPI |
| MikroTik RouterOS | REST API |

**Naming conventions:**
- [x] **RXY** where:
  - **R**: device type (router)
  - **X**: device number id
  - **Y**: vendor (A-Arista, C-Cisco, M-MikroTik, etc.)

**Router configurations:**
- [x] Please find my test lab's config files under the [**lab_configs**](https://github.com/pdudotdev/aiNOC/tree/main/lab_configs) directory
- [x] They are the network's fallback configs for `containerlab redeploy -t lab.yml`
- [x] Default credentials: see **.env** file at [**.env.example**](.env.example)

## 📞 On-Call Mode
**On-Call Mode** was introduced in v3.0 and enhanced in v4.0.

### What it does, in a nutshell?
- [x] User configures connectivity paths
  - **Cisco**: IP SLA & tracking
  - **Arista**: Monitor Connectivity
  - **MikroTik**: NetWatch
- [x] User configures **Syslog** and **NTP**
- [x] User configures **Syslog** server (Vector)
- [x] User configures **Vector** with correct parser
- [x] Connectivity path failures are logged to **Syslog**
- [x] **Vector** listens for and parses multi-vendor logs
- [x] `sla_paths/paths.json` outlines paths for the agent
- [x] `oncall/watcher.py` monitors Vector for new logs
- [x] Once a new log arrives, the agent is invoked
- [x] Agent gets log details pre-filled in prompt
- [x] Agent starts troubleshooting procedures
- [x] Watcher creates a new Jira ticket / case
- [x] Identifies root cause and potential fix
- [x] Upon user approval, applies and verifies the fix
- [x] Logs results to Jira ticket and marks completion
- [x] Agent invocations are logged to `oncall_watcher.log`
- [x] Skipped events are deferred for later analysis

## 🌱 AI Automation 101
If you're completely new to Network Automation using AI & MCP, then you may want to [**start here**](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55) before moving on.

## ⬆️ Planned Upgrades
Expected in version v5.0:
- [ ] Fresh, enterprise-focused topology
- [ ] New vendors (Juniper, Aruba, SONiC)
- [ ] New protocols (VRRP/HSRP, STP/MSTP)
- [ ] Performance-based SLAs
- [ ] NetBox integration

## 📄 Disclaimer
You are responsible for defining your own troubleshooting methodologies and context files, as well as building your own test environment and meeting the necessary conditions (e.g., RAM/vCPU, router OS images, Claude subscription/API key, etc.).

## 📜 License
Licensed under the [**GNU GENERAL PUBLIC LICENSE Version 3**](https://github.com/pdudotdev/aiNOC/blob/main/LICENSE).