"""UT-006 — Command Validation: validate_commands() — FORBIDDEN CLI list validation."""
import pytest
from tools.config import validate_commands, FORBIDDEN


# ── FORBIDDEN CLI commands ─────────────────────────────────────────────────────

FORBIDDEN_CLI_CASES = [
    "reload",
    "write erase",
    "erase startup-config",
    "format flash:",
    "delete flash:running-config",
    "boot system flash",
    "crypto key zeroize rsa",
    "no router ospf 1",
    "no router bgp 65000",
    "default interface Ethernet0/1",
    "clear ip ospf process",
    "clear ip bgp *",
    "clear ip route *",
    "debug all",
    # Case-insensitive matching
    "RELOAD",
    "Write Erase",
    "NO ROUTER BGP 65000",
]


@pytest.mark.parametrize("cmd", FORBIDDEN_CLI_CASES)
def test_forbidden_cli_command_blocked(cmd):
    """Verify that known-dangerous CLI commands are rejected by validate_commands().
    Parametrized across all FORBIDDEN patterns including case variants.
    """
    with pytest.raises(ValueError, match="Forbidden command"):
        validate_commands([cmd])


SAFE_CLI_CASES = [
    "ip ospf hello-interval 10",
    "ip ospf dead-interval 40",
    "neighbor 10.0.0.1 remote-as 65001",
    "network 192.168.1.0 0.0.0.255 area 0",
    "ip route 0.0.0.0 0.0.0.0 1.2.3.4",
    "router ospf 1",           # "no router" is forbidden; "router " is allowed
    "passive-interface default",
    "no passive-interface Ethernet0/1",
]


@pytest.mark.parametrize("cmd", SAFE_CLI_CASES)
def test_safe_cli_command_passes(cmd):
    """Legitimate configuration commands must pass validate_commands() without error.
    Confirms that the FORBIDDEN set does not over-block valid operational commands.
    """
    validate_commands([cmd])  # must not raise


# ── Mixed batch: one forbidden stops the whole batch ──────────────────────────

def test_forbidden_in_batch_raises():
    """A single forbidden command in a batch must reject the entire batch.
    Prevents partially applied changes that could leave the device in an inconsistent state.
    """
    cmds = [
        "ip ospf hello-interval 10",
        "reload",                      # forbidden
        "ip ospf dead-interval 40",
    ]
    with pytest.raises(ValueError, match="Forbidden command"):
        validate_commands(cmds)


# ── Rollback advisory generation ──────────────────────────────────────────────

from tools.config import _generate_rollback_advisory


def test_rollback_inverts_no_prefix():
    """A 'no <cmd>' command must produce '<cmd>' as the rollback advisory.
    Inversion lets the operator quickly undo a negation if needed.
    """
    result = _generate_rollback_advisory(["no ip ospf hello-interval 10"])
    assert result == ["ip ospf hello-interval 10"]


def test_rollback_adds_no_prefix():
    """A positive configuration command must produce 'no <cmd>' as the rollback advisory.
    The rollback advisory gives operators a ready-made undo command.
    """
    result = _generate_rollback_advisory(["ip ospf dead-interval 40"])
    assert result == ["no ip ospf dead-interval 40"]


def test_rollback_batch():
    """A batch of commands must produce a matching batch of rollback advisories.
    Each command is independently inverted, preserving order.
    """
    cmds = ["ip ospf hello-interval 5", "no ip ospf dead-interval"]
    result = _generate_rollback_advisory(cmds)
    assert result[0] == "no ip ospf hello-interval 5"
    assert result[1] == "ip ospf dead-interval"


# ── New FORBIDDEN patterns (v5.0 expansion) ────────────────────────────────────

NEW_FORBIDDEN_CASES = [
    # Configuration persistence
    "copy running-config startup-config",
    "copy run start",
    "copy run flash:backup.cfg",
    "write memory",
    "write mem",
    # Wholesale config replacement
    "configure replace flash:backup",
    # Credential and AAA manipulation
    "username admin privilege 15 secret newpass",
    "no username admin",
    "enable secret newpassword",
    "enable password cleartext",
    "snmp-server community public RO",
    "snmp-server community private RW",
    # Crypto key operations
    "crypto key generate rsa modulus 2048",
    "crypto key zeroize rsa",
    # Management lockout
    "transport input none",
    # Case-insensitive variants
    "COPY RUN START",
    "Write Memory",
    "USERNAME testuser SECRET pass",
    "ENABLE SECRET newpass",
    "SNMP-SERVER COMMUNITY public RO",
]


@pytest.mark.parametrize("cmd", NEW_FORBIDDEN_CASES)
def test_new_forbidden_patterns_blocked(cmd):
    """Verify that v5.0-added dangerous CLI patterns are rejected by validate_commands()."""
    with pytest.raises(ValueError, match="Forbidden command"):
        validate_commands([cmd])


# ── Commands that look similar but must NOT be blocked ────────────────────────

NEW_SAFE_CASES = [
    "copy tftp: running-config",          # copy TO running-config is safe (write is safe)
    "show running-config",                 # read-only
    "ip ospf hello-interval 5",
    "no ip ospf hello-interval",
    "router ospf 1",                       # "no router" is forbidden; adding router proc is fine
    "ip route 0.0.0.0 0.0.0.0 Null0",
    "interface GigabitEthernet1",
    "no shutdown",
    "description This WR port is enabled",  # description with WR substring
]


@pytest.mark.parametrize("cmd", NEW_SAFE_CASES)
def test_new_safe_commands_pass(cmd):
    """Commands that resemble blocked patterns but are operationally valid must pass."""
    validate_commands([cmd])  # must not raise


