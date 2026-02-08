# ✨ Network Automation and Troubleshooting with Claude, MCP, and Python

[![Stable Release](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/pdudotdev/netaimcp/releases/tag/v1.0.0)
[![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/netaimcp)](https://github.com/pdudotdev/netaimcp/commits/main/)

## 📖 Table of Contents
- ⚙️ **Troubleshooting Networks with Claude and MCP**
  - [🔭 Overview](#-overview)
  - [⚒️ Tech Stack](#-tech-stack)
  - [📋 Included Vendors](#-included-vendors)
  - [🎓 Networking Topics](#-networking-topics)
  - [🔄 Network Topology](#-network-topology)
  - [🔥 Automation and Troubleshooting](#-automation-and-troubleshooting)
  - [⚠️ Disclaimer](#-disclaimer)
  - [📜 License](#-license)

## 🔭 Overview
The purpose of this project is to showcase the capabilities of **Claude** and **MCP**, combined with **Python** and **Scrapli**, in regards to network automation and troubleshooting.

By design, the project is **multi-vendor**, **multi-protocol**, **multi-area/multi-AS**, **OSI L3-focused**, in order to automate and troubleshoot various scenarios in a diverse and complex network.

I am **NOT** going to explain here how to: build the topology • write the MCP server in Python • enhance the MCP server with new tools. I already did that from scratch in my beginner-friendly [**Udemy course**](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55). 

**Join the course to get:**
- [x] **Lab manual** (PDF) for this project
- [x] Full instructor support (Q&A)
- [x] Regular upgrades (monthly)
- [x] Access to a private Discord

⚠️ **NOTE**: This project assumes at least **CCNA**-level knowledge (**CCNP** preferred), as well as familiarity with **Linux** terminal commands, **Python** syntax, and multi-vendor **CLIs**.

🍀 **NOTE**: This is an evolving project, with new features being added periodically, so feel free to check back once in a while.

## ⚒️ Tech Stack
The main tools and technologies used for building the project:
- [x] Claude AI (Claude Code)
- [x] MCP Server (FastMCP)
- [x] ContainerLab
- [x] Docker
- [x] Python
- [x] Scrapli
- [x] Ubuntu
- [x] VS Code
- [x] VirtualBox/VMware

## 📋 Included Vendors
- [x] **Arista**: EOS (cEOS)
- [x] **Cisco**: IOS/IOS-XE (IOL)

## 🎓 Networking Topics
Networking topics in this topology:
- [x] **OSPF multi-area**:
  - Basic protocol config
    - Reference bandwidth
    - Point-to-point links
    - Passive interfaces
    - MD5 authentication
    - External type 1 routes
  - Route redistribution
  - Route summarization (ABR)
  - Route filtering with prefix lists
  - Route filtering with distribute lists
  - Area types: normal, totally stubby, totally nssa

- [x] **EIGRP**:
  - Basic protocol config
    - Passive interfaces
    - MD5 authentication
    - Stub connected/summary
  - Local summarization
  - Route redistribution
  - Default metric via route map

- [x] **Others**:
  - Policy-Based Routing
  - IP SLA icmp-echo

## 🔄 Network Topology
- [x] Current network topology
  - *Subject to periodic upgrades*

![topology](/topology/TOPOLOGY.png)

- [x] Containerlab YAML file:
  - [**Lab topology**](lab.yml)

- [x] Router naming convention:
  - **RXY** where:
    - **R**: device type (router)
    - **X**: device number id
    - **Y**: vendor (A-Arista, C-Cisco, etc.)

- [x] Router configuration files:
  - R1A: [startup-config](https://github.com/pdudotdev/netaimcp/blob/main/clab-mcp-lab/R1A/flash/)
  - R2A: [startup-config](https://github.com/pdudotdev/netaimcp/blob/main/clab-mcp-lab/R2A/flash/)
  - R3C: [nvram_id](https://github.com/pdudotdev/netaimcp/blob/main/clab-mcp-lab/R3C)
  - R4C: [nvram_id](https://github.com/pdudotdev/netaimcp/tree/main/clab-mcp-lab/R4C)
  - R5C: [nvram_id](https://github.com/pdudotdev/netaimcp/tree/main/clab-mcp-lab/R5C)
  - R6A: [startup-config](https://github.com/pdudotdev/netaimcp/blob/main/clab-mcp-lab/R6A/flash/)
  - R7A: [startup-config](https://github.com/pdudotdev/netaimcp/blob/main/clab-mcp-lab/R7A/flash/)
  - R8C: [nvram_id](https://github.com/pdudotdev/netaimcp/tree/main/clab-mcp-lab/R8C)
  - R9C: [nvram_id](https://github.com/pdudotdev/netaimcp/tree/main/clab-mcp-lab/R9C)
  - R10C: [nvram_id](https://github.com/pdudotdev/netaimcp/tree/main/clab-mcp-lab/R10C)
  - R11C: [nvram_id](https://github.com/pdudotdev/netaimcp/tree/main/clab-mcp-lab/R11C)

⚠️ **NOTE**: The config files above are considered the **default configuration** for this network, and their contents may change (or new files may be added) with each **new release**, as the topology grows in complexity. Watch the release number and notes for this repository.

⚠️ **NOTE**: Since these config files above are considered the **default configuration** for this network, they are going to be your fallback config whenever you use `containerlab redeploy -t lab.yml`

## 🔥 Automation and Troubleshooting
Troubleshooting scenarios are located in the [**troubleshoot.md**](https://github.com/pdudotdev/netaimcp/blob/main/scenarios/troubleshoot.md) file that is going to be constantly updated as the network grows in complexity.

✍️ **NOTE**: Each scenario is created by starting from the **default configuration** of the network (see [Network Topology](#-network-topology)) and intentionally breaking one or more things to trigger a certain type of failure. Then, with just a simple prompt, we enable Claude to use the MCP server for identifying the root cause(s) and fixing the network. 

### Example of scenario workflow
Each **troubleshooting scenario** has the following structure:
- [x] **Summary**:
```
R1A OSPF adjacency stuck in EXCHANGE, while R2A is stuck in EXCH START state.
```
- [x] **Causing Failure**: 
```
Changing the MTU on R2A to cause a mismatch with R1A, using the commands below:

interface Ethernet 3
 mtu 1400
```
- [x] **Confirming Failure**:
```
Checking the effects of the commands above:

R2A(config-if-Et3)#show interfaces Ethernet 3 | i MTU
  IP MTU 1400 bytes, BW 1000000 kbit
R2A(config-if-Et3)#show ip ospf neighbor 
Neighbor ID     Instance VRF      Pri State                  Dead Time   Address         Interface
3.3.3.3         1        default  1   FULL                   00:00:35    10.0.0.10       Ethernet4
1.1.1.1         1        default  0   EXCH START             00:00:34    10.0.0.1        Ethernet3
7.7.7.7         1        default  0   FULL                   00:00:34    10.1.1.9        Ethernet2
6.6.6.6         1        default  0   FULL                   00:00:33    10.1.1.13       Ethernet1

R1A#show ip ospf neighbor
Neighbor ID     Instance VRF      Pri State                  Dead Time   Address         Interface
2.2.2.2         1        default  0   EXCHANGE               00:00:32    10.0.0.2        Ethernet4
3.3.3.3         1        default  1   FULL                   00:00:38    10.0.0.6        Ethernet3
11.11.11.11     1        default  1   FULL                   00:00:32    172.16.0.10     Ethernet2
10.10.10.10     1        default  1   FULL                   00:00:30    172.16.0.6      Ethernet1
```
- [x] **User Prompt**:
```
Why is the R1A-R2A OSPF adjacency stuck? Can you check and fix please?
```
- [x] **Commands issued by Claude**:
```
show ip ospf neighbor
show ip ospf interface Ethernet 3
show running-config interface Ethernet 3
interface Ethernet 3
no mtu 1400
```
- [x] **Confirmation**:
```
R2A#show ip ospf neighbor
Neighbor ID     Instance VRF      Pri State                  Dead Time   Address         Interface
3.3.3.3         1        default  1   FULL                   00:00:34    10.0.0.10       Ethernet4
1.1.1.1         1        default  0   FULL                   00:00:38    10.0.0.1        Ethernet3
7.7.7.7         1        default  0   FULL                   00:00:29    10.1.1.9        Ethernet2
6.6.6.6         1        default  0   FULL                   00:00:33    10.1.1.13       Ethernet1 
```

📂 **NOTE**: All automation (non-troubleshooting) scenarios related to **network information gathering**, **pushing changes to multiple network devices**, **network state validation** etc. are going to be added in an upcoming release (see the **Lab Manual** inside the course). The priority now is **troubleshooting**.

## ⚠️ Disclaimer
This project is intended for educational purposes only. Users are responsible for building their own lab environment and meeting the necessary conditions (e.g., RAM/vCPU, router OS images, Claude subscription/API key, etc.).

## 📜 License
Licensed under the [GNU GENERAL PUBLIC LICENSE Version 3](https://github.com/pdudotdev/netaimcp/blob/main/LICENSE).