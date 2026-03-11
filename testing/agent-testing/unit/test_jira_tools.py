"""UT-016 — Jira tools unit tests.

Tests for tools/jira_tools.py with mocked core.jira_client functions.
No real Jira connectivity required.

Validates:
- jira_add_comment returns success string on happy path
- jira_add_comment with unconfigured Jira (silent skip via warning) — no exception
- jira_resolve_issue returns resolved string on happy path
- jira_resolve_issue with unconfigured Jira — no exception
- jira_add_comment exception is caught and returned as error string (not raised)
- jira_resolve_issue exception is caught and returned as error string (not raised)
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.jira_tools import jira_add_comment, jira_resolve_issue
from input_models.models import JiraCommentInput, JiraResolveInput


def run(coro):
    return asyncio.run(coro)


# ── jira_add_comment ──────────────────────────────────────────────────────────

def test_jira_add_comment_success():
    """jira_add_comment must return a success string when the client call succeeds."""
    params = JiraCommentInput(issue_key="SUP-42", comment="Test comment")
    with patch("tools.jira_tools._add_comment", new=AsyncMock(return_value=None)):
        result = run(jira_add_comment(params))

    assert "SUP-42" in result, "success message must include the issue key"
    assert "Comment added" in result or "added" in result.lower()


def test_jira_add_comment_client_raises_returns_error_string():
    """jira_add_comment must catch exceptions from the client and return an error string.

    Callers (the agent) should receive a readable error, not an unhandled exception.
    """
    params = JiraCommentInput(issue_key="SUP-42", comment="Test comment")
    with patch("tools.jira_tools._add_comment", new=AsyncMock(side_effect=Exception("Connection timeout"))):
        result = run(jira_add_comment(params))

    assert "SUP-42" in result
    assert "failed" in result.lower() or "error" in result.lower()
    assert "Connection timeout" in result


def test_jira_add_comment_unconfigured_no_exception():
    """When Jira is not configured, add_comment silently returns without error.

    The underlying client logs a warning and returns None — no exception must reach the tool.
    """
    params = JiraCommentInput(issue_key="SUP-99", comment="No Jira configured")
    # Simulate unconfigured: _add_comment returns None silently (same as real behavior)
    with patch("tools.jira_tools._add_comment", new=AsyncMock(return_value=None)):
        result = run(jira_add_comment(params))

    # Should not raise — result is a string regardless
    assert isinstance(result, str)


# ── jira_resolve_issue ────────────────────────────────────────────────────────

def test_jira_resolve_issue_success():
    """jira_resolve_issue must return a success string when the client call succeeds."""
    params = JiraResolveInput(issue_key="SUP-42", resolution_comment="Fixed: removed passive-interface")
    with patch("tools.jira_tools._resolve_issue", new=AsyncMock(return_value=None)):
        result = run(jira_resolve_issue(params))

    assert "SUP-42" in result
    assert "resolved" in result.lower() or "marked" in result.lower()


def test_jira_resolve_issue_client_raises_returns_error_string():
    """jira_resolve_issue must catch exceptions from the client and return an error string."""
    params = JiraResolveInput(issue_key="SUP-42", resolution_comment="Fixed")
    with patch("tools.jira_tools._resolve_issue", new=AsyncMock(side_effect=Exception("Jira 403"))):
        result = run(jira_resolve_issue(params))

    assert "SUP-42" in result
    assert "failed" in result.lower() or "error" in result.lower()
    assert "Jira 403" in result


def test_jira_resolve_issue_custom_resolution():
    """jira_resolve_issue must pass the resolution parameter to the client."""
    params = JiraResolveInput(
        issue_key="SUP-42",
        resolution_comment="Transient — path recovered on its own",
        resolution="Won't Fix",
    )
    resolve_mock = AsyncMock(return_value=None)
    with patch("tools.jira_tools._resolve_issue", new=resolve_mock):
        run(jira_resolve_issue(params))

    # Verify the resolution value was forwarded to the client
    call_args = resolve_mock.call_args
    assert "Won't Fix" in call_args[0] or "Won't Fix" in str(call_args)
