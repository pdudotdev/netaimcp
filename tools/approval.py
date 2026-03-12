"""
MCP tools: request_approval, post_approval_outcome

request_approval:
  Sends an approval request to Discord and waits for the operator's emoji reaction.
  Returns the decision so the agent can act on it (push_config on approval, log on rejection).

  If Discord is not configured (DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID missing),
  returns {"decision": "skipped"} so the agent falls back to CLI-only approval.

post_approval_outcome:
  Posts the final outcome (approved+verified, rejected, expired) as a reply to the
  original approval message. Called by the agent AFTER fix + verification — not inside
  request_approval — so that the verification result can be included.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core.discord_approval import (
    is_configured,
    post_approval_request,
    poll_for_reaction,
    post_outcome,
)
from input_models.models import ApprovalInput, ApprovalOutcomeInput

log = logging.getLogger("ainoc.approval")

_DATA_FILE = Path(__file__).parent.parent / "data" / "pending_approval.json"


def _write_state(record: dict) -> None:
    _DATA_FILE.parent.mkdir(exist_ok=True)
    _DATA_FILE.write_text(json.dumps(record, indent=2))


async def request_approval(params: ApprovalInput) -> dict:
    """
    Request operator approval for a proposed configuration change via Discord.

    Posts a rich embed to the configured Discord channel showing findings,
    proposed commands, target devices, and risk level. The bot adds ✅ and ❌
    reactions — the operator taps one to approve or reject. The tool polls
    Discord's API until a human reacts or the timeout expires.

    The timeout defaults to APPROVAL_TIMEOUT_MINUTES from .env (or 10 if unset).
    Pass timeout_minutes explicitly to override.

    If Discord is not configured, returns {"decision": "skipped"} and the
    agent must log to Jira that no approval channel is configured and proceed
    to Session Closure without pushing config.

    After this tool returns, the agent must call post_approval_outcome with
    the message_id and final outcome (including verification result for
    approved decisions).

    Args:
        issue_key: Jira issue key (optional, for context in the Discord embed)
        summary: One-line description of the proposed fix
        findings: Full findings table in markdown format
        commands: List of CLI commands to apply
        devices: List of target device names
        risk_level: Risk level from assess_risk (low / medium / high)
        timeout_minutes: Minutes to wait before expiring (default: from APPROVAL_TIMEOUT_MINUTES env var, or 10)

    Returns:
        {
            "decision": "approved" | "rejected" | "expired" | "skipped" | "error",
            "approved_by": "<username>",   # on approved
            "rejected_by": "<username>",   # on rejected
            "reason": "<text>",            # on skipped or error
            "message_id": "<discord_id>",  # when Discord was used — pass to post_approval_outcome
        }
    """
    p = ApprovalInput(**params) if isinstance(params, dict) else params

    # Honour APPROVAL_TIMEOUT_MINUTES env var when the caller used the Pydantic default
    if p.timeout_minutes == 10:
        env_timeout = os.getenv("APPROVAL_TIMEOUT_MINUTES", "").strip()
        if env_timeout.isdigit():
            p = p.model_copy(update={"timeout_minutes": int(env_timeout)})

    if not is_configured():
        log.info("Discord not configured — writing SKIPPED approval record (push blocked)")
        now = datetime.now(timezone.utc)
        state = {
            "request_id": str(uuid.uuid4()),
            "issue_key": p.issue_key,
            "summary": p.summary,
            "devices": p.devices,
            "risk_level": p.risk_level,
            "status": "SKIPPED",
            "created_at": now.isoformat(),
        }
        _write_state(state)
        return {"decision": "skipped", "reason": "Discord not configured — no approval channel available"}

    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())

    # Persist request state (audit trail + resumability)
    state = {
        "request_id": request_id,
        "issue_key": p.issue_key,
        "summary": p.summary,
        "devices": p.devices,
        "risk_level": p.risk_level,
        "status": "PENDING",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=p.timeout_minutes)).isoformat(),
    }
    _write_state(state)

    try:
        message_id = await post_approval_request(
            summary=p.summary,
            findings=p.findings,
            commands=p.commands,
            devices=p.devices,
            risk_level=p.risk_level,
            issue_key=p.issue_key,
            timeout_minutes=p.timeout_minutes,
        )

        # Update state with Discord message reference
        state["message_id"] = message_id
        _write_state(state)

        # Poll for operator reaction
        result = await poll_for_reaction(message_id, p.timeout_minutes)
        result["message_id"] = message_id

        # Update persisted state with decision
        state["status"] = result["decision"].upper()
        state["decided_at"] = datetime.now(timezone.utc).isoformat()
        state["decided_by"] = result.get("approved_by") or result.get("rejected_by")
        _write_state(state)

        # Auto-post expiry outcome to Discord — expiry is terminal so there is no
        # verification step for the agent to wait for. Approved/rejected decisions
        # are posted later via post_approval_outcome (after fix + verification).
        if result["decision"] == "expired":
            try:
                await post_outcome(
                    original_message_id=message_id,
                    decision="expired",
                )
            except Exception as e:
                log.warning("Failed to post Discord expiry outcome: %s", e)

        return result

    except Exception as e:
        log.error("Discord approval error: %s", e)
        state["status"] = "ERROR"
        _write_state(state)
        return {"decision": "error", "reason": str(e)}


async def post_approval_outcome(params: ApprovalOutcomeInput) -> dict:
    """
    Post the final outcome of an approval as a reply to the original Discord message.

    Call this AFTER applying the fix and verifying it (for approved decisions),
    or immediately after receiving a rejected/expired decision from request_approval.

    This is intentionally separate from request_approval so that the verification
    result can be included in the Discord message.

    Args:
        message_id: Discord message ID returned by request_approval
        decision: "approved" | "rejected" | "expired"
        decided_by: Username who reacted (from approved_by / rejected_by fields)
        verified: True if post-fix verification passed, False if failed, None if not applicable
        verification_detail: Short summary of verification result (e.g. "OSPF neighbor FULL")

    Returns:
        {"status": "posted"} on success
        {"status": "skipped", "reason": "..."} if Discord not configured
        {"status": "error", "reason": "..."} on Discord API failure
    """
    p = ApprovalOutcomeInput(**params) if isinstance(params, dict) else params

    if not is_configured():
        return {"status": "skipped", "reason": "Discord not configured"}

    # Read issue_key from the approval state file so it can appear in the outcome embed
    issue_key: str | None = None
    try:
        state = json.loads(_DATA_FILE.read_text())
        issue_key = state.get("issue_key")
    except Exception:
        pass

    try:
        await post_outcome(
            original_message_id=p.message_id,
            decision=p.decision,
            decided_by=p.decided_by,
            verified=p.verified,
            verification_detail=p.verification_detail,
            issue_key=issue_key,
        )
        log.info(
            "Discord outcome posted: message_id=%s decision=%s verified=%s",
            p.message_id,
            p.decision,
            p.verified,
        )
        return {"status": "posted"}
    except Exception as e:
        log.warning("Failed to post Discord outcome: %s", e)
        return {"status": "error", "reason": str(e)}
