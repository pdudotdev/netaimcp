"""
Discord-based remote approval for On-Call fix proposals.

The agent calls request_approval() (via MCP tools/approval.py) which:
  1. Posts a rich embed to the configured Discord channel with findings + proposed fix
  2. Adds ✅ and ❌ reactions to the message so the operator can respond
  3. Polls Discord's reaction API until a human reacts or the timeout expires
  4. Posts a reply to the original message showing the final outcome

No web server, no inbound connections — all outbound Discord REST API calls.
"""
import asyncio
import logging
import os
import urllib.parse
from datetime import datetime, timezone, timedelta

import aiohttp

log = logging.getLogger("ainoc.discord")

DISCORD_API = "https://discord.com/api/v10"
APPROVE_EMOJI = "✅"
REJECT_EMOJI = "❌"
_APPROVE_ENC = urllib.parse.quote(APPROVE_EMOJI, safe="")
_REJECT_ENC = urllib.parse.quote(REJECT_EMOJI, safe="")

RISK_COLORS = {"low": 0x00B300, "medium": 0xFFA500, "high": 0xFF0000}
RISK_LABELS = {"low": "🟢 LOW", "medium": "🟡 MEDIUM", "high": "🔴 HIGH"}
OUTCOME_COLORS = {
    "approved": 0x00B300,
    "approved_failed": 0xFFA500,
    "rejected": 0xFF0000,
    "expired": 0x808080,
}


def is_configured() -> bool:
    """Return True if both DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID are set."""
    return bool(os.getenv("DISCORD_BOT_TOKEN") and os.getenv("DISCORD_CHANNEL_ID"))


def _auth_headers() -> dict:
    return {"Authorization": f"Bot {os.getenv('DISCORD_BOT_TOKEN')}"}


def _json_headers() -> dict:
    return {**_auth_headers(), "Content-Type": "application/json"}


def _channel() -> str:
    return os.getenv("DISCORD_CHANNEL_ID", "")


def _truncate(text: str, limit: int = 1000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n*… (truncated)*"


def _table_to_bullets(table_text: str) -> str:
    """Convert a markdown table to Discord-friendly bullet points.

    Markdown tables don't render in Discord — pipes appear as raw text.
    This converts each data row into: '<status>  **<finding>** — <detail>'
    Header and separator rows are skipped.
    """
    lines = []
    for row in table_text.strip().splitlines():
        row = row.strip()
        if not row:
            continue
        # Skip separator rows (|---|---|---|)
        if all(c in "-| " for c in row):
            continue
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) >= 3:
            finding, detail, status = cells[0], cells[1], cells[2]
            # Skip the header row (Finding / Detail / Status)
            if finding.lower() in ("finding", "check", "item"):
                continue
            lines.append(f"{status}  **{finding}** — {detail}")
        elif len(cells) == 2:
            if cells[0].lower() in ("finding", "check", "item"):
                continue
            lines.append(f"• **{cells[0]}** — {cells[1]}")
    return "\n".join(lines) if lines else table_text


async def post_approval_request(
    summary: str,
    findings: str,
    commands: list[str],
    devices: list[str],
    risk_level: str,
    issue_key: str | None,
    timeout_minutes: int = 10,
) -> str:
    """Post rich embed to Discord channel. Add ✅ and ❌ reactions. Return message_id."""
    color = RISK_COLORS.get(risk_level.lower(), 0x808080)
    risk_label = RISK_LABELS.get(risk_level.lower(), risk_level.upper())
    title = f"🔧 Fix Approval Required — {issue_key or 'No Ticket'}"
    commands_block = "```\n" + "\n".join(commands) + "\n```"

    embed = {
        "title": title,
        "color": color,
        "fields": [
            {"name": "📋 Summary", "value": _truncate(summary, 256), "inline": False},
            {"name": "📊 Findings", "value": _truncate(_table_to_bullets(findings), 1000), "inline": False},
            {
                "name": "🔧 Proposed Commands",
                "value": _truncate(commands_block, 1000),
                "inline": False,
            },
            {"name": "📡 Target Devices", "value": ", ".join(devices), "inline": True},
            {"name": "⚠️ Risk Level", "value": risk_label, "inline": True},
        ],
        "footer": {
            "text": (
                f"React ✅ to approve  ·  ❌ to reject  "
                f"·  Expires in {timeout_minutes} min"
            )
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with aiohttp.ClientSession() as session:
        # Post the message
        async with session.post(
            f"{DISCORD_API}/channels/{_channel()}/messages",
            headers=_json_headers(),
            json={"embeds": [embed]},
        ) as resp:
            if resp.status not in (200, 201):
                body = await resp.text()
                raise RuntimeError(f"Discord post failed ({resp.status}): {body[:200]}")
            data = await resp.json()
            message_id: str = data["id"]

        # Add ✅ reaction (bot's own — gives operator a tap target)
        async with session.put(
            f"{DISCORD_API}/channels/{_channel()}/messages/{message_id}"
            f"/reactions/{_APPROVE_ENC}/@me",
            headers=_auth_headers(),
        ):
            pass

        await asyncio.sleep(0.3)  # Brief pause to stay within Discord rate limits

        # Add ❌ reaction
        async with session.put(
            f"{DISCORD_API}/channels/{_channel()}/messages/{message_id}"
            f"/reactions/{_REJECT_ENC}/@me",
            headers=_auth_headers(),
        ):
            pass

    log.info("Discord approval request posted: message_id=%s", message_id)
    return message_id


async def poll_for_reaction(
    message_id: str,
    timeout_minutes: int = 10,
) -> dict:
    """Poll Discord for a human user's reaction. Returns decision dict."""
    deadline = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
    poll_interval = 5  # seconds

    log.info(
        "Polling Discord for approval on message %s (timeout=%dm)",
        message_id,
        timeout_minutes,
    )

    async with aiohttp.ClientSession() as session:
        while datetime.now(timezone.utc) < deadline:
            await asyncio.sleep(poll_interval)

            # Check ✅ reactions — filter out bot accounts
            async with session.get(
                f"{DISCORD_API}/channels/{_channel()}/messages/{message_id}"
                f"/reactions/{_APPROVE_ENC}",
                headers=_auth_headers(),
            ) as resp:
                if resp.status == 200:
                    users = await resp.json()
                    human = next((u for u in users if not u.get("bot")), None)
                    if human:
                        username = human.get("username", "operator")
                        log.info("Discord approval received from %s", username)
                        try:
                            async with session.post(
                                f"{DISCORD_API}/channels/{_channel()}/messages",
                                headers=_json_headers(),
                                json={
                                    "content": f"✅ Approval received from @{username}. aiNOC is proceeding with the fix.",
                                    "message_reference": {"message_id": message_id},
                                },
                            ):
                                pass
                        except Exception:
                            pass
                        return {"decision": "approved", "approved_by": username}

            # Check ❌ reactions — filter out bot accounts
            async with session.get(
                f"{DISCORD_API}/channels/{_channel()}/messages/{message_id}"
                f"/reactions/{_REJECT_ENC}",
                headers=_auth_headers(),
            ) as resp:
                if resp.status == 200:
                    users = await resp.json()
                    human = next((u for u in users if not u.get("bot")), None)
                    if human:
                        username = human.get("username", "operator")
                        log.info("Discord rejection received from %s", username)
                        try:
                            async with session.post(
                                f"{DISCORD_API}/channels/{_channel()}/messages",
                                headers=_json_headers(),
                                json={
                                    "content": f"❌ Rejection received from @{username}. aiNOC will not apply the fix.",
                                    "message_reference": {"message_id": message_id},
                                },
                            ):
                                pass
                        except Exception:
                            pass
                        return {"decision": "rejected", "rejected_by": username}

    # Remove the bot's own reactions so operator can't click stale buttons after expiry
    try:
        async with aiohttp.ClientSession() as cleanup_session:
            for emoji_enc in (_APPROVE_ENC, _REJECT_ENC):
                async with cleanup_session.delete(
                    f"{DISCORD_API}/channels/{_channel()}/messages/{message_id}"
                    f"/reactions/{emoji_enc}/@me",
                    headers=_auth_headers(),
                ):
                    pass
                await asyncio.sleep(0.3)
    except Exception as e:
        log.warning("Failed to remove reactions on expiry: %s", e)

    log.info("Discord approval timed out for message %s", message_id)
    return {"decision": "expired"}


async def post_deferred_list(
    events: list,
    issue_key: str | None = None,
) -> None:
    """Post an informational embed listing deferred SLA failures. No reactions, no polling."""
    lines = []
    for i, e in enumerate(events, 1):
        name = e.get("device_name", e.get("device", "?"))
        ip = e.get("device", "?")
        msg = e.get("msg", "")[:150]
        ts = e.get("ts", "?")
        lines.append(f"{i}. **{name}** ({ip}): {msg} *(at {ts})*")

    body = "\n".join(lines)
    ticket_note = f"Jira ticket: **{issue_key}**" if issue_key else "No Jira ticket"
    footer = f"{ticket_note} · Manual follow-up may be required for any still-active failures."

    embed = {
        "title": "⚠️ Deferred SLA Failures",
        "description": _truncate(body, 2000),
        "color": 0xFFA500,  # orange
        "footer": {"text": footer},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API}/channels/{_channel()}/messages",
            headers=_json_headers(),
            json={"embeds": [embed]},
        ) as resp:
            if resp.status not in (200, 201):
                body_text = await resp.text()
                raise RuntimeError(f"Discord deferred list post failed ({resp.status}): {body_text[:200]}")

    log.info("Deferred SLA failure list posted to Discord (%d event(s))", len(events))


async def post_investigation_started(
    device_name: str,
    device_ip: str,
    event_msg: str,
    event_ts: str,
    issue_key: str | None = None,
    session_name: str | None = None,
) -> None:
    """Post an informational embed when an on-call investigation begins. No reactions, no polling."""
    if not is_configured():
        return

    ticket_line = f"**Jira ticket:** {issue_key}" if issue_key else "No Jira ticket"

    embed = {
        "title": f"🚨 NEW ISSUE: DEVICE {device_name} — Investigation Started",
        "description": (
            f"**Device:** {device_name} ({device_ip})\n"
            f"**Event:** {_truncate(event_msg, 300)}\n"
            f"**Event time:** {event_ts}\n"
            f"{ticket_line}\n\n"
            f"⏳ *Currently investigating — please wait for summary and proposed fix.*"
        ),
        "color": 0x3498DB,  # blue — informational
        "footer": {"text": f"Agent session: {session_name}" if session_name else "Agent session started"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                f"{DISCORD_API}/channels/{_channel()}/messages",
                headers=_json_headers(),
                json={"embeds": [embed]},
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    log.warning("Discord investigation-started post failed (%s): %s", resp.status, body[:200])
                    return
        log.info("Investigation-started notification posted to Discord")
    except Exception as exc:
        log.warning("Failed to post investigation-started to Discord: %s", exc)


async def post_session_complete(
    device_name: str,
    device_ip: str,
    issue_key: str | None = None,
    session_name: str | None = None,
    session_cost: float | None = None,
    session_duration: str | None = None,
    approval_used: bool = False,
) -> None:
    """Post a green embed when the agent session exits normally.

    If approval_used is False: describes the outcome as transient/self-recovered.
    If approval_used is True: posts session metrics only; the approval outcome embed already
    covers the fix result.
    """
    if not is_configured():
        return

    ticket_line = f"Jira ticket: **{issue_key}**" if issue_key else "No Jira ticket"

    fields: list[dict] = [
        {"name": "📡 Device", "value": f"{device_name} ({device_ip})", "inline": True},
    ]
    if session_duration is not None:
        fields.append({"name": "⏱ Duration", "value": session_duration, "inline": True})
    if session_cost is not None:
        fields.append({"name": "💰 Cost", "value": f"${session_cost:.4f}", "inline": True})

    if approval_used:
        description = f"Session ended — see approval outcome above for details.\n\n{ticket_line}"
    else:
        description = (
            "Issue appears to be transient — recovered without intervention. No fix needed.\n\n"
            f"{ticket_line}"
        )

    embed = {
        "title": f"✅ Session Complete — {device_name}",
        "description": description,
        "color": 0x00B300,  # green
        "fields": fields,
        "footer": {"text": f"Session: {session_name}" if session_name else "Session ended"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                f"{DISCORD_API}/channels/{_channel()}/messages",
                headers=_json_headers(),
                json={"embeds": [embed]},
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    log.warning("Discord session-complete post failed (%s): %s", resp.status, body[:200])
                    return
        log.info("Session complete (transient) notification posted to Discord")
    except Exception as exc:
        log.warning("Failed to post session complete to Discord: %s", exc)


async def post_session_error(
    device_name: str,
    device_ip: str,
    issue_key: str | None = None,
    session_name: str | None = None,
    error_type: str = "unknown",  # "timeout" | "crash" | "watcher_error" | "unknown"
    exit_code: int | None = None,
    log_tail: str | None = None,
    session_cost: float | None = None,
    session_duration: str | None = None,
) -> None:
    """Post a red error embed when the agent session ends abnormally (timeout, crash, watcher error)."""
    if not is_configured():
        return

    error_labels = {
        "timeout": "⏱ Session Timeout",
        "crash": "💥 Agent Crash",
        "watcher_error": "⚠️ Watcher Error",
        "unknown": "❓ Unknown Error",
    }
    error_label = error_labels.get(error_type, error_type.upper())
    ticket_line = f"Jira ticket: **{issue_key}**" if issue_key else "No Jira ticket"

    fields: list[dict] = [
        {"name": "📡 Device", "value": f"{device_name} ({device_ip})", "inline": True},
        {"name": "🔴 Error Type", "value": error_label, "inline": True},
    ]
    if exit_code is not None:
        fields.append({"name": "Exit Code", "value": str(exit_code), "inline": True})
    if session_duration is not None:
        fields.append({"name": "⏱ Duration", "value": session_duration, "inline": True})
    if session_cost is not None:
        fields.append({"name": "💰 Cost", "value": f"${session_cost:.4f}", "inline": True})
    if log_tail:
        fields.append({
            "name": "📋 Session Log (last lines)",
            "value": _truncate(f"```\n{log_tail}\n```", 1000),
            "inline": False,
        })

    embed = {
        "title": f"⚠️ Agent Session Error — {device_name}",
        "description": (
            f"{ticket_line}\n\n"
            "The agent session ended abnormally. Manual investigation may be required."
        ),
        "color": 0xFF0000,  # red
        "fields": fields,
        "footer": {"text": f"Session: {session_name}" if session_name else "Session ended"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                f"{DISCORD_API}/channels/{_channel()}/messages",
                headers=_json_headers(),
                json={"embeds": [embed]},
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    log.warning("Discord session-error post failed (%s): %s", resp.status, body[:200])
                    return
        log.info("Session error notification posted to Discord (error_type=%s)", error_type)
    except Exception as exc:
        log.warning("Failed to post session error to Discord: %s", exc)


async def post_progress_update(message: str) -> None:
    """Post a plain text progress message to the Discord channel."""
    if not is_configured():
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DISCORD_API}/channels/{_channel()}/messages",
                headers=_json_headers(),
                json={"content": message},
            ) as resp:
                if resp.status not in (200, 201):
                    log.warning("Progress update post failed (%s)", resp.status)
    except Exception as exc:
        log.warning("Failed to post progress update: %s", exc)


async def post_outcome(
    original_message_id: str,
    decision: str,
    decided_by: str | None = None,
    verified: bool | None = None,
    verification_detail: str | None = None,
    issue_key: str | None = None,
) -> None:
    """Post a reply to the original approval message showing the final outcome."""
    if decision == "approved":
        if verified is True:
            color = OUTCOME_COLORS["approved"]
            status = f"✅ Fix approved by @{decided_by or 'operator'} and **verified**"
        elif verified is False:
            color = OUTCOME_COLORS["approved_failed"]
            status = f"⚠️ Fix approved by @{decided_by or 'operator'} — verification **failed**"
        else:
            color = OUTCOME_COLORS["approved"]
            status = f"✅ Fix approved by @{decided_by or 'operator'}"
    elif decision == "rejected":
        color = OUTCOME_COLORS["rejected"]
        status = f"❌ Fix **rejected** by @{decided_by or 'operator'} — issue remains open in Jira for further investigation"
    else:
        color = OUTCOME_COLORS["expired"]
        status = "⏱ Approval **expired** — no response received"

    fields = [{"name": "Outcome", "value": status, "inline": False}]
    if verification_detail:
        fields.append(
            {
                "name": "Verification",
                "value": _truncate(verification_detail, 512),
                "inline": False,
            }
        )
    if issue_key:
        fields.append({"name": "Jira", "value": f"Ticket **{issue_key}** updated", "inline": False})

    outcome_embed = {
        "color": color,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API}/channels/{_channel()}/messages",
            headers=_json_headers(),
            json={
                "embeds": [outcome_embed],
                "message_reference": {"message_id": original_message_id},
            },
        ) as resp:
            if resp.status not in (200, 201):
                log.warning(
                    "Failed to post Discord outcome reply (status=%d)", resp.status
                )
