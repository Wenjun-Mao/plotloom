"""Owned validation bytes for source readers and relocatable installed readers.

These files are not a checkout or native execution pin. Installed readers never
search the working directory, another repository, or runtime project data.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
RESOURCE_VERSION = "plotloom.validation-resources.v1"
RESOURCE_FILES = (
    "scripts/art-style.mjs",
    "scripts/brief-art-style.mjs",
    "scripts/brief-cast-style.mjs",
    "scripts/brief-storyboard-style.mjs",
    "scripts/cast-style.mjs",
    "scripts/provider-literal-context.mjs",
    "scripts/storyboard-dialogue-timing.mjs",
    "third_party/shuohao-skills/LICENSE",
    "third_party/shuohao-skills/NOTICE",
    "third_party/shuohao-skills/skills/novel-art/scripts/gate-summary.mjs",
    "third_party/shuohao-skills/skills/novel-art/scripts/novel-art.mjs",
    "third_party/shuohao-skills/skills/novel-art/scripts/provider-literals.mjs",
    "third_party/shuohao-skills/skills/novel-art/scripts/report-language.mjs",
    "third_party/shuohao-skills/skills/novel-characters/scripts/novel-characters.mjs",
    "third_party/shuohao-skills/skills/novel-characters/scripts/provider-literals.mjs",
    "third_party/shuohao-skills/skills/novel-characters/scripts/report-language.mjs",
    "third_party/shuohao-skills/skills/novel-storyboard/scripts/dialogue-timing.mjs",
    "third_party/shuohao-skills/skills/novel-storyboard/scripts/gate-summary.mjs",
    "third_party/shuohao-skills/skills/novel-storyboard/scripts/novel-storyboard.mjs",
    "third_party/shuohao-skills/skills/novel-storyboard/scripts/provider-literals.mjs",
    "third_party/shuohao-skills/skills/novel-storyboard/scripts/report-language.mjs",
)
_PYTHON_POLICIES = frozenset(
    "src/plotloom/" + name for name in (
        "content_language_contract.py", "content_language_schema.py", "content_language_classifier.py",
        "language_policy.py", "codex_exec_profile.py", "codex_exec_prompts.py", "outline_echoes.py",
        "creative_field_ownership.py", "dialogue_timing_policy.py", "art_structure.py",
        "autopilot_brief_style.py", "content_language_presentation.py", "production_presentation.py",
        "native_bridge_presentation_contract.py", "validation_resources.py",
        "provider_literals.py", "provider_literal_dialogue.py", "provider_literal_review.py",
        "provider_literal_preparation.py", "provider_literal_discovery.py",
    )
)


def _checkout_root() -> Path | None:
    root = _PACKAGE_ROOT.parents[1]
    if _PACKAGE_ROOT == root / "src" / "plotloom" and (root / "pyproject.toml").is_file():
        return root
    return None


def validation_resource_root() -> Path:
    """Use actual source bytes in a checkout, verified owned bytes in a wheel."""
    source = _checkout_root()
    if source is not None:
        return source
    root = _PACKAGE_ROOT / "_validation"
    manifest_path = root / "manifest.json"
    if root.is_symlink() or not manifest_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("packaged validation resources must remain in their owning package")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = manifest.get("files", {})
    if manifest.get("version") != RESOURCE_VERSION or set(hashes) != set(RESOURCE_FILES):
        raise ValueError("packaged validation resource inventory is invalid")
    actual = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
    if actual != set(RESOURCE_FILES) | {"manifest.json"}:
        raise ValueError("packaged validation resource inventory differs from the manifest")
    for name in RESOURCE_FILES:
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or sha256(path.read_bytes()).hexdigest() != hashes[name]:
            raise ValueError(f"packaged validation resource integrity failed: {name}")
    return root


def policy_resource(name: str) -> Path:
    """Resolve only the literal policy's existing logical fingerprint members."""
    if name in _PYTHON_POLICIES:
        path = _PACKAGE_ROOT / Path(name).name
        if not path.resolve().is_relative_to(_PACKAGE_ROOT.resolve()):
            raise ValueError("Python validation policy escaped its owning package")
        return path
    if name not in RESOURCE_FILES:
        raise ValueError("validation resource is outside the owned inventory")
    return validation_resource_root() / name
