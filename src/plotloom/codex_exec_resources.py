"""Source-checkout resources available to a frozen Codex Exec handoff."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path


class CodexExecResourceError(ValueError):
    """The frozen package cannot be served from its pinned source resources."""


@dataclass(frozen=True)
class _StageResources:
    upstream_skill_path: str
    specialist_skill_path: str
    upstream_read_path: str
    validator_paths: tuple[str, ...] = ()
    python_project: bool = False
    submodule_stage_path: str | None = None


@dataclass(frozen=True)
class CodexExecSourceResources:
    read_paths: tuple[Path, ...]
    tools: tuple[tuple[str, Path], ...]
    python_environment: Path | None = None
    python_environment_hash: str | None = None
    python_source_hash: str | None = None


def _symlink_alias_chain(path: Path) -> tuple[tuple[Path, str], ...]:
    """Return every symlink component without collapsing an intermediate alias."""
    pending = list(Path(os.path.abspath(path)).parts[1:])
    prefix = Path(Path(path).anchor)
    aliases = []
    traversals = 0
    while pending:
        part, *pending = pending
        candidate = prefix / part
        if candidate.is_symlink():
            traversals += 1
            if traversals > 32:
                raise CodexExecResourceError("validator runtime symlink chain is too deep")
            target = candidate.readlink()
            aliases.append((candidate, str(target)))
            expanded = target if target.is_absolute() else candidate.parent / target
            prefix = Path(os.path.normpath(str(expanded)))
            pending = list(prefix.parts[1:]) + pending
            prefix = Path(prefix.anchor)
        else:
            prefix = candidate
    return tuple(aliases)


_STAGES = {
    "video-directions": _StageResources(
        "docs/creative-workflow/native-video-directions.md",
        ".agents/skills/plotloom-video-directions-specialist/SKILL.md",
        "docs/creative-workflow/native-video-directions.md",
        ("scripts/video_directions.py",), python_project=True,
    ),
    "outline": _StageResources(
        "third_party/shuohao-skills/skills/novel-outline/SKILL.md",
        ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
        "third_party/shuohao-skills/skills/novel-outline",
        submodule_stage_path="skills/novel-outline",
    ),
    "branches": _StageResources(
        "third_party/shuohao-skills/skills/novel-outline/SKILL.md",
        ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
        "third_party/shuohao-skills/skills/novel-outline",
        ("scripts/branch_suggestion.py",),
        python_project=True,
        submodule_stage_path="skills/novel-outline",
    ),
    "characters": _StageResources(
        "third_party/shuohao-skills/skills/novel-characters/SKILL.md",
        ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
        "third_party/shuohao-skills/skills/novel-characters",
        ("scripts/cast-style.mjs",),
        submodule_stage_path="skills/novel-characters",
    ),
    "art": _StageResources(
        "third_party/shuohao-skills/skills/novel-art/SKILL.md",
        ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
        "third_party/shuohao-skills/skills/novel-art",
        ("scripts/art-style.mjs",),
        submodule_stage_path="skills/novel-art",
    ),
    "script": _StageResources(
        "third_party/shuohao-skills/skills/novel-script/SKILL.md",
        ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
        "third_party/shuohao-skills/skills/novel-script",
        submodule_stage_path="skills/novel-script",
    ),
    "storyboard": _StageResources(
        "third_party/shuohao-skills/skills/novel-storyboard/SKILL.md",
        ".agents/skills/plotloom-shuohao-specialist/SKILL.md",
        "third_party/shuohao-skills/skills/novel-storyboard",
        submodule_stage_path="skills/novel-storyboard",
    ),
    "bridge-intent": _StageResources(
        "docs/creative-workflow/native-bridge-intent.md",
        ".agents/skills/plotloom-intent-specialist/SKILL.md",
        "docs/creative-workflow/native-bridge-intent.md",
        ("scripts/native_bridge_intent.py",),
        python_project=True,
    ),
    "bridge-presentation": _StageResources(
        "docs/creative-workflow/native-bridge-presentation.md",
        ".agents/skills/plotloom-presentation-specialist/SKILL.md",
        "docs/creative-workflow/native-bridge-presentation.md",
        ("scripts/native_bridge_presentation.py",),
        python_project=True,
    ),
}


def upstream_skill_path_for_stage(stage: str) -> str:
    try:
        return _STAGES[stage].upstream_skill_path
    except KeyError as error:
        raise CodexExecResourceError("Codex Exec package has an unsupported creative stage") from error


def _source_path(source_root: Path, relative: str) -> Path:
    path = source_root / relative
    if path.is_symlink() or not path.exists():
        raise CodexExecResourceError(f"pinned Codex Exec source resource is unavailable: {relative}")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(source_root):
        raise CodexExecResourceError(f"pinned Codex Exec source resource escapes its checkout: {relative}")
    if not (resolved.is_file() or resolved.is_dir()):
        raise CodexExecResourceError(f"pinned Codex Exec source resource is not a file or directory: {relative}")
    return resolved


def _git_value(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if result.returncode != 0 or result.stderr:
        raise CodexExecResourceError("pinned Codex Exec source revision is unavailable")
    return result.stdout.strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tool_identity(name: str, executable: Path | None) -> dict[str, object]:
    if executable is None:
        return {"name": name, "path": None, "version": None, "sha256": None}
    resolved = executable.resolve(strict=True)
    if not resolved.is_file() or not resolved.stat().st_mode & 0o111:
        raise CodexExecResourceError(f"required validator runtime is not executable: {name}")
    result = subprocess.run(
        [str(resolved), "--version"],
        capture_output=True,
        timeout=5,
        check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    if result.returncode != 0 or result.stderr:
        raise CodexExecResourceError(f"required validator runtime has no version identity: {name}")
    try:
        version = result.stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as error:
        raise CodexExecResourceError(f"required validator runtime has an invalid version identity: {name}") from error
    return {
        "name": name,
        "path": str(resolved),
        "aliases": [
            {"path": str(path), "target": target}
            for path, target in _symlink_alias_chain(executable)
        ],
        "version": version,
        "sha256": _sha256_file(resolved),
    }


def validator_toolchain_hash(source_root: Path) -> str:
    """Bind locally available validator runtimes into the profile identity."""
    from .codex_exec_python_environment import inspect_checked_python_environment

    uv = shutil.which("uv")
    node = shutil.which("node")
    if uv is None or node is None:
        raise CodexExecResourceError("the pinned validator toolchain requires uv and Node")
    environment = inspect_checked_python_environment(source_root)
    entries = [
        _tool_identity("uv", Path(uv)),
        _tool_identity("node", Path(node)),
        _tool_identity("python", environment.interpreter),
        {"checkedPythonEnvironment": environment.identity_hash},
    ]
    encoded = json.dumps(entries, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _required_tool_paths(plan: _StageResources, environment=None, *, include_node=False) -> tuple[tuple[str, Path], ...]:
    tool_names = ("uv", "python") if plan.python_project else ("node",)
    if plan.python_project and include_node:
        tool_names += ("node",)
    tools = []
    for name in tool_names:
        if name == "python":
            raw_path = environment.interpreter
        else:
            discovered = shutil.which(name)
            raw_path = Path(discovered) if discovered else None
        if raw_path is None or not raw_path.exists():
            raise CodexExecResourceError(f"required validator runtime is unavailable: {name}")
        resolved = raw_path.resolve(strict=True)
        if not resolved.is_file() or not resolved.stat().st_mode & 0o111:
            raise CodexExecResourceError(f"required validator runtime is not executable: {name}")
        tools.append((name, resolved))
    return tuple(tools)


def codex_exec_source_resources(source_root: Path, package_request: dict) -> CodexExecSourceResources:
    """Validate exact pinned stage resources and return their read-only roots and tools."""
    from .codex_exec_stage_routing import codex_exec_saved_brief_route

    root = source_root.expanduser().resolve(strict=True)
    stage = package_request.get("stage")
    try:
        plan = _STAGES[stage]
    except (KeyError, TypeError) as error:
        raise CodexExecResourceError("Codex Exec package has an unsupported creative stage") from error
    if package_request.get("upstreamSkillPath") != plan.upstream_skill_path:
        raise CodexExecResourceError("frozen upstream skill path does not match its creative stage")
    pin = package_request.get("executionPin")
    if not isinstance(pin, dict) or set(pin) != {"upstreamRevision", "upstreamSkillHash", "specialistSkillHash"}:
        raise CodexExecResourceError("frozen Codex Exec source pin is malformed")
    if (
        not all(isinstance(pin.get(key), str) for key in pin)
        or not 7 <= len(pin["upstreamRevision"]) <= 64
        or any(character not in "0123456789abcdef" for character in pin["upstreamRevision"])
        or any(
            len(pin[key]) != 64 or any(character not in "0123456789abcdef" for character in pin[key])
            for key in ("upstreamSkillHash", "specialistSkillHash")
        )
    ):
        raise CodexExecResourceError("frozen Codex Exec source pin is malformed")

    skill = _source_path(root, plan.upstream_skill_path)
    if not skill.is_file():
        raise CodexExecResourceError("frozen upstream skill must resolve to one regular source file")
    if hashlib.sha256(skill.read_bytes()).hexdigest() != pin["upstreamSkillHash"]:
        raise CodexExecResourceError("frozen upstream skill bytes no longer match the package pin")
    specialist_skill = _source_path(root, plan.specialist_skill_path)
    if not specialist_skill.is_file() or hashlib.sha256(specialist_skill.read_bytes()).hexdigest() != pin["specialistSkillHash"]:
        raise CodexExecResourceError("frozen Plotloom specialist instructions no longer match the package pin")

    if plan.submodule_stage_path is not None:
        submodule = _source_path(root, "third_party/shuohao-skills")
        revision = _git_value(submodule, "rev-parse", "HEAD")
        changed = _git_value(submodule, "status", "--porcelain", "--untracked-files=all", "--", plan.submodule_stage_path)
        if revision != pin["upstreamRevision"] or changed:
            raise CodexExecResourceError("pinned Shuohao stage resources differ from the frozen package")
    else:
        revision = _git_value(root, "rev-parse", "HEAD")
        if revision != pin["upstreamRevision"]:
            raise CodexExecResourceError("pinned native contract revision differs from the frozen package")

    try:
        saved_brief_route = codex_exec_saved_brief_route(stage, package_request)
    except (TypeError, ValueError) as error:
        raise CodexExecResourceError("frozen saved-Brief contract does not match its source policy") from error
    planned_script = False
    if stage == "script":
        from .script_dialogue_compatibility import assert_current_planned_dialogue, planned_dialogue_from_admission
        planned = planned_dialogue_from_admission(package_request.get("inputArtifacts", {}).get("script-admission.json"))
        if planned is not None:
            assert_current_planned_dialogue(planned)
            planned_script = True
            plan = replace(plan, python_project=True, validator_paths=("scripts/script_receiving.py",))
    marked_art = False
    if stage == "art":
        from .art_structure import marked_art_structure
        marked_art = marked_art_structure(package_request.get("inputArtifacts", {}))
        if marked_art:
            plan = replace(plan, python_project=True)
    validator_paths = saved_brief_route.source_paths if saved_brief_route else plan.validator_paths
    relative_paths = [plan.upstream_read_path, *validator_paths]
    if stage in {"outline", "characters", "art"} and package_request.get("contentValidationContract") is not None:
        relative_paths.append("scripts/text-content-validation.mjs")
    if stage == "script" and package_request.get("contentValidationContract") is not None:
        relative_paths.append("scripts/script-content-validation.mjs")
    if stage == "storyboard":
        relative_paths.append("scripts/storyboard-dialogue-timing.mjs")
        if package_request.get("contentValidationContract") is not None:
            relative_paths.append("scripts/storyboard-content-validation.mjs")
        if saved_brief_route is None:
            relative_paths.append("scripts/storyboard-receiving.mjs")
    if marked_art:
        relative_paths.append("scripts/art_content_validation.py")
        if saved_brief_route:
            relative_paths.extend(("scripts/brief-cast-style.mjs",
                "third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs"))
    environment = None
    source_hash = None
    if plan.python_project:
        from .codex_exec_python_environment import inspect_checked_python_environment
        from .codex_exec_runtime_tree import python_source_identity

        environment = inspect_checked_python_environment(root)
        _source_parent, source_hash = python_source_identity(root)
        relative_paths.extend(("src", "pyproject.toml", "uv.lock"))
    paths = list(dict.fromkeys(_source_path(root, relative) for relative in relative_paths))
    tools = _required_tool_paths(plan, environment, include_node=planned_script or marked_art)
    for name, executable in tools:
        if name == "uv":
            paths.append(executable)
        elif name == "node":
            # Node loads its standard libraries beside the pinned binary.
            paths.append(executable.parent.parent.resolve(strict=True))
        else:
            paths.extend((environment.root, environment.runtime_root))
    return CodexExecSourceResources(
        tuple(dict.fromkeys(paths)), tools,
        environment.root if environment else None,
        environment.identity_hash if environment else None,
        source_hash,
    )


def codex_exec_source_read_paths(source_root: Path, package_request: dict) -> tuple[Path, ...]:
    """Compatibility projection for callers that need only the filesystem roots."""
    return codex_exec_source_resources(source_root, package_request).read_paths


def codex_exec_image_resources(source_root: Path, package_request: dict) -> CodexExecSourceResources:
    """Grant only the image skill whose bytes and revision the package froze."""
    root = source_root.expanduser().resolve(strict=True)
    pin = package_request.get("specialistPreflight")
    if (
        package_request.get("packageVersion") != 8
        or package_request.get("executorBackend") != "codex_exec"
        or package_request.get("executionContract") != "codex_exec.v1"
        or not isinstance(pin, dict)
        or pin.get("version") != "p1.5-pin.v2"
        or pin.get("skillVersion") != "plotloom-image-specialist.v4"
        or pin.get("executionContract") != "codex_exec.v1"
        or pin.get("codeRevision") != _git_value(root, "rev-parse", "HEAD")
    ):
        raise CodexExecResourceError("Codex Exec image instructions require the current frozen source contract")
    skill = _source_path(root, ".agents/skills/plotloom-image-specialist/SKILL.md")
    if not skill.is_file() or _sha256_file(skill) != pin.get("skillHash"):
        raise CodexExecResourceError("frozen Plotloom image instructions no longer match the package pin")
    return CodexExecSourceResources((skill,), ())
