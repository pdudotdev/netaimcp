import sys
import time
import asyncio
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from MCPServer import (
execute_command,
get_ospf,
get_eigrp,
get_bgp,
get_interfaces,
get_routing,
get_routing_policies,
ping,
traceroute,
run_show,
OspfQuery,
EigrpQuery,
BgpQuery,
InterfacesQuery,
RoutingQuery,
RoutingPolicyQuery,
PingInput,
TracerouteInput,
ShowCommand,
)

# Devices to test (adjust if needed)
IOS1 = "R3C"
IOS2 = "R5C"
IOS3 = "R8C"

EOS1 = "R1A"
EOS2 = "R2A"
EOS3 = "R7A"

ROS1 = "R18M"
ROS2 = "R19M"
ROS3 = "R20M"

async def test_ssh_ios():
    print("\n=== IOS SSH TEST ===")
    result = await execute_command(IOS1, "show version")
    print(result)


async def test_eapi_arista():
    print("\n=== Arista eAPI TEST ===")
    result = await execute_command(EOS1, "show version")
    print(result)


async def test_rest_mikrotik():
    print("\n=== MikroTik REST TEST ===")
    action = {"method": "GET", "path": "/rest/ip/route"}
    result = await execute_command(ROS1, action)
    print(result)


async def test_tools():
    print("\n=== TOOL TESTS (MULTI-VENDOR) ===")

    print("\n-- OSPF (EOS) --") 
    print(await get_ospf(OspfQuery(device=EOS1, query="neighbors")))

    print("\n-- EIGRP (IOS) --") 
    print(await get_eigrp(EigrpQuery(device=IOS1, query="neighbors")))

    print("\n-- BGP (ROS) --") 
    print(await get_bgp(BgpQuery(device=ROS1, query="summary")))

    print("\n-- Interfaces (ROS) --") 
    print(await get_interfaces(InterfacesQuery(device=ROS2, query="interface_status")))
    
    print("\n-- Routing table (IOS) --") 
    print(await get_routing(RoutingQuery(device=IOS2, prefix="10.0.0.9")))

    print("\n-- Ping (EOS) --") 
    print(await ping(PingInput(device=EOS2, destination="10.1.1.5"))) 

    print("\n-- Routing policies (IOS) --") 
    print(await get_routing_policies(RoutingPolicyQuery(device=IOS3, query="route_maps"))) 
    
    print("\n-- Traceroute (ROS) --") 
    print(await traceroute(TracerouteInput(device=ROS3, destination="172.16.77.2"))) 
    
    print("\n-- run_show (EOS) --") 
    print(await run_show(ShowCommand(device=EOS3, command="show ip arp")))

    print("\n-- Redistribution policies (ROS) --")
    print(await get_routing_policies(RoutingPolicyQuery(device=ROS1, query="redistribution")))

async def test_cache_behavior():
    print("\n=== CACHE TEST ===")

    device = IOS1
    command = "show clock"

    print("\n-- First call (should execute) --")
    r1 = await execute_command(device, command)
    print("cache_hit:", r1.get("cache_hit"))

    print("\n-- Second call within TTL (should use cache) --")
    r2 = await execute_command(device, command)
    print("cache_hit:", r2.get("cache_hit"))

    print("\nSleeping past TTL...")
    await asyncio.sleep(6)  # CMD_TTL = 5s

    print("\n-- Third call after TTL (should execute again) --")
    r3 = await execute_command(device, command)
    print("cache_hit:", r3.get("cache_hit"))

async def main():
    await test_ssh_ios()
    await test_eapi_arista()
    await test_rest_mikrotik()
    await test_tools()
    await test_cache_behavior()

if __name__ == "__main__":
    asyncio.run(main())
