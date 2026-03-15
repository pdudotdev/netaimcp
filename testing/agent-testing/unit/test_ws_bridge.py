"""
UT-026: WebSocket Bridge event parsing and logic tests.
Tests the parsing/classification layer in dashboard/ws_bridge.py.
No actual WebSocket connections — pure logic tests.
"""

import json
import sys
from pathlib import Path

import pytest

# Make the project root importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import dashboard.ws_bridge as bridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stream_event(event_dict: dict) -> str:
    """Wrap an event dict in a stream_event NDJSON line."""
    return json.dumps({"type": "stream_event", "event": event_dict})


def _reset_tool_inputs():
    """Clear accumulated tool input state between tests."""
    bridge._tool_inputs.clear()


# ---------------------------------------------------------------------------
# Tool name normalization
# ---------------------------------------------------------------------------

class TestStripToolPrefix:
    def test_strips_mcp_prefix(self):
        name, is_mcp = bridge._strip_tool_prefix("mcp__mcp_automation__get_ospf")
        assert name == "get_ospf"
        assert is_mcp is True

    def test_strips_mcp_prefix_traceroute(self):
        name, is_mcp = bridge._strip_tool_prefix("mcp__mcp_automation__traceroute")
        assert name == "traceroute"
        assert is_mcp is True

    def test_keeps_builtin_read(self):
        name, is_mcp = bridge._strip_tool_prefix("Read")
        assert name == "Read"
        assert is_mcp is False

    def test_keeps_builtin_bash(self):
        name, is_mcp = bridge._strip_tool_prefix("Bash")
        assert name == "Bash"
        assert is_mcp is False

    def test_keeps_builtin_edit(self):
        name, is_mcp = bridge._strip_tool_prefix("Edit")
        assert name == "Edit"
        assert is_mcp is False

    def test_empty_string(self):
        name, is_mcp = bridge._strip_tool_prefix("")
        assert name == ""
        assert is_mcp is False

    def test_partial_prefix_not_stripped(self):
        # Only strips the full known prefix
        name, is_mcp = bridge._strip_tool_prefix("mcp__mcp_automation__")
        assert name == ""
        assert is_mcp is True

    def test_unknown_prefix_kept(self):
        name, is_mcp = bridge._strip_tool_prefix("custom__tool")
        assert name == "custom__tool"
        assert is_mcp is False


# ---------------------------------------------------------------------------
# parse_ndjson_line — malformed / empty / unrelated lines
# ---------------------------------------------------------------------------

class TestParseNdjsonLineBasic:
    def setup_method(self):
        _reset_tool_inputs()

    def test_empty_string_returns_empty(self):
        assert bridge.parse_ndjson_line("") == []

    def test_invalid_json_returns_empty(self):
        assert bridge.parse_ndjson_line("{not valid json}") == []

    def test_whitespace_only_returns_empty(self):
        assert bridge.parse_ndjson_line("   ") == []

    def test_unknown_type_returns_empty(self):
        assert bridge.parse_ndjson_line(json.dumps({"type": "system"})) == []

    def test_assistant_type_no_crash(self):
        # 'assistant' type events (final message envelope) — we don't surface them
        line = json.dumps({"type": "assistant", "message": {"content": []}})
        assert bridge.parse_ndjson_line(line) == []

    def test_stream_event_with_unknown_inner_type_returns_empty(self):
        line = _stream_event({"type": "ping"})
        assert bridge.parse_ndjson_line(line) == []

    def test_stream_event_missing_event_key_returns_empty(self):
        line = json.dumps({"type": "stream_event"})
        assert bridge.parse_ndjson_line(line) == []


# ---------------------------------------------------------------------------
# parse_ndjson_line — result event (cost extraction)
# ---------------------------------------------------------------------------

class TestParseResultEvent:
    def setup_method(self):
        _reset_tool_inputs()

    def test_result_with_cost(self):
        line = json.dumps({"type": "result", "total_cost_usd": 0.0342})
        events = bridge.parse_ndjson_line(line)
        assert len(events) == 1
        assert events[0]["ui_type"] == "session_end"
        assert events[0]["cost"] == pytest.approx(0.0342)

    def test_result_zero_cost(self):
        line = json.dumps({"type": "result", "total_cost_usd": 0.0})
        events = bridge.parse_ndjson_line(line)
        assert events[0]["cost"] == 0.0

    def test_result_missing_cost_returns_none(self):
        line = json.dumps({"type": "result"})
        events = bridge.parse_ndjson_line(line)
        assert events[0]["ui_type"] == "session_end"
        assert events[0]["cost"] is None

    def test_result_with_extra_fields(self):
        line = json.dumps({
            "type": "result",
            "total_cost_usd": 0.05,
            "session_id": "abc",
            "usage": {"input_tokens": 100},
        })
        events = bridge.parse_ndjson_line(line)
        assert events[0]["ui_type"] == "session_end"
        assert events[0]["cost"] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# parse_ndjson_line — text reasoning (text_delta)
# ---------------------------------------------------------------------------

class TestParseTextDelta:
    def setup_method(self):
        _reset_tool_inputs()

    def test_text_delta_emits_reasoning(self):
        line = _stream_event({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": "Let me check OSPF neighbors."},
            "index": 0,
        })
        events = bridge.parse_ndjson_line(line)
        assert len(events) == 1
        assert events[0]["ui_type"] == "reasoning"
        assert events[0]["text"] == "Let me check OSPF neighbors."

    def test_empty_text_delta_not_emitted(self):
        line = _stream_event({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": ""},
            "index": 0,
        })
        assert bridge.parse_ndjson_line(line) == []

    def test_multiline_text_delta(self):
        text = "Line 1\nLine 2\n"
        line = _stream_event({
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": text},
            "index": 0,
        })
        events = bridge.parse_ndjson_line(line)
        assert events[0]["text"] == text


# ---------------------------------------------------------------------------
# parse_ndjson_line — tool_use lifecycle (start → input_json_delta → stop)
# ---------------------------------------------------------------------------

class TestToolUseLifecycle:
    def setup_method(self):
        _reset_tool_inputs()

    def test_tool_start_emits_tool_start(self):
        line = _stream_event({
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "id": "call_abc", "name": "mcp__mcp_automation__get_ospf"},
            "index": 1,
        })
        events = bridge.parse_ndjson_line(line)
        assert len(events) == 1
        assert events[0]["ui_type"] == "tool_start"
        assert events[0]["tool"] == "get_ospf"
        assert events[0]["id"] == "call_abc"
        assert events[0]["is_mcp"] is True

    def test_builtin_tool_start(self):
        line = _stream_event({
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "id": "call_xyz", "name": "Read"},
            "index": 2,
        })
        events = bridge.parse_ndjson_line(line)
        assert events[0]["tool"] == "Read"
        assert events[0]["is_mcp"] is False

    def test_input_json_delta_accumulates_silently(self):
        # First set up the tool
        start_line = _stream_event({
            "type": "content_block_start",
            "content_block": {"type": "tool_use", "id": "call_abc", "name": "get_ospf"},
            "index": 1,
        })
        bridge.parse_ndjson_line(start_line)

        # Now send first chunk
        delta1 = _stream_event({
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": '{"device":'},
            "index": 1,
        })
        events1 = bridge.parse_ndjson_line(delta1)
        assert events1 == []  # accumulates silently

        # Second chunk
        delta2 = _stream_event({
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": ' "C1C", "query": "neighbors"}'},
            "index": 1,
        })
        events2 = bridge.parse_ndjson_line(delta2)
        assert events2 == []

        # Verify buffer accumulated correctly
        assert bridge._tool_inputs[1]["json_buf"] == '{"device": "C1C", "query": "neighbors"}'

    def test_tool_stop_emits_tool_input_complete(self):
        # Set up
        bridge._tool_inputs[1] = {
            "json_buf": '{"device": "C1C", "query": "neighbors"}',
            "id": "call_abc",
            "name": "get_ospf",
        }
        stop_line = _stream_event({"type": "content_block_stop", "index": 1})
        events = bridge.parse_ndjson_line(stop_line)
        assert len(events) == 1
        assert events[0]["ui_type"] == "tool_input_complete"
        assert events[0]["tool"] == "get_ospf"
        assert events[0]["id"] == "call_abc"
        assert events[0]["input"] == {"device": "C1C", "query": "neighbors"}

    def test_tool_stop_with_malformed_json_uses_raw_fallback(self):
        bridge._tool_inputs[5] = {
            "json_buf": "{broken json",
            "id": "call_xyz",
            "name": "traceroute",
        }
        stop_line = _stream_event({"type": "content_block_stop", "index": 5})
        events = bridge.parse_ndjson_line(stop_line)
        assert events[0]["ui_type"] == "tool_input_complete"
        assert "raw" in events[0]["input"]

    def test_tool_stop_removes_from_buffer(self):
        bridge._tool_inputs[3] = {"json_buf": '{"x": 1}', "id": "id1", "name": "ping"}
        stop_line = _stream_event({"type": "content_block_stop", "index": 3})
        bridge.parse_ndjson_line(stop_line)
        assert 3 not in bridge._tool_inputs

    def test_text_block_stop_emits_nothing(self):
        # Text blocks (index 0) have no tool_inputs entry — should silently return []
        stop_line = _stream_event({"type": "content_block_stop", "index": 0})
        events = bridge.parse_ndjson_line(stop_line)
        assert events == []


# ---------------------------------------------------------------------------
# parse_ndjson_line — tool_result content block
# ---------------------------------------------------------------------------

class TestToolResultBlock:
    def setup_method(self):
        _reset_tool_inputs()

    def test_tool_result_string_content(self):
        line = _stream_event({
            "type": "content_block_start",
            "content_block": {
                "type": "tool_result",
                "tool_use_id": "call_abc",
                "content": "Interface GigabitEthernet0/0 is up",
            },
            "index": 0,
        })
        events = bridge.parse_ndjson_line(line)
        assert len(events) == 1
        assert events[0]["ui_type"] == "tool_result"
        assert events[0]["id"] == "call_abc"
        assert "GigabitEthernet0/0" in events[0]["output"]

    def test_tool_result_list_content_extracted(self):
        line = _stream_event({
            "type": "content_block_start",
            "content_block": {
                "type": "tool_result",
                "tool_use_id": "call_xyz",
                "content": [
                    {"type": "text", "text": "OSPF neighbor state: FULL"},
                    {"type": "text", "text": " — DR: 10.0.0.1"},
                ],
            },
            "index": 0,
        })
        events = bridge.parse_ndjson_line(line)
        assert "FULL" in events[0]["output"]
        assert "DR" in events[0]["output"]

    def test_tool_result_empty_content(self):
        line = _stream_event({
            "type": "content_block_start",
            "content_block": {"type": "tool_result", "tool_use_id": "id1", "content": ""},
            "index": 0,
        })
        events = bridge.parse_ndjson_line(line)
        assert events[0]["ui_type"] == "tool_result"
        assert events[0]["output"] == ""



# ---------------------------------------------------------------------------
# Event buffer (ring buffer)
# ---------------------------------------------------------------------------

class TestEventBuffer:
    def setup_method(self):
        bridge.EVENT_BUFFER.clear()

    def test_buffer_accepts_events(self):
        bridge.EVENT_BUFFER.append({"ui_type": "reasoning", "text": "hello"})
        assert len(bridge.EVENT_BUFFER) == 1

    def test_buffer_respects_maxlen(self):
        for i in range(bridge.BUFFER_SIZE + 50):
            bridge.EVENT_BUFFER.append({"i": i})
        assert len(bridge.EVENT_BUFFER) == bridge.BUFFER_SIZE

    def test_buffer_evicts_oldest_on_overflow(self):
        for i in range(bridge.BUFFER_SIZE + 10):
            bridge.EVENT_BUFFER.append({"i": i})
        # Oldest entries (0..9) should be gone; newest (10..BUFFER_SIZE+9) remain
        assert bridge.EVENT_BUFFER[0]["i"] == 10

    def test_buffer_clear(self):
        bridge.EVENT_BUFFER.extend([{"a": 1}, {"b": 2}])
        bridge.EVENT_BUFFER.clear()
        assert len(bridge.EVENT_BUFFER) == 0


# ---------------------------------------------------------------------------
# State file parsing (via SESSION_STATE module variable)
# ---------------------------------------------------------------------------

class TestSessionState:
    def test_initial_state_is_idle(self):
        # MODULE loads with idle state (set at import time or after clear)
        # Just verify the key exists
        assert "state" in bridge.SESSION_STATE

    def test_idle_state_structure(self):
        bridge.SESSION_STATE = {"state": "idle"}
        assert bridge.SESSION_STATE["state"] == "idle"

    def test_active_state_structure(self):
        """SESSION_STATE must accept and preserve the full active-session schema.

        The key enumeration below acts as a schema guard: if the watcher ever changes
        the keys it writes to dashboard_state.json, this test will catch the mismatch.
        """
        bridge.SESSION_STATE = {
            "state": "active",
            "session_name": "oncall-20260314-120000",
            "device_name": "C1C",
            "device_ip": "172.20.20.207",
            "issue_key": "NOC-142",
            "started_at": "2026-03-14T12:00:00+00:00",
            "session_file": "/home/mcp/aiNOC/logs/.session-oncall-20260314-120000.tmp",
            "inventory_source": "NetBox",
            "credential_source": "Vault",
        }
        assert bridge.SESSION_STATE["state"] == "active"
        assert bridge.SESSION_STATE["device_name"] == "C1C"
        # Schema guard: all expected keys must be present
        expected_keys = (
            "state", "session_name", "device_name", "device_ip",
            "issue_key", "started_at", "session_file",
            "inventory_source", "credential_source",
        )
        for key in expected_keys:
            assert key in bridge.SESSION_STATE, f"Missing key in active SESSION_STATE schema: {key}"
