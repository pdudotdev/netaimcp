import ipaddress
import json
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# Compiled patterns for parameter validation
_VRF_RE    = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')
_SOURCE_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9/:.-]{0,49}$')   # IP or interface name
_PREFIX_RE = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$')
_JIRA_KEY_RE = re.compile(r'^[A-Z][A-Z0-9]+-\d+$')


class BaseParamsModel(BaseModel):
    """Base class for all MCP tool input models.

    Adds a pre-validator that handles the case where the model passes `params`
    as a JSON string instead of a dict (e.g. '{"device": "R1A"}}' with trailing
    garbage). Uses raw_decode() so any trailing characters after valid JSON are
    silently ignored.

    Also validates the optional `vrf` field (present on most subclasses) to
    prevent CLI injection via VRF name substitution in platform_map.py.
    """
    @model_validator(mode='before')
    @classmethod
    def parse_string_input(cls, v):
        if isinstance(v, str):
            try:
                obj, _ = json.JSONDecoder().raw_decode(v.strip())
                return obj
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"Could not parse params as JSON: {v!r}") from e
        return v

    @field_validator('vrf', mode='before', check_fields=False)
    @classmethod
    def _validate_vrf(cls, v):
        if v is None:
            return v
        if not _VRF_RE.match(str(v)):
            raise ValueError(
                f"vrf must be alphanumeric with underscores/dashes, max 32 chars. Got: {v!r}"
            )
        return v


# OSPF query - input model
class OspfQuery(BaseParamsModel):
    device: str = Field(..., description="Device name from inventory")
    query: Literal["neighbors", "database", "borders", "config", "interfaces", "details"] = Field(
        ..., description="neighbors | database | borders | config | interfaces | details"
    )
    vrf: str | None = Field(None, description="Optional VRF name (default: global routing table)")
    transport: Literal["restconf", "ssh"] | None = Field(
        None, description="Force a specific transport tier (restconf/ssh). Default: auto (ActionChain fallback). Only applies to c8000v devices."
    )

# BGP query - input model
class BgpQuery(BaseParamsModel):
    device: str
    query: Literal["summary", "table", "config", "neighbors"] = Field(
        ..., description="summary | table | config | neighbors"
    )
    neighbor: str | None = Field(None, description="Optional neighbor IP to filter output (neighbors query, IOS only)")
    vrf: str | None = Field(None, description="Optional VRF name (default: global routing table)")
    transport: Literal["restconf", "ssh"] | None = Field(
        None, description="Force a specific transport tier (restconf/ssh). Default: auto (ActionChain fallback). Only applies to c8000v devices."
    )

    @field_validator('neighbor')
    @classmethod
    def _validate_neighbor(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"neighbor must be a valid IP address, got: {v!r}")
        return v

class RoutingQuery(BaseParamsModel):
    device: str
    prefix: str | None = Field(None, description="Optional prefix to look up")
    vrf: str | None = Field(None, description="Optional VRF name (default: global routing table)")
    transport: Literal["restconf", "ssh"] | None = Field(
        None, description="Force a specific transport tier (restconf/ssh). Default: auto (ActionChain fallback). Only applies to c8000v devices."
    )

    @field_validator('prefix')
    @classmethod
    def _validate_prefix(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _PREFIX_RE.match(v):
            raise ValueError(
                f"prefix must be a valid IPv4 address or CIDR (e.g. 10.0.0.0/24), got: {v!r}"
            )
        return v

# Routing policies query - input model
class RoutingPolicyQuery(BaseParamsModel):
    device: str
    query: Literal[
        "redistribution", "route_maps", "prefix_lists",
        "policy_based_routing", "access_lists"
    ] = Field(..., description="redistribution | route_maps | prefix_lists | policy_based_routing | access_lists")
    vrf: str | None = Field(None, description="Optional VRF name (default: global routing table)")
    transport: Literal["restconf", "ssh"] | None = Field(
        None, description="Force a specific transport tier (restconf/ssh). Default: auto (ActionChain fallback). Only applies to c8000v devices."
    )

# Interfaces query - input model
class InterfacesQuery(BaseParamsModel):
    device: str = Field(..., description="Device name from inventory")
    transport: Literal["restconf", "ssh"] | None = Field(
        None, description="Force a specific transport tier (restconf/ssh). Default: auto (ActionChain fallback). Only applies to c8000v devices."
    )

# Ping - input model
class PingInput(BaseParamsModel):
    device: str = Field(..., description="Device name from inventory")
    destination: str = Field(..., description="IP address to ping")
    source: str | None = Field(None, description="Optional source IP or interface name")
    vrf: str | None = Field(None, description="Optional VRF name (default: global routing table)")

    @field_validator('destination')
    @classmethod
    def _validate_destination(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"destination must be a valid IP address, got: {v!r}")
        return v

    @field_validator('source')
    @classmethod
    def _validate_source(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Accept valid IP address or interface name (e.g. Loopback0, GigabitEthernet1, Ethernet0/1)
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            pass
        if not _SOURCE_RE.match(v):
            raise ValueError(
                f"source must be a valid IP address or interface name, got: {v!r}"
            )
        return v

# Traceroute - input model
class TracerouteInput(BaseParamsModel):
    device: str = Field(..., description="Device name from inventory")
    destination: str = Field(..., description="IP address to trace")
    source: str | None = Field(None, description="Optional source IP or interface name")
    vrf: str | None = Field(None, description="Optional VRF name (default: global routing table)")

    @field_validator('destination')
    @classmethod
    def _validate_destination(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"destination must be a valid IP address, got: {v!r}")
        return v

    @field_validator('source')
    @classmethod
    def _validate_source(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            pass
        if not _SOURCE_RE.match(v):
            raise ValueError(
                f"source must be a valid IP address or interface name, got: {v!r}"
            )
        return v

# Show command - input model
class ShowCommand(BaseParamsModel):
    """Run a show command against a network device."""
    device: str = Field(..., description="Device name from inventory (e.g. A1C, E1C)")
    command: str = Field(..., description="Show command to execute on the device")

    @field_validator("command")
    @classmethod
    def must_be_read_only(cls, v: str) -> str:
        """Enforce read-only commands across all supported transports.

        Accepted forms:
          - CLI string starting with 'show ' (IOS asyncssh / Scrapli SSH)
          - RESTCONF JSON: {"url": "...", "method": "GET"}
        """
        stripped = v.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                # RESTCONF dict: url + GET method (read-only)
                if "url" in parsed:
                    if parsed.get("method", "GET").upper() != "GET":
                        raise ValueError(
                            f"run_show RESTCONF action must use method=GET. Got: {stripped[:80]!r}"
                        )
                    return v
                raise ValueError(
                    f"run_show JSON action must have 'url' key. Got: {stripped[:80]!r}"
                )
        except json.JSONDecodeError:
            pass

        # CLI command: must start with "show " (case-insensitive)
        if not stripped.lower().startswith("show "):
            raise ValueError(
                f"run_show only accepts read-only commands (must start with 'show '). Got: {stripped!r}"
            )
        return v

# Config commands - input model
class ConfigCommand(BaseParamsModel):
    """Send configuration commands to one or more devices."""
    devices: list[str] = Field(..., description="Device names from inventory (e.g. ['E1C','E2C'])")
    commands: list[str] = Field(..., description="Configuration commands to apply")

# Empty placeholder - input model
class EmptyInput(BaseParamsModel):
    pass

# Risk score - input model
class RiskInput(BaseParamsModel):
    devices: list[str] = Field(..., description="Devices affected by the config change")
    commands: list[str] = Field(..., description="The configuration commands to apply")

# Jira case management - input models
class JiraCommentInput(BaseParamsModel):
    issue_key: str = Field(..., description="Jira issue key (e.g. 'SUP-12')")
    comment: str = Field(..., description="Comment text to add to the ticket")

    @field_validator('issue_key')
    @classmethod
    def _validate_issue_key(cls, v: str) -> str:
        if not _JIRA_KEY_RE.match(v):
            raise ValueError(
                f"issue_key must match Jira format (e.g. SUP-12, AINOC-1). Got: {v!r}"
            )
        return v

class JiraResolveInput(BaseParamsModel):
    issue_key: str = Field(..., description="Jira issue key (e.g. 'SUP-12')")
    resolution_comment: str = Field(..., description="Resolution summary to add as final comment")
    resolution: str = Field("Done", description="Transition name: 'Done', 'Resolved', or \"Won't Fix\"")

    @field_validator('issue_key')
    @classmethod
    def _validate_issue_key(cls, v: str) -> str:
        if not _JIRA_KEY_RE.match(v):
            raise ValueError(
                f"issue_key must match Jira format (e.g. SUP-12, AINOC-1). Got: {v!r}"
            )
        return v

# Approval request - input model
class ApprovalInput(BaseParamsModel):
    """Request operator approval for a proposed configuration change via Discord."""
    issue_key: str | None = Field(None, description="Jira issue key (if available, e.g. 'SUP-12')")
    summary: str = Field(..., description="One-line summary of the proposed fix")
    findings: str = Field(..., description="Full findings table in markdown format")
    commands: list[str] = Field(..., description="Configuration commands to apply")
    devices: list[str] = Field(..., description="Target device names from inventory")
    risk_level: Literal["low", "medium", "high"] = Field(
        ..., description="Risk level from assess_risk: low | medium | high"
    )
    timeout_minutes: int = Field(10, description="Minutes to wait for operator response (default: 10)")

    @field_validator('issue_key')
    @classmethod
    def _validate_issue_key(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _JIRA_KEY_RE.match(v):
            raise ValueError(
                f"issue_key must match Jira format (e.g. SUP-12, AINOC-1). Got: {v!r}"
            )
        return v


class ApprovalOutcomeInput(BaseParamsModel):
    """Post the final outcome of an approval to Discord."""
    message_id: str = Field(..., description="Discord message ID returned by request_approval")
    decision: str = Field(..., description="approved | rejected | expired")
    decided_by: str | None = Field(None, description="Username who approved or rejected")
    verified: bool | None = Field(None, description="True if post-fix verification passed, False if failed, None if not applicable")
    verification_detail: str | None = Field(None, description="Short verification result summary (e.g. 'OSPF neighbor restored to FULL')")
