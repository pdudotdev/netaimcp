# ✨ aiNOC

**aiNOC:**<br/>
[![Latest Release](https://img.shields.io/badge/version-5.3.0-blue.svg)](https://github.com/pdudotdev/aiNOC/releases/tag/5.3.0) [![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/aiNOC)](https://github.com/pdudotdev/aiNOCcommits/main/)

**Core version vendors:**<br/>
![Cisco IOS-XE](https://img.shields.io/badge/Cisco-IOS--XE-0176C1)

**Core version management:**<br/>
![RESTCONF](https://img.shields.io/badge/RESTCONF-primary-2E8B57) ![CLI](https://img.shields.io/badge/CLI-fallback-A90000)

**On-request extensions:**<br/>
![Arista EOS](https://img.shields.io/badge/Arista-EOS-2A64D4) ![Juniper JunOS](https://img.shields.io/badge/Juniper-JunOS-009A44) ![MikroTik RouterOS](https://img.shields.io/badge/MikroTik-RouterOS-2A3042) ![Aruba AOS-CX](https://img.shields.io/badge/Aruba-AOS--CX-FF6600) ![SONiC](https://img.shields.io/badge/SONiC-FRR-9B9BD5) ![VyOS](https://img.shields.io/badge/VyOS-VyOS-5B9BD5)

**On-request extensions:**<br/>
![NETCONF](https://img.shields.io/badge/NETCONF-D4841A) ![REST](https://img.shields.io/badge/REST-7B52AB) ![gNMI](https://img.shields.io/badge/gNMI-2259B6) ![eAPI](https://img.shields.io/badge/eAPI-092991)

## 📖 **Table of Contents**
- 📜 **aiNOC**
  - [🔭 Overview](#-overview)
  - [♻️ Repository Lifecycle](#️-repository-lifecycle)
  - [🍀 Here's a Quick Demo](#-heres-a-quick-demo)
  - [⭐ What's New in v5.0](#-whats-new-in-v50)
  - [⚒️ Current Tech Stack](#️-current-tech-stack)
  - [📋 Supported Vendors](#-supported-vendors)
  - [🚛 Supported Transports](#️-supported-transports)
  - [🎓 Troubleshooting Scope](#-troubleshooting-scope)
  - [🛠️ Installation & Usage](#️-installation--usage)
  - [🔄 Test Network Topology](#-test-network-topology)
  - [📞 aiNOC Operating Modes](#-ainoc-operating-modes)
  - [⬆️ Planned Upgrades](#️-planned-upgrades)
  - [🌱 AI Automation 101](#-ai-automation-101)
  - [📄 Disclaimer](#-disclaimer)
  - [📜 License](#-license)
  - [📧 Collaborations](#-collaborations)

## 🔭 Overview
AI-based **network troubleshooting framework** for multi-vendor, multi-protocol, multi-area/multi-AS enterprise networks.

▫️ **Key characteristics:**
- [x] **Multi-vendor support**
- [x] **Multi-protocol, L2/L3**
- [x] **Multi-area/multi-AS**
- [x] **CLI/RESTCONF (Core)**
- [x] **NETCONF/REST/gNMI/eAPI (extensions)**
- [x] **15 MCP tools, 4 skills**
- [x] **33 operational guardrails**
- [x] **Human in the loop**
- [x] **Jira integration**

▫️ **Core vs. On-Request**:
- [x] **Core**: 
  - Easy to integrate in Cisco IOS/IOS-XE environments
  - CLI + RESTCONF transports, OSPF/BGP troubleshooting
  - Jira integration, On-Call watcher (both modes)
- [x] **On-Request**: 
  - Custom vendor modules (Arista, Juniper, MikroTik, etc.)
  - Custom vendor transports (REST, NETCONF, gNMI, eAPI) 
  - Built and adapted per client's network environment

▫️ **Operating modes of aiNOC**:
- [x] **Interactive Mode** (current terminal)
- [x] **Service Mode** (**systemd** service)
- [x] See [**aiNOC Operating Modes**](#-ainoc-operating-modes)

▫️ **Important project files**:
- [x] See [**file roles**](metadata/about/file_roles.md)

▫️ **Agent guardrails list**:
- [x] See [**guardrails**](metadata/about/guardrails.md)

▫️ **Adding new protocols or vendors**:
- [x] See [**scalability guide**](metadata/about/scalability.md)

▫️ **Supported models**:
- [x] Haiku 4.5 (best for costs)
- [x] Sonnet 4.6 (best balance)
- [x] Opus 4.6 (default, best reasoning)

⚠️ **NOTE:** Due to the intermittent nature of troubleshooting, it's worth using an advanced model by default. Costs won't become unsustainable even if addressing and fixing several issues per day.

▫️ **Set your default model**:<br/>
Create `settings.json` under `.claude/`:
```
{
  "model":"opus",
  "effortLevel":"medium"
}
```

▫️ **High-level architecture:**

![arch](metadata/topology/ARCHv3.png)

## 🍀 Here's a Quick Demo
- [x] *Demo video for v5.0 coming soon*

## ♻️ Repository Lifecycle
**New features** are being added periodically (protocols, integrations, optimizations).

**Stay up-to-date**:
- [x] **Watch** and **Star** this repository

**Current version**:
- [x] **aiNOC v5.2**

## ⭐ What's New in v5.2
- [x] See [**changelog.md**](changelog.md)

## ⚒️ Core Tech Stack

| Tool |   |
|------|---|
| Claude Code | ✓ |
| MCP (FastMCP) | ✓ |
| ContainerLab | ✓ |
| Python | ✓ |
| Scrapli | ✓ |
| Genie | ✓ |
| RESTCONF | ✓ |
| Jira API | ✓ |
| Vector | ✓ |
| Ubuntu | ✓ |

## 📋 Supported Vendors

| Vendor | Platform | cli_style | Status |
|--------|----------|-----------|--------|
| Cisco | IOS/IOS-XE | `ios` | Core |
| Arista | EOS | `eos` | On-Request |
| Juniper | JunOS | `junos` | On-Request |
| MikroTik | RouterOS | `routeros` | On-Request |
| Aruba | AOS-CX | `aos` | On-Request |
| SONiC | FRR | `frr` | On-Request |
| VyOS | VyOS | `vyos` | On-Request |

## 🚛 Supported Transports

| Management | Devices | Tier | Status |
|-----------|---------|------|--------|
| RESTCONF (httpx) | Cisco IOS-XE | Primary | Core |
| CLI (scrapli) | Cisco IOS/IOS-XE | Fallback | Core |
| NETCONF | custom | — | On-Request |
| REST API | custom | — | On-Request |
| gNMI | custom | — | On-Request |
| eAPI | Arista | — | On-Request |

## 🎓 Troubleshooting Scope

| aiNOC Core |
|----------|
| **OSPF** |
| **BGP**  | 
| **Redistribution** | 
| **Policy-based routing**|
| **Route-maps, prefix lists** |
| **NAT/PAT, access lists** |

| aiNOC On-Request Extenstions |
|----------|
| **EIGRP** |
| **HSRP** | 
| **VRRP** |
| **STP/MSTP** | 
| *etc.* |

## 🛠️ Installation & Usage
▫️ **Step 1**:
```
git clone https://github.com/pdudotdev/aiNOC/
cd aiNOC
python3 -m venv mcp
source mcp/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

▫️ **Step 2**:
The included `CLAUDE.md` and `skills/*` are templates. **Customize them** with your own troubleshooting methodology, tool descriptions, and operational guidelines.

**NOTE**: There is no one-size-fits-all `CLAUDE.md` or `SKILL.md` that works in any network environment. These should be customized for each specific topology, vendor combination, and architecture.

▫️ **Step 3**:
- Configure IP SLA (or Connectivity Monitor, Netwatch etc.) paths in your network
- Make sure they are being tracked and logged remotely to **Vector** (Syslog)
- Configure the transforms inside `/etc/vector/vector.yaml` - [**example**](metadata/about/vector.yaml)
- aiNOC monitors Vector's `/var/log/network.json` file for specific logs and parses them per-vendor

▫️ **Step 4**:
Run the **aiNOC** watcher — two modes:

⌨️ **Interactive** (dev/testing): runs in your current terminal, agent sessions open inline.
```
python3 oncall/watcher.py
```

♻️ **Service** (production): install once, runs permanently, survives reboots. Each agent session
spawns in a **tmux** window. Session output is saved to `logs/session-oncall-<timestamp>.md`.
```bash
sudo apt install tmux
sudo cp oncall/oncall-watcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oncall-watcher.service
```
Manage with: 
`systemctl start|stop|restart|status oncall-watcher`

▫️ **Step 5**:
Check if **Watcher** and **Vector** are running:
```
# Interactive mode
sudo systemctl status vector
python3 oncall/watcher.py
# ainoc.watcher — Watcher started. Monitoring /var/log/network.json for IP SLA Down events.
```
*or (if installed as a systemd service):*
```
# Service mode
sudo systemctl status vector
sudo systemctl status oncall-watcher.service
```

## 🔄 Test Network Topology
▫️ **Network diagram**:

![topology](metadata/topology/TOPOLOGY-v5.0.png)

▫️ **Router configurations:**
- [x] Please find my test lab's config files under the [**lab_configs**](https://github.com/pdudotdev/aiNOC/tree/main/lab_configs) directory
- [x] They are the network's fallback configs for `containerlab redeploy -t AINOC-TOPOLOGY.yml`
- [x] Default credentials: see **.env** file at [**.env.example**](.env.example)

## 📞 aiNOC Operating Modes

aiNOC runs as an **On-Call watcher** that monitors Vector's `/var/log/network.json` for SLA path failures and automatically invokes a Claude agent to diagnose the issue and propose a fix.

### How It Works

1. Network devices track connectivity paths (Cisco IP SLA — extensible to Arista Connectivity Monitor, Juniper RPM probes, MikroTik Netwatch etc. via module builds)
2. Failures are logged to Syslog → **Vector** parses and writes to `/var/log/network.json`
3. **`oncall/watcher.py`** detects the failure, opens a Jira ticket, and invokes a Claude agent session
4. Agent follows structured troubleshooting: `CLAUDE.md` + `/skills` + MCP tools → identifies root cause → proposes fix
5. Only upon **operator approval**, the agent applies and verifies the fix
6. Results are logged to **Jira** and the watcher resumes monitoring

### Deployment

The watcher always runs in service mode — Claude is invoked non-interactively via tmux + print mode (`-p`), auto-exits when done, and the watcher resumes immediately. No interactive CLI required.

| Command | Description |
|---------|-------------|
| `python3 oncall/watcher.py` | Run directly (dev/test) |
| `systemctl start oncall-watcher` | Run as systemd service (production) |

The operator interacts exclusively via **Discord** (approval/rejection embeds). Full session output saved to `logs/session-oncall-<timestamp>.md`.

▫️ See [Installation & Usage](#️-installation--usage) for setup instructions.

### Storm Prevention

Only one agent session runs at a time. Concurrent SLA failures during an active session are captured and documented to Jira and Discord after the session ends — they are not re-triggered or investigated automatically. A drain mechanism ensures no duplicate event processing. A process-level lock file (`oncall/oncall.lock`) with stale-PID detection prevents duplicate watcher instances.

## ⬆️ Planned Upgrades
- [ ] New protocols and services
- [ ] Performance-based SLAs
- [ ] Slack support
- [ ] Digital twin feature

## 🌱 AI Automation 101
If you're completely new to Network Automation using AI & MCP, then you may want to [**start here**](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55).

## 📄 Disclaimer
You are responsible for defining your own troubleshooting methodologies and context files, as well as building your own test environment and meeting the necessary conditions (e.g., RAM/vCPU, router OS images, Claude subscription/API key, etc.).

## 📜 License
Licensed under the [**GNU GENERAL PUBLIC LICENSE Version 3**](https://github.com/pdudotdev/aiNOC/blob/main/LICENSE).

## 📧 Collaborations
Interested in collaborating?
- **Email**:  
  - Reach out at **hello@ainoc.dev**
- **LinkedIn**:
  - Let's discuss via [**LinkedIn**](https://www.linkedin.com/in/tmihaicatalin/)