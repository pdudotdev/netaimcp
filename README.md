# ✨ aiNOC

[![Latest Release](https://img.shields.io/badge/version-4.5.0-blue.svg)](https://github.com/pdudotdev/aiNOC/releases/tag/4.5.0)
[![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/aiNOC)](https://github.com/pdudotdev/aiNOCcommits/main/)

![Cisco IOS-XE](https://img.shields.io/badge/Cisco-IOS--XE-0176C1)
![Arista EOS](https://img.shields.io/badge/Arista-EOS-2A64D4)
![MikroTik RouterOS](https://img.shields.io/badge/MikroTik-RouterOS-2A3042)

![Transports](https://img.shields.io/badge/Transports-555555)
![SSH](https://img.shields.io/badge/SSH-2E8B57)
![eAPI](https://img.shields.io/badge/eAPI-D4841A)
![REST API](https://img.shields.io/badge/REST_API-7B52AB)

## 📖 **Table of Contents**
- 📜 **aiNOC Project**
  - [🔭 Overview](#-overview)
  - [♻️ Repository Lifecycle](#️-repository-lifecycle)
  - [🍀 Here's a Quick Demo](#-heres-a-quick-demo)
  - [⭐ What's New in v4.0](#-whats-new-in-v40)
  - [⚒️ Current Tech Stack](#️-current-tech-stack)
  - [📋 Supported Vendors](#-supported-vendors)
  - [🖇️ Supported Transports](#️-supported-transports)
  - [🎓 Troubleshooting Scope](#-troubleshooting-scope)
  - [🛠️ Installation & Usage](#️-installation--usage)
  - [🔄 Test Network Topology](#-test-network-topology)
  - [📞 aiNOC in On-Call Mode](#-ainoc-in-on-call-mode)
  - [⬆️ Planned Upgrades](#️-planned-upgrades)
  - [🌱 AI Automation 101](#-ai-automation-101)
  - [📄 Disclaimer](#-disclaimer)
  - [📜 License](#-license)
  - [📧 Professional Collaborations](#-professional-collaborations)

## 🔭 Overview
aiNOC is an AI-based **network troubleshooting framework** for multi-vendor, multi-protocol, multi-area/multi-AS, OSI L2-L4 enterprise networks.

**Key characteristics:**
- [x] **Multi-vendor support**
- [x] **Multi-protocol, L2-L4**
- [x] **Multi-area/multi-AS**
- [x] **SSH/eAPI/REST API**
- [x] **15 MCP tools, 6 skills**
- [x] **32 operational guardrails**
- [x] **Jira integration**

Operating mode of **aiNOC**:
- [x] **On-Call mode (OC)** *(primary)*
  - Agent is invoked by SLA path failures, see [**On-Call Mode**](#-on-call-mode)
  - Ad-hoc troubleshooting via the console is also supported

**Important project files**:
- [x] See [**file roles**](metadata/about/file_roles.md)

**Agent guardrails list**:
- [x] See [**guardrails**](metadata/about/guardrails.md)

**Supported models**:
- [x] Haiku 4.5 (best for costs)
- [x] Sonnet 4.6 (best balance)
- [x] Opus 4.6 (default, best reasoning)

⚠️ **NOTE:** Due to the intermittent nature of troubleshooting, it's worth using an advanced model by default - costs won't become unsustainable even if troubleshooting several issues per day.

**Set your default model**:<br/>
Create `settings.json` under `.claude/`:
```
{
  "model":"opus",
  "effortLevel":"medium"
}
```

**High-level architecture:**

![arch](metadata/topology/ARCHv3.png)

## 🍀 Here's a Quick Demo
- [x] ▶ See a [**DEMO HERE**](https://www.youtube.com/watch?v=oxSa25R6EgI) for v3.0.
  - *Next video demo coming with the next major release*

## ♻️ Repository Lifecycle
**New features** are being added periodically (vendors, protocols, integrations, etc.).

**Stay up-to-date**:
- [x] **Watch** and **Star** this repository

**Current version**:
- [x] **aiNOC v4.5**

## ⭐ What's New in v4.5
- [x] See **changelog.md**

## ⚒️ Current Tech Stack

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

## 🖇️ Supported Transports

| Vendor | Transport |
|--------|-----------|
| Cisco IOS | Scrapli SSH |
| Arista EOS | Arista eAPI |
| MikroTik RouterOS | REST API |

## 🎓 Troubleshooting Scope

| Category | Capabilities |
|----------|-------------|
| **OSPF** | Reference bandwidth · Point-to-point links · Passive interfaces · MD5 authentication · External type 1 routes · Default route injection · ABR route summarization · EIGRP ↔ OSPF redistribution · Prefix list filtering · Distribute list filtering · Area types: normal, stubby, totally NSSA |
| **EIGRP** | Passive interfaces · MD5 authentication · Stub summary · OSPF ↔ EIGRP redistribution · Default metric via route maps |
| **BGP** | eBGP dual-ISP · Default-originate · Prefix lists and route maps · Route reflectors and clients |
| **Others** | Policy-Based Routing · IP SLA · MikroTik Netwatch · Arista Connectivity Monitor · NAT/PAT on ASBRs · Management APIs · Static routing · Syslog · NTP |

## 🛠️ Installation & Usage
**Step 1**:
```
git clone https://github.com/pdudotdev/aiNOC/
cd aiNOC
python3 -m venv mcp
source mcp/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Step 2**:

The included `CLAUDE.md` and `/skills/*` are templates. **Customize them** with your own troubleshooting methodology, tool descriptions, and operational guidelines.

**Step 3**:
- Configure IP SLA, Connectivity Monitor, Netwatch etc. paths in your network
- Make sure they are being tracked and logged remotely to **Vector** (Syslog)
- Configure the transforms inside `/etc/vector/vector.yaml` - [**example**](metadata/about/vector.yaml)
- aiNOC monitors Vector's `/var/log/network.json` file for specific logs and parses them

**Step 4**:
Run **aiNOC** in **On-Call Mode**, in the terminal or as a **daemon**:
```
python3 oncall_watcher.py      # default: interactive terminal
python3 oncall_watcher.py -d   # daemon mode, across reboots
```

**Step 5**:
Check if **Watcher** and **Vector** are running:
```
sudo systemctl status oncall_watcher.service
sudo systemctl status vector
```

## 🔄 Test Network Topology
**Network diagram**:

![topology](metadata/topology/TOPOLOGY-v2.0.png)

**Naming conventions:**
- [x] **RXY** where:
  - **R**: device type (router)
  - **X**: device number id
  - **Y**: vendor (A-Arista, C-Cisco, M-MikroTik, etc.)

**Router configurations:**
- [x] Please find my test lab's config files under the [**lab_configs**](https://github.com/pdudotdev/aiNOC/tree/main/lab_configs) directory
- [x] They are the network's fallback configs for `containerlab redeploy -t lab.yml`
- [x] Default credentials: see **.env** file at [**.env.example**](.env.example)

## 📞 aiNOC in On-Call Mode
**On-Call Mode** is the primary operating mode of aiNOC (introduced in v3.0, enhanced in v4.0 and v4.5).

### What it does, in a nutshell?
- [x] User configures connectivity paths
  - **Cisco**: IP SLA & tracking
  - **Arista**: Connectivity Monitor
  - **MikroTik**: NetWatch
- [x] User configures **Syslog** and **NTP**
- [x] User configures **Syslog** server (Vector)
- [x] User configures **Vector** with correct transforms
- [x] Connectivity path failures are logged to **Syslog**
- [x] **Vector** listens for and parses multi-vendor logs
- [x] `sla_paths/paths.json` outlines paths for the agent
- [x] `oncall/watcher.py` monitors Vector for new logs
- [x] Once a new log arrives, the agent is invoked
- [x] Watcher creates a new **Jira** ticket
- [x] Agent gets log details pre-filled in prompt
- [x] Agent starts troubleshooting procedures (`CLAUDE.md`, `/skills`, etc.)
- [x] Identifies root cause and potential fix
- [x] Upon user approval, applies and verifies the fix
- [x] Logs results to **Jira** ticket and marks completion
- [x] Actions logged to `oncall/watcher.log`
- [x] Skipped events are deferred for later analysis

## ⬆️ Planned Upgrades
Expected in version v5.0:
- [ ] Fresh, enterprise-focused topology
- [ ] New vendors (Juniper, Aruba, SONiC)
- [ ] New protocols (VRRP/HSRP, STP/MSTP)
- [ ] Performance-based SLAs
- [ ] NetBox integration

## 🌱 AI Automation 101
If you're completely new to Network Automation using AI & MCP, then you may want to [**start here**](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55) before moving on.

## 📄 Disclaimer
You are responsible for defining your own troubleshooting methodologies and context files, as well as building your own test environment and meeting the necessary conditions (e.g., RAM/vCPU, router OS images, Claude subscription/API key, etc.).

## 📜 License
Licensed under the [**GNU GENERAL PUBLIC LICENSE Version 3**](https://github.com/pdudotdev/aiNOC/blob/main/LICENSE).

## 📧 Professional Collaborations
Interested in customizing and adapting **aiNOC** to your own network, or looking to collaborate long-term?
- **Email**:  
  - Please direct your inquiries to **hello@ainoc.dev**.
- **LinkedIn**:
  - Send me a DM on [**LinkedIn**](https://www.linkedin.com/in/tmihaicatalin/) and let's talk. 