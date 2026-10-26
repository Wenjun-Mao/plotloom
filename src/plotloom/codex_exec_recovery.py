"""Positive, closed-world proof for completed read-only CLI turns."""
from __future__ import annotations

import json
import shlex
from collections import Counter
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field

from .codex_exec_constants import HASH
from .codex_exec_files import read_confined_regular_file
from .codex_exec_runtime import read_exec_events
from .codex_exec_tool_source import (
    CodexExecTelemetryError,
    _ObjectParser,
    _Token,
    _tokens,
)
from plotloom.domain_base import CamelModel

MAX_BYTES = 2_000_000


class NoRemoteDispatchProof(CamelModel):
    """Proof of no dispatch, explicitly without an observed CLI exit code."""
    version: Literal["plotloom.codex-exec.no-remote-dispatch.v1"] = "plotloom.codex-exec.no-remote-dispatch.v1"
    session_id: UUID
    stream_hash: str = Field(pattern=HASH)
    rollout_hash: str = Field(pattern=HASH)
    command_hashes: tuple[str, ...]
    tool_call_count: int = Field(ge=0)
    observed_cli_exit_code: None = None


def _read_rows(path: Path):
    content = read_confined_regular_file(path.parent, path.name, max_bytes=MAX_BYTES)
    if not content.endswith(b"\n"):
        raise CodexExecTelemetryError("recovery evidence must end at a complete record")
    rows = [json.loads(raw) for raw in content.splitlines()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise CodexExecTelemetryError("recovery evidence must contain typed records")
    return content, rows


def _read_command(source: str, allowed: set[str]) -> str:
    tokens = _tokens(source)
    prefix = tuple(_Token(k, v) for k, v in (
        ("identifier", "text"), ("(", "("), ("identifier", "await"),
        ("identifier", "tools"), (".", "."), ("identifier", "exec_command")))
    if tokens[:6] != prefix:
        raise CodexExecTelemetryError("recovery allows only one literal read-only exec_command")
    parser = _ObjectParser(tokens, 6)
    parser.take("(")
    parser.take("{")
    arguments = {}
    while parser.index < len(tokens) and tokens[parser.index].kind != "}":
        key = tokens[parser.index]
        parser.index += 1
        if key.kind not in {"identifier", "string"} or key.value in arguments:
            raise CodexExecTelemetryError("recovery command has invalid argument names")
        parser.take(":")
        arguments[key.value] = parser.value()
        if tokens[parser.index].kind != "}":
            parser.take(",")
    parser.take("}")
    parser.take(")")
    parser.take(")")
    if tokens[parser.index:] not in {(), (_Token(";", ";"),)}:
        raise CodexExecTelemetryError("recovery exec source contains additional statements")
    if set(arguments) - {"cmd", "max_output_tokens"} or arguments.get("cmd") not in allowed:
        raise CodexExecTelemetryError("recovery command is outside the exact read-only inventory")
    if "max_output_tokens" in arguments and (
        type(arguments["max_output_tokens"]) is not int or not 1 <= arguments["max_output_tokens"] <= 20_000
    ):
        raise CodexExecTelemetryError("recovery command has unsupported output limits")
    return arguments["cmd"]


def _completed_output(output):
    if not isinstance(output, list) or not output:
        raise CodexExecTelemetryError("recovery command lacks its structured tool output")
    results = []
    for block in output:
        if not isinstance(block, dict) or set(block) != {"type", "text"} or block["type"] != "input_text":
            raise CodexExecTelemetryError("recovery output has an unsupported content block")
        try:
            result = json.loads(block["text"])
        except (TypeError, ValueError):
            continue
        results.append(result)
    if len(results) != 1 or not isinstance(results[0], dict):
        raise CodexExecTelemetryError("recovery output must have one native command result")
    result = results[0]
    if (set(result) - {"chunk_id", "wall_time_seconds", "exit_code", "original_token_count", "output"}
            or type(result.get("exit_code")) is not int or not isinstance(result.get("output"), str)):
        raise CodexExecTelemetryError("recovery command did not finish or has unsupported result fields")


def prove_no_remote_dispatch(stdout: Path, rollout: Path, session_id: UUID, *, job_root: Path, source_root: Path):
    """Account for every executed tool; absence of recognized ImageGen is insufficient."""
    from hashlib import sha256

    from .codex_exec_telemetry import read_cli_session

    stream = read_exec_events(stdout, max_event_bytes=MAX_BYTES, max_total_bytes=MAX_BYTES)
    session = read_cli_session(rollout, session_id, max_event_bytes=MAX_BYTES, max_total_bytes=MAX_BYTES)
    if (stream.session_id != session_id or stream.terminal_event != "turn.completed"
            or stream.diagnostics or stream.file_changes or session.image_calls or session.image_events
            or session.reference_views):
        raise CodexExecTelemetryError("recovery requires a complete turn without remote or file effects")
    stream_bytes, stream_rows = _read_rows(stdout)
    rollout_bytes, rows = _read_rows(rollout)
    if sha256(stream_bytes).hexdigest() != stream.transcript_sha256 or sha256(rollout_bytes).hexdigest() != session.transcript_sha256:
        raise CodexExecTelemetryError("recovery evidence changed between inspections")
    skill = source_root / ".agents/skills/plotloom-image-specialist/SKILL.md"
    allowed = {"ls -la ../package && cat ../package/COPY_ASSIGNMENT.txt",
               "cat ../package/COPY_ASSIGNMENT.txt", "cat ../package/request.json", f"cat {shlex.quote(str(skill))}"}
    cwd = str(job_root / "delivery")
    pending = None
    calls = []
    turn_id = None
    context_seen = False
    completed = False
    for index, row in enumerate(rows):
        if type(row.get("ordinal")) is not int or row["ordinal"] != index or completed:
            raise CodexExecTelemetryError("recovery rollout is incomplete, reordered or continued")
        kind, payload = row.get("type"), row.get("payload")
        if not isinstance(payload, dict):
            raise CodexExecTelemetryError("recovery rollout has an unsupported payload")
        if kind == "session_meta":
            if index != 0 or payload.get("id") != str(session_id) or payload.get("cwd") != cwd:
                raise CodexExecTelemetryError("recovery rollout does not bind the exact job session")
        elif kind == "turn_context":
            if context_seen or payload.get("cwd") != cwd or payload.get("turn_id") != turn_id:
                raise CodexExecTelemetryError("recovery context differs from its one job turn")
            context_seen = True
        elif kind in {"world_state", "token_usage_record"}:
            continue
        elif kind == "response_item":
            subtype = payload.get("type")
            if subtype in {"message", "reasoning"}:
                continue
            if subtype == "custom_tool_call":
                call_id = payload.get("call_id")
                if pending or payload.get("name") != "exec" or not isinstance(call_id, str) or not call_id:
                    raise CodexExecTelemetryError("recovery contains an unsupported or overlapping tool call")
                command = _read_command(payload.get("input", ""), allowed)
                if call_id in {item[0] for item in calls}:
                    raise CodexExecTelemetryError("recovery tool call identity repeats")
                pending = (call_id, command)
            elif subtype == "custom_tool_call_output":
                if not pending or payload.get("call_id") != pending[0]:
                    raise CodexExecTelemetryError("recovery contains an unbound tool output")
                _completed_output(payload.get("output"))
                calls.append(pending)
                pending = None
            else:
                raise CodexExecTelemetryError("recovery contains an unaccounted response item")
        elif kind == "event_msg":
            subtype = payload.get("type")
            if subtype == "task_started":
                if turn_id is not None or not isinstance(payload.get("turn_id"), str):
                    raise CodexExecTelemetryError("recovery requires exactly one native turn")
                turn_id = payload["turn_id"]
            elif subtype == "task_complete":
                if not turn_id or payload.get("turn_id") != turn_id or pending or not context_seen:
                    raise CodexExecTelemetryError("recovery native turn is not fully complete")
                completed = True
            elif subtype == "item_completed":
                item = payload.get("item", {})
                if payload.get("thread_id") != str(session_id) or payload.get("turn_id") != turn_id:
                    raise CodexExecTelemetryError("recovery native item belongs to another turn")
                if item.get("type") == "CommandExecution":
                    if (not pending or item.get("command") != ["/bin/zsh", "-lc", pending[1]]
                            or item.get("cwd") != (job_root / "delivery").as_uri()
                            or item.get("status") != "completed" or type(item.get("exit_code")) is not int):
                        raise CodexExecTelemetryError("recovery native command is not a completed bound read")
                elif item.get("type") not in {"UserMessage", "AgentMessage", "Reasoning"}:
                    raise CodexExecTelemetryError("recovery contains an unaccounted native tool or extension")
            elif subtype not in {"token_count", "thread_settings_applied"}:
                raise CodexExecTelemetryError("recovery contains an unaccounted native event")
        else:
            raise CodexExecTelemetryError("recovery contains an unsupported record type")
    if not completed or pending:
        raise CodexExecTelemetryError("recovery rollout lacks complete terminal evidence")
    pending_commands = {}
    completed_commands = []
    for row in stream_rows:
        if row["type"] in {"thread.started", "turn.started", "turn.completed"}:
            continue
        item = row.get("item", {})
        if item.get("type") == "agent_message" and row["type"] == "item.completed":
            continue
        if item.get("type") != "command_execution":
            raise CodexExecTelemetryError("recovery stream contains another tool")
        command = shlex.split(item.get("command", ""))
        if len(command) != 3 or command[:2] != ["/bin/zsh", "-lc"] or command[2] not in allowed:
            raise CodexExecTelemetryError("recovery stream contains an unsupported shell command")
        item_id = item.get("id")
        if row["type"] == "item.started" and item_id not in pending_commands:
            pending_commands[item_id] = command[2]
        elif (row["type"] == "item.completed" and pending_commands.pop(item_id, None) == command[2]
              and item.get("status") == "completed" and type(item.get("exit_code")) is int):
            completed_commands.append(command[2])
        else:
            raise CodexExecTelemetryError("recovery stream command has no exact completed pair")
    if pending_commands or Counter(completed_commands) - Counter(command for _id, command in calls):
        raise CodexExecTelemetryError("recovery stream and full rollout disagree on executed commands")
    return NoRemoteDispatchProof(sessionId=session_id, streamHash=stream.transcript_sha256,
        rolloutHash=session.transcript_sha256, commandHashes=tuple(sha256(cmd.encode()).hexdigest() for _id, cmd in calls),
        toolCallCount=len(calls))
