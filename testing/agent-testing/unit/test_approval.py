"""UT-017 — Discord approval unit tests.

Tests for core/discord_approval.py and tools/approval.py with mocked aiohttp.
No real Discord connectivity required.

Validates:
- post_approval_request posts embed and adds ✅/❌ reactions
- poll_for_reaction returns "approved" when a human reacts ✅
- poll_for_reaction returns "rejected" when a human reacts ❌
- poll_for_reaction returns "expired" when no human reacts within timeout
- poll_for_reaction removes bot reactions (DELETE) on expiry
- poll_for_reaction ignores bot reactions (bot.get("bot") == True)
- post_outcome posts a reply referencing the original message
- post_outcome rejection message mentions Jira
- _table_to_bullets converts markdown table to bullet points
- request_approval tool returns {"decision": "skipped"} when Discord not configured
- request_approval tool returns decision dict when Discord is configured
- request_approval honours APPROVAL_TIMEOUT_MINUTES env var
- request_approval auto-posts expiry outcome to Discord (expired is terminal)
- request_approval does NOT auto-post for approved (agent calls post_approval_outcome after verify)
- post_approval_outcome posts outcome when Discord configured
- post_approval_outcome returns skipped when Discord not configured
- ApprovalInput validates issue_key format
- ApprovalInput rejects invalid issue_key
- ApprovalInput issue_key is optional (None accepted)
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.discord_approval import (
    _table_to_bullets,
    is_configured,
    post_approval_request,
    poll_for_reaction,
    post_outcome,
)
from input_models.models import ApprovalInput, ApprovalOutcomeInput
from tools.approval import request_approval, post_approval_outcome


def run(coro):
    return asyncio.run(coro)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_response(status: int, json_data=None, text_data=""):
    """Return a mock aiohttp response context manager."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.text = AsyncMock(return_value=text_data)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


SAMPLE_FINDINGS = "| Finding | Detail | Status |\n|---------|--------|--------|\n| OSPF | 0 neighbors | ✗ |"
SAMPLE_COMMANDS = ["router ospf 1", "no ip ospf dead-interval 7"]


# ── is_configured ─────────────────────────────────────────────────────────────

def test_is_configured_false_when_no_env(monkeypatch):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_CHANNEL_ID", raising=False)
    assert is_configured() is False


def test_is_configured_false_when_only_token(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token123")
    monkeypatch.delenv("DISCORD_CHANNEL_ID", raising=False)
    assert is_configured() is False


def test_is_configured_true_when_both_set(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token123")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "123456789")
    assert is_configured() is True


# ── _table_to_bullets ─────────────────────────────────────────────────────────

def test_table_to_bullets_converts_standard_table():
    """_table_to_bullets must convert pipe-delimited rows to bullet points."""
    table = (
        "| Finding | Detail | Status |\n"
        "|---------|--------|--------|\n"
        "| OSPF    | 0 nbrs | ✗      |\n"
        "| Iface   | Up/Up  | ✓      |\n"
    )
    result = _table_to_bullets(table)
    assert "OSPF" in result
    assert "0 nbrs" in result
    assert "✗" in result
    assert "|" not in result  # pipes must be gone
    assert "---" not in result  # separator must be gone


def test_table_to_bullets_skips_header_row():
    """Header row (Finding / Detail / Status) must not appear in output."""
    table = "| Finding | Detail | Status |\n|---|---|---|\n| OSPF | 0 nbrs | ✗ |\n"
    result = _table_to_bullets(table)
    # "finding" header cell should not appear as a bullet
    assert "**Finding**" not in result
    assert "**OSPF**" in result


def test_table_to_bullets_passthrough_non_table():
    """Non-table text must be returned unchanged."""
    plain = "Just a plain description with no pipes."
    assert _table_to_bullets(plain) == plain


# ── post_approval_request ─────────────────────────────────────────────────────

def test_post_approval_request_posts_embed_and_reactions(monkeypatch):
    """post_approval_request must POST message, PUT ✅, PUT ❌, return message_id."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    post_resp = _make_mock_response(200, json_data={"id": "msg999"})
    react_resp = _make_mock_response(204)

    call_log = []

    class MockSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        def post(self, url, **kwargs):
            call_log.append(("POST", url))
            return post_resp
        def put(self, url, **kwargs):
            call_log.append(("PUT", url))
            return react_resp

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        result = run(
            post_approval_request(
                summary="OSPF dead timer",
                findings=SAMPLE_FINDINGS,
                commands=SAMPLE_COMMANDS,
                devices=["C1C"],
                risk_level="low",
                issue_key="SUP-42",
            )
        )

    assert result == "msg999"
    methods = [m for m, _ in call_log]
    assert methods.count("POST") == 1, "must POST the message exactly once"
    assert methods.count("PUT") == 2, "must PUT ✅ and ❌ reactions"


def test_post_approval_request_raises_on_discord_error(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    fail_resp = _make_mock_response(403, text_data="Forbidden")

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def post(self, url, **kwargs): return fail_resp

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        with pytest.raises(RuntimeError, match="403"):
            run(
                post_approval_request(
                    summary="test", findings="f", commands=["cmd"],
                    devices=["C1C"], risk_level="low", issue_key=None,
                )
            )


# ── poll_for_reaction ─────────────────────────────────────────────────────────

def test_poll_returns_approved_on_human_checkmark(monkeypatch):
    """poll_for_reaction must return 'approved' when a non-bot user reacts ✅."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    human_user = {"id": "human1", "username": "ops_engineer"}
    bot_user = {"id": "bot1", "username": "aiNOC", "bot": True}

    approve_resp = _make_mock_response(200, json_data=[bot_user, human_user])
    reject_resp = _make_mock_response(200, json_data=[bot_user])  # only bot on ❌

    call_count = [0]

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def get(self, url, **kwargs):
            call_count[0] += 1
            if "%E2%9C%85" in url or "%e2%9c%85" in url or "✅" in url:
                return approve_resp
            return reject_resp
        def post(self, url, **kwargs):
            return _make_mock_response(200, json_data={"id": "ack1"})

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        with patch("core.discord_approval.asyncio.sleep", new=AsyncMock()):
            result = run(poll_for_reaction("msg999", timeout_minutes=1))

    assert result["decision"] == "approved"
    assert result["approved_by"] == "ops_engineer"


def test_poll_returns_rejected_on_human_x(monkeypatch):
    """poll_for_reaction must return 'rejected' when a non-bot user reacts ❌."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    human_user = {"id": "human1", "username": "ops_lead"}
    bot_user = {"id": "bot1", "username": "aiNOC", "bot": True}

    approve_resp = _make_mock_response(200, json_data=[bot_user])  # only bot on ✅
    reject_resp = _make_mock_response(200, json_data=[bot_user, human_user])

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def get(self, url, **kwargs):
            if "%E2%9C%85" in url or "✅" in url:
                return approve_resp
            return reject_resp
        def post(self, url, **kwargs):
            return _make_mock_response(200, json_data={"id": "ack2"})

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        with patch("core.discord_approval.asyncio.sleep", new=AsyncMock()):
            result = run(poll_for_reaction("msg999", timeout_minutes=1))

    assert result["decision"] == "rejected"
    assert result["rejected_by"] == "ops_lead"


def test_poll_ignores_bot_reactions(monkeypatch):
    """poll_for_reaction must NOT count the bot's own initial reactions as approval."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    bot_only = [{"id": "bot1", "username": "aiNOC", "bot": True}]

    call_count = [0]

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def get(self, url, **kwargs):
            call_count[0] += 1
            return _make_mock_response(200, json_data=bot_only)

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        # Patch sleep and the deadline to expire quickly (timeout=0 → immediate expiry)
        with patch("core.discord_approval.asyncio.sleep", new=AsyncMock()):
            with patch(
                "core.discord_approval.datetime",
                wraps=__import__("datetime").datetime,
            ):
                # Use timeout_minutes=0 so deadline is in the past immediately
                result = run(poll_for_reaction("msg999", timeout_minutes=0))

    assert result["decision"] == "expired"


def test_poll_returns_expired_on_timeout(monkeypatch):
    """poll_for_reaction must return 'expired' after timeout with no human reactions."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    empty_reactions = _make_mock_response(200, json_data=[])

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def get(self, url, **kwargs):
            return empty_reactions

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        with patch("core.discord_approval.asyncio.sleep", new=AsyncMock()):
            result = run(poll_for_reaction("msg999", timeout_minutes=0))

    assert result["decision"] == "expired"


def test_poll_removes_reactions_on_expiry(monkeypatch):
    """poll_for_reaction must DELETE both bot reactions from the message on expiry."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    empty_reactions = _make_mock_response(200, json_data=[])
    delete_resp = _make_mock_response(204)

    delete_calls = []

    class PollSession:
        """Used during the poll loop (GET reactions only)."""
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def get(self, url, **kwargs):
            return empty_reactions

    class CleanupSession:
        """Used for the cleanup DELETE calls after expiry."""
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def delete(self, url, **kwargs):
            delete_calls.append(url)
            return delete_resp

    sessions = [PollSession(), CleanupSession()]
    session_iter = iter(sessions)

    def session_factory():
        return next(session_iter)

    with patch("core.discord_approval.aiohttp.ClientSession", side_effect=session_factory):
        with patch("core.discord_approval.asyncio.sleep", new=AsyncMock()):
            result = run(poll_for_reaction("msgClean", timeout_minutes=0))

    assert result["decision"] == "expired"
    assert len(delete_calls) == 2, "must DELETE both ✅ and ❌ reactions"
    # Both DELETE URLs must reference the message
    assert all("msgClean" in url for url in delete_calls)


# ── post_outcome ──────────────────────────────────────────────────────────────

def test_post_outcome_sends_reply(monkeypatch):
    """post_outcome must POST a message referencing the original message_id."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    post_resp = _make_mock_response(200, json_data={"id": "reply1"})
    posted_payloads = []

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def post(self, url, **kwargs):
            posted_payloads.append(kwargs.get("json", {}))
            return post_resp

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        run(post_outcome("original123", "approved", decided_by="ops_engineer", verified=True, issue_key="NOC-42"))

    assert len(posted_payloads) == 1
    payload = posted_payloads[0]
    assert payload.get("message_reference", {}).get("message_id") == "original123"
    # Outcome embed must mention approval
    fields = payload.get("embeds", [{}])[0].get("fields", [])
    outcome_text = " ".join(f.get("value", "") for f in fields)
    assert "approved" in outcome_text.lower()
    assert "NOC-42" in outcome_text


def test_post_outcome_rejection_mentions_jira(monkeypatch):
    """post_outcome rejection embed must mention Jira remains open."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    post_resp = _make_mock_response(200, json_data={"id": "reply2"})
    posted_payloads = []

    class MockSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        def post(self, url, **kwargs):
            posted_payloads.append(kwargs.get("json", {}))
            return post_resp

    with patch("core.discord_approval.aiohttp.ClientSession", return_value=MockSession()):
        run(post_outcome("orig456", "rejected", decided_by="ops_lead"))

    fields = posted_payloads[0].get("embeds", [{}])[0].get("fields", [])
    outcome_text = " ".join(f.get("value", "") for f in fields)
    assert "jira" in outcome_text.lower()
    assert "remains open" in outcome_text.lower()


# ── request_approval tool ─────────────────────────────────────────────────────

def test_request_approval_skips_when_discord_not_configured(monkeypatch, tmp_path):
    """request_approval must return 'skipped' when Discord env vars are absent."""
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_CHANNEL_ID", raising=False)

    params = ApprovalInput(
        summary="Test",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
    )

    state_file = tmp_path / "pending_approval.json"
    with patch("tools.approval._DATA_FILE", state_file):
        result = run(request_approval(params))

    assert result["decision"] == "skipped"
    assert "Discord not configured" in result.get("reason", "")
    # Code-level gate must NOT be left in APPROVED state — push_config must be blocked
    written = json.loads(state_file.read_text())
    assert written["status"] == "SKIPPED", "No-Discord path must write SKIPPED, not APPROVED"


def test_request_approval_returns_approved_decision(monkeypatch, tmp_path):
    """request_approval must return approved decision from poll_for_reaction."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalInput(
        issue_key="SUP-42",
        summary="Fix OSPF timer",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
    )

    with patch("tools.approval._DATA_FILE", tmp_path / "pending_approval.json"):
        with patch(
            "tools.approval.post_approval_request",
            new=AsyncMock(return_value="msg42"),
        ):
            with patch(
                "tools.approval.poll_for_reaction",
                new=AsyncMock(return_value={"decision": "approved", "approved_by": "operator"}),
            ):
                result = run(request_approval(params))

    assert result["decision"] == "approved"
    assert result["approved_by"] == "operator"
    assert result["message_id"] == "msg42"

    # State file must have been written
    state_file = tmp_path / "pending_approval.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state["status"] == "APPROVED"
    assert state["issue_key"] == "SUP-42"


def test_request_approval_does_not_auto_post_on_approved(monkeypatch, tmp_path):
    """request_approval must NOT call post_outcome for approved — agent does it via post_approval_outcome."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalInput(
        summary="Test",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
    )

    mock_post_outcome = AsyncMock()
    with patch("tools.approval._DATA_FILE", tmp_path / "pending_approval.json"):
        with patch("tools.approval.post_approval_request", new=AsyncMock(return_value="msgX")):
            with patch(
                "tools.approval.poll_for_reaction",
                new=AsyncMock(return_value={"decision": "approved", "approved_by": "op"}),
            ):
                with patch("tools.approval.post_outcome", mock_post_outcome):
                    run(request_approval(params))

    mock_post_outcome.assert_not_called()


def test_request_approval_expired_does_not_auto_post_outcome(monkeypatch, tmp_path):
    """request_approval must NOT auto-post expiry outcome — agent handles it via post_approval_outcome."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalInput(
        summary="Test",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
    )

    mock_post_outcome = AsyncMock()
    with patch("tools.approval._DATA_FILE", tmp_path / "pending_approval.json"):
        with patch("tools.approval.post_approval_request", new=AsyncMock(return_value="msgExpiry")):
            with patch(
                "tools.approval.poll_for_reaction",
                new=AsyncMock(return_value={"decision": "expired"}),
            ):
                with patch("tools.approval.post_outcome", mock_post_outcome):
                    result = run(request_approval(params))

    assert result["decision"] == "expired"
    # Auto-post removed — the agent calls post_approval_outcome after receiving "expired"
    mock_post_outcome.assert_not_called()


def test_request_approval_honours_env_timeout(monkeypatch, tmp_path):
    """request_approval must use APPROVAL_TIMEOUT_MINUTES env var when timeout_minutes==10 (default)."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")
    monkeypatch.setenv("APPROVAL_TIMEOUT_MINUTES", "45")

    params = ApprovalInput(
        summary="Test",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
        # timeout_minutes not set → defaults to 10 → should be overridden to 45
    )

    captured = {}

    async def mock_post_request(**kwargs):
        captured["timeout"] = kwargs.get("timeout_minutes")
        return "msg_env"

    with patch("tools.approval._DATA_FILE", tmp_path / "pending_approval.json"):
        with patch("tools.approval.post_approval_request", new=AsyncMock(side_effect=mock_post_request)):
            with patch(
                "tools.approval.poll_for_reaction",
                new=AsyncMock(return_value={"decision": "expired"}),
            ):
                run(request_approval(params))

    assert captured.get("timeout") == 45


def test_request_approval_returns_error_on_discord_exception(monkeypatch, tmp_path):
    """request_approval must catch Discord errors and return error decision."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalInput(
        summary="Test",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
    )

    with patch("tools.approval._DATA_FILE", tmp_path / "pending_approval.json"):
        with patch(
            "tools.approval.post_approval_request",
            new=AsyncMock(side_effect=RuntimeError("Discord API error")),
        ):
            result = run(request_approval(params))

    assert result["decision"] == "error"
    assert "Discord API error" in result.get("reason", "")


# ── post_approval_outcome tool ────────────────────────────────────────────────

def test_post_approval_outcome_posts_when_configured(monkeypatch, tmp_path):
    """post_approval_outcome must call post_outcome and return status=posted."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalOutcomeInput(
        message_id="msg99",
        decision="approved",
        decided_by="ops_eng",
        verified=True,
        verification_detail="OSPF neighbor FULL",
    )

    mock_post_outcome = AsyncMock()
    with patch("tools.approval.post_outcome", mock_post_outcome), \
         patch("tools.approval._DATA_FILE", tmp_path / "no_state.json"):
        result = run(post_approval_outcome(params))

    assert result["status"] == "posted"
    mock_post_outcome.assert_awaited_once_with(
        original_message_id="msg99",
        decision="approved",
        decided_by="ops_eng",
        verified=True,
        verification_detail="OSPF neighbor FULL",
        issue_key=None,
    )


def test_post_approval_outcome_posts_with_verified_false(monkeypatch, tmp_path):
    """post_approval_outcome must pass verified=False when fix verification failed."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalOutcomeInput(
        message_id="msg88",
        decision="approved",
        decided_by="ops_eng",
        verified=False,
        verification_detail="OSPF neighbor still absent",
    )

    mock_post_outcome = AsyncMock()
    with patch("tools.approval.post_outcome", mock_post_outcome), \
         patch("tools.approval._DATA_FILE", tmp_path / "no_state.json"):
        result = run(post_approval_outcome(params))

    assert result["status"] == "posted"
    call_kwargs = mock_post_outcome.call_args.kwargs
    assert call_kwargs["verified"] is False


def test_post_approval_outcome_skips_when_not_configured(monkeypatch):
    """post_approval_outcome must return skipped when Discord not configured."""
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_CHANNEL_ID", raising=False)

    params = ApprovalOutcomeInput(
        message_id="msg77",
        decision="rejected",
        decided_by="ops_eng",
    )

    result = run(post_approval_outcome(params))
    assert result["status"] == "skipped"


def test_post_approval_outcome_handles_discord_error(monkeypatch):
    """post_approval_outcome must return error status on Discord API failure."""
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "chan123")

    params = ApprovalOutcomeInput(
        message_id="msg66",
        decision="approved",
        decided_by="op",
        verified=True,
    )

    with patch("tools.approval.post_outcome", new=AsyncMock(side_effect=RuntimeError("503"))):
        result = run(post_approval_outcome(params))

    assert result["status"] == "error"
    assert "503" in result.get("reason", "")


# ── ApprovalInput model ───────────────────────────────────────────────────────

def test_approval_input_valid():
    p = ApprovalInput(
        issue_key="SUP-42",
        summary="Fix OSPF",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C", "C2C"],
        risk_level="medium",
        timeout_minutes=45,
    )
    assert p.issue_key == "SUP-42"
    assert p.risk_level == "medium"
    assert p.timeout_minutes == 45


def test_approval_input_issue_key_optional():
    p = ApprovalInput(
        summary="Fix OSPF",
        findings=SAMPLE_FINDINGS,
        commands=SAMPLE_COMMANDS,
        devices=["C1C"],
        risk_level="low",
    )
    assert p.issue_key is None


def test_approval_input_invalid_issue_key():
    with pytest.raises(Exception):
        ApprovalInput(
            issue_key="not-valid",
            summary="Test",
            findings="f",
            commands=["cmd"],
            devices=["C1C"],
            risk_level="low",
        )


def test_approval_input_invalid_risk_level():
    with pytest.raises(Exception):
        ApprovalInput(
            summary="Test",
            findings="f",
            commands=["cmd"],
            devices=["C1C"],
            risk_level="critical",  # not in Literal["low", "medium", "high"]
        )


def test_approval_input_default_timeout():
    p = ApprovalInput(
        summary="Test",
        findings="f",
        commands=["cmd"],
        devices=["C1C"],
        risk_level="high",
    )
    assert p.timeout_minutes == 10
