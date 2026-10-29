"""Precisely bound benign native clock.sleep calls in ordinary CLI telemetry."""
import json
import re

from .codex_exec_tool_source import CodexExecTelemetryError


class ClockSleeps:
    def __init__(self, session_id):
        self.session_id = str(session_id)
        self.turn_id = None
        self.pending = {}
        self.seen = set()

    def accept(self, row):
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            return False
        kind = payload.get("type")
        if row.get("type") == "turn_context":
            if self.pending and payload.get("turn_id") != self.turn_id:
                raise CodexExecTelemetryError("clock sleep crossed its frozen turn")
            self.turn_id = payload.get("turn_id")
        if row.get("type") == "response_item" and kind == "function_call" and payload.get("namespace") == "clock":
            call = payload.get("call_id")
            try:
                arguments = json.loads(payload.get("arguments", "{}"))
            except (TypeError, ValueError) as error:
                raise CodexExecTelemetryError("invalid native clock arguments") from error
            duration = arguments.get("duration_ms") if isinstance(arguments, dict) else None
            if (payload.get("name") != "sleep" or not isinstance(call, str) or not call or len(call) > 160
                    or call in self.seen or not self.turn_id or not isinstance(arguments, dict) or set(arguments) != {"duration_ms"}
                    or type(duration) is not int or not 1 <= duration <= 43_200_000):
                raise CodexExecTelemetryError("unsupported native clock call")
            self.pending[call] = (duration, False)
            self.seen.add(call)
            return True
        item = payload.get("item", {})
        if row.get("type") == "event_msg" and isinstance(item, dict) and item.get("kind") == "clock.sleep":
            call = item.get("id")
            prior = self.pending.get(call)
            if (prior is None or prior[1] or set(item) != {"type", "kind", "id", "durationMs"}
                    or item["type"] != "Extension" or type(item["durationMs"]) is not int or item["durationMs"] != prior[0]
                    or payload.get("thread_id") != self.session_id or payload.get("turn_id") != self.turn_id):
                raise CodexExecTelemetryError("clock sleep extension differs from its exact call")
            self.pending[call] = (prior[0], True)
            return True
        if row.get("type") == "response_item" and kind == "function_call_output" and payload.get("call_id") in self.seen:
            call = payload["call_id"]
            prior = self.pending.get(call)
            output = payload.get("output")
            if (prior is None or not prior[1] or not isinstance(output, str)
                    or re.fullmatch(r"Wall time: [0-9]+(?:\.[0-9]+)? seconds\nSleep completed\.", output) is None):
                raise CodexExecTelemetryError("clock sleep lacks its completed exact output")
            del self.pending[call]
            return True
        return False

    def finish(self):
        if self.pending:
            raise CodexExecTelemetryError("clock sleep evidence is incomplete")
