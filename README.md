# ✨ aiNOC

[![Version](https://img.shields.io/badge/version-5.5.0-1a1a2e)](https://github.com/pdudotdev/aiNOC/releases/tag/5.5.0)
![License](https://img.shields.io/badge/license-BSL%201.1-1a1a2e)
[![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/aiNOC?color=1a1a2e)](https://github.com/pdudotdev/aiNOC/commits/main/)

| | |
|---|---|
| | **Core Version** |
| **Vendors** | ![Cisco IOS-XE](https://img.shields.io/badge/Cisco_IOS--XE-0d47a1) |
| **Management** | ![RESTCONF](https://img.shields.io/badge/RESTCONF-1565c0) ![CLI](https://img.shields.io/badge/CLI-1565c0) |
| **Integrations** | ![Jira](https://img.shields.io/badge/Jira-1976d2) ![NetBox](https://img.shields.io/badge/NetBox-1976d2) ![Discord](https://img.shields.io/badge/Discord-1976d2) ![HashiCorp Vault](https://img.shields.io/badge/HashiCorp_Vault-1976d2) |
| | **On-Request** |
| **Vendors** | ![Arista EOS](https://img.shields.io/badge/Arista_EOS-1e88e5) ![Juniper JunOS](https://img.shields.io/badge/Juniper_JunOS-1e88e5) ![Aruba AOS-CX](https://img.shields.io/badge/Aruba_AOS--CX-1e88e5) ![SONiC FRR](https://img.shields.io/badge/SONiC_FRR-1e88e5) ![MikroTik RouterOS](https://img.shields.io/badge/MikroTik_RouterOS-1e88e5) ![VyOS](https://img.shields.io/badge/VyOS-1e88e5) |
| **Management** | ![NETCONF](https://img.shields.io/badge/NETCONF-2196f3) ![REST APIs](https://img.shields.io/badge/REST_APIs-2196f3) ![gNMI](https://img.shields.io/badge/gNMI-2196f3) ![eAPI](https://img.shields.io/badge/eAPI-2196f3) |
| **Integrations** | ![Slack](https://img.shields.io/badge/Slack-42a5f5) ![ServiceNow](https://img.shields.io/badge/ServiceNow-42a5f5)
| | **Stats** |
| **Performance** | ![MTTD](https://img.shields.io/badge/MTTD-4s-64b5f6) ![MTTR](https://img.shields.io/badge/MTTR-8min-64b5f6) ![Cost/Session](https://img.shields.io/badge/Avg.%20cost%2Fsession-%241.86-64b5f6) |

## 📖 **Table of Contents**
- 📜 **aiNOC**
  - [🔭 Overview](#-overview)
  - [🍀 Here's a Quick Demo](#-heres-a-quick-demo)
  - [⭐ What's New in v5.5](#-whats-new-in-v55)
  - [⚒️ Current Tech Stack](#️-current-tech-stack)
  - [📋 Supported Vendors](#-supported-vendors)
  - [🚛 Supported Transports](#-supported-transports)
  - [🎓 Troubleshooting Scope](#-troubleshooting-scope)
  - [🛠️ Installation & Usage](#️-installation--usage)
  - [🔄 Test Network Topology](#-test-network-topology)
  - [📞 aiNOC Service Mode](#-ainoc-service-mode)
  - [⬆️ Planned Upgrades](#️-planned-upgrades)
  - [♻️ Repository Lifecycle](#️-repository-lifecycle)
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
- [x] **NETCONF/REST/gNMI/eAPI**
- [x] **15 MCP tools, 4 skills**
- [x] **12 operational guardrails**
- [x] **HITL for any config changes**
- [x] **Dashboard for agent monitoring**
- [x] **Discord integration**
- [x] **Jira integration**
- [x] **HashiCorp Vault**
- [x] **NetBox**

▫️ **Core vs. On-Request features**:
- [x] **Core**: 
  - Easy to integrate in Cisco IOS/IOS-XE environments
  - CLI, RESTCONF management, OSPF/BGP troubleshooting
  - Jira, Discord, NetBox, HashiCorp Vault integration
- [x] **On-Request**: 
  - Custom vendor modules (Arista, Juniper, MikroTik, etc.)
  - Custom management (REST APIs, NETCONF, gNMI, eAPI) 
  - Built and adapted per client's network environment

▫️ **aiNOC operating mode in v5.0+**:
- [x] See [**aiNOC Service Mode**](#-ainoc-service-mode)

▫️ **Important project files**:
- [x] See [**file roles**](metadata/about/file_roles.md)

▫️ **Agent guardrails list**:
- [x] See [**guardrails**](metadata/about/guardrails.md)

▫️ **Supported models**:
- [x] Haiku 4.5
- [x] Sonnet 4.6
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

![arch](metadata/topology/ARCHv5.png)

## 🍀 Here's a Quick Demo
- [x] See a [**DEMO**](https://www.youtube.com/watch?v=w5E-MTINkyU) of **aiNOC v5.5**

## ⭐ What's New in v5.5
- [x] See [**changelog.md**](changelog.md)

## ⚒️ Core Tech Stack

| Tool |   |
|------|---|
| Claude Code | ✓ |
| MCP (FastMCP) | ✓ |
| Python | ✓ |
| Scrapli | ✓ |
| Genie | ✓ |
| RESTCONF | ✓ |
| Jira API | ✓ |
| Discord API | ✓ |
| HashiCorp Vault | ✓ |
| NetBox | ✓ |
| Vector | ✓ |
| Ubuntu | ✓ |

## 📋 Supported Vendors

| Vendor | Platform | cli_style | Status |
|--------|----------|-----------|--------|
| Cisco | IOS-XE | `ios` | Core |
| Arista | EOS | `eos` | On-Request |
| Juniper | JunOS | `junos` | On-Request |
| MikroTik | RouterOS | `routeros` | On-Request |
| Aruba | AOS-CX | `aos` | On-Request |
| SONiC | FRR | `frr` | On-Request |
| VyOS | VyOS | `vyos` | On-Request |

## 🚛 Supported Transports

| Management | Devices | Tier | Status |
|-----------|---------|------|--------|
| RESTCONF | Cisco IOS-XE | Primary | Core |
| CLI | Cisco IOS-XE | Fallback | Core |
| NETCONF | custom | — | On-Request |
| REST APIs | custom | — | On-Request |
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

| aiNOC On-Request Extensions |
|----------|
| **EIGRP** |
| **HSRP** | 
| **VRRP** |
| *etc.* |

## 🛠️ Installation & Usage
▫️ **Step 1**:
```
git clone https://github.com/pdudotdev/aiNOC/
cd aiNOC/
python3 -m venv mcp
source mcp/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

▫️ **Step 2**:
The included `CLAUDE.md` and `skills/*` are templates. **Customize them** with your own troubleshooting methodology, tool descriptions, and operational guidelines.

⚠️ **NOTE**: There is no one-size-fits-all `CLAUDE.md` or `SKILL.md` that works in any network environment. These should be customized for each specific topology, vendor combination, and architecture.

▫️ **Step 3**:
- Configure IP SLA (or Connectivity Monitor, Netwatch etc.) paths in your network
- Make sure they are being tracked and logged remotely to **Vector** (Syslog)
- Configure the transforms inside `/etc/vector/vector.yaml` - [**example**](metadata/about/vector.yaml)
- aiNOC monitors Vector's `/var/log/network.json` file for specific logs and parses them per-vendor

▫️ **Step 4**:
Run the **aiNOC** watcher and dashboard services. 
Claude is invoked non-interactively via **tmux + print mode** (`-p`) with a default prompt template. 
The human operator monitors agent operations via the **web dashboard on <IP>:5555**, and interacts via **Discord** (fix approval ✅ or rejection ❌ embeds).

```
sudo apt install tmux
sudo cp oncall/oncall-watcher.service /etc/systemd/system/
sudo cp dashboard/oncall-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oncall-watcher.service
sudo systemctl enable --now oncall-dashboard.service
```
Manage with:
`systemctl start | stop | restart | status oncall-watcher`

▫️ **Step 5**:
Check if the **service** and **Vector** are running:
```
sudo systemctl status vector
sudo systemctl status oncall-watcher.service
sudo systemctl status oncall-dashboard.service
```

## 🔄 Test Network Topology
▫️ **Network diagram**:

![topology](metadata/topology/TOPOLOGY-v5.0.png)

▫️ **Router configurations:**
- [x] Please find my test lab's config files under the [**lab_configs**](https://github.com/pdudotdev/aiNOC/tree/main/lab_configs) directory
- [x] They are the network's fallback configs for `containerlab redeploy -t AINOC-TOPOLOGY.yml`
- [x] Default credentials: see **.env** file at [**.env.example**](.env.example)

## 📞 aiNOC Service Mode

aiNOC runs as an **on-call watcher** that monitors Vector's `/var/log/network.json` for SLA path failures and automatically invokes a Claude agent to diagnose the issue and propose a fix.

### How It Works

1. Network devices track connectivity paths (Cisco **IP SLA** — extensible to Arista Connectivity Monitor, Juniper RPM probes, MikroTik Netwatch etc.)
2. Failures are logged remotely to **Syslog** → **Vector** records, parses, and writes to `/var/log/network.json`
3. `oncall-watcher` service detects the SLA failure, opens a **Jira** ticket, and invokes the **aiNOC agent** session
4. **Web dashboard** is activated and displays agent's work in real time. User is notified and kept in the loop via **Discord**.
5. Agent follows structured troubleshooting methodology: `CLAUDE.md` + `/skills` + `MCP tools` → identifies root cause(s) → proposes fix
6. Only upon **human operator approval** via Discord, the agent applies and verifies the fix, otherwise issue is documented and the case stays open
7. Case resolution is logged to **Jira** and **Discord**, and the watcher resumes monitoring
8. aiNOC agent learns a new lesson about network troubleshooting and documents to `lessons.md`

See [**Installation & Usage**](#️-installation--usage) for instructions.

## ⬆️ Planned Upgrades
- [ ] New protocols supported
- [ ] Performance-based SLAs

## ♻️ Repository Lifecycle
**New features** are being added periodically (protocols, integrations, optimizations).

**Stay up-to-date**:
- [x] **Watch** and **Star** this repository

**Current version**:
- [x] **aiNOC v5.5**

## 📄 Disclaimer
You are responsible for defining your own troubleshooting methodologies and context files, as well as building your own test environment and meeting the necessary conditions (e.g., RAM/CPU, Claude subscription/API key, etc.).

## 📜 License
Licensed under the [**Business Source License 1.1**](https://github.com/pdudotdev/aiNOC/blob/main/LICENSE).
The source code is available for research, educational, and non-commercial use. Commercial use, SaaS deployment, enterprise automation, or resale of this software is prohibited without explicit written permission from the author.

## 📧 Collaborations
Interested in collaborating?
- **Email**:  
  - Reach out at [**hello@ainoc.dev**](mailto:hello@ainoc.dev)
- **LinkedIn**:
  - Let's discuss via [**LinkedIn**](https://www.linkedin.com/in/tmihaicatalin/)