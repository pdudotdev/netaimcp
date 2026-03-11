"""Async Jira REST API v3 client.

Used by oncall/watcher.py (via asyncio.run) for ticket creation, and by
MCPServer.py (via MCP tools) for comments and resolution.

All functions check for required env vars — if absent, log a warning and
return gracefully so the workflow continues unchanged.
"""

import asyncio
import base64
import logging
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# Timeout for all Jira API calls — shorter than device timeout since Jira is cloud-hosted.
_JIRA_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)


def _config() -> dict:
    """Read Jira config from env vars at call time (not cached at import)."""
    return {
        "base_url":    os.getenv("JIRA_BASE_URL", "").rstrip("/"),
        "email":       os.getenv("JIRA_EMAIL", ""),
        "api_token":   os.getenv("JIRA_API_TOKEN", ""),
        "project_key": os.getenv("JIRA_PROJECT_KEY", ""),
        "issue_type":  os.getenv("JIRA_ISSUE_TYPE", "[System] Incident"),
    }


def _is_configured() -> bool:
    cfg = _config()
    return bool(cfg["base_url"] and cfg["email"] and cfg["api_token"] and cfg["project_key"])


def _headers() -> dict:
    cfg = _config()
    creds = base64.b64encode(f"{cfg['email']}:{cfg['api_token']}".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def _to_adf(text: str) -> dict:
    """Convert a plain-text string to minimal Atlassian Document Format (ADF)."""
    paragraphs = []
    for line in text.strip().split("\n"):
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line or " "}],
        })
    return {"version": 1, "type": "doc", "content": paragraphs}


async def create_issue(
    summary:     str,
    description: str,
    priority:    str = "High",
    labels:      list[str] | None = None,
) -> str | None:
    """Create a Jira incident. Returns the issue key (e.g. 'SUP-12') or None on failure.

    Tries JIRA_ISSUE_TYPE first; falls back to 'Task' if the configured type is rejected.
    """
    if not _is_configured():
        log.warning("Jira not configured — skipping issue creation")
        return None

    cfg = _config()
    if labels is None:
        labels = ["network-incident", "automated", "on-call"]

    body = {
        "fields": {
            "project":     {"key": cfg["project_key"]},
            "summary":     summary,
            "description": _to_adf(description),
            "issuetype":   {"name": cfg["issue_type"]},
            "priority":    {"name": priority},
            "labels":      labels,
        }
    }

    try:
        async with aiohttp.ClientSession(headers=_headers(), timeout=_JIRA_TIMEOUT) as session:
            url = f"{cfg['base_url']}/rest/api/3/issue"
            async with session.post(url, json=body) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    return data["key"]

                # Fall back to Task if the configured issue type is rejected
                if resp.status == 400:
                    body["fields"]["issuetype"] = {"name": "Task"}
                    async with session.post(url, json=body) as resp2:
                        if resp2.status == 201:
                            data = await resp2.json()
                            log.warning(
                                "Jira: issue type '%s' rejected, created as Task: %s",
                                cfg["issue_type"], data["key"],
                            )
                            return data["key"]
                        err = await resp2.text()
                        log.error(
                            "Jira create_issue failed (fallback): %s %s",
                            resp2.status, err[:200],
                        )
                        return None

                err = await resp.text()
                log.error("Jira create_issue failed: %s %s", resp.status, err[:200])
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        log.error("Jira create_issue failed (connection error): %s", exc)
        return None


async def add_comment(issue_key: str, comment_text: str) -> None:
    """Add a plain-text comment to a Jira issue."""
    if not _is_configured():
        log.warning("Jira not configured — skipping comment on %s", issue_key)
        return

    cfg = _config()
    body = {"body": _to_adf(comment_text)}
    try:
        async with aiohttp.ClientSession(headers=_headers(), timeout=_JIRA_TIMEOUT) as session:
            url = f"{cfg['base_url']}/rest/api/3/issue/{issue_key}/comment"
            async with session.post(url, json=body) as resp:
                if resp.status not in (200, 201):
                    err = await resp.text()
                    log.error(
                        "Jira add_comment failed on %s: %s %s",
                        issue_key, resp.status, err[:200],
                    )
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        log.error("Jira add_comment failed on %s (connection error): %s", issue_key, exc)


async def resolve_issue(
    issue_key:          str,
    resolution_comment: str,
    resolution:         str = "Done",
) -> None:
    """Transition a Jira issue to resolved state and add a resolution comment.

    Fetches available transitions and picks the first one whose name matches
    `resolution` (case-insensitive). Also checks for 'done', 'resolve', 'resolved',
    'close', 'closed' as fallback names.
    Falls back to comment-only if no matching transition is found.
    """
    if not _is_configured():
        log.warning("Jira not configured — skipping resolve of %s", issue_key)
        return

    cfg = _config()
    try:
        async with aiohttp.ClientSession(headers=_headers(), timeout=_JIRA_TIMEOUT) as session:
            url = f"{cfg['base_url']}/rest/api/3/issue/{issue_key}/transitions"
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.warning(
                        "Jira: could not fetch transitions for %s — comment only",
                        issue_key,
                    )
                    await add_comment(issue_key, resolution_comment)
                    return
                data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        log.error("Jira resolve_issue failed on %s (connection error): %s", issue_key, exc)
        return

    transitions = data.get("transitions", [])
    target_names = {resolution.lower(), "done", "resolve", "resolved", "close", "closed"}
    transition_id = None
    for t in transitions:
        if t["name"].lower() in target_names:
            transition_id = t["id"]
            break

    if transition_id:
        resolution_name = "Won't Fix" if resolution.lower() in {"won't fix", "wont fix"} else "Done"
        try:
            async with aiohttp.ClientSession(headers=_headers(), timeout=_JIRA_TIMEOUT) as session:
                payload = {
                    "transition": {"id": transition_id},
                    "fields": {"resolution": {"name": resolution_name}},
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status not in (200, 204):
                        err = await resp.text()
                        log.warning(
                            "Jira transition failed for %s: %s %s",
                            issue_key, resp.status, err[:200],
                        )
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            log.error("Jira transition failed on %s (connection error): %s", issue_key, exc)
    else:
        log.warning(
            "Jira: no matching transition for '%s' on %s — comment only",
            resolution, issue_key,
        )

    # Always add the resolution comment regardless of transition outcome
    await add_comment(issue_key, resolution_comment)
