"""Strict literal-source and inline-image contracts for Codex Exec tools."""
from __future__ import annotations

import ast
import base64
import io
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import unquote_to_bytes, urlsplit

from PIL import Image, ImageFile

MAX_INLINE_IMAGE_PIXELS = 24_000_000


class CodexExecTelemetryError(ValueError):
    """The installed CLI emitted an unsupported or unbound evidence shape."""


@dataclass(frozen=True)
class InlineImageEvidence:
    content_sha256: str
    size_bytes: int


@dataclass(frozen=True)
class _Token:
    kind: str
    value: Any


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
            # Templates remain opaque in unrelated snippets. A recognized tool
            # call in interpolation cannot satisfy either exact source grammar.
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
                raise CodexExecTelemetryError("tool arguments cannot use template strings")
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
        allowed = {"prompt", "referenced_image_paths", "transparent_background", "num_last_images_to_include"}
        if set(result) - allowed or not isinstance(result.get("prompt"), str) or not result["prompt"].strip():
            raise CodexExecTelemetryError("ImageGen arguments do not match the pinned tool declaration")
        if type(result.get("transparent_background")) is not bool:
            raise CodexExecTelemetryError("ImageGen transparency must be an explicit boolean")
        if "referenced_image_paths" in result and not isinstance(result["referenced_image_paths"], list):
            raise CodexExecTelemetryError("ImageGen references must be a literal path list")
        prior = result.get("num_last_images_to_include")
        if prior is not None and (type(prior) is not int or prior != 0):
            raise CodexExecTelemetryError("ImageGen cannot consume prior-session outputs")
        return result


def parse_imagegen_tool_source(source: str) -> dict[str, Any] | None:
    """Accept one direct awaited ImageGen call with exact pinned argument names."""
    tokens = _tokens(source, allow_unrelated_syntax=True)
    matches = []
    names = [i for i, token in enumerate(tokens) if token.kind == "identifier" and token.value == "image_gen__imagegen"]
    for index in names:
        if not (
            index >= 2 and tokens[index - 2] == _Token("identifier", "tools")
            and tokens[index - 1] == _Token(".", ".")
            and (index == 2 or tokens[index - 3] != _Token(".", "."))
            and index + 1 < len(tokens) and tokens[index + 1].kind == "("
        ):
            raise CodexExecTelemetryError("ImageGen call does not use the exact built-in tools namespace")
        matches.append(index + 1)
    if not matches:
        return None
    if len(matches) != 1:
        raise CodexExecTelemetryError("one CLI tool invocation cannot contain multiple ImageGen calls")
    index = matches[0] - 1
    prefix = (_Token("identifier", "await"), _Token("identifier", "tools"), _Token(".", "."))
    if index != len(prefix) or tokens[:index] != prefix:
        raise CodexExecTelemetryError("ImageGen evidence requires one direct top-level awaited built-in call")
    parser = _ObjectParser(tokens, matches[0])
    arguments = parser.imagegen_arguments()
    if tokens[parser.index:] not in {(), (_Token(";", ";"),)} or any(
        token.kind == "opaque_string" for token in tokens
    ):
        raise CodexExecTelemetryError("ImageGen evidence cannot share an exec snippet with other JavaScript")
    return arguments


def parse_view_image_tool_source(source: str) -> str | None:
    """Accept only the single awaited view result emitted as an image block."""
    tokens = _tokens(source, allow_unrelated_syntax=True)
    names = [i for i, token in enumerate(tokens) if token.kind == "identifier" and token.value == "view_image"]
    if not names:
        return None
    if len(names) != 1:
        raise CodexExecTelemetryError("one exec snippet cannot contain multiple view_image calls")
    index = names[0]
    expected_prefix = tuple(_Token(kind, value) for kind, value in (
        ("identifier", "image"), ("(", "("), ("(", "("), ("identifier", "await"),
        ("identifier", "tools"), (".", "."), ("identifier", "view_image"),
        ("(", "("), ("{", "{"), ("identifier", "path"), (":", ":"),
    ))
    if index != 6 or tokens[:11] != expected_prefix:
        raise CodexExecTelemetryError("view_image evidence requires one exact awaited image-emission expression")
    if len(tokens) not in {18, 19} or tokens[11].kind != "string":
        raise CodexExecTelemetryError("view_image evidence has an unsupported path or expression shape")
    expected_suffix = tuple(_Token(kind, value) for kind, value in (
        ("}", "}"), (")", ")"), (")", ")"), (".", "."),
        ("identifier", "image_url"), (")", ")"),
    ))
    if tokens[12:18] != expected_suffix or (len(tokens) == 19 and tokens[18:] != (_Token(";", ";"),)):
        raise CodexExecTelemetryError("view_image evidence cannot share an exec snippet with other JavaScript")
    path = tokens[11].value
    if (
        not isinstance(path, str) or not path.startswith("/") or "\\" in path or "\x00" in path
        or path != PurePosixPath(path).as_posix()
        or ".." in PurePosixPath(path).parts or "." in PurePosixPath(path).parts
    ):
        raise CodexExecTelemetryError("view_image argument must be one absolute canonical package path")
    return path


def image_view_event_path(value: Any) -> str:
    """Decode the pinned CLI ImageView ``file://`` URL into one canonical path."""
    if not isinstance(value, str):
        raise CodexExecTelemetryError("ImageView event lacks its exact file URL")
    parsed = urlsplit(value)
    if parsed.scheme != "file" or parsed.netloc or parsed.query or parsed.fragment:
        raise CodexExecTelemetryError("ImageView event path is not a local file URL")
    try:
        path = unquote_to_bytes(parsed.path).decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise CodexExecTelemetryError("ImageView event path is not valid UTF-8") from error
    if (
        not path.startswith("/") or "\\" in path or "\x00" in path
        or path != PurePosixPath(path).as_posix()
        or ".." in PurePosixPath(path).parts or "." in PurePosixPath(path).parts
    ):
        raise CodexExecTelemetryError("ImageView event path is not canonical absolute file data")
    return path


def validate_inline_image_result(output: Any, *, max_bytes: int) -> InlineImageEvidence:
    """Require one complete inline raster image block, never text that claims a view."""
    if not isinstance(output, list):
        raise CodexExecTelemetryError("view_image exec result has no typed content blocks")
    image_blocks = []
    for block in output:
        if not isinstance(block, dict) or block.get("type") not in {"input_text", "input_image"}:
            raise CodexExecTelemetryError("view_image exec result contains an unsupported content block")
        if block["type"] == "input_image":
            image_blocks.append(block)
        else:
            text = block.get("text")
            if not isinstance(text, str):
                raise CodexExecTelemetryError("view_image text result has an unsupported shape")
            if "truncated" in text.lower() or "data:" in text.lower():
                raise CodexExecTelemetryError("view_image exec result is truncated or dumps image data as text")
    if len(image_blocks) != 1:
        raise CodexExecTelemetryError("view_image exec result must contain exactly one input_image block")
    image_url = image_blocks[0].get("image_url")
    if not isinstance(image_url, str) or not image_url.startswith("data:"):
        raise CodexExecTelemetryError("input_image block does not contain inline image bytes")
    header, separator, encoded = image_url[5:].partition(",")
    if not separator or not header.endswith(";base64") or not encoded:
        raise CodexExecTelemetryError("input_image data URL is malformed or truncated")
    mime_type = header[:-7].casefold()
    if mime_type not in {"image/png", "image/jpeg", "image/gif", "image/webp", "application/octet-stream"}:
        raise CodexExecTelemetryError("input_image data URL does not declare a supported raster type")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise CodexExecTelemetryError("input_image base64 is malformed or truncated") from error
    if not data or len(data) > max_bytes:
        raise CodexExecTelemetryError("input_image bytes are empty or exceed the event limit")
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise CodexExecTelemetryError("Pillow is configured to load truncated image data")
    try:
        with io.BytesIO(data) as image_bytes, Image.open(image_bytes) as image:
            width, height = image.size
            pixel_count = width * height
            if (
                width < 1 or height < 1 or pixel_count > MAX_INLINE_IMAGE_PIXELS
                or (Image.MAX_IMAGE_PIXELS is not None and pixel_count > Image.MAX_IMAGE_PIXELS)
            ):
                raise CodexExecTelemetryError("input_image dimensions exceed the frozen reference pixel limit")
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            if image.size != (width, height):
                raise CodexExecTelemetryError("input_image dimensions changed between validation passes")
            image.load()
    except CodexExecTelemetryError:
        raise
    except (
        OSError, SyntaxError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning,
    ) as error:
        raise CodexExecTelemetryError("input_image bytes are not a complete supported raster image") from error
    return InlineImageEvidence(sha256(data).hexdigest(), len(data))
