"""Jira case management tool handlers — thin wrappers around jira_client functions."""
from core.jira_client import add_comment as _add_comment
from core.jira_client import resolve_issue as _resolve_issue
from input_models.models import JiraCommentInput, JiraResolveInput


async def jira_add_comment(params: JiraCommentInput) -> str:
    """Add a comment to the active Jira incident ticket."""
    try:
        await _add_comment(params.issue_key, params.comment)
        return f"Comment added to {params.issue_key}"
    except Exception as e:
        return f"Jira comment failed for {params.issue_key}: {e}"


async def jira_resolve_issue(params: JiraResolveInput) -> str:
    """Transition Jira ticket to resolved state with a resolution summary."""
    try:
        await _resolve_issue(params.issue_key, params.resolution_comment, params.resolution)
        return f"{params.issue_key} marked as resolved"
    except Exception as e:
        return f"Jira resolve failed for {params.issue_key}: {e}"
