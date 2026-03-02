"""Unit tests for input model validation (Literal enums, ShowCommand restriction, JSON parsing)."""
import json
import pytest
from pydantic import ValidationError

from input_models.models import (
    OspfQuery, EigrpQuery, BgpQuery, RoutingPolicyQuery, ShowCommand,
    ConfigCommand, SnapshotInput,
)


# ── OspfQuery ──────────────────────────────────────────────────────────────────

VALID_OSPF_QUERIES = ["neighbors", "database", "borders", "config", "interfaces", "details"]
INVALID_OSPF_QUERIES = ["lsdb", "summary", "all", "", "  "]


@pytest.mark.parametrize("q", VALID_OSPF_QUERIES)
def test_ospf_query_valid(q):
    """All documented OSPF query strings must be accepted by OspfQuery.
    Parametrized across every valid query to prevent silent omissions.
    """
    m = OspfQuery(device="R1A", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_OSPF_QUERIES)
def test_ospf_query_invalid(q):
    """Undocumented OSPF query strings must raise ValidationError at model construction.
    Catches invalid queries before they reach the device and cause runtime KeyError.
    """
    with pytest.raises(ValidationError):
        OspfQuery(device="R1A", query=q)


# ── EigrpQuery ─────────────────────────────────────────────────────────────────

VALID_EIGRP_QUERIES = ["neighbors", "topology", "config", "interfaces"]
INVALID_EIGRP_QUERIES = ["database", "routes", "summary", ""]


@pytest.mark.parametrize("q", VALID_EIGRP_QUERIES)
def test_eigrp_query_valid(q):
    """All documented EIGRP query strings must be accepted by EigrpQuery."""
    m = EigrpQuery(device="R9C", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_EIGRP_QUERIES)
def test_eigrp_query_invalid(q):
    """Undocumented EIGRP query strings must raise ValidationError at construction."""
    with pytest.raises(ValidationError):
        EigrpQuery(device="R9C", query=q)


# ── BgpQuery ───────────────────────────────────────────────────────────────────

VALID_BGP_QUERIES = ["summary", "table", "config"]
INVALID_BGP_QUERIES = ["neighbors", "routes", "detail", ""]


@pytest.mark.parametrize("q", VALID_BGP_QUERIES)
def test_bgp_query_valid(q):
    """All documented BGP query strings must be accepted by BgpQuery."""
    m = BgpQuery(device="R2C", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_BGP_QUERIES)
def test_bgp_query_invalid(q):
    """Undocumented BGP query strings must raise ValidationError at construction."""
    with pytest.raises(ValidationError):
        BgpQuery(device="R2C", query=q)


# ── RoutingPolicyQuery ─────────────────────────────────────────────────────────

VALID_RP_QUERIES = [
    "redistribution", "route_maps", "prefix_lists",
    "policy_based_routing", "access_lists", "nat_pat",
]
INVALID_RP_QUERIES = ["routes", "summary", "bgp", ""]


@pytest.mark.parametrize("q", VALID_RP_QUERIES)
def test_routing_policy_query_valid(q):
    """All documented routing-policy query strings must be accepted by RoutingPolicyQuery."""
    m = RoutingPolicyQuery(device="R3C", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_RP_QUERIES)
def test_routing_policy_query_invalid(q):
    """Undocumented routing-policy query strings must raise ValidationError at construction."""
    with pytest.raises(ValidationError):
        RoutingPolicyQuery(device="R3C", query=q)


# ── ShowCommand CLI restriction ────────────────────────────────────────────────

VALID_SHOW_CMDS = [
    "show ip route",
    "show ip ospf neighbor",
    "SHOW running-config",          # case-insensitive
    "  show interfaces  ",          # leading whitespace
]

INVALID_SHOW_CMDS = [
    "configure terminal",
    "conf t",
    "clear ip ospf process",
    "debug all",
    "no router ospf 1",
    "reload",
    "",
    "ip route 0.0.0.0 0.0.0.0 1.2.3.4",
]


@pytest.mark.parametrize("cmd", VALID_SHOW_CMDS)
def test_show_command_valid_cli(cmd):
    """Show commands with 'show' prefix must be accepted by ShowCommand.
    Parametrized across case variants and leading-whitespace forms.
    """
    m = ShowCommand(device="R1A", command=cmd)
    assert m.command == cmd


@pytest.mark.parametrize("cmd", INVALID_SHOW_CMDS)
def test_show_command_invalid_cli(cmd):
    """Non-show commands must be rejected by ShowCommand with ValidationError.
    run_show is read-only; configure/clear/debug/reload commands bypass push_config guardrails.
    """
    with pytest.raises(ValidationError):
        ShowCommand(device="R1A", command=cmd)


# ── ShowCommand RouterOS JSON restriction ──────────────────────────────────────

def test_show_command_routeros_get_allowed():
    """RouterOS JSON-encoded GET actions must be accepted by ShowCommand.
    GET is the only read-only HTTP method; it cannot modify device state.
    """
    action = json.dumps({"method": "GET", "path": "/rest/routing/ospf/neighbor"})
    m = ShowCommand(device="R18M", command=action)
    assert m.command == action


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "POST"])
def test_show_command_routeros_non_get_rejected(method):
    """RouterOS JSON-encoded non-GET methods must be rejected by ShowCommand.
    PUT/PATCH/DELETE/POST can modify device state and must go through push_config.
    """
    action = json.dumps({"method": method, "path": "/rest/routing/ospf/instance"})
    with pytest.raises(ValidationError):
        ShowCommand(device="R18M", command=action)


@pytest.mark.parametrize("bad_path", [
    "/ip/route",               # missing /rest/ prefix
    "rest/routing/ospf",       # missing leading slash
    "../etc/passwd",           # path traversal
    "/rest/../../system",      # path traversal within /rest/
    "/rest/ospf\x00neighbor",  # null byte injection
])
def test_show_command_routeros_bad_path_rejected(bad_path):
    """RouterOS GET actions with invalid or dangerous paths must be rejected by ShowCommand.
    Paths must start with '/rest/' and must not contain traversal sequences or null bytes.
    """
    action = json.dumps({"method": "GET", "path": bad_path})
    with pytest.raises(ValidationError):
        ShowCommand(device="R18M", command=action)


# ── SnapshotInput profile validation ─────────────────────────────────────────

@pytest.mark.parametrize("profile", ["ospf", "stp", "eigrp", "bgp"])
def test_snapshot_profile_valid(profile):
    """Valid snapshot profiles must be accepted by SnapshotInput."""
    m = SnapshotInput(devices=["R1A"], profile=profile)
    assert m.profile == profile


@pytest.mark.parametrize("profile", ["all", "", "OSPF", "isis"])
def test_snapshot_profile_invalid(profile):
    """Invalid snapshot profiles must raise ValidationError at model construction.
    Only 'ospf', 'stp', 'eigrp', and 'bgp' are defined; other values are rejected.
    """
    with pytest.raises(ValidationError):
        SnapshotInput(devices=["R1A"], profile=profile)


# ── ConfigCommand snapshot_before field ───────────────────────────────────────

def test_config_command_snapshot_before_defaults_false():
    """snapshot_before must default to False to preserve backward-compatible push_config behaviour."""
    m = ConfigCommand(devices=["R1A"], commands=["ip ospf hello-interval 10"])
    assert m.snapshot_before is False


def test_config_command_snapshot_before_true():
    """snapshot_before=True must be accepted and stored by ConfigCommand."""
    m = ConfigCommand(devices=["R1A"], commands=["ip ospf hello-interval 10"], snapshot_before=True)
    assert m.snapshot_before is True


# ── BaseParamsModel.parse_string_input ─────────────────────────────────────────

def test_parse_string_input_valid_json():
    """A JSON-encoded string must be decoded and used to build the model.
    FastMCP sometimes passes tool params as a JSON string rather than a dict.
    """
    m = OspfQuery.model_validate('{"device": "R1A", "query": "neighbors"}')
    assert m.device == "R1A"
    assert m.query == "neighbors"


def test_parse_string_input_json_with_trailing_garbage():
    """JSON with trailing characters after the closing brace must be accepted.
    raw_decode() is used specifically to handle this MCP encoding artifact.
    """
    m = OspfQuery.model_validate('{"device": "R1A", "query": "neighbors"}}extra')
    assert m.device == "R1A"
    assert m.query == "neighbors"


def test_parse_string_input_invalid_json_raises():
    """A non-JSON string must raise ValidationError, not crash with a raw exception."""
    with pytest.raises(ValidationError):
        OspfQuery.model_validate("not json at all")


def test_parse_string_input_passthrough_dict():
    """A dict input must pass through parse_string_input unchanged.
    The validator only acts when the input is a string — dicts are the normal path.
    """
    m = OspfQuery.model_validate({"device": "R1A", "query": "neighbors"})
    assert m.device == "R1A"
    assert m.query == "neighbors"


def test_parse_string_input_nested_json():
    """Nested JSON objects must be decoded correctly through parse_string_input."""
    # EigrpQuery is a simpler model; ConfigCommand has nested list fields
    m = ConfigCommand.model_validate(
        '{"devices": ["R1A", "R3C"], "commands": ["ip ospf hello-interval 10"]}'
    )
    assert m.devices == ["R1A", "R3C"]
    assert len(m.commands) == 1
