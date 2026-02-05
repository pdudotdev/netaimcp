# ✨ Network Automation and Troubleshooting with Claude AI, MCP, and Python

[![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/netaimcp)](https://github.com/pdudotdev/netaimcp/commits/main/)

## 📖 Table of Contents
- ⚙️ **Troubleshooting Networks with Claude and MCP**
  - [🔭 Overview](#-overview)
  - [⚒️ Tech Stack](#-tech-stack)
  - [📋 Included Vendors](#-included-vendors)
  - [🎓 Networking Topics](#-networking-topics)
  - [🔄 Network Topology](#-network-topology)
  - [🔥 Automation and Troubleshooting](#-scenarios)
  - [⬆️ Planned Upgrades](#-planned-upgrades)
  - [⚠️ Disclaimer](#-disclaimer)
  - [📜 License](#-license)

## 🔭 Overview
The purpose of this project is to showcase the capabilities of **Claude AI** and **MCP**, combined with **Python** and **Scrapli**, in regards to network automation and troubleshooting.

By design, the project is **multi-vendor**, **multi-protocol**, **multi-area/multi-AS**, **OSI L3-focused**, in order to automate and troubleshoot various scenarios in a diverse and complex network.

I am **NOT** going to explain here how to build the topology | write the MCP server in Python | enhance the MCP server with new tools. I already did that from scratch in my beginner-friendly [**Udemy course**](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55). Feel free to join to get instructor support, regular updates, access to Discord etc.

However, I am providing the **topology diagram**, the **startup config** of each router, as well as the actual **Containerlab YAML file** defining the network.

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
- [x] VS Code
- [x] Ubuntu 24
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
  - [Lab topology](lab.yml)

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

⚠️ **NOTE**: To see the contents of the **nvram** files for Cisco routers, simply use **Notepad** in Windows or **cat** in Linux.

⚠️ **NOTE**: The config files above are considered the **default configuration** for this network, and their contents may change (or new files may be added) with each new **Release**, as the topology grows in complexity. Watch the release number and notes for this repository.

⚠️ **NOTE**: Since these config files above are considered the **default configuration** for this network, they are going to be your fallback config whenever you use `containerlab redeploy -t lab.yml`

## 🔥 Automation and Troubleshooting
Troubleshooting scenarios are located in the [**troubleshoot.md**](https://github.com/pdudotdev/netaimcp/blob/main/scenarios/troubleshoot.md) file that is going to be constantly updated as the network grows in complexity.

✍️ **NOTE**: Each scenario is created by starting from the **default configuration** of the network (see [Network Topology](#-network-topology)) and intentionally breaking one or more things to trigger a certain type of failure. Then, with just a simple prompt, we enable Claude to use the MCP server for identifying the root cause(s) and fixing the network. 

### Example of scenario workflow
Each **troubleshooting scenario** has the following structure:
- [x] **Summary**:
```
R3C lost R2A as an OSPF neighbor.
```
- [x] **Causing Failure**: 
```
Changing the MTU on R2A to cause a mismatch, using the commands below:

interface FastEthernet0/1
 mtu 1400
```
- [x] **Confirming Failure**:
```
Checking the effects of the commands above:

show interfaces FastEthernet0/1
show ip ospf neighbor
```
- [x] **Claude Prompt**:
```
Why is the R2A-R3C OSPF neighborship broken? Can you check and fix please?
```
- [x] **Commands by Claude**:
```
show ip ospf neighbor
show interfaces FastEthernet0/1
show ip ospf interface FastEthernet0/1
interface FastEthernet0/1
mtu 1500
```
- [x] **Confirmation by Claude**:
```
Problem found!
Cause: The MTU on R2A's FastEthernet0/1 doesn't match R3C's.
<...>
Fix: Setting MTU to 1500 on R2A's FastEthernet0/1.
OSPF adjacency is now fully operational.
```

📂 **NOTE**: All automation (non-troubleshooting) scenarios related to **network information gathering**, **pushing changes to multiple network devices**, **network state validation** etc. are going to be added in an upcoming release. The priority now is **troubleshooting**.

## 🧪 Planned Upgrades
- [ ] Adding BGP
- [ ] Adding IS-IS
- [ ] Adding new vendors

## ⚠️ Disclaimer
This project is intended for educational purposes only. Users are responsible for building their own lab environment and meeting the necessary conditions (e.g., RAM/vCPU, router OS images, Claude subscription/API key, etc.). Use this tool responsibly.

## 📜 License
Licensed under the [GNU GENERAL PUBLIC LICENSE Version 3](https://github.com/pdudotdev/netaimcp/blob/main/LICENSE).