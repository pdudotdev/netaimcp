"""Network state tools: get_intent, snapshot_state, check_maintenance_window, assess_risk."""
import json
import logging
import os
import time
import pytz
from datetime import datetime, time as dt_time

log = logging.getLogger("ainoc.tools.state")

from core.inventory import devices
from transport import execute_command
from input_models.models import EmptyInput, SnapshotInput, RiskInput

_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_INTENT_FILE = os.path.join(_BASE_DIR, "intent",  "INTENT.json")
_POLICY_FILE = os.path.join(_BASE_DIR, "policy",  "MAINTENANCE.json")
_PATHS_FILE  = os.path.join(_BASE_DIR, "sla_paths", "paths.json")

# Roles that make a device a critical control-plane node
_HIGH_RISK_ROLES = {"ABR", "ASBR", "IGP_REDISTRIBUTOR", "NAT_EDGE", "ROUTE_REFLECTOR"}

# Snapshot commands per profile and cli_style.
# Each entry: (output_filename, CLI-command-or-REST-action).
_SNAPSHOT_PROFILES: dict[str, dict[str, list]] = {
    "ospf": {
        "ios": [
            ("running_config", "show running-config"),
            ("ospf_config",    "show ip ospf"),
            ("neighbors",      "show ip ospf neighbor"),
        ],
        "eos": [
            ("running_config", "show running-config"),
            ("ospf_config",    "show ip ospf"),
            ("neighbors",      "show ip ospf neighbor detail"),
        ],
        "routeros": [
            ("ip_addresses",   {"method": "GET", "path": "/rest/ip/address"}),
            ("ospf_instances", {"method": "GET", "path": "/rest/routing/ospf/instance"}),
            ("ospf_neighbors", {"method": "GET", "path": "/rest/routing/ospf/neighbor"}),
        ],
    },
    "stp": {
        "ios": [
            ("running_config", "show running-config"),
            ("stp_general",    "show spanning-tree"),
            ("stp_details",    "show spanning-tree detail"),
        ],
        "eos": [
            ("running_config", "show running-config"),
            ("stp_general",    "show spanning-tree"),
        ],
        # RouterOS does not have STP; profile yields no commands for routeros
    },
    "eigrp": {
        "ios": [
            ("running_config",  "show running-config"),
            ("eigrp_neighbors", "show ip eigrp neighbors"),
            ("eigrp_topology",  "show ip eigrp topology"),
        ],
        # EIGRP not supported on EOS or RouterOS in this lab
    },
    "bgp": {
        "ios": [
            ("running_config", "show running-config"),
            ("bgp_summary",    "show ip bgp summary"),
            ("bgp_table",      "show ip bgp"),
        ],
        "eos": [
            ("running_config", "show running-config"),
            ("bgp_summary",    "show ip bgp summary"),
            ("bgp_table",      "show ip bgp"),
        ],
        "routeros": [
            ("bgp_connections", {"method": "GET", "path": "/rest/routing/bgp/connection"}),
            ("bgp_sessions",    {"method": "GET", "path": "/rest/routing/bgp/session"}),
        ],
    },
}


async def get_intent(params: EmptyInput) -> dict:
    """Return the desired network intent."""
    if not os.path.exists(_INTENT_FILE):
        raise RuntimeError("INTENT.json not found")
    with open(_INTENT_FILE) as f:
        return json.load(f)


async def snapshot_state(params: SnapshotInput) -> dict:
    """
    Takes a snapshot of device state for the given profile.
    Intended to be used before changes so differences can be reviewed manually.
    """
    snapshot_id = time.strftime("%Y%m%d-%H%M%S")
    base_path   = os.path.join("snapshots", snapshot_id)
    os.makedirs(base_path, exist_ok=True)

    stored = {}

    for dev_name in params.devices:
        device = devices.get(dev_name)
        if not device:
            continue

        cli_style    = device["cli_style"]
        profile_cmds = _SNAPSHOT_PROFILES.get(params.profile, {}).get(cli_style)

        if not profile_cmds:
            stored[dev_name] = f"No snapshot profile '{params.profile}' defined for {cli_style}"
            continue

        dev_path = os.path.join(base_path, dev_name)
        os.makedirs(dev_path, exist_ok=True)

        outputs = {}
        for cmd_name, cmd_action in profile_cmds:
            result = await execute_command(dev_name, cmd_action, ttl=0)
            # Store plain text for CLI output; JSON for REST/parsed results
            if "raw" in result and isinstance(result["raw"], str):
                outputs[cmd_name] = result["raw"]
            else:
                outputs[cmd_name] = json.dumps(result.get("parsed") or result, indent=2)

        for name, content in outputs.items():
            with open(os.path.join(dev_path, f"{name}.txt"), "w") as f:
                f.write(content)

        stored[dev_name] = list(outputs.keys())

    log.info("snapshot complete: id=%s devices=%s", snapshot_id, list(stored.keys()))
    return {
        "snapshot_id": snapshot_id,
        "stored_at":   base_path,
        "devices":     stored,
    }


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
    if not os.path.exists(_POLICY_FILE):
        return {"allowed": True, "reason": "No maintenance policy defined"}

    with open(_POLICY_FILE) as f:
        policy = json.load(f)

    tz           = pytz.timezone(policy.get("timezone", "UTC"))
    now          = datetime.now(tz)
    current_day  = now.strftime("%a").lower()[:3]
    current_time = now.time()

    for window in policy.get("windows", []):
        if current_day in window["days"]:
            start = dt_time.fromisoformat(window["start"])
            end   = dt_time.fromisoformat(window["end"])
            if start <= current_time <= end:
                log.info("maintenance window check: allowed=True at %s", now.isoformat())
                return {
                    "allowed":      True,
                    "current_time": now.isoformat(),
                    "reason":       "Within maintenance window",
                }

    log.info("maintenance window check: allowed=False at %s", now.isoformat())
    return {
        "allowed":      False,
        "current_time": now.isoformat(),
        "reason":       "Outside maintenance window",
    }


async def assess_risk(params: RiskInput) -> dict:
    """
    Assigns a simple risk level (low / medium / high) to a configuration change.
    This tool does NOT block changes. It only reports risk.
    """
    cmd_text     = " ".join(params.commands).lower()
    device_count = len(params.devices)
    risk         = "low"
    reasons      = []

    # ── Device count ─────────────────────────────────────────────────────────
    if device_count >= 3:
        risk = "high"
        reasons.append(f"Change affects {device_count} devices")
    elif device_count > 1:
        risk = "medium"
        reasons.append(f"Change affects multiple devices ({device_count})")

    # ── Critical device roles from INTENT.json ────────────────────────────────
    try:
        with open(_INTENT_FILE) as f:
            intent = json.load(f)
        routers = intent.get("routers", {})
        for dev_name in params.devices:
            dev_roles = set(routers.get(dev_name, {}).get("roles", []))
            critical = dev_roles & _HIGH_RISK_ROLES
            if critical:
                risk = "high"
                reasons.append(f"{dev_name} has critical role(s): {', '.join(sorted(critical))}")
    except Exception as e:
        log.warning("assess_risk: could not load INTENT.json: %s", e)

    # ── SLA path impact from paths.json ───────────────────────────────────────
    try:
        with open(_PATHS_FILE) as f:
            sla_paths = json.load(f).get("paths", [])
        affected = {p["id"] for p in sla_paths
                    if any(d in p.get("scope_devices", []) for d in params.devices)}
        if len(affected) >= 3:
            risk = "high"
            reasons.append(f"Change affects {len(affected)} SLA monitoring paths")
        elif affected:
            if risk == "low":
                risk = "medium"
            reasons.append(f"Change affects {len(affected)} SLA monitoring path(s)")
    except Exception as e:
        log.warning("assess_risk: could not load paths.json: %s", e)

    # ── Command content ───────────────────────────────────────────────────────
    if any(k in cmd_text for k in ("router ", "ospf", "bgp", "isis", "eigrp")):
        risk = "high"
        reasons.append("Touches routing control plane")

    if any(k in cmd_text for k in ("shutdown", "no shutdown")):
        risk = "high"
        reasons.append("Interface disruption possible")

    return {
        "risk":    risk,
        "devices": device_count,
        "reasons": reasons or ["Minor configuration change"],
    }
