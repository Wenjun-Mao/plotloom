"""Versioned YAML prompt repository with strict Jinja rendering and traces."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import yaml
from jinja2 import Environment, StrictUndefined, TemplateError
from pydantic import BaseModel, ValidationError

from .contracts import PromptMessage, PromptSpec, PromptTrace, RenderedPrompt
from .exceptions import PromptRenderError, PromptSpecError


_PROMPT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


def repository_prompt_root() -> Path:
    """Return the package-owned prompt root without consulting cwd.

    Keeping the templates inside the Python module makes editable source runs
    and installed wheels use the same single source of truth. This is also the
    extraction boundary: moving ``plotloom`` to its future repository
    brings the prompt contracts with it.
    """

    return Path(__file__).resolve().parents[1] / "prompt_templates"


def canonical_json(value: Any) -> str:
    """Serialize trace inputs deterministically.

    Prompt variables must be JSON-shaped. Refusing opaque Python objects keeps
    hashes reproducible across processes instead of silently stringifying them.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _to_json(value: Any) -> str:
    return canonical_json(value)


class PromptRepository:
    """Load immutable prompt specs from a single versioned directory."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else repository_prompt_root()

    def source_path(self, prompt_id: str) -> Path:
        if not _PROMPT_ID_RE.fullmatch(prompt_id):
            raise PromptSpecError(f"Invalid prompt id: {prompt_id!r}")
        return self.root / f"{prompt_id}.yaml"

    def load(self, prompt_id: str) -> tuple[PromptSpec, str, Path]:
        path = self.source_path(prompt_id)
        try:
            raw_source = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise PromptSpecError(f"Prompt spec not found: {path}") from exc
        try:
            raw_spec = yaml.safe_load(raw_source)
        except yaml.YAMLError as exc:
            raise PromptSpecError(f"Prompt YAML is invalid: {path}: {exc}") from exc
        if not isinstance(raw_spec, dict):
            raise PromptSpecError(f"Prompt YAML must contain an object: {path}")
        try:
            spec = PromptSpec.model_validate(raw_spec)
        except ValidationError as exc:
            raise PromptSpecError(
                f"Prompt spec does not satisfy the versioned contract: {path}: {exc}"
            ) from exc
        if spec.id != prompt_id:
            raise PromptSpecError(
                f"Prompt id mismatch: requested {prompt_id!r}, source declares {spec.id!r}"
            )
        return spec, sha256_text(raw_source), path

    def list_ids(self) -> tuple[str, ...]:
        if not self.root.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self.root.glob("*.yaml")))


class PromptRenderer:
    """Render PromptSpec templates using Jinja StrictUndefined."""

    def __init__(self, repository: PromptRepository | None = None) -> None:
        self.repository = repository or PromptRepository()
        self.environment = Environment(
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        self.environment.filters["tojson"] = _to_json

    def render(self, prompt_id: str, variables: Mapping[str, Any]) -> RenderedPrompt:
        spec, spec_hash, source_path = self.repository.load(prompt_id)
        supplied = dict(variables)
        unknown = sorted(set(supplied) - set(spec.variables))
        if unknown:
            raise PromptRenderError(
                f"Prompt {prompt_id!r} received undeclared variables: {', '.join(unknown)}"
            )

        context: dict[str, Any] = {}
        missing: list[str] = []
        for name, variable_spec in spec.variables.items():
            if name in supplied:
                context[name] = supplied[name]
            elif variable_spec.required:
                missing.append(name)
            else:
                context[name] = variable_spec.default
        if missing:
            raise PromptRenderError(
                f"Prompt {prompt_id!r} is missing required variables: {', '.join(sorted(missing))}"
            )

        try:
            system = self.environment.from_string(spec.system).render(**context).strip()
            user = self.environment.from_string(spec.user).render(**context).strip()
        except TemplateError as exc:
            raise PromptRenderError(f"Prompt {prompt_id!r} failed strict rendering: {exc}") from exc
        if not system or not user:
            raise PromptRenderError(f"Prompt {prompt_id!r} rendered an empty message")

        try:
            input_json = canonical_json(context)
        except (TypeError, ValueError) as exc:
            raise PromptRenderError(
                f"Prompt {prompt_id!r} variables are not JSON-serializable: {exc}"
            ) from exc
        messages = (
            PromptMessage(role="system", content=system),
            PromptMessage(role="user", content=user),
        )
        rendered_json = canonical_json([message.model_dump(mode="json") for message in messages])
        trace = PromptTrace(
            prompt_id=spec.id,
            prompt_version=spec.version,
            stage=spec.stage,
            spec_hash=spec_hash,
            input_hash=sha256_text(input_json),
            rendered_hash=sha256_text(rendered_json),
            source=self._trace_source(source_path),
            variable_names=tuple(sorted(context)),
        )
        return RenderedPrompt(messages=messages, output=spec.output, trace=trace)

    def _trace_source(self, source_path: Path) -> str:
        if self.repository.root.resolve() == repository_prompt_root().resolve():
            return f"plotloom/prompt_templates/{source_path.name}"
        return str(source_path.resolve())
