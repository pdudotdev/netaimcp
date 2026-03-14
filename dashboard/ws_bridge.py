# aiNOC - AI Network Troubleshooting Framework
# Copyright (c) 2026 Mihai Catalin Teodosiu
# Licensed under the Business Source License 1.1

#!/usr/bin/env python3
"""
aiNOC Dashboard WebSocket Bridge
Tail-follows the watcher's stream-json NDJSON session file and broadcasts
parsed events to connected browser clients over WebSocket.
Serves dashboard/index.html on the same port as the WebSocket server.

Runs as a standalone always-on systemd service (oncall-dashboard.service),
independent of the watcher. If not running, watcher operates normally.
Communication with watcher is via filesystem only:
  - data/dashboard_state.json  (session lifecycle: active/idle)
  - logs/.session-oncall-*.tmp (NDJSON event stream)

Single port: DASHBOARD_PORT env var (default 5555) handles both HTTP and WebSocket.
"""

import asyncio
import collections
import json
import logging
import os
import sys
from pathlib import Path

from websockets.asyncio.server import serve, broadcast as ws_broadcast
from websockets.datastructures import Headers
from websockets.http11 import Response

# ---------------------------------------------------------------------------
# Paths and configuration
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).parent.parent
DASHBOARD_DIR = Path(__file__).parent
STATE_FILE = PROJECT_DIR / "data" / "dashboard_state.json"
STOP_FILE = PROJECT_DIR / "data" / "stop_session"
INDEX_HTML = DASHBOARD_DIR / "index.html"

PORT = int(os.getenv("DASHBOARD_PORT", "5555"))
BUFFER_SIZE = 200          # ring buffer: max events replayed to late-joining clients
TAIL_POLL_INTERVAL = 0.1   # seconds between file tail-follow reads

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("ainoc.dashboard")
# Suppress websockets' INFO logs for HTTP-served connections (logged as "rejected")
logging.getLogger("websockets.server").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Shared state (module-level — all coroutines run in one event loop)
# ---------------------------------------------------------------------------
CLIENTS: set = set()
EVENT_BUFFER: collections.deque = collections.deque(maxlen=BUFFER_SIZE)
SESSION_STATE: dict = {"state": "idle"}

# Pending tool inputs keyed by content-block index — accumulated input_json_delta chunks
_tool_inputs: dict[int, dict] = {}


# ---------------------------------------------------------------------------
# Event parsing — raw stream_event NDJSON → simplified UI events
# ---------------------------------------------------------------------------

def _strip_tool_prefix(name: str) -> str:
    """Normalize MCP tool names for display. Keeps built-in names as-is."""
    return name.removeprefix("mcp__mcp_automation__")


def parse_ndjson_line(raw: str) -> list[dict]:
    """Parse one NDJSON line from stream-json output into zero or more UI events.

    Claude CLI stream-json format:
      {"type": "stream_event", "event": {"type": "...", ...}}  -- streaming events
      {"type": "result", "total_cost_usd": ..., ...}           -- final result
      {"type": "assistant", ...}                                -- final message envelope
      {"type": "system", ...}                                   -- system prompt info

    Returns a list of UI event dicts (may be empty for events we don't surface).
    """
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []

    t = obj.get("type")

    # ------------------------------------------------------------------
    # Final result line — session cost + completion signal
    # ------------------------------------------------------------------
    if t == "result":
        return [{"ui_type": "session_end", "cost": obj.get("total_cost_usd")}]

    # ------------------------------------------------------------------
    # Streaming events
    # ------------------------------------------------------------------
    if t != "stream_event":
        return []

    ev = obj.get("event", {})
    ev_type = ev.get("type", "")

    # -- Text reasoning (incremental character streaming) ---------------
    if ev_type == "content_block_delta":
        delta = ev.get("delta", {})
        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            if text:
                return [{"ui_type": "reasoning", "text": text}]

        elif delta.get("type") == "input_json_delta":
            # Accumulate tool input JSON chunks keyed by content-block index
            idx = ev.get("index", -1)
            partial = delta.get("partial_json", "")
            if idx not in _tool_inputs:
                _tool_inputs[idx] = {"json_buf": "", "id": None, "name": None}
            _tool_inputs[idx]["json_buf"] += partial

    # -- Tool call starts -----------------------------------------------
    elif ev_type == "content_block_start":
        cb = ev.get("content_block", {})
        if cb.get("type") == "tool_use":
            idx = ev.get("index", -1)
            tool_id = cb.get("id", "")
            name = _strip_tool_prefix(cb.get("name", ""))
            _tool_inputs[idx] = {"json_buf": "", "id": tool_id, "name": name}
            return [{"ui_type": "tool_start", "tool": name, "id": tool_id}]

        elif cb.get("type") == "tool_result":
            # Tool result arrives as a content block in the next user message
            tool_use_id = cb.get("tool_use_id", "")
            content = cb.get("content", "")
            if isinstance(content, list):
                # Extract text from content array
                content = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                )
            return [{"ui_type": "tool_result", "id": tool_use_id, "output": str(content)}]

    # -- Tool call complete (emit full input) ---------------------------
    elif ev_type == "content_block_stop":
        idx = ev.get("index", -1)
        if idx in _tool_inputs:
            entry = _tool_inputs.pop(idx)
            if entry.get("id"):  # was a tool_use block (not text)
                try:
                    input_obj = json.loads(entry["json_buf"]) if entry["json_buf"] else {}
                except json.JSONDecodeError:
                    input_obj = {"raw": entry["json_buf"]}
                return [{
                    "ui_type": "tool_input_complete",
                    "tool": entry.get("name", ""),
                    "id": entry["id"],
                    "input": input_obj,
                }]

    return []


# ---------------------------------------------------------------------------
# Session file tail-follower
# ---------------------------------------------------------------------------

async def _tail_session_file(path: Path) -> None:
    """Async tail-follow a session NDJSON file and broadcast parsed events."""
    log.info("Tail-following session file: %s", path)
    # Wait for file to appear (race condition: state file written before file created)
    for _ in range(50):  # up to 5 seconds
        if path.exists():
            break
        await asyncio.sleep(0.1)
    else:
        log.warning("Session file never appeared: %s", path)
        return

    _tool_inputs.clear()
    position = 0

    while True:
        # Check if session ended (state flipped to idle)
        if SESSION_STATE.get("state") != "active":
            # Drain any remaining lines before stopping
            try:
                with open(path, errors="replace") as fh:
                    fh.seek(position)
                    remainder = fh.read()
                for line in remainder.splitlines():
                    line = line.strip()
                    if line:
                        for ui_event in parse_ndjson_line(line):
                            await _broadcast(ui_event)
                            EVENT_BUFFER.append(ui_event)
            except Exception:
                pass
            log.info("Session ended — stopping tail")
            return

        try:
            with open(path, errors="replace") as fh:
                fh.seek(position)
                new_text = fh.read()
        except FileNotFoundError:
            await asyncio.sleep(TAIL_POLL_INTERVAL)
            continue
        if new_text:
            lines = new_text.split("\n")
            # If text doesn't end in newline, last item is a partial line — hold it
            if not new_text.endswith("\n"):
                lines_to_process = lines[:-1]
                consumed = len("\n".join(lines_to_process))
                if lines_to_process:
                    consumed += 1  # trailing newline of the last complete line
            else:
                lines_to_process = lines[:-1]  # trailing empty string after final \n
                consumed = len(new_text)

            for line in lines_to_process:
                line = line.strip()
                if not line:
                    continue
                for ui_event in parse_ndjson_line(line):
                    await _broadcast(ui_event)
                    EVENT_BUFFER.append(ui_event)

            position += consumed

        await asyncio.sleep(TAIL_POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Session state watcher
# ---------------------------------------------------------------------------

async def watch_state_file() -> None:
    """Poll data/dashboard_state.json and manage the session tail-follow task."""
    global SESSION_STATE
    tail_task: asyncio.Task | None = None
    last_session_name = None

    log.info("Watching state file: %s", STATE_FILE)
    while True:
        try:
            raw = STATE_FILE.read_text()
            state = json.loads(raw)
        except FileNotFoundError:
            state = {"state": "idle"}
        except (json.JSONDecodeError, OSError):
            state = {"state": "idle"}

        state_changed = state != SESSION_STATE
        SESSION_STATE = state

        if state.get("state") == "active":
            session_name = state.get("session_name")
            if session_name != last_session_name:
                # New session started — cancel any previous tail task
                if tail_task and not tail_task.done():
                    tail_task.cancel()
                    try:
                        await tail_task
                    except asyncio.CancelledError:
                        pass

                last_session_name = session_name
                EVENT_BUFFER.clear()
                _tool_inputs.clear()

                # Notify clients of new session
                await _broadcast({"ui_type": "session_start", **state})

                session_file = state.get("session_file")
                if session_file:
                    tail_task = asyncio.create_task(
                        _tail_session_file(Path(session_file))
                    )

        elif state_changed and state.get("state") == "idle":
            # Session ended — notify clients
            last_session_name = None
            if tail_task and not tail_task.done():
                tail_task.cancel()
                try:
                    await tail_task
                except asyncio.CancelledError:
                    pass
            await _broadcast({"ui_type": "session_idle"})

        await asyncio.sleep(0.5)  # poll state file every 500ms


# ---------------------------------------------------------------------------
# WebSocket broadcast
# ---------------------------------------------------------------------------

def _write_stop_sentinel() -> None:
    """Create the stop sentinel file that signals the watcher to kill the agent session."""
    try:
        STOP_FILE.parent.mkdir(exist_ok=True)
        STOP_FILE.write_text("")
        log.info("Stop sentinel written: %s", STOP_FILE)
    except Exception as e:
        log.warning("Could not write stop sentinel: %s", e)


async def _broadcast(event: dict) -> None:
    """Send a UI event to all connected WebSocket clients."""
    if not CLIENTS:
        return
    msg = json.dumps(event)
    ws_broadcast(CLIENTS, msg)


# ---------------------------------------------------------------------------
# HTTP handler — serves index.html on the same port as the WebSocket server.
# websockets 16.0 process_request intercepts plain HTTP GET requests before
# the WebSocket handshake; returning a Response bypasses the upgrade.
# ---------------------------------------------------------------------------

def _http_handler(connection, request):
    """Route plain HTTP GET requests; pass WebSocket upgrade requests through.

    WebSocket upgrade requests carry 'Upgrade: websocket' — return None so
    websockets proceeds with the normal handshake. Plain HTTP requests (browser
    page load, favicon, etc.) are served directly as HTTP responses.
    Returning a Response for non-WS requests prevents websockets from attempting
    a handshake and failing on keep-alive connections.
    """
    # WebSocket upgrade request — let websockets handle the handshake normally
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None

    # Plain HTTP: serve the dashboard page
    if request.path in ("/", "/index.html"):
        try:
            body = INDEX_HTML.read_bytes()
            headers = Headers({"Content-Type": "text/html; charset=utf-8"})
            return Response(200, "OK", headers, body)
        except FileNotFoundError:
            headers = Headers({"Content-Type": "text/plain"})
            return Response(404, "Not Found", headers, b"Dashboard not found")

    # Silently swallow favicon requests
    if request.path == "/favicon.ico":
        return Response(204, "No Content", Headers({}), b"")

    # Anything else — 404
    headers = Headers({"Content-Type": "text/plain"})
    return Response(404, "Not Found", headers, b"Not found")


# ---------------------------------------------------------------------------
# WebSocket connection handler
# ---------------------------------------------------------------------------

async def ws_handler(websocket) -> None:
    """Handle a WebSocket client connection."""
    remote = websocket.remote_address
    log.info("WebSocket client connected: %s", remote)
    CLIENTS.add(websocket)
    try:
        # Send current state + buffered events on connect (replay for late joiners)
        init_msg = {
            "ui_type": "init",
            "state": SESSION_STATE,
            "buffer": list(EVENT_BUFFER),
        }
        await websocket.send(json.dumps(init_msg))

        # Handle stop commands from the dashboard; ignore all other messages
        async for msg in websocket:
            try:
                data = json.loads(msg)
                if data.get("action") == "stop":
                    log.info("Stop requested by dashboard client %s", remote)
                    _write_stop_sentinel()
            except (json.JSONDecodeError, ValueError):
                pass
    except Exception:
        pass
    finally:
        CLIENTS.discard(websocket)
        log.info("WebSocket client disconnected: %s", remote)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    log.info("aiNOC Dashboard bridge starting on port %d", PORT)

    async with serve(ws_handler, "0.0.0.0", PORT, process_request=_http_handler):
        log.info("Listening on http://0.0.0.0:%d  (HTTP + WebSocket)", PORT)
        await watch_state_file()  # runs forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Dashboard bridge stopped")
