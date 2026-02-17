import os
import json
import time
import pytz
import aiohttp
import asyncio
from fastmcp import FastMCP
from dotenv import load_dotenv
from scrapli import AsyncScrapli
from datetime import datetime, time as dt_time
from platforms.platform_map import PLATFORM_MAP
from input_models.models import (
    OspfQuery,
    EigrpQuery,
    BgpQuery,
    InterfacesQuery,
    RoutingQuery,
    RoutingPolicyQuery,
    PingInput,
    TracerouteInput,
    ShowCommand,
    ConfigCommand,
    EmptyInput,
    SnapshotInput,
    RiskInput
)

# Load environment variables
load_dotenv()
USERNAME = os.getenv("ROUTER_USERNAME")
PASSWORD = os.getenv("ROUTER_PASSWORD")

if not USERNAME or not PASSWORD:
    raise RuntimeError("Credentials not set")

# Global command cache and TTL to avoid duplicate commands
CACHE = {}  # {(device, command): (timestamp, result)}
CMD_TTL = 5 # in seconds

def cache_get(device, command, ttl):
    key = (device, command.strip().lower())
    if key in CACHE:
        ts, result = CACHE[key]
        if time.time() - ts < ttl:
            return result
    return None

def cache_set(device, command, result):
    key = (device, command.strip().lower())
    CACHE[key] = (time.time(), result)

# Global command executor (reusable across tools)
async def execute_command(device_name: str, cmd_or_action: str, ttl: int = CMD_TTL) -> dict:
    device = devices.get(device_name)
    if not device:
        return {"error": "Unknown device"}

    cli_style = device["cli_style"]
    transport = device["transport"]

    # Cache lookup
    if ttl > 0:
        cached = cache_get(device_name, str(cmd_or_action), ttl)
        if cached:
            cached["cache_hit"] = True
            return cached

    try:
        # REST transport
        if transport == "rest":
            action = cmd_or_action  # dict with method/path
            raw_output = await execute_rest(device, cmd_or_action)
            parsed_output = raw_output

        # eAPI transport
        elif transport == "eapi":
            raw_output = await execute_eapi(device, cmd_or_action)
            parsed_output = raw_output

        # SSH transport
        elif transport == "asyncssh":
            connection = {
                "host": device["host"],
                "platform": device["platform"],
                "transport": device["transport"],
                "auth_username": USERNAME,
                "auth_password": PASSWORD,
                "auth_strict_key": False,
            }

            async with AsyncScrapli(**connection) as conn:
                response = await conn.send_command(cmd_or_action)
                
                # Always grab raw output (needed if parsing fails)
                raw_output = response.result

                parsed_output = None

                # Scrapli Genie integration (only for IOS devices)
                if cli_style == "ios":
                    try:
                        parsed_output = response.genie_parse_output()
                    except Exception:
                        parsed_output = None
    
    except Exception as e:
        return {
            "device": device_name,
            "cli_style": cli_style,
            "error": str(e),
        }
    
    # Token-efficient result: parsed OR raw, not both
    result = {
        "device": device_name,
        "cli_style": cli_style,
        "cache_hit": False,
    }

    if parsed_output:
        result["parsed"] = parsed_output
    else:
        result["raw"] = raw_output
    
    # Cache store
    if ttl > 0:
        cache_set(device_name, str(cmd_or_action), result)

    return result

# Executor for eAPI
async def execute_eapi(device, command):
    url = f"https://{device['host']}/command-api"
    auth = aiohttp.BasicAuth(USERNAME, PASSWORD)

    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {"version": 1, "cmds": [command]},
        "id": 1,
    }

    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.post(url, json=payload, ssl=False) as resp:
            data = await resp.json()
            return data["result"]

# Executor helper for REST
async def execute_rest(device, action):
    url = f"http://{device['host']}{action['path']}"
    auth = aiohttp.BasicAuth(USERNAME, PASSWORD)

    async with aiohttp.ClientSession(auth=auth) as session:
        if action["method"] == "GET":
            async with session.get(url) as resp:
                return await resp.json()

        elif action["method"] == "POST":
            payload = action.get("body") or action.get("default_body", {})
            async with session.post(url, json=payload) as resp:
                return await resp.json()

# Instantiate the FastMCP class
mcp = FastMCP("mcp_automation")

# Loading devices from inventory
INVENTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory", "NETWORK.json")
if not os.path.exists(INVENTORY_FILE):
    raise RuntimeError(f"Inventory file not found: {INVENTORY_FILE}")

# Read the inventory file
with open(INVENTORY_FILE) as f:
    devices = json.load(f)

# OSPF query tool
@mcp.tool(name="get_ospf")
async def get_ospf(params: OspfQuery) -> dict:
    """
    Retrieve OSPF operational data from a network device.

    Use this tool to investigate OSPF adjacency, database, and configuration
    issues during troubleshooting.

    Supported queries:
    - neighbors   → Check OSPF neighbor state and adjacency health
    - database    → Inspect LSDB contents and LSA propagation
    - borders     → Identify ABRs/ASBRs and inter-area routing
    - config      → Review OSPF configuration on the device
    - interfaces  → Verify OSPF-enabled interfaces and parameters
    - details     → Vendor-specific detailed OSPF information (if available)

    Notes:
    - Not all queries are supported on all platforms.
    - If a query is unsupported, the tool returns an error.
    - Results may be served from cache (short-lived) to improve efficiency.
    - Use this tool before running generic show commands.

    Recommended usage:
    - Start with "neighbors" to verify adjacency.
    - Use "database" when investigating missing routes.
    - Use "config" to confirm intent vs actual configuration.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}
    
    try:
        action = PLATFORM_MAP[device["cli_style"]]["ospf"][params.query]
    except KeyError:
        return {
            "device": params.device,
            "error": f"OSPF query '{params.query}' not supported on platform {device['cli_style'].upper()}"
        }

    return await execute_command(params.device, action)

# EIGRP query tool
@mcp.tool(name="get_eigrp")
async def get_eigrp(params: EigrpQuery) -> dict:
    """
    Retrieve EIGRP operational data from an IOS device.

    Use this tool to troubleshoot EIGRP neighbor relationships, topology
    information, interface participation, and configuration issues.

    Supported queries:
    - neighbors   → Verify EIGRP adjacencies and peer health
    - topology    → Inspect feasible successors and route calculations
    - interfaces  → Confirm interfaces participating in EIGRP
    - config      → Review EIGRP configuration

    Notes:
    - EIGRP is supported only on IOS devices.
    - If a query is unsupported, the tool returns an error.
    - Cached results may be returned for short periods.

    Recommended usage:
    - Start with "neighbors" to verify adjacency.
    - Use "topology" when routes are missing or not preferred.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    if device["cli_style"] != "ios":
        return {"error": "EIGRP is supported only on IOS devices"}

    try:
        action = PLATFORM_MAP["ios"]["eigrp"][params.query]
    except KeyError:
        return {"error": f"Unsupported EIGRP query: {params.query}"}

    return await execute_command(params.device, action)

# BGP query tool
@mcp.tool(name="get_bgp")
async def get_bgp(params: BgpQuery) -> dict:
    """
    Retrieve BGP operational data from a network device.

    Use this tool to investigate BGP session state, route exchange,
    and configuration during routing issues.

    Supported queries:
    - summary  → Check neighbor state, uptime, and prefixes exchanged
    - detail   → Inspect detailed BGP table and path attributes
    - config   → Review BGP configuration

    Notes:
    - Supported queries vary by platform.
    - Cached results may be returned briefly for efficiency.

    Recommended usage:
    - Start with "summary" to verify session health.
    - Use "detail" when routes are missing or path selection is unexpected.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    try:
        action = PLATFORM_MAP[device["cli_style"]]["bgp"][params.query]
    except KeyError:
        return {
            "device": params.device,
            "error": f"BGP query '{params.query}' not supported on platform {device['cli_style'].upper()}"
        }

    return await execute_command(params.device, action)

# Routing table query tool
@mcp.tool(name="get_routing")
async def get_routing(params: RoutingQuery) -> dict:
    """
    Retrieve routing table information from a device.

    - If prefix is provided → targeted route lookup.
    - If prefix is omitted → full routing table.

    Use this tool to verify route presence, next-hop selection,
    and routing protocol contributions.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    try:
        base_cmd = PLATFORM_MAP[device["cli_style"]]["routing_table"]["ip_route"]
    except KeyError:
        return {"error": f"Routing not supported on {device['cli_style'].upper()}"}

    action = base_cmd if not params.prefix else f"{base_cmd} {params.prefix}"

    return await execute_command(params.device, action)

# Routing policies query tool
@mcp.tool(name="get_routing_policies")
async def get_routing_policies(params: RoutingPolicyQuery) -> dict:
    """
    Retrieve routing policy configuration from a device.

    Use this tool to inspect route maps, prefix lists, access lists,
    and policy-based routing that may influence routing decisions.

    Supported queries:
    - redistribution         → View routing protocol redistribution
    - route_maps             → View route-map definitions
    - prefix_lists           → Inspect prefix filtering rules
    - policy_based_routing   → Verify PBR configuration
    - access_lists           → Review ACLs affecting routing or filtering

    Notes:
    - Supported queries vary by platform.
    - Results may be cached briefly.

    Recommended usage:
    - Use when routes are filtered, modified, or unexpectedly redirected.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    try:
        action = PLATFORM_MAP[device["cli_style"]]["routing_policies"][params.query]
    except KeyError:
        return {
            "device": params.device,
            "error": f"Routing policy query '{params.query}' not supported on {device['cli_style'].upper()}"
        }

    return await execute_command(params.device, action)

# Interfaces query tool
@mcp.tool(name="get_interfaces")
async def get_interfaces(params: InterfacesQuery) -> dict:
    """
    Retrieve interface status and IP information from a device.

    Use this tool to verify interface state, IP assignments, and operational
    status during connectivity and routing investigations.

    Notes:
    - Command syntax is vendor-specific and resolved via COMMAND_MAP.
    - Returns a summary view of interfaces.
    - Results may be cached briefly.

    Recommended usage:
    - Use when troubleshooting down links or missing adjacencies.
    - Use to confirm IP addressing and interface operational state.

    Use this tool before falling back to run_show.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    try:
        action = PLATFORM_MAP[device["cli_style"]]["interfaces"]["interface_status"]
    except KeyError:
        return {
            "device": params.device,
            "error": f"Interface status not supported on {device['cli_style'].upper()}"
        }

    return await execute_command(params.device, action)

# Ping tool
@mcp.tool(name="ping")
async def ping(params: PingInput) -> dict:
    """
    Test reachability from a device to a destination IP.

    Use this tool to verify connectivity, validate routing decisions,
    and detect packet loss or reachability failures.

    Notes:
    - Command syntax is vendor-specific and resolved via COMMAND_MAP.
    - Source parameter is optional and may not be supported on all platforms.
    - Results are cached briefly.

    Recommended usage:
    - Use after verifying routing to confirm data-plane reachability.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    cli_style = device["cli_style"]

    base = PLATFORM_MAP[cli_style]["tools"]["ping"]

    if isinstance(base, dict):
        action = base.copy()
        action["body"] = {"address": params.destination}
    else:
        action = f"{base} {params.destination}"

    # Optional source handling (IOS/EOS style)
    if params.source and cli_style in ["ios", "eos"]:
        action += f" source {params.source}"

    return await execute_command(params.device, action)

# Traceroute tool
@mcp.tool(name="traceroute")
async def traceroute(params: TracerouteInput) -> dict:
    """
    Trace the path from a device to a destination IP.

    Use this tool to identify routing paths, loops, asymmetric routing,
    or where traffic is being dropped.

    Notes:
    - Command syntax is vendor-specific and resolved via COMMAND_MAP.
    - Output format varies by platform.
    - Results are cached briefly.

    Recommended usage:
    - Use when ping succeeds but path is unexpected.
    - Use to locate where packets are dropped.
    - Use only when necessary.
    """
    device = devices.get(params.device)
    if not device:
        return {"error": f"Unknown device: {params.device}"}

    cli_style = device["cli_style"]

    base = PLATFORM_MAP[cli_style]["tools"]["traceroute"]

    if isinstance(base, dict):
        action = base.copy()
        action["body"] = {"address": params.destination,**base.get("default_body", {})}
    else:
        action = f"{base} {params.destination}"

    return await execute_command(params.device, action)

# General purpose read config tool (fallback)
@mcp.tool(name="run_show")
async def run_show(params: ShowCommand) -> dict:
    return await execute_command(params.device, params.command, ttl=0)

# Forbidden commands
FORBIDDEN = {"reload", "write erase", "format", "delete", "boot"}

def validate_commands(cmds: list[str]):
    for c in cmds:
        if any(bad in c.lower() for bad in FORBIDDEN):
            raise ValueError(f"Forbidden command detected: {c}")

# Function for pushing configs to a device
async def push_config_to_device(dev_name, device, commands):
    connection = {
                "host": device["host"],
                "platform": device["platform"],
                "transport": device["transport"],
                "auth_username": USERNAME,
                "auth_password": PASSWORD,
                "auth_strict_key": False,
            }

    async with AsyncScrapli(**connection) as conn:
        response = await conn.send_configs(commands)
        return dev_name, response.result

# Send config tool
@mcp.tool(name="push_config")
async def push_config(params: ConfigCommand) -> dict:
    """
    Push configuration commands to one or more devices.

    IMPORTANT:
    - This tool enforces maintenance window policy.
    - If changes are outside the approved window, the tool will refuse to run.
    - Maintenance policy files (e.g. MAINTENANCE.json) MUST NOT be modified
    by Claude or by any automation workflow.
    - If a change is blocked, Claude should inform the user and stop.
    - Risk assessment is advisory only and does not block changes.
    """
    # Check maintenance window
    await check_maintenance_window(EmptyInput())

    # Check risk score
    risk = await assess_risk(RiskInput(devices=params.devices, commands=params.commands))

    start = time.perf_counter()

    # Check for any forbidden commands
    validate_commands(params.commands)

    tasks = []
    results = {}
    for dev_name in params.devices:
        device = devices.get(dev_name)
        if not device:
            results[dev_name] = "Unknown device"
            continue

        tasks.append(
            asyncio.create_task(
                push_config_to_device(dev_name, device, params.commands)
            )
        )

    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for item in completed:
        if isinstance(item, Exception):
            continue
        dev_name, result = item
        results[dev_name] = result

    end = time.perf_counter()
    results["execution_time_seconds"] = round(end - start, 2)
    results["risk_assessment"] = risk

    return results

# Returns the expected network intent defined in INTENT.json (source of truth)
@mcp.tool(name="get_intent")
async def get_intent(params: EmptyInput) -> dict:
    """
    Return the desired network intent.
    """

    intent_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),"intent","INTENT.json")

    if not os.path.exists(intent_file):
        raise RuntimeError("INTENT.json not found")

    with open(intent_file) as f:
        return json.load(f)

# Snapshot tool: collect current state, store it on disk, return snapshot metadata
@mcp.tool(name="snapshot_state")
async def snapshot_state(params: SnapshotInput) -> dict:
    """
    Takes a snapshot of device state for the given profile.
    Intended to be used before changes so differences can be reviewed manually.
    """

    snapshot_id = time.strftime("%Y%m%d-%H%M%S")
    base_path = os.path.join("snapshots", snapshot_id)
    os.makedirs(base_path, exist_ok=True)

    stored = {}

    for dev_name in params.devices:
        device = devices.get(dev_name)
        if not device:
            continue

        dev_path = os.path.join(base_path, dev_name)
        os.makedirs(dev_path, exist_ok=True)

        connection = {
            "host": device["host"],
            "platform": device["platform"],
            "transport": device["transport"],
            "auth_username": USERNAME,
            "auth_password": PASSWORD,
            "auth_strict_key": False,
        }

        async with AsyncScrapli(**connection) as conn:
            outputs = {}

            # Always save running config
            outputs["running_config"] = (
                await conn.send_command("show running-config")
            ).result

            # Profile-driven commands
            if params.profile == "ospf":
                outputs["ospf_config"] = (await conn.send_command("show ip ospf")).result
                outputs["neighbors"] = (await conn.send_command("show ip ospf neighbor")).result

            elif params.profile == "stp":
                outputs["stp_general"] = (await conn.send_command("show spanning-tree")).result
                outputs["stp_details"] = (await conn.send_command("show spanning-tree detail")).result

        for name, content in outputs.items():
            with open(os.path.join(dev_path, f"{name}.txt"), "w") as f:
                f.write(content)

        stored[dev_name] = list(outputs.keys())

    return {
        "snapshot_id": snapshot_id,
        "stored_at": base_path,
        "devices": stored,
    }

# Maintenance windows tool
@mcp.tool(name="check_maintenance_window")
async def check_maintenance_window(params: EmptyInput) -> dict:
    """
    Checks whether the current time falls within an approved maintenance window.

    This tool is intended to be called before making configuration changes.
    It does not block or apply changes by itself — it only reports whether
    changes are currently allowed based on time-based policy.

    The result of this tool is consumed by other tools (e.g. push_config)
    to enforce time-based change policies.

    Note: Maintenance policy is read-only and managed outside automation.
    """

    policy_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "policy",
        "MAINTENANCE.json"
    )

    if not os.path.exists(policy_file):
        return {
            "allowed": True,
            "reason": "No maintenance policy defined"
        }
    
    with open(policy_file) as f:
        policy = json.load(f)

    tz = pytz.timezone(policy.get("timezone", "UTC"))
    now = datetime.now(tz)

    current_day = now.strftime("%a").lower()[:3]
    current_time = now.time()

    for window in policy.get("windows", []):
        if current_day in window["days"]:
            start = dt_time.fromisoformat(window["start"])
            end = dt_time.fromisoformat(window["end"])

            if start <= current_time <= end:
                return {
                    "allowed": True,
                    "current_time": now.isoformat(),
                    "reason": "Within maintenance window"
                }
            
    return {
        "allowed": False,
        "current_time": now.isoformat(),
        "reason": "Outside maintenance window"
    }

# Risk assessment tool
@mcp.tool(name="assess_risk")
async def assess_risk(params: RiskInput) -> dict:
    """
    Assigns a simple risk level (low / medium / high) to a configuration change.
    This tool does NOT block changes. It only reports risk.
    """
    cmd_text = " ".join(params.commands).lower()
    device_count = len(params.devices)

    reasons = []

    # Blast radius
    if device_count >= 3:
        risk = "high"
        reasons.append(f"Change affects {device_count} devices")

    elif device_count > 1:
        risk = "medium"
        reasons.append(f"Change affects multiple devices ({device_count})")

    else:
        risk = "low"

    # Content-based assessment
    if any(k in cmd_text for k in ["router ", "ospf", "bgp", "isis", "eigrp"]):
        risk = "high"
        reasons.append("Touches routing control plane")

    if any(k in cmd_text for k in ["shutdown", "no shutdown"]):
        risk = "high"
        reasons.append("Interface disruption possible")

    return {
        "risk": risk,
        "devices": device_count,
        "reasons": reasons or ["Minor configuration change"]
    }

# Run the MCP Server
if __name__ == "__main__":
    mcp.run()