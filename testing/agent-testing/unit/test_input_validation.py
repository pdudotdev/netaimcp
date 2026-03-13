"""UT-004 — Input Validation: input model validation (Literal enums, ShowCommand restriction, JSON parsing)."""
import json
import pytest
from pydantic import ValidationError

from input_models.models import (
    OspfQuery, BgpQuery, RoutingQuery, RoutingPolicyQuery, ShowCommand,
    ConfigCommand, PingInput, TracerouteInput,
)


# ── OspfQuery ──────────────────────────────────────────────────────────────────

VALID_OSPF_QUERIES = ["neighbors", "database", "borders", "config", "interfaces", "details"]
INVALID_OSPF_QUERIES = ["lsdb", "summary", "all", "", "  "]


@pytest.mark.parametrize("q", VALID_OSPF_QUERIES)
def test_ospf_query_valid(q):
    """All documented OSPF query strings must be accepted by OspfQuery.
    Parametrized across every valid query to prevent silent omissions.
    """
    m = OspfQuery(device="E1C", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_OSPF_QUERIES)
def test_ospf_query_invalid(q):
    """Undocumented OSPF query strings must raise ValidationError at model construction.
    Catches invalid queries before they reach the device and cause runtime KeyError.
    """
    with pytest.raises(ValidationError):
        OspfQuery(device="E1C", query=q)


# ── BgpQuery ───────────────────────────────────────────────────────────────────

VALID_BGP_QUERIES = ["summary", "table", "config", "neighbors"]
INVALID_BGP_QUERIES = ["routes", "detail", "peer", ""]


@pytest.mark.parametrize("q", VALID_BGP_QUERIES)
def test_bgp_query_valid(q):
    """All documented BGP query strings must be accepted by BgpQuery."""
    m = BgpQuery(device="E1C", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_BGP_QUERIES)
def test_bgp_query_invalid(q):
    """Undocumented BGP query strings must raise ValidationError at construction."""
    with pytest.raises(ValidationError):
        BgpQuery(device="E1C", query=q)


def test_bgp_neighbor_field_accepted():
    """Optional neighbor IP field must be accepted on BgpQuery."""
    m = BgpQuery(device="E1C", query="neighbors", neighbor="200.40.40.2")
    assert m.neighbor == "200.40.40.2"


def test_bgp_neighbor_field_optional():
    """neighbor field must default to None when omitted."""
    m = BgpQuery(device="E1C", query="summary")
    assert m.neighbor is None


# ── RoutingPolicyQuery ─────────────────────────────────────────────────────────

VALID_RP_QUERIES = [
    "redistribution", "route_maps", "prefix_lists",
    "policy_based_routing", "access_lists",
]
INVALID_RP_QUERIES = ["routes", "summary", "bgp", "nat_pat", ""]


@pytest.mark.parametrize("q", VALID_RP_QUERIES)
def test_routing_policy_query_valid(q):
    """All documented routing-policy query strings must be accepted by RoutingPolicyQuery."""
    m = RoutingPolicyQuery(device="E1C", query=q)
    assert m.query == q


@pytest.mark.parametrize("q", INVALID_RP_QUERIES)
def test_routing_policy_query_invalid(q):
    """Undocumented routing-policy query strings must raise ValidationError at construction."""
    with pytest.raises(ValidationError):
        RoutingPolicyQuery(device="E1C", query=q)


# ── VRF field on query models ──────────────────────────────────────────────────

def test_ospf_query_vrf_field_accepted():
    """Optional vrf field must be accepted on OspfQuery."""
    m = OspfQuery(device="E1C", query="neighbors", vrf="VRF1")
    assert m.vrf == "VRF1"


def test_ospf_query_vrf_field_defaults_to_none():
    """vrf field must default to None when omitted."""
    m = OspfQuery(device="E1C", query="neighbors")
    assert m.vrf is None


def test_bgp_query_vrf_field_accepted():
    """Optional vrf field must be accepted on BgpQuery."""
    m = BgpQuery(device="E1C", query="summary", vrf="VRF1")
    assert m.vrf == "VRF1"


def test_bgp_query_vrf_and_neighbor_coexist():
    """vrf and neighbor fields must both be accepted simultaneously on BgpQuery."""
    m = BgpQuery(device="E1C", query="neighbors", neighbor="200.40.40.2", vrf="VRF1")
    assert m.vrf == "VRF1"
    assert m.neighbor == "200.40.40.2"


def test_routing_query_vrf_field_accepted():
    """Optional vrf field must be accepted on RoutingQuery."""
    m = RoutingQuery(device="E1C", vrf="VRF1")
    assert m.vrf == "VRF1"


def test_routing_query_vrf_defaults_to_none():
    """vrf field must default to None on RoutingQuery when omitted."""
    m = RoutingQuery(device="E1C")
    assert m.vrf is None


def test_routing_policy_query_vrf_field_accepted():
    """Optional vrf field must be accepted on RoutingPolicyQuery."""
    m = RoutingPolicyQuery(device="E1C", query="redistribution", vrf="VRF1")
    assert m.vrf == "VRF1"


def test_ping_vrf_field_accepted():
    """Optional vrf field must be accepted on PingInput."""
    m = PingInput(device="A1C", destination="10.0.0.1", vrf="VRF1")
    assert m.vrf == "VRF1"


def test_ping_vrf_defaults_to_none():
    """vrf field must default to None on PingInput when omitted."""
    m = PingInput(device="A1C", destination="10.0.0.1")
    assert m.vrf is None


def test_traceroute_vrf_field_accepted():
    """Optional vrf field must be accepted on TracerouteInput."""
    m = TracerouteInput(device="A1C", destination="10.0.0.1", vrf="VRF1")
    assert m.vrf == "VRF1"


def test_traceroute_vrf_defaults_to_none():
    """vrf field must default to None on TracerouteInput when omitted."""
    m = TracerouteInput(device="A1C", destination="10.0.0.1")
    assert m.vrf is None


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
    m = ShowCommand(device="A1C", command=cmd)
    assert m.command == cmd


@pytest.mark.parametrize("cmd", INVALID_SHOW_CMDS)
def test_show_command_invalid_cli(cmd):
    """Non-show commands must be rejected by ShowCommand with ValidationError.
    run_show is read-only; configure/clear/debug/reload commands bypass push_config guardrails.
    """
    with pytest.raises(ValidationError):
        ShowCommand(device="A1C", command=cmd)


# ── BaseParamsModel.parse_string_input ─────────────────────────────────────────

def test_parse_string_input_valid_json():
    """A JSON-encoded string must be decoded and used to build the model.
    FastMCP sometimes passes tool params as a JSON string rather than a dict.
    """
    m = OspfQuery.model_validate('{"device": "E1C", "query": "neighbors"}')
    assert m.device == "E1C"
    assert m.query == "neighbors"


def test_parse_string_input_json_with_trailing_garbage():
    """JSON with trailing characters after the closing brace must be accepted.
    raw_decode() is used specifically to handle this MCP encoding artifact.
    """
    m = OspfQuery.model_validate('{"device": "E1C", "query": "neighbors"}}extra')
    assert m.device == "E1C"
    assert m.query == "neighbors"


def test_parse_string_input_invalid_json_raises():
    """A non-JSON string must raise ValidationError, not crash with a raw exception."""
    with pytest.raises(ValidationError):
        OspfQuery.model_validate("not json at all")


def test_parse_string_input_passthrough_dict():
    """A dict input must pass through parse_string_input unchanged.
    The validator only acts when the input is a string — dicts are the normal path.
    """
    m = OspfQuery.model_validate({"device": "E1C", "query": "neighbors"})
    assert m.device == "E1C"
    assert m.query == "neighbors"


def test_parse_string_input_nested_json():
    """Nested JSON objects must be decoded correctly through parse_string_input."""
    m = ConfigCommand.model_validate(
        '{"devices": ["E1C", "E2C"], "commands": ["ip ospf hello-interval 10"]}'
    )
    assert m.devices == ["E1C", "E2C"]
    assert len(m.commands) == 1


# ── ShowCommand JSON restriction ──────────────────────────────────────────────

def test_show_command_netconf_rpc_rejected():
    """JSON with 'rpc' key must be rejected — NETCONF removed."""
    action = json.dumps({"rpc": "get-ospf-neighbor-information"})
    with pytest.raises(ValidationError):
        ShowCommand(device="E1C", command=action)


def test_show_command_netconf_unknown_key_rejected():
    """JSON dict without 'url' key must be rejected by ShowCommand."""
    action = json.dumps({"edit-config": "<config>...</config>"})
    with pytest.raises(ValidationError):
        ShowCommand(device="E1C", command=action)


# ── ShowCommand RESTCONF restriction ──────────────────────────────────────────

def test_show_command_restconf_url_get_allowed():
    """RESTCONF JSON with 'url' and method=GET must be accepted by ShowCommand."""
    action = json.dumps({"url": "Cisco-IOS-XE-ospf-oper:ospf-oper-data", "method": "GET"})
    m = ShowCommand(device="E1C", command=action)
    assert m.command == action


def test_show_command_restconf_url_method_defaults_to_get():
    """RESTCONF JSON with 'url' and no method specified must be accepted (default GET)."""
    action = json.dumps({"url": "ietf-interfaces:interfaces"})
    m = ShowCommand(device="E1C", command=action)
    assert m.command == action


def test_show_command_restconf_patch_rejected():
    """RESTCONF JSON with method=PATCH must be rejected by ShowCommand (not read-only)."""
    action = json.dumps({"url": "Cisco-IOS-XE-native:native/router/bgp", "method": "PATCH"})
    with pytest.raises(ValidationError):
        ShowCommand(device="E1C", command=action)


# ── Additional RESTCONF method rejection ──────────────────────────────────────

def test_show_command_restconf_put_rejected():
    """RESTCONF JSON with method=PUT must be rejected by ShowCommand (not read-only)."""
    action = json.dumps({"url": "Cisco-IOS-XE-native:native/router/bgp", "method": "PUT"})
    with pytest.raises(ValidationError):
        ShowCommand(device="E1C", command=action)


def test_show_command_restconf_post_rejected():
    """RESTCONF JSON with method=POST must be rejected by ShowCommand (not read-only)."""
    action = json.dumps({"url": "Cisco-IOS-XE-native:native/router/bgp", "method": "POST"})
    with pytest.raises(ValidationError):
        ShowCommand(device="E1C", command=action)


def test_show_command_restconf_delete_rejected():
    """RESTCONF JSON with method=DELETE must be rejected by ShowCommand (not read-only)."""
    action = json.dumps({"url": "Cisco-IOS-XE-native:native/router/bgp", "method": "DELETE"})
    with pytest.raises(ValidationError):
        ShowCommand(device="E1C", command=action)


# ── transport Literal validation ───────────────────────────────────────────────

@pytest.mark.parametrize("model,kwargs", [
    (OspfQuery,          {"device": "E1C", "query": "neighbors"}),
    (BgpQuery,           {"device": "E1C", "query": "summary"}),
    (RoutingQuery,       {"device": "E1C"}),
    (RoutingPolicyQuery, {"device": "E1C", "query": "redistribution"}),
])
def test_transport_netconf_rejected(model, kwargs):
    """transport='netconf' must be rejected — NETCONF transport was removed in v5.0."""
    with pytest.raises(ValidationError):
        model(**kwargs, transport="netconf")


@pytest.mark.parametrize("model,kwargs", [
    (OspfQuery,          {"device": "E1C", "query": "neighbors"}),
    (BgpQuery,           {"device": "E1C", "query": "summary"}),
    (RoutingQuery,       {"device": "E1C"}),
    (RoutingPolicyQuery, {"device": "E1C", "query": "redistribution"}),
])
@pytest.mark.parametrize("transport", ["restconf", "ssh"])
def test_transport_valid_values_accepted(model, kwargs, transport):
    """transport='restconf' and transport='ssh' must be accepted by all query models."""
    m = model(**kwargs, transport=transport)
    assert m.transport == transport


# ── IP address validation: PingInput ───────────────────────────────────────────

@pytest.mark.parametrize("ip", ["192.168.1.1", "10.0.0.1", "8.8.8.8", "172.16.0.1", "::1", "2001:db8::1"])
def test_ping_destination_valid_ip(ip):
    """Valid IPv4 and IPv6 addresses must be accepted as ping destination."""
    m = PingInput(device="A1C", destination=ip)
    assert m.destination == ip


@pytest.mark.parametrize("bad", [
    "8.8.8.8 repeat 999999",     # option injection
    "8.8.8.8 source Loopback0",  # option injection
    "google.com",                 # hostname — not allowed
    "",                           # empty
    "not-an-ip",
    "8.8.8.8; reload",
    "1.2.3.4\nshow run",         # newline injection
])
def test_ping_destination_invalid_rejected(bad):
    """Injection attempts and non-IP values must be rejected by PingInput.destination."""
    with pytest.raises(ValidationError):
        PingInput(device="A1C", destination=bad)


@pytest.mark.parametrize("src", ["10.0.0.1", "192.168.1.1", "Loopback0", "GigabitEthernet1", "Ethernet0/1"])
def test_ping_source_valid(src):
    """Valid IP addresses and interface names must be accepted as ping source."""
    m = PingInput(device="A1C", destination="8.8.8.8", source=src)
    assert m.source == src


@pytest.mark.parametrize("bad_src", [
    "Loopback0; reload",   # injection via source
    "Gi1\nshow run",       # newline injection
    "src with spaces and more stuff that is too long" * 5,  # over limit
])
def test_ping_source_invalid_rejected(bad_src):
    """Injection attempts in source field must be rejected by PingInput.source."""
    with pytest.raises(ValidationError):
        PingInput(device="A1C", destination="8.8.8.8", source=bad_src)


def test_ping_source_none_accepted():
    """source=None (omitted) must be accepted — source is optional."""
    m = PingInput(device="A1C", destination="8.8.8.8", source=None)
    assert m.source is None


# ── IP address validation: TracerouteInput ─────────────────────────────────────

@pytest.mark.parametrize("ip", ["10.0.0.1", "192.0.2.1", "::1"])
def test_traceroute_destination_valid_ip(ip):
    """Valid IP addresses must be accepted as traceroute destination."""
    m = TracerouteInput(device="A1C", destination=ip)
    assert m.destination == ip


@pytest.mark.parametrize("bad", ["host.example.com", "10.0.0.1 timeout 60", "10.0.0.1 | more", ""])
def test_traceroute_destination_invalid_rejected(bad):
    """Injection attempts and hostnames must be rejected by TracerouteInput.destination."""
    with pytest.raises(ValidationError):
        TracerouteInput(device="A1C", destination=bad)


# ── IP address validation: BgpQuery.neighbor ───────────────────────────────────

@pytest.mark.parametrize("ip", ["10.0.0.1", "192.168.0.254", "2001:db8::1"])
def test_bgp_neighbor_valid_ip(ip):
    """Valid IP addresses must be accepted as BGP neighbor filter."""
    m = BgpQuery(device="E1C", query="neighbors", neighbor=ip)
    assert m.neighbor == ip


@pytest.mark.parametrize("bad", [
    "1.2.3.4 | include password",  # pipe injection — leaks passwords
    "10.0.0.1 detail",             # option injection
    "neighbor-hostname",           # hostname
    "10.0.0.1\nshow run",         # newline injection
])
def test_bgp_neighbor_invalid_rejected(bad):
    """Injection attempts in neighbor field must be rejected by BgpQuery."""
    with pytest.raises(ValidationError):
        BgpQuery(device="E1C", query="neighbors", neighbor=bad)


def test_bgp_neighbor_none_accepted():
    """neighbor=None (omitted) must be accepted — neighbor is optional."""
    m = BgpQuery(device="E1C", query="neighbors", neighbor=None)
    assert m.neighbor is None


# ── Prefix validation: RoutingQuery.prefix ─────────────────────────────────────

@pytest.mark.parametrize("prefix", ["10.0.0.0/8", "192.168.1.0/24", "0.0.0.0/0", "10.1.2.3"])
def test_routing_prefix_valid(prefix):
    """Valid IPv4 prefixes and addresses must be accepted by RoutingQuery.prefix."""
    m = RoutingQuery(device="C1C", prefix=prefix)
    assert m.prefix == prefix


@pytest.mark.parametrize("bad", [
    "10.0.0.0/8 longer-prefixes",  # option injection
    "10.0.0.0 | include bgp",      # pipe injection
    "default",                      # IOS keyword
    "0.0.0.0\nshow run",           # newline injection
])
def test_routing_prefix_invalid_rejected(bad):
    """Injection attempts in prefix field must be rejected by RoutingQuery."""
    with pytest.raises(ValidationError):
        RoutingQuery(device="C1C", prefix=bad)


def test_routing_prefix_none_accepted():
    """prefix=None (omitted) must be accepted — prefix is optional."""
    m = RoutingQuery(device="C1C", prefix=None)
    assert m.prefix is None


# ── VRF name validation ────────────────────────────────────────────────────────

@pytest.mark.parametrize("vrf", ["Mgmt-intf", "VRF_A", "vrf1", "my-vrf", "V1"])
def test_vrf_valid_names_accepted(vrf):
    """Valid VRF names (alphanumeric + underscore/dash) must be accepted."""
    m = OspfQuery(device="E1C", query="neighbors", vrf=vrf)
    assert m.vrf == vrf


@pytest.mark.parametrize("bad_vrf", [
    "default\nreload",         # newline injection
    "vrf; reload",             # semicolon injection
    "x" * 33,                  # too long (>32 chars)
    "vrf name with spaces",    # spaces not allowed
    "vrf!name",                # special chars
])
def test_vrf_invalid_rejected(bad_vrf):
    """Injection attempts and invalid VRF names must be rejected."""
    with pytest.raises(ValidationError):
        OspfQuery(device="E1C", query="neighbors", vrf=bad_vrf)


def test_vrf_none_accepted():
    """vrf=None (omitted) must be accepted — vrf is optional on all models."""
    m = OspfQuery(device="E1C", query="neighbors", vrf=None)
    assert m.vrf is None


# ── Jira issue_key validation ──────────────────────────────────────────────────

from input_models.models import JiraCommentInput, JiraResolveInput


@pytest.mark.parametrize("key", ["SUP-1", "SUP-12", "AINOC-100", "AB-9999"])
def test_jira_comment_issue_key_valid(key):
    """Valid Jira issue keys (PROJECT-NUMBER) must be accepted."""
    m = JiraCommentInput(issue_key=key, comment="test")
    assert m.issue_key == key


@pytest.mark.parametrize("bad_key", [
    "../../admin",           # path traversal
    "sup-12",               # lowercase project key
    "SUP12",                # missing dash
    "SUP-",                 # missing number
    "SUP-abc",              # non-numeric ID
    "../etc/passwd",        # path traversal
    "SUP-1; DROP TABLE",   # injection
])
def test_jira_comment_issue_key_invalid_rejected(bad_key):
    """Path traversal attempts and malformed issue keys must be rejected."""
    with pytest.raises(ValidationError):
        JiraCommentInput(issue_key=bad_key, comment="test")


@pytest.mark.parametrize("key", ["SUP-1", "AINOC-42"])
def test_jira_resolve_issue_key_valid(key):
    """Valid Jira issue keys must be accepted by JiraResolveInput."""
    m = JiraResolveInput(issue_key=key, resolution_comment="resolved")
    assert m.issue_key == key


def test_jira_resolve_issue_key_invalid_rejected():
    """Path traversal in JiraResolveInput.issue_key must be rejected."""
    with pytest.raises(ValidationError):
        JiraResolveInput(issue_key="../../admin", resolution_comment="test")
