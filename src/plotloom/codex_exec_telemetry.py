"""Strict parsing of the qualified Codex CLI and private session event shapes."""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID


class CodexExecTelemetryError(ValueError):
    """The installed CLI emitted an unsupported or unbound evidence shape."""


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any


@dataclass(frozen=True)
class ImageGenCall:
    call_id: str
    prompt: str
    reference_paths: tuple[str, ...]
    transparent_background: bool
    num_last_images_to_include: int | None


@dataclass(frozen=True)
class ImageGenEvent:
    call_id: str
    event_id: str
    status: str
    saved_path: str | None
    transparent_background: bool | None


@dataclass(frozen=True)
class CodexSessionEvidence:
    session_id: UUID
    image_calls: tuple[ImageGenCall, ...]
    image_events: tuple[ImageGenEvent, ...]
    transcript_sha256: str
    transcript_size_bytes: int


def _tokens(source: str, *, allow_unrelated_syntax: bool = False) -> tuple[_Token, ...]:
    values: list[_Token] = []
    index = 0
    while index < len(source):
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if source.startswith("//", index):
            ending = source.find("\n", index + 2)
            index = len(source) if ending < 0 else ending + 1
            continue
        if source.startswith("/*", index):
            ending = source.find("*/", index + 2)
            if ending < 0:
                raise CodexExecTelemetryError("tool source has an unterminated comment")
            index = ending + 2
            continue
        if char in {'"', "'"}:
            quote = char
            start = index
            index += 1
            escaped = False
            while index < len(source):
                current = source[index]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    index += 1
                    break
                index += 1
            else:
                raise CodexExecTelemetryError("tool source has an unterminated string")
            literal = source[start:index]
            try:
                value = json.loads(literal) if quote == '"' else ast.literal_eval(literal)
            except (ValueError, SyntaxError, json.JSONDecodeError) as error:
                if allow_unrelated_syntax:
                    values.append(_Token("opaque_string", None))
                    continue
                raise CodexExecTelemetryError("tool source string is not a supported literal") from error
            if not isinstance(value, str):
                raise CodexExecTelemetryError("tool source string is not text")
            values.append(_Token("string", value))
            continue
        if char == "`":
            # The qualified ImageGen source shape does not use templates. Keep
            # them opaque for unrelated exec snippets; if an ImageGen call is
            # also present, the exact whole-source grammar below rejects it.
            index += 1
            escaped = False
            while index < len(source):
                current = source[index]
                index += 1
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == "`":
                    break
            if not allow_unrelated_syntax:
                raise CodexExecTelemetryError("ImageGen arguments cannot use template strings")
            values.append(_Token("opaque_string", None))
            continue
        if char.isalpha() or char in "_$":
            start = index
            index += 1
            while index < len(source) and (source[index].isalnum() or source[index] in "_$"):
                index += 1
            values.append(_Token("identifier", source[start:index]))
            continue
        if char.isdigit():
            start = index
            index += 1
            while index < len(source) and source[index].isdigit():
                index += 1
            values.append(_Token("number", int(source[start:index])))
            continue
        if char in "{}[]():,.;=":
            values.append(_Token(char, char))
            index += 1
            continue
        if allow_unrelated_syntax:
            values.append(_Token("other", char))
            index += 1
            continue
        raise CodexExecTelemetryError("tool source contains unsupported syntax")
    return tuple(values)


class _ObjectParser:
    def __init__(self, tokens: tuple[_Token, ...], index: int):
        self.tokens = tokens
        self.index = index

    def take(self, kind: str) -> _Token:
        if self.index >= len(self.tokens) or self.tokens[self.index].kind != kind:
            raise CodexExecTelemetryError("ImageGen arguments have an unsupported shape")
        token = self.tokens[self.index]
        self.index += 1
        return token

    def value(self):
        if self.index >= len(self.tokens):
            raise CodexExecTelemetryError("ImageGen arguments are incomplete")
        token = self.tokens[self.index]
        self.index += 1
        if token.kind == "string" or token.kind == "number":
            return token.value
        if token.kind == "identifier" and token.value in {"true", "false", "null"}:
            return {"true": True, "false": False, "null": None}[token.value]
        if token.kind == "[":
            result = []
            if self.index < len(self.tokens) and self.tokens[self.index].kind == "]":
                self.index += 1
                return result
            while True:
                value = self.value()
                if not isinstance(value, str):
                    raise CodexExecTelemetryError("ImageGen reference arguments must be literal paths")
                result.append(value)
                if self.index < len(self.tokens) and self.tokens[self.index].kind == "]":
                    self.index += 1
                    return result
                self.take(",")
        raise CodexExecTelemetryError("ImageGen arguments must use supported literal values")

    def imagegen_arguments(self) -> dict[str, Any]:
        self.take("(")
        self.take("{")
        result: dict[str, Any] = {}
        while self.index < len(self.tokens) and self.tokens[self.index].kind != "}":
            token = self.tokens[self.index]
            self.index += 1
            if token.kind not in {"identifier", "string"}:
                raise CodexExecTelemetryError("ImageGen argument names must be literal keys")
            key = token.value
            if key in result:
                raise CodexExecTelemetryError("ImageGen arguments cannot repeat a field")
            self.take(":")
            result[key] = self.value()
            if self.index < len(self.tokens) and self.tokens[self.index].kind == "}":
                break
            self.take(",")
        self.take("}")
        self.take(")")
        allowed = {"prompt", "images", "transparent_background", "num_last_images_to_include"}
        if set(result) - allowed or not isinstance(result.get("prompt"), str) or not result["prompt"].strip():
            raise CodexExecTelemetryError("ImageGen arguments do not match the supported prompt contract")
        if type(result.get("transparent_background")) is not bool:
            raise CodexExecTelemetryError("ImageGen transparency must be an explicit boolean")
        if "images" in result and not isinstance(result["images"], list):
            raise CodexExecTelemetryError("ImageGen references must be a literal path list")
        prior = result.get("num_last_images_to_include")
        if prior is not None and (type(prior) is not int or prior != 0):
            raise CodexExecTelemetryError("ImageGen cannot consume prior-session outputs")
        return result


def parse_imagegen_tool_source(source: str) -> dict[str, Any] | None:
    """Parse the sole supported, awaited top-level ImageGen expression.

    The CLI transcript records JavaScript source and a separate extension
    event, but does not bind that event to the source call's arguments. Only
    accepting one direct statement prevents a dead branch, helper function,
    template interpolation, or unrelated call from donating arguments to an
    observed event.
    """
    tokens = _tokens(source, allow_unrelated_syntax=True)
    matches = []
    imagegen_names = [index for index, token in enumerate(tokens)
                      if token.kind == "identifier" and token.value == "image_gen__imagegen"]
    for index in imagegen_names:
        is_builtin = (
            index >= 2
            and tokens[index - 2].kind == "identifier" and tokens[index - 2].value == "tools"
            and tokens[index - 1].kind == "."
            and (index == 2 or tokens[index - 3].kind != ".")
            and index + 1 < len(tokens) and tokens[index + 1].kind == "("
        )
        if not is_builtin:
            raise CodexExecTelemetryError("ImageGen call does not use the exact built-in tools namespace")
        matches.append(index + 1)
    if not matches:
        return None
    if len(matches) != 1:
        raise CodexExecTelemetryError("one CLI tool invocation cannot contain multiple ImageGen calls")
    index = matches[0] - 1
    expected_prefix = (
        _Token("identifier", "await"),
        _Token("identifier", "tools"),
        _Token(".", "."),
    )
    if index != len(expected_prefix) or tokens[:index] != expected_prefix:
        raise CodexExecTelemetryError(
            "ImageGen evidence requires one direct top-level awaited built-in call"
        )
    parser = _ObjectParser(tokens, matches[0])
    arguments = parser.imagegen_arguments()
    suffix = tokens[parser.index:]
    if suffix not in {(), (_Token(";", ";"),)}:
        raise CodexExecTelemetryError(
            "ImageGen evidence cannot share an exec snippet with other JavaScript"
        )
    if any(token.kind == "opaque_string" for token in tokens):
        raise CodexExecTelemetryError(
            "ImageGen evidence cannot share an exec snippet with opaque template code"
        )
    return arguments


def read_cli_session(session_path: Path, expected_session_id: UUID, *, max_event_bytes: int, max_total_bytes: int) -> CodexSessionEvidence:
    """Read only the session named by the CLI thread.started event."""
    from hashlib import sha256
    import os
    import stat

    if max_event_bytes < 1 or max_total_bytes < max_event_bytes:
        raise ValueError("Codex session byte limits must be positive and ordered")
    if session_path.is_symlink():
        raise CodexExecTelemetryError("Codex session evidence must be a regular file")
    descriptor = os.open(session_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    digest = sha256()
    total = 0
    calls: list[ImageGenCall] = []
    pending: list[ImageGenCall] = []
    events: list[ImageGenEvent] = []
    event_ids_by_call: dict[str, str] = {}
    first = True
    last_ordinal = -1
    try:
        initial = os.fstat(descriptor)
        if not stat.S_ISREG(initial.st_mode):
            raise CodexExecTelemetryError("Codex session evidence must be a regular file")
        with os.fdopen(os.dup(descriptor), "rb", closefd=True) as stream:
            while True:
                raw = stream.readline(max_event_bytes + 1)
                if not raw:
                    break
                total += len(raw)
                if total > max_total_bytes:
                    raise CodexExecTelemetryError("Codex session evidence exceeds the qualified byte limit")
                if len(raw) > max_event_bytes:
                    raise CodexExecTelemetryError("Codex session event exceeds the qualified byte limit")
                digest.update(raw)
                event_bytes = raw[:-1] if raw.endswith(b"\n") else raw
                try:
                    row = json.loads(event_bytes)
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    raise CodexExecTelemetryError("Codex session line is not valid JSON") from error
                if not isinstance(row, dict) or not isinstance(row.get("type"), str):
                    raise CodexExecTelemetryError("Codex session line has no typed event")
                if first:
                    first = False
                    metadata = row.get("payload")
                    if (row["type"] != "session_meta" or not isinstance(metadata, dict)
                            or metadata.get("id") != str(expected_session_id)):
                        raise CodexExecTelemetryError("Codex session file does not belong to the exact CLI session")
                ordinal = row.get("ordinal")
                if type(ordinal) is int:
                    if ordinal <= last_ordinal:
                        raise CodexExecTelemetryError("Codex session event order is not monotonic")
                    last_ordinal = ordinal
                payload = row.get("payload")
                if row["type"] == "response_item" and isinstance(payload, dict) and payload.get("type") == "custom_tool_call":
                    tool_name = payload.get("name")
                    if tool_name != "exec":
                        raise CodexExecTelemetryError("Codex session contains an unsupported custom tool")
                    source = payload.get("input")
                    call_id = payload.get("call_id")
                    if not isinstance(source, str) or not isinstance(call_id, str) or not call_id:
                        raise CodexExecTelemetryError("Codex tool call lacks its typed source and ID")
                    arguments = parse_imagegen_tool_source(source)
                    if arguments is not None:
                        call = ImageGenCall(
                            call_id=call_id,
                            prompt=arguments["prompt"],
                            reference_paths=tuple(arguments.get("images", ())),
                            transparent_background=arguments["transparent_background"],
                            num_last_images_to_include=arguments.get("num_last_images_to_include"),
                        )
                        if any(prior.call_id == call.call_id for prior in calls):
                            raise CodexExecTelemetryError("Codex ImageGen call IDs are not unique")
                        calls.append(call)
                        pending.append(call)
                if row["type"] == "event_msg" and isinstance(payload, dict) and isinstance(payload.get("item"), dict):
                    item = payload["item"]
                    if item.get("type") == "Extension":
                        if item.get("kind") != "image_gen.generation" or not pending:
                            raise CodexExecTelemetryError("Codex extension event has no matching ImageGen tool call")
                        status = item.get("status")
                        if status not in {"in_progress", "completed", "failed"}:
                            raise CodexExecTelemetryError("Codex ImageGen event status is unsupported")
                        call = pending[0]
                        event_id = item.get("id")
                        if not isinstance(event_id, str) or not event_id:
                            raise CodexExecTelemetryError("Codex ImageGen event lacks its exact event ID")
                        prior_event_id = event_ids_by_call.setdefault(call.call_id, event_id)
                        if prior_event_id != event_id:
                            raise CodexExecTelemetryError("Codex ImageGen progress changed its event identity")
                        transparency = item.get("transparentBackground")
                        if status in {"completed", "failed"} and type(transparency) is not bool:
                            raise CodexExecTelemetryError("terminal Codex ImageGen event lacks declared transparency")
                        if transparency is not None and (
                            type(transparency) is not bool or transparency != call.transparent_background
                        ):
                            raise CodexExecTelemetryError("Codex ImageGen event does not match its declared transparency")
                        if status in {"completed", "failed"}:
                            pending.pop(0)
                            saved_path = item.get("savedPath")
                            if status == "completed" and (not isinstance(saved_path, str) or not saved_path):
                                raise CodexExecTelemetryError("completed ImageGen event lacks its declared output path")
                            events.append(ImageGenEvent(
                                call_id=call.call_id,
                                event_id=event_id,
                                status=status,
                                saved_path=saved_path,
                                transparent_background=transparency,
                            ))
        final = os.fstat(descriptor)
        current = session_path.stat(follow_symlinks=False)
        if (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns) != (
            final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns
        ) or (current.st_dev, current.st_ino) != (initial.st_dev, initial.st_ino) or total != initial.st_size:
            raise CodexExecTelemetryError("Codex session changed during evidence inspection")
        if first:
            raise CodexExecTelemetryError("Codex session evidence is empty")
        if pending:
            raise CodexExecTelemetryError("ImageGen call lacks its exact terminal extension event")
        if len({event.event_id for event in events}) != len(events):
            raise CodexExecTelemetryError("Codex ImageGen event IDs are not unique")
        return CodexSessionEvidence(expected_session_id, tuple(calls), tuple(events), digest.hexdigest(), total)
    finally:
        os.close(descriptor)
