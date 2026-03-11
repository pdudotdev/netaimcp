"""Session pool stub — no persistent connection pools required.

Kept for MCPServer.py import compatibility (close_sessions on shutdown).
"""


async def close_sessions() -> None:
    """No-op: connections are per-request; no persistent pools to close."""
    pass
