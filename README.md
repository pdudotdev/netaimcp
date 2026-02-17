# ✨ Network Automation and Troubleshooting with Claude, MCP, and Python

[![Latest Release](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/pdudotdev/netaimcp/releases/tag/2.0.0)
[![Last Commit](https://img.shields.io/github/last-commit/pdudotdev/netaimcp)](https://github.com/pdudotdev/netaimcp/commits/main/)

## 📖 **Table of Contents**
- 📜 **Lab Manual**
  - [🔭 Overview](#-overview)
  - [⭐ What's New in v2.0](#-whats-new-in-v20)
  - [🌱 AI Network Automation 101](#-ai-network-automation-101)
  - [♻️ Repository Lifecycle](#%EF%B8%8F-repository-lifecycle)
  - [⚒️ Tech Stack](#%EF%B8%8F-tech-stack)
  - [📋 Included Vendors](#-included-vendors)
  - [🎓 Networking Topics](#-networking-topics)
  - [🛠️ Environment Setup](#%EF%B8%8F-environment-setup)
  - [📂 Router OS Images](#-router-os-images)
  - [🖥️ Terminal Management](#%EF%B8%8F-terminal-management)
  - [🔄 Network Topology](#-network-topology)
  - [🔥 Troubleshooting](#-troubleshooting)
  - [🌱 Starting Fresh](#-starting-fresh)
  - [⬆️ Planned Upgrades](#%EF%B8%8F-planned-upgrades)
  - [📄 Disclaimer](#-disclaimer)
  - [📜 License](#-license)

## 🔭 Overview
The purpose of this project is to showcase the capabilities of **Claude Code**, **MCP**, **Python**, and other tools, in regards to troubleshooting and automating network tasks.

Key characteristics of this project:
- [x] **Multi-vendor**
- [x] **Multi-protocol**
- [x] **Multi-area/multi-AS**
- [x] **SSH/eAPI/REST API**
- [x] **OSI L3-focused**

What you'll find below:
- [x] How to **setup this lab** from scratch
- [x] The current **topology diagram** PNG
- [x] The **startup config** of each router
- [x] The **Containerlab YAML** lab file
- [x] The **NETWORK.json** inventory file
- [x] Important notes and guidance

⚠️ **NOTE**: This project assumes **CCNP**-level knowledge, as well as familiarity with **Linux** terminal commands, **Python** syntax, and multi-vendor **CLIs**.

## ⭐ What's New in v2.0
• The 2.0.0 upgrade is focused on:
- [x] Network topology expansion
- [x] Improving the MCP toolset
- [x] Optimizing AI performance
- [x] Less hallucinations and costs
- [x] Going beyond SSH connections

• Updates for reduced hallucinations, command repetition avoidance, API cost reductions:
- [x] Returning **structured outputs** (Cisco: Genie, Arista: eAPI, MikroTik: REST API).
- [x] Strict command determinism: **platform_map**, query enums in input models, platform-aware commands.
- [x] Tool **caching feature** to avoid duplicate commands in a short time span and avoid tshoot loops.
- [x] Improved MCP server code with **protocol-specific** and clear, helpful tools for troubleshooting.
- [x] Avoiding to dump entire show run output using targeted config sections and protocol views.
- [x] Updated **INTENT.json** and **NETWORK.json** for better network context.
- [x] The legacy **run_show** tool is now just a fallback method.
- [x] Improved tool docstrings with clear instructions.

• Enhancements:
- [x] New vendor added: **MikroTik**
- [x] New protocol added: **BGP**
- [x] Protocol-specific MCP tools
- [x] Claude reasoning highlighted
- [x] Cisco: **Genie** output parsing
- [x] Arista: **eAPI** instead of SSH
- [x] MikroTik: **REST API** queries
- [x] Platform map with commands
- [x] Cleaner, more modular code
- [x] Improved topology diagram
- [x] Minor bug fixing

## 🌱 AI Network Automation 101
If you're completely new to Network Automation using AI & MCP, then you may want to [start here](#-starting-fresh) before moving on with this lab.

## ♻️ Repository Lifecycle
This repository is **NOT** static. I am periodically adding **new features** (devices, vendors, protocols, configs, optimizations).

**Stay up-to-date**:
- [x] **Watch** and **Star** this repository

**Current version**:
- [x] The current version of this project is **v2.0**

## ⚒️ Tech Stack
The main tools and technologies used for building the project:
- [x] Claude AI (Claude Code)
- [x] MCP Server (FastMCP)
- [x] ContainerLab
- [x] Python
- [x] Scrapli
- [x] Genie
- [x] REST API
- [x] EOS eAPI
- [x] Ubuntu
- [x] VS Code
- [x] VirtualBox/VMware

## 📋 Included Vendors
- [x] **Arista**: EOS (cEOS)
- [x] **Cisco**: IOS/IOS-XE (IOL)
- [x] **MikroTik**: RouterOS

## 🎓 Networking Topics
Networking topics in this topology:
- [x] **OSPF multi-area**:
  - Basic protocol config
    - Reference bandwidth
    - Point-to-point links
    - Passive interfaces
    - MD5 authentication
    - External type 1 routes
  - Route redistribution EIGRP-OSPF
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
  - Route redistribution OSPF-EIGRP
  - Default metric via route map

- [x] **BGP**:
  - eBGP/iBGP neighbors
  - iBGP next-hop-self
  - ISP default-originate
  - Prefix list and route map
  - Route reflector in ISP A

- [x] **Others**:
  - Policy-Based Routing
  - IP SLA icmp-echo
  - Management APIs

## 🛠️ Environment Setup
Below you'll find guidance for building the lab before you move to the network topology section.

**My VM resources for this lab**:
- [x] VirtualBox or VMware
- [x] Ubuntu 24.04.4 VM
- [x] 12 processor cores
- [x] 32 GB RAM memory
- [x] 50 GB hard disk

**Resource consumption**:
Resources are not yet fully used, but they need to account for peak network usage and future expansions of the lab.
```
free -h
               total        used        free      shared  buff/cache   available
Mem:            31Gi        14Gi        10Gi       732Mi       7.8Gi        16Gi
```

**Summary checklist**:
- [x] VirtualBox or VMware, Ubuntu VM
- [x] Initial configuration:
```
sudo apt update && sudo apt upgrade -y
sudo apt install curl python3.12-venv python3-pip vim
```
- [x] Install VS Code.
- [x] Directory setup:
```
mkdir mcp-project
cd mcp-project
python3 -m venv mcp
source mcp/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
- [x] Docker engine:
```
sudo apt update
sudo apt install ca-certificates
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl status docker
sudo docker run hello-world
```
- [x] Containerlab:
```
curl -sL https://containerlab.dev/setup | sudo -E bash -s "all"
newgrp docker
clab --help
clab version
```
- [x] Containerlab common commands:
```
containerlab deploy -t lab.yml
containerlab save -t lab.yml
containerlab inspect -t lab.yml
containerlab redeploy -t lab.yml
docker exec -it <container-name/id> Cli     (-i interactive, -t pseudo-tty/terminal)

containerlab graph -t lab.yml
containerlab destroy -t lab.yml
```
- [x] Claude Code:
```
curl -fsSL https://claude.ai/install.sh | bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
claude doctor
```
- [x] Claude auth (needs **API key**):
```
claude auth login
```
- [x] Claude ↔ MCP server:
```
claude mcp add mcp_automation -s user -- ./mcp/bin/python MCPServer.py
claude mcp list
```

## 📂 Router OS Images
### Arista EOS
To download the official **Arista cEOS** file, Google it or see the **Full Guide** in Section 2 of the [course](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55).

- [x] You need to import it into Docker using:
```
sudo docker import ~/cEOS64-lab-4.35.0F.tar.xz ceos:4.35.0F
docker images
```
- [x] Containerlab's [documentation for EOS](https://containerlab.dev/manual/kinds/ceos/)

### Cisco IOS
You are responsible of getting your own Cisco IOL file, however here's a starting point:
- [x] Containerlab's [documentation for IOL](https://containerlab.dev/manual/kinds/cisco_iol/)

### MikroTik RouterOS
- [x] Go to https://mikrotik.com/download/chr
- [x] Download the **VMDK image**
- [x] `cp Downloads/chr-7.20.8.vmdk vrnetlab/mikrotik/routeros/`
- [x] `cd ~/vrnetlab/mikrotik/routeros/`
- [x] `make docker-image`
- [x] Check with: `docker images`
- [x] Output:
`vrnetlab/mikrotik_routeros:7.20.8   a918b39e9772        976MB`
- [x] Now you'll be able to use **mikrotik_ros** in your **lab.yml** file.
- [x] Containerlab's [documentation for RouterOS](https://containerlab.dev/manual/kinds/vr-ros/)

**Quick note**:
- [x] Notice `CLAB_MGMT_PASSTHROUGH: "true"` in the **lab.yml** below:
- [x] This setting enables **TRANSPARENT MANAGEMENT**, details [here](https://containerlab.dev/manual/vrnetlab/#management-interface)

## 🖥️ Terminal Management
Since we're dealing with a complex topology containing many devices, we need to make our lives easier when it comes to the **management connections**.

For this reason, I'm using **Tabby**:
- [x] Download link [here](https://tabby.sh/)
- [x] The installer is **tabby-1.0.230-linux-x64.deb** (version no. might differ)
- [x] Installation: `sudo dpkg -i tabby-1.0.230-linux-x64.deb`
- [x] Start it with `tabby` and pin it to the Dash
- [x] Go to **Settings - Profiles & connections - New - New Profile Group**
- [x] Go to **New - New profile - SSH connection**, name it **R1A**, assign it to your Group
- [x] Scroll down to **Connection**, Host 172.20.20.201 (see **lab.yml** below ), Port 22
- [x] Set **Username** to **admin**. Set a **Password** in the keychain, also **admin**.
- [x] Hit **Save**. Do this for each router after you create your topology.
- [x] Connect to each device using the ▶︎ button. You may be prompted for the password again.
- [x] To quickly create the same connection type for each router, **Duplicate** R1A, then just change the name and IP address.

⚠️ **NOTE**: You don't have to use **Tabby** if you already like using a similar tool. They're all basically doing the same thing, just the UI slightly differs.

## 🔄 Network Topology
- [x] Current network topology:

![topology](TOPOLOGY-v2.0.png)

- [x] Containerlab **lab.yml** file:
```
name: mcp-lab

topology:
  defaults:
    env:
      CLAB_MGMT_PASSTHROUGH: "true"
  nodes:
    R1A:
      kind: arista_ceos
      image: ceos:4.35.0F
      mgmt-ipv4: 172.20.20.201
    R2C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.202
    R3C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.203
    R4C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.204
    R5C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.205
    R6A:
      kind: arista_ceos
      image: ceos:4.35.0F
      mgmt-ipv4: 172.20.20.206
    R7A:
      kind: arista_ceos
      image: ceos:4.35.0F
      mgmt-ipv4: 172.20.20.207
    R8C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.208
    R9C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.209
    R10C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.210
    R11C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.211
    R12C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.212
    R13C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.213
    R14C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.214
    R15C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.215
    R16C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.216
    R17C:
      kind: cisco_iol
      image: vrnetlab/cisco_iol:17.16.01a
      mgmt-ipv4: 172.20.20.217
    R18M:
      kind: mikrotik_ros
      image: vrnetlab/mikrotik_routeros:7.20.8
      mgmt-ipv4: 172.20.20.218
    R19M:
      kind: mikrotik_ros
      image: vrnetlab/mikrotik_routeros:7.20.8
      mgmt-ipv4: 172.20.20.219
    R20M:
      kind: mikrotik_ros
      image: vrnetlab/mikrotik_routeros:7.20.8
      mgmt-ipv4: 172.20.20.220
  links:
    - endpoints: ["R1A:eth1", "R10C:Ethernet0/1"]
    - endpoints: ["R1A:eth2", "R11C:Ethernet0/1"]
    - endpoints: ["R10C:Ethernet0/2", "R11C:Ethernet0/2"]
    - endpoints: ["R1A:eth3", "R3C:Ethernet0/3"]
    - endpoints: ["R1A:eth4", "R2C:Ethernet0/3"]
    - endpoints: ["R3C:Ethernet0/2", "R4C:Ethernet0/1"]
    - endpoints: ["R3C:Ethernet0/1", "R5C:Ethernet0/1"]
    - endpoints: ["R4C:Ethernet0/2", "R5C:Ethernet0/2"]
    - endpoints: ["R2C:Ethernet1/0", "R3C:Ethernet1/0"]
    - endpoints: ["R2C:Ethernet0/2", "R7A:eth1"]
    - endpoints: ["R2C:Ethernet0/1", "R6A:eth1"]
    - endpoints: ["R7A:eth2", "R8C:Ethernet0/2"]
    - endpoints: ["R6A:eth2", "R8C:Ethernet0/1"]
    - endpoints: ["R8C:Ethernet0/3", "R9C:Ethernet0/1"]
    - endpoints: ["R2C:Ethernet1/1", "R12C:Ethernet0/1"]
    - endpoints: ["R2C:Ethernet1/2", "R16C:Ethernet1/1"]
    - endpoints: ["R3C:Ethernet1/2", "R12C:Ethernet1/3"]
    - endpoints: ["R3C:Ethernet1/1", "R16C:Ethernet1/2"]
    - endpoints: ["R16C:Ethernet1/0", "R17C:Ethernet1/0"]
    - endpoints: ["R12C:Ethernet1/1", "R13C:Ethernet1/0"]
    - endpoints: ["R12C:Ethernet1/2", "R15C:Ethernet1/2"]
    - endpoints: ["R12C:Ethernet1/0", "R14C:Ethernet1/0"]
    - endpoints: ["R14C:Ethernet1/1", "R15C:Ethernet1/1"]
    - endpoints: ["R13C:Ethernet1/1", "R15C:Ethernet1/0"]
    - endpoints: ["R14C:Ethernet1/2", "R18M:eth1"] #R18M:eth1 is ether2 on the device
    - endpoints: ["R14C:Ethernet1/3", "R19M:eth3"] #R19M:eth3 is ether4 on the device
    - endpoints: ["R17C:Ethernet0/1", "R18M:eth2"] #R18M:eth2 is ether3 on the device
    - endpoints: ["R17C:Ethernet0/2", "R19M:eth2"] #R19M:eth2 is ether3 on the device
    - endpoints: ["R18M:eth3", "R19M:eth1"]        #R18M:eth3 is ether4 on the device; R19M:eth1 is ether2 on the device
    - endpoints: ["R18M:eth4", "R20M:eth1"]        #R18M:eth4 is ether5 on the device; R20M:eth1 is ether2 on the device
    - endpoints: ["R19M:eth4", "R20M:eth2"]        #R19M:eth4 is ether5 on the device; R20M:eth2 is ether3 on the device
    # The MikroTik / Containerlab interface naming conventions are explained here: https://containerlab.dev/manual/kinds/vr-ros/#interface-naming
```

- [x] **NETWORK.json** inventory file:
```
{
"R1A": {"host": "172.20.20.201", "platform": "arista_eos", "transport": "eapi", "cli_style": "eos", "location": "New York HQ"},
"R2C": {"host": "172.20.20.202", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R3C": {"host": "172.20.20.203", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R4C": {"host": "172.20.20.204", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R5C": {"host": "172.20.20.205", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R6A": {"host": "172.20.20.206", "platform": "arista_eos", "transport": "eapi", "cli_style": "eos", "location": "New York HQ"},
"R7A": {"host": "172.20.20.207", "platform": "arista_eos", "transport": "eapi", "cli_style": "eos", "location": "New York HQ"},
"R8C": {"host": "172.20.20.208", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R9C": {"host": "172.20.20.209", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R10C": {"host": "172.20.20.210", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R11C": {"host": "172.20.20.211", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "New York HQ"},
"R12C": {"host": "172.20.20.212", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "ISP A"},
"R13C": {"host": "172.20.20.213", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "ISP A"},
"R14C": {"host": "172.20.20.214", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "ISP A"},
"R15C": {"host": "172.20.20.215", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "ISP A"},
"R16C": {"host": "172.20.20.216", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "ISP B"},
"R17C": {"host": "172.20.20.217", "platform": "cisco_iosxe", "transport": "asyncssh", "cli_style": "ios", "location": "ISP B"},
"R18M": {"host": "172.20.20.218", "platform": "mikrotik_routeros", "transport": "rest", "cli_style": "routeros", "location": "London Branch"},
"R19M": {"host": "172.20.20.219", "platform": "mikrotik_routeros", "transport": "rest", "cli_style": "routeros", "location": "London Branch"},
"R20M": {"host": "172.20.20.220", "platform": "mikrotik_routeros", "transport": "rest", "cli_style": "routeros", "location": "London Branch"}
}
```
⚠️ **NOTE**: Adding `"cli_style": "eos"` or `"cli_style": "ios"` to the **NETWORK.json** inventory file provides additional context to Claude when executing commands on one type of device or another, and it's also useful for further reference in the **MCPServer.py** code.

- [x] Router naming convention:
  - **RXY** where:
    - **R**: device type (router)
    - **X**: device number id
    - **Y**: vendor (A-Arista, C-Cisco, M-MikroTik, etc.)

- [x] Interface naming convention:
  For example, the first usable data interface is **1** *(**0** is the Mgmt interface assigned by Containerlab)*. This is equivalent to:
  - **eth1** on Arista
  - **e0/1** on Cisco
  - **ether2** on MikroTik (see comments and link in **lab.yml**)

- [x] Default SSH credentials:
  - Arista: `admin:admin`
  - Cisco: `admin:admin`
  - MikroTik: `admin:admin`

- [x] **.env** credentials file:
```
ROUTER_USERNAME=admin
ROUTER_PASSWORD=admin
```

- [x] Router configurations:
  - Each config below refers to only the most relevant parts of the startup-config files

- [x] Startup configuration files:
  - Saved as:
    - Arista: `/mcp-project/clab-mcp-lab/RXA/flash/startup-config`
    - Cisco: `/mcp-project/clab-mcp-lab/RXC/nvram_number`
    - MikroTik: `/mcp-project/clab-mcp-lab/RXM/ftpboot/config.auto.rsc`
  - Save the running configs to the startup config files with:
    - `clab save -t lab.yml`
  - Restore the lab to the startup configurations with:
    - `clab redeploy -t lab.yml`

💾 **Router R1A**:
```
interface Ethernet1
   description TO-R10C
   no switchport
   no shutdown
   ip address 172.16.0.5/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA2
!
interface Ethernet2
   description TO-R11C
   no switchport
   no shutdown
   ip address 172.16.0.9/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA2
!
interface Ethernet3
   description TO-R3C
   no switchport
   no shutdown
   ip address 10.0.0.5/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA0
!
interface Ethernet4
   description TO-R2A
   no switchport
   no shutdown
   ip address 10.0.0.1/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA0
!
ip routing
!
router ospf 1
   router-id 1.1.1.1
   auto-cost reference-bandwidth 100000
   area 0.0.0.2 stub no-summary
   area 0.0.0.2 range 172.16.0.0/24
   network 10.0.0.0/30 area 0
   network 10.0.0.4/30 area 0
   network 172.16.0.4/30 area 2
   network 172.16.0.8/30 area 2
   max-lsa 12000
!
management api http-commands
no protocol http
protocol https
no shutdown
!
no ip route 0.0.0.0/0 172.20.20.1
!
```

💾 **Router R2C**:
```
!
interface Loopback1
 ip address 2.2.2.66 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.202 255.255.255.0
 ipv6 address 3FFF:172:20:20::7/64
!
interface Ethernet0/1
 description TO-R6A
 ip address 10.1.1.14 255.255.255.252
 ip nat inside
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA1
 ip ospf network point-to-point
!         
interface Ethernet0/2
 description TO-R7A
 ip address 10.1.1.10 255.255.255.252
 ip nat inside
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA1
 ip ospf network point-to-point
!
interface Ethernet0/3
 description TO-R1A
 ip address 10.0.0.2 255.255.255.252
 ip nat inside
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA0
 ip ospf network point-to-point
!
interface Ethernet1/0
 description TO-R3C
 ip address 10.0.0.9 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA0
 ip ospf network point-to-point
!         
interface Ethernet1/1
 description TO-R12C
 ip address 200.40.40.1 255.255.255.252
 ip nat outside
!
interface Ethernet1/2
 description TO-R16C
 ip address 200.50.50.1 255.255.255.252
 ip nat outside
!
interface Ethernet1/3
 no ip address
 shutdown
!
router ospf 1
 router-id 2.2.2.2
 auto-cost reference-bandwidth 100000
 max-lsa 12000
 area 0 filter-list prefix NO-2222LO in
 area 1 nssa default-information-originate no-summary
 passive-interface Loopback1
 network 2.2.2.66 0.0.0.0 area 1
 network 10.0.0.0 0.0.0.3 area 0
 network 10.0.0.8 0.0.0.3 area 0
 network 10.1.1.8 0.0.0.3 area 1
 network 10.1.1.12 0.0.0.3 area 1
 default-information originate metric-type 1
 distribute-list prefix FILTER_3333LO_LOCAL in
!
router bgp 1010
 bgp router-id 2.2.2.2
 bgp log-neighbor-changes
 neighbor 10.0.0.10 remote-as 1010
 neighbor 200.40.40.2 remote-as 4040
 neighbor 200.50.50.2 remote-as 5050
!
ip forward-protocol nd
ip forward-protocol udp
!
!
ip http server
ip http secure-server
ip nat inside source route-map NAT-ISPA interface Ethernet1/1 overload
ip nat inside source route-map NAT-ISPB interface Ethernet1/2 overload
ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 Ethernet0/0 172.20.20.1
ip ssh bulk-mode 131072
!
ip access-list standard NAT_INSIDE
 10 permit 10.0.0.0 0.255.255.255
 20 permit 172.16.0.0 0.0.255.255
 30 permit 192.168.0.0 0.0.255.255
!
ip prefix-list FILTER_3333LO_LOCAL seq 10 deny 3.3.3.3/32
ip prefix-list FILTER_3333LO_LOCAL seq 20 permit 0.0.0.0/0 le 32
!
ip prefix-list NO-2222LO seq 10 deny 2.2.2.66/32
ip prefix-list NO-2222LO seq 20 permit 0.0.0.0/0 le 32
no logging btrace
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map NAT-ISPA permit 10 
 match ip address NAT_INSIDE
 match interface Ethernet1/1
!
route-map NAT-ISPB permit 10 
 match ip address NAT_INSIDE
 match interface Ethernet1/2
!
```

💾 **Router R3C**:
```
!
key chain MCP
 key 1
  key-string MCPLAB10
!
interface Loopback1
 ip address 3.3.3.3 255.255.255.0
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.203 255.255.255.0
 ipv6 address 3FFF:172:20:20::6/64
!
interface Ethernet0/1
 description TO-R5C
 ip address 192.168.10.5 255.255.255.252
 ip authentication mode eigrp 10 md5
 ip authentication key-chain eigrp 10 MCP
 ip nat inside
 ip summary-address eigrp 10 0.0.0.0 0.0.0.0
!
interface Ethernet0/2
 description TO-R4C
 ip address 192.168.10.1 255.255.255.252
 ip authentication mode eigrp 10 md5
 ip authentication key-chain eigrp 10 MCP
 ip nat inside
 ip summary-address eigrp 10 0.0.0.0 0.0.0.0
!
interface Ethernet0/3
 description TO-R1A
 ip address 10.0.0.6 255.255.255.252
 ip nat inside
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA0
 ip ospf network point-to-point
!
interface Ethernet1/0
 description TO-R2A
 ip address 10.0.0.10 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA0
 ip ospf network point-to-point
!
interface Ethernet1/1
 description TO-R16C
 ip address 200.50.50.5 255.255.255.252
 ip nat outside
!
interface Ethernet1/2
 description TO-R12C
 ip address 200.40.40.5 255.255.255.252
 ip nat outside
!
interface Ethernet1/3
 no ip address
 shutdown
!
!
router eigrp 10
 network 192.168.10.0 0.0.0.3
 network 192.168.10.4 0.0.0.3
 redistribute ospf 1 route-map OSPF-TO-EIGRP
!
router ospf 1
 router-id 3.3.3.3
 auto-cost reference-bandwidth 100000
 redistribute eigrp 10 metric-type 1
 passive-interface Loopback1
 network 3.3.3.0 0.0.0.255 area 0
 network 10.0.0.4 0.0.0.3 area 0
 network 10.0.0.8 0.0.0.3 area 0
 default-information originate metric-type 1
!
router bgp 1010
 bgp router-id 3.3.3.3
 bgp log-neighbor-changes
 neighbor 10.0.0.9 remote-as 1010
 neighbor 200.40.40.6 remote-as 4040
 neighbor 200.50.50.6 remote-as 5050
!
ip forward-protocol nd
ip forward-protocol udp
!
!
ip http server
ip http secure-server
ip nat inside source route-map NAT-ISPA interface Ethernet1/2 overload
ip nat inside source route-map NAT-ISPB interface Ethernet1/1 overload
ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 Ethernet0/0 172.20.20.1
ip ssh bulk-mode 131072
!
ip access-list standard NAT_INSIDE
 10 permit 10.0.0.0 0.255.255.255
 20 permit 172.16.0.0 0.0.255.255
 30 permit 192.168.0.0 0.0.255.255
no logging btrace
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map OSPF-TO-EIGRP permit 10 
 set metric 1000000 1 255 1 1500
!
route-map NAT-ISPA permit 10 
 match ip address NAT_INSIDE
 match interface Ethernet1/2
!
route-map NAT-ISPB permit 10 
 match ip address NAT_INSIDE
 match interface Ethernet1/1
!
```

💾 **Router R4C**:
```
key chain MCP
 key 1
  key-string MCPLAB10
!
interface Loopback1
 ip address 4.4.1.1 255.255.255.0
!
interface Loopback2
 ip address 4.4.2.1 255.255.255.0
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.204 255.255.255.0
 ipv6 address 3FFF:172:20:20::2/64
!
interface Ethernet0/1
 description TO-R3C
 no shutdown
 ip address 192.168.10.2 255.255.255.252
 ip authentication mode eigrp 10 md5
 ip authentication key-chain eigrp 10 MCP
 ip summary-address eigrp 10 4.4.0.0 255.255.252.0
!
interface Ethernet0/2
 description TO-R5C
 no shutdown
 ip address 192.168.10.9 255.255.255.252
 ip authentication mode eigrp 10 md5
 ip authentication key-chain eigrp 10 MCP
 ip summary-address eigrp 10 4.4.0.0 255.255.252.0
!
interface Ethernet0/3
 no ip address
 shutdown
!
!
router eigrp 10
 network 4.4.1.0 0.0.0.255
 network 4.4.2.0 0.0.0.255
 network 192.168.10.0 0.0.0.3
 network 192.168.10.8 0.0.0.3
 passive-interface Loopback1
 passive-interface Loopback2
!
```

💾 **Router R5C**:
```
key chain MCP
 key 1
  key-string MCPLAB10
!
interface Loopback1
 ip address 5.5.1.1 255.255.255.0
!
interface Loopback2
 ip address 5.5.2.1 255.255.255.0
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.205 255.255.255.0
 ipv6 address 3FFF:172:20:20::2/64
!
interface Ethernet0/1
 description TO-R3C
 no shutdown
 ip address 192.168.10.6 255.255.255.252
 ip authentication mode eigrp 10 md5
 ip authentication key-chain eigrp 10 MCP
 ip summary-address eigrp 10 5.5.0.0 255.255.252.0
!
interface Ethernet0/2
 description TO-R4C
 no shutdown
 ip address 192.168.10.10 255.255.255.252
 ip authentication mode eigrp 10 md5
 ip authentication key-chain eigrp 10 MCP
 ip summary-address eigrp 10 5.5.0.0 255.255.252.0
 !
interface Ethernet0/3
 no ip address
 shutdown
!
!
router eigrp 10
 network 5.5.1.0 0.0.0.255
 network 5.5.2.0 0.0.0.255
 network 192.168.10.4 0.0.0.3
 network 192.168.10.8 0.0.0.3
 passive-interface Loopback1
 passive-interface Loopback2
!
ip sla responder
ip sla 1
 icmp-echo 10.10.10.10 source-ip 5.5.1.1
ip sla schedule 1 life forever start-time now
!
```

💾 **Router R6A**:
```
interface Ethernet1
   description TO-R2A
   no switchport
   no shutdown
   ip address 10.1.1.13/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA1
!
interface Ethernet2
   description TO-R8C
   no switchport
   no shutdown
   ip address 10.1.1.2/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA1
!
interface Loopback1
   ip address 6.6.6.6/32
!
ip routing
!
router ospf 1
   router-id 6.6.6.6
   auto-cost reference-bandwidth 100000
   passive-interface Loopback1
   area 0.0.0.1 nssa
   network 6.6.6.6/32 area 0.0.0.1
   network 10.1.1.0/30 area 0.0.0.1
   network 10.1.1.12/30 area 0.0.0.1
   max-lsa 12000
!
management api http-commands
no protocol http
protocol https
no shutdown
!
no ip route 0.0.0.0/0 172.20.20.1
!
```

💾 **Router R7A**:
```
interface Ethernet1
   description TO-R2A
   no switchport
   no shutdown
   ip address 10.1.1.9/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA1
!
interface Ethernet2
   description TO-R8C
   no switchport
   no shutdown
   ip address 10.1.1.6/30
   ip ospf network point-to-point
   ip ospf authentication message-digest
   ip ospf message-digest-key 1 md5 AREA1
!
interface Loopback1
   ip address 7.7.7.7/32
!
ip routing
!
router ospf 1
   router-id 7.7.7.7
   auto-cost reference-bandwidth 100000
   passive-interface Loopback1
   area 0.0.0.1 nssa
   network 7.7.7.7/32 area 0.0.0.1
   network 10.1.1.4/30 area 0.0.0.1
   network 10.1.1.8/30 area 0.0.0.1
   max-lsa 12000
!
management api http-commands
no protocol http
protocol https
no shutdown
!
no ip route 0.0.0.0/0 172.20.20.1
!
```

💾 **Router R8C**:
```
key chain MCP
 key 1
  key-string MCPLAB20
!
interface Loopback1
 ip address 8.8.8.8 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.208 255.255.255.0
 ipv6 address 3FFF:172:20:20::A/64
!
interface Ethernet0/1
 description TO-R6A
 no shutdown
 ip address 10.1.1.1 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA1
 ip ospf network point-to-point
!
interface Ethernet0/2
 description TO-R7A
 no shutdown
 ip address 10.1.1.5 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA1
 ip ospf network point-to-point
!
interface Ethernet0/3
 description TO-R9C
 no shutdown
 ip address 192.168.20.1 255.255.255.252
 ip authentication mode eigrp 20 md5
 ip authentication key-chain eigrp 20 MCP
 ip policy route-map ACCESS-R2-LO
!
!
router eigrp 20
 network 8.8.8.8 0.0.0.0
 network 192.168.20.0 0.0.0.3
 redistribute ospf 1 route-map OSPF-TO-EIGRP
 passive-interface Loopback1
!
router ospf 1
 router-id 8.8.8.8
 auto-cost reference-bandwidth 100000
 area 1 nssa
 redistribute eigrp 20 metric-type 1
 network 10.1.1.0 0.0.0.3 area 1
 network 10.1.1.4 0.0.0.3 area 1
!
ip access-list extended 100
 10 permit ip host 192.168.20.2 host 2.2.2.66
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map OSPF-TO-EIGRP permit 10 
 set metric 1000000 1 255 1 1500
!
route-map ACCESS-R2-LO permit 10 
 match ip address 100
 set ip next-hop 10.1.1.6
!
```

💾 **Router R9C**:
```
key chain MCP
 key 1
  key-string MCPLAB20
!
interface Loopback1
 ip address 9.9.1.1 255.255.255.0
!
interface Loopback2
 ip address 9.9.2.1 255.255.255.0
!
interface Loopback3
 ip address 9.9.3.1 255.255.255.0
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.209 255.255.255.0
 ipv6 address 3FFF:172:20:20::8/64
!
interface Ethernet0/1
 description TO-R8C
 no shutdown
 ip address 192.168.20.2 255.255.255.252
 ip authentication mode eigrp 20 md5
 ip authentication key-chain eigrp 20 MCP
 ip summary-address eigrp 20 9.9.0.0 255.255.252.0
!
interface Ethernet0/2
 no ip address
 shutdown
!
interface Ethernet0/3
 no ip address
 shutdown
!
!
router eigrp 20
 network 9.9.1.0 0.0.0.255
 network 9.9.2.0 0.0.0.255
 network 9.9.3.0 0.0.0.255
 network 192.168.20.0 0.0.0.3
 passive-interface Loopback1
 passive-interface Loopback2
 passive-interface Loopback3
 eigrp stub connected summary
!
ip sla 1
 icmp-echo 11.11.11.11 source-ip 9.9.1.1
ip sla schedule 1 life forever start-time now
ip sla 2
 icmp-echo 5.5.2.1 source-ip 9.9.2.1
ip sla schedule 2 life forever start-time now
!
```

💾 **Router R10C**:
```
interface Loopback1
 ip address 10.10.10.10 255.255.255.0
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.210 255.255.255.0
 ipv6 address 3FFF:172:20:20::6/64
!
interface Ethernet0/1
 description TO-R1A
 no shutdown
 ip address 172.16.0.6 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA2
 ip ospf network point-to-point
!
interface Ethernet0/2
 description TO-R11C
 no shutdown
 ip address 172.16.0.1 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA2
 ip ospf network point-to-point
!
interface Ethernet0/3
 no ip address
 shutdown
!
router ospf 1
 router-id 10.10.10.10
 auto-cost reference-bandwidth 100000
 area 2 stub
 passive-interface Loopback1
 network 10.10.10.0 0.0.0.255 area 2
 network 172.16.0.0 0.0.0.3 area 2
 network 172.16.0.4 0.0.0.3 area 2
!
ip sla responder
!
```

💾 **Router R11C**:
```
interface Loopback1
 ip address 11.11.11.11 255.255.255.0
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.211 255.255.255.0
 ipv6 address 3FFF:172:20:20::C/64
!
interface Ethernet0/1
 description TO-R1A
 no shutdown
 ip address 172.16.0.10 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA2
 ip ospf network point-to-point
!
interface Ethernet0/2
 description TO-R10C
 no shutdown
 ip address 172.16.0.2 255.255.255.252
 ip ospf authentication message-digest
 ip ospf message-digest-key 1 md5 AREA2
 ip ospf network point-to-point
!
interface Ethernet0/3
 no ip address
 shutdown
!
router ospf 1
 router-id 11.11.11.11
 auto-cost reference-bandwidth 100000
 area 2 stub
 passive-interface Loopback1
 network 11.11.11.0 0.255.255.255 area 2
 network 172.16.0.0 0.0.0.3 area 2
 network 172.16.0.8 0.0.0.3 area 2
!
ip sla responder
!
```

💾 **Router R12C**:
```
!
interface Loopback0
 ip address 12.12.12.12 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.212 255.255.255.0
 ipv6 address 3FFF:172:20:20::13/64
!
interface Ethernet0/1
 description TO-R2A
 ip address 200.40.40.2 255.255.255.252
!
interface Ethernet0/2
 no ip address
 shutdown
!
interface Ethernet0/3
 no ip address
 shutdown
!
interface Ethernet1/0
 description TO-R14C
 ip address 192.168.40.5 255.255.255.252
!
interface Ethernet1/1
 description TO-R13C
 ip address 192.168.40.17 255.255.255.252
!
interface Ethernet1/2
 description TO-R15C
 ip address 192.168.40.1 255.255.255.252
!
interface Ethernet1/3
 description TO-R3C
 ip address 200.40.40.6 255.255.255.252
!
router ospf 40
 router-id 12.12.12.12
 network 12.12.12.12 0.0.0.0 area 0
 network 192.168.40.0 0.0.0.255 area 0
!
router bgp 4040
 bgp router-id 12.12.12.12
 bgp log-neighbor-changes
 network 200.40.40.0 mask 255.255.255.252
 network 200.40.40.4 mask 255.255.255.252
 neighbor 13.13.13.13 remote-as 4040
 neighbor 13.13.13.13 update-source Loopback0
 neighbor 13.13.13.13 route-reflector-client
 neighbor 14.14.14.14 remote-as 4040
 neighbor 14.14.14.14 update-source Loopback0
 neighbor 14.14.14.14 route-reflector-client
 neighbor 15.15.15.15 remote-as 4040
 neighbor 15.15.15.15 update-source Loopback0
 neighbor 15.15.15.15 route-reflector-client
 neighbor 200.40.40.1 remote-as 1010
 neighbor 200.40.40.1 default-originate
 neighbor 200.40.40.1 route-map FROM-CUST in
 neighbor 200.40.40.5 remote-as 1010
 neighbor 200.40.40.5 default-originate
 neighbor 200.40.40.5 route-map FROM-CUST in
!
ip forward-protocol nd
ip forward-protocol udp
!
!
ip http server
ip http secure-server
ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 Ethernet0/0 172.20.20.1
ip ssh bulk-mode 131072
!
ip prefix-list FROM-CUST seq 5 permit 0.0.0.0/0 ge 1
no logging btrace
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map FROM-CUST permit 10 
 match ip address prefix-list FROM-CUST
!
```

💾 **Router R13C**:
```
!
interface Loopback0
 ip address 13.13.13.13 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.213 255.255.255.0
 ipv6 address 3FFF:172:20:20::F/64
!
interface Ethernet0/1
 no ip address
 shutdown
!
interface Ethernet0/2
 no ip address
 shutdown
!
interface Ethernet0/3
 no ip address
 shutdown
!
interface Ethernet1/0
 description TO-R12C
 ip address 192.168.40.18 255.255.255.252
!
interface Ethernet1/1
 description TO-R15C
 ip address 192.168.40.13 255.255.255.252
!
interface Ethernet1/2
 no ip address
 shutdown
!
interface Ethernet1/3
 no ip address
 shutdown
!
router ospf 40
 router-id 13.13.13.13
 network 13.13.13.13 0.0.0.0 area 0
 network 192.168.40.0 0.0.0.255 area 0
!
router bgp 4040
 bgp router-id 13.13.13.13
 bgp log-neighbor-changes
 neighbor 12.12.12.12 remote-as 4040
 neighbor 12.12.12.12 update-source Loopback0
!
```

💾 **Router R14C**:
```
!
interface Loopback0
 ip address 14.14.14.14 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.214 255.255.255.0
 ipv6 address 3FFF:172:20:20::A/64
!
interface Ethernet0/1
 no ip address
 shutdown
!
interface Ethernet0/2
 no ip address
 shutdown
!
interface Ethernet0/3
 no ip address
 shutdown
!
interface Ethernet1/0
 description TO-R12C
 ip address 192.168.40.6 255.255.255.252
!
interface Ethernet1/1
 description TO-R15C
 ip address 192.168.40.9 255.255.255.252
!
interface Ethernet1/2
 description TO-R18M
 ip address 220.40.40.1 255.255.255.252
!
interface Ethernet1/3
 description TO-R19M
 ip address 220.40.40.5 255.255.255.252
!
router ospf 40
 router-id 14.14.14.14
 network 14.14.14.14 0.0.0.0 area 0
 network 192.168.40.0 0.0.0.255 area 0
!
router bgp 4040
 bgp router-id 14.14.14.14
 bgp log-neighbor-changes
 network 220.40.40.0 mask 255.255.255.252
 network 220.40.40.4 mask 255.255.255.252
 neighbor 12.12.12.12 remote-as 4040
 neighbor 12.12.12.12 update-source Loopback0
 neighbor 220.40.40.2 remote-as 2020
 neighbor 220.40.40.2 default-originate
 neighbor 220.40.40.2 route-map FROM-CUST in
 neighbor 220.40.40.6 remote-as 2020
 neighbor 220.40.40.6 default-originate
 neighbor 220.40.40.6 route-map FROM-CUST in
!
ip forward-protocol nd
ip forward-protocol udp
!
!
ip http server
ip http secure-server
ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 Ethernet0/0 172.20.20.1
ip ssh bulk-mode 131072
!
ip prefix-list BLOCK-DEFAULT seq 5 deny 0.0.0.0/0
ip prefix-list BLOCK-DEFAULT seq 10 permit 0.0.0.0/0 le 32
no logging btrace
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map FROM-CUST deny 10 
 match ip address prefix-list BLOCK-DEFAULT
!
route-map FROM-CUST permit 100 
!
```

💾 **Router R15C**:
```
!
interface Loopback0
 ip address 15.15.15.15 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.215 255.255.255.0
 ipv6 address 3FFF:172:20:20::8/64
!
interface Ethernet0/1
 no ip address
 shutdown
!
interface Ethernet0/2
 no ip address
 shutdown
!
interface Ethernet0/3
 no ip address
 shutdown
!
interface Ethernet1/0
 description TO-R13C
 ip address 192.168.40.14 255.255.255.252
!
interface Ethernet1/1
 description TO-R14C
 ip address 192.168.40.10 255.255.255.252
!
interface Ethernet1/2
 description TO-R12C
 ip address 192.168.40.2 255.255.255.252
!
interface Ethernet1/3
 no ip address
 shutdown
!
router ospf 40
 router-id 15.15.15.15
 network 15.15.15.15 0.0.0.0 area 0
 network 192.168.40.0 0.0.0.255 area 0
!
router bgp 4040
 bgp router-id 15.15.15.15
 bgp log-neighbor-changes
 neighbor 12.12.12.12 remote-as 4040
 neighbor 12.12.12.12 update-source Loopback0
!
```

💾 **Router R16C**:
```
!
interface Loopback0
 ip address 16.16.16.16 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.216 255.255.255.0
 ipv6 address 3FFF:172:20:20::D/64
!
interface Ethernet0/1
 no ip address
 shutdown
!
interface Ethernet0/2
 no ip address
 shutdown
!
interface Ethernet0/3
 no ip address
 shutdown
!
interface Ethernet1/0
 description TO-R17C
 ip address 192.168.50.1 255.255.255.252
!
interface Ethernet1/1
 description TO-R2A
 ip address 200.50.50.2 255.255.255.252
!
interface Ethernet1/2
 description TO-R3C
 ip address 200.50.50.6 255.255.255.252
!
interface Ethernet1/3
 no ip address
 shutdown
!
router ospf 50
 router-id 16.16.16.16
 network 16.16.16.16 0.0.0.0 area 0
 network 192.168.50.0 0.0.0.3 area 0
!
router bgp 5050
 bgp router-id 16.16.16.16
 bgp log-neighbor-changes
 network 200.50.50.0 mask 255.255.255.252
 network 200.50.50.4 mask 255.255.255.252
 neighbor 17.17.17.17 remote-as 5050
 neighbor 17.17.17.17 update-source Loopback0
 neighbor 192.168.50.2 remote-as 5050
 neighbor 200.50.50.1 remote-as 1010
 neighbor 200.50.50.1 default-originate
 neighbor 200.50.50.1 route-map CUST-IN in
 neighbor 200.50.50.5 remote-as 1010
 neighbor 200.50.50.5 default-originate
 neighbor 200.50.50.5 route-map CUST-IN in
!
ip forward-protocol nd
ip forward-protocol udp
!
!
ip http server
ip http secure-server
ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 Ethernet0/0 172.20.20.1
ip ssh bulk-mode 131072
!
ip prefix-list CUST-IN seq 5 permit 0.0.0.0/0 ge 1
no logging btrace
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map CUST-IN permit 10 
 match ip address prefix-list CUST-IN
!
```

💾 **Router R17C**:
```
!
interface Loopback0
 ip address 17.17.17.17 255.255.255.255
!
interface Ethernet0/0
 description clab-mgmt
 vrf forwarding clab-mgmt
 ip address 172.20.20.217 255.255.255.0
 ipv6 address 3FFF:172:20:20::3/64
!
interface Ethernet0/1
 description TO-R18M
 ip address 220.50.50.1 255.255.255.252
!
interface Ethernet0/2
 description TO-R19M
 ip address 220.50.50.5 255.255.255.252
!
interface Ethernet0/3
 no ip address
 shutdown
!
interface Ethernet1/0
 description TO-R16C
 ip address 192.168.50.2 255.255.255.252
!
interface Ethernet1/1
 no ip address
 shutdown
!
interface Ethernet1/2
 no ip address
 shutdown
!
interface Ethernet1/3
 no ip address
 shutdown
!
router ospf 50
 router-id 17.17.17.17
 network 17.17.17.17 0.0.0.0 area 0
 network 192.168.50.0 0.0.0.3 area 0
!
router bgp 5050
 bgp router-id 17.17.17.17
 bgp log-neighbor-changes
 network 220.50.50.0 mask 255.255.255.252
 network 220.50.50.4 mask 255.255.255.252
 neighbor 16.16.16.16 remote-as 5050
 neighbor 16.16.16.16 update-source Loopback0
 neighbor 192.168.50.1 remote-as 5050
 neighbor 220.50.50.2 remote-as 2020
 neighbor 220.50.50.2 default-originate
 neighbor 220.50.50.2 route-map CUST-IN in
 neighbor 220.50.50.6 remote-as 2020
 neighbor 220.50.50.6 default-originate
 neighbor 220.50.50.6 route-map CUST-IN in
!
ip forward-protocol nd
ip forward-protocol udp
!
!
ip http server
ip http secure-server
ip route vrf clab-mgmt 0.0.0.0 0.0.0.0 Ethernet0/0 172.20.20.1
ip ssh bulk-mode 131072
!
ip prefix-list CUST-IN seq 5 permit 0.0.0.0/0 ge 1
no logging btrace
ipv6 route vrf clab-mgmt ::/0 Ethernet0/0 3FFF:172:20:20::1
route-map CUST-IN permit 10 
 match ip address prefix-list CUST-IN
!
```

💾 **Router R18M**:
```
/interface ethernet set ether2 comment="TO-R14C" disabled=no
/ip address add address=220.40.40.2/30 interface=ether2
/interface ethernet set ether3 comment="TO-R17C" disabled=no
/ip address add address=220.50.50.2/30 interface=ether3
/interface ethernet set ether4 comment="TO-R19M" disabled=no
/ip address add address=172.16.77.2/30 interface=ether4
/interface ethernet set ether5 comment="TO-R20M" disabled=no
/ip address add address=172.16.77.5/30 interface=ether5
/interface/ bridge/ add name=lo1 comment="Loopback1"
/ip address add address=18.18.18.1/24 interface=lo1

/interface ethernet print
/ip address print

/routing ospf/instance/
add name=default router-id=18.18.18.18
/routing ospf area/
add name=backbone area-id=0.0.0.0 instance=default
/routing ospf/ interface-template/
add interfaces=ether4 area=backbone
add interfaces=ether5 area=backbone
add interfaces=lo1 area=backbone passive
/routing ospf instance set default originate-default=if-installed

/routing ospf/neighbor/print
/routing ospf/instance/print
/ip route print where ospf
/routing/ospf/lsa/print detail

/routing/bgp/instance/add name=default as=2020 router-id=18.18.18.18
/routing/bgp/connection/add name=TO-R14C instance=default remote.as=4040 remote.address=220.40.40.1 local.role=ebgp
/routing/bgp/connection/add name=TO-R17C instance=default remote.as=5050 remote.address=220.50.50.1 local.role=ebgp
/routing/bgp/connection/add name=TO-R19M instance=default remote.as=2020 remote.address=172.16.77.1 local.role=ibgp
/routing/bgp/connection/set [find where remote.address=172.16.77.1] nexthop-choice=force-self

/routing/bgp/instance/print
/routing/bgp/connection/print
/routing/bgp/session/print

/ip firewall/nat/
add chain=srcnat out-interface=ether2 action=masquerade
add chain=srcnat out-interface=ether3 action=masquerade

/ip service/ enable www-ssl 
/ip service set www-ssl address=172.20.20.0/24
/certificate add name=rest-cert common-name=router
/certificate sign rest-cert
/ip service set www-ssl certificate=rest-cert
/ip service/print
```

💾 **Router R19M**:
```
/interface ethernet set ether2 comment="TO-R18M" disabled=no
/ip address add address=172.16.77.1/30 interface=ether2
/interface ethernet set ether3 comment="TO-R17C" disabled=no
/ip address add address=220.50.50.6/30 interface=ether3
/interface ethernet set ether4 comment="TO-R14C" disabled=no
/ip address add address=220.40.40.6/30 interface=ether4
/interface ethernet set ether5 comment="TO-R20M" disabled=no
/ip address add address=172.16.77.9/30 interface=ether5
/interface/ bridge/ add name=lo1 comment="Loopback1"
/ip address add address=19.19.19.1/24 interface=lo1

/interface ethernet print
/ip address print

/routing ospf/instance/
add name=default router-id=19.19.19.19
/routing ospf area/
add name=backbone area-id=0.0.0.0 instance=default
/routing ospf/ interface-template/
add interfaces=ether2 area=backbone
add interfaces=ether5 area=backbone
add interfaces=lo1 area=backbone passive
/routing ospf instance set default originate-default=if-installed

/routing ospf/neighbor/print
/routing ospf/instance/print
/ip route print where ospf
/routing/ospf/lsa/print detail

/routing/bgp/instance/add name=default as=2020 router-id=19.19.19.19
/routing/bgp/connection/add name=TO-R14C instance=default remote.as=4040 remote.address=220.40.40.5 local.role=ebgp 
/routing/bgp/connection/add name=TO-R17C instance=default remote.as=5050 remote.address=220.50.50.5 local.role=ebgp
/routing/bgp/connection/add name=TO-R18M instance=default remote.as=2020 remote.address=172.16.77.2 local.role=ibgp
/routing/bgp/connection/set [find where remote.address=172.16.77.2] nexthop-choice=force-self

/routing/bgp/instance/print
/routing/bgp/connection/print
/routing/bgp/session/print

/ip firewall/nat/
add chain=srcnat out-interface=ether3 action=masquerade
add chain=srcnat out-interface=ether4 action=masquerade

/ip service/ enable www-ssl 
/ip service set www-ssl address=172.20.20.0/24
/certificate add name=rest-cert common-name=router
/certificate sign rest-cert
/ip service set www-ssl certificate=rest-cert
/ip service/print
```

💾 **Router R20M**:
```
/interface ethernet set ether2 comment="TO-R18M" disabled=no
/ip address add address=172.16.77.6/30 interface=ether2
/interface ethernet set ether3 comment="TO-R19M" disabled=no
/ip address add address=172.16.77.10/30 interface=ether3
/interface/ bridge/ add name=lo1 comment="Loopback1"
/ip address add address=20.20.20.1/24 interface=lo1

/interface ethernet print
/ip address print

/routing ospf/instance/
add name=default router-id=20.20.20.20
/routing ospf area/
add name=backbone area-id=0.0.0.0 instance=default
/routing ospf/ interface-template/
add interfaces=ether2 area=backbone
add interfaces=ether3 area=backbone
add interfaces=lo1 area=backbone passive

/routing ospf neighbor print
/ip route print where ospf

/ip service/ enable www-ssl 
/ip service set www-ssl address=172.20.20.0/24
/certificate add name=rest-cert common-name=router
/certificate sign rest-cert
/ip service set www-ssl certificate=rest-cert
/ip service/print
```

⚠️ **NOTE**: Check the **MikroTik REST API** from your Ubuntu terminal with:
```
curl -u admin:admin https://172.20.20.218/rest/system/resource
curl -u admin:admin https://172.20.20.219/rest/interface
curl -u admin:admin https://172.20.20.219/rest/ip/route
curl -u admin:admin -X POST https://172.20.20.220/rest/tool/ping -H "Content-Type: application/json" -d '{"address":"172.16.77.9","count":4}'
```

⚠️ **NOTE**: The router configurations above are considered the **default configuration** for this network and in **this version of the project**, and they are **subject to change** with each new release, as the topology grows in complexity.

⚠️ **NOTE**: Since these configurations are considered the **default configuration** for the current network version, they are going to be your fallback config whenever you use `containerlab redeploy -t lab.yml`

## 🔥 Troubleshooting
Troubleshooting scenarios are located in the [troubleshoot.md](https://github.com/pdudotdev/netaimcp/blob/main/scenarios/troubleshoot.md) file that is going to be constantly updated as the network grows in complexity.

✍️ **NOTE**: Each scenario is created by starting from the **default configuration** of the network (see [Network Topology](#-network-topology)) and intentionally breaking one or more things to trigger a certain type of failure. Then, with just a simple prompt, we enable Claude to use the MCP server's tools for identifying the root cause(s) and fixing the issue. 

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

📂 **NOTE**: All other types of automation scenarios related to **pushing changes to multiple network devices**, **network state validation** etc. are going to be added in upcoming releases. The priority is **troubleshooting**.

## 🌱 Starting Fresh
I have a [beginner-friendly course](https://www.udemy.com/course/mcp-server/?referralCode=D62613A8194D2D915B55) on Udemy on how to setup everything from scratch and build your first AI and MCP-based network automation project. Although a shameless plug, I highly recommend going through that course before moving on with this lab.

Now let's go [back](#%EF%B8%8F-repository-lifecycle) to the top of this lab manual.

**Join the course to also get:**
- [x] Full instructor support (Q&A)
- [x] Upgrades on a regular basis
- [x] Access to a private Discord

## ⬆️ Planned Upgrades
Expected in version v3.0:
- [ ] New branch with mixed vendors
- [ ] New troubleshooting scenarios
- [ ] Extra features: NetBox, RAG
- [ ] Multi-agent architecture

## 📄 Disclaimer
This project is intended for educational purposes only. You are responsible for building your own lab environment and meeting the necessary conditions (e.g., RAM/vCPU, router OS images, Claude subscription/API key, etc.).

## 📜 License
Licensed under the [GNU GENERAL PUBLIC LICENSE Version 3](https://github.com/pdudotdev/netaimcp/blob/main/LICENSE).