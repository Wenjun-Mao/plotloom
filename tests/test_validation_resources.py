"""Installed readers retain exact validation bytes without inventing a checkout."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from plotloom import validation_resources as resources
from plotloom.art_style import freeze_art_style
from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.cast_style import freeze_cast_style
from plotloom.content_language_contract import freeze_language_candidate
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.language_policy import freeze_request_language
from plotloom.provider_literals import literal_policy_identity
from plotloom.storyboard_brief_style import freeze_storyboard_brief_style

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def installed(tmp_path, monkeypatch):
    package = tmp_path / "site-packages/plotloom"
    shutil.copytree(ROOT / "src/plotloom", package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    monkeypatch.setattr(resources, "_PACKAGE_ROOT", package)
    return package


def test_source_and_installed_fingerprints_and_node_derivation_are_identical(installed):
    direction = "Continuous natural window light"
    brief = freeze_brief_style(direction)
    original = CreativeHandoffRequest(job_id="ch_" + "1" * 32,
        project_id="00000000-0000-4000-8000-000000000001", section_id="story", stage="outline",
        expected_stage_revision=0, source={"title": "The Lamp", "text": "Mara keeps the lamp on."},
        creative_brief="Write the requested stage from the complete sources.")
    freeze_request_language(original, "en-US")
    candidate = {"lang": "en", "summary": "Mara keeps the lamp on."}
    request_file = installed.parent / "language-input.json"
    request_file.write_text(json.dumps({"original": original.model_dump(mode="json", by_alias=True), "candidate": candidate}))
    expected = {"brief": brief, "f5": freeze_storyboard_brief_style(brief),
        "cast": freeze_cast_style("realistic", direction), "art": freeze_art_style("realistic", direction),
        "literal": list(literal_policy_identity()), "language": freeze_language_candidate(original, candidate)}
    probe = """
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import plotloom
assert Path(plotloom.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.storyboard_brief_style import freeze_storyboard_brief_style
from plotloom.cast_style import freeze_cast_style
from plotloom.art_style import freeze_art_style
from plotloom.provider_literals import literal_policy_identity
from plotloom.content_language_contract import freeze_language_candidate
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_execution_pin import current_execution_pin
from plotloom.creative_handoff_contracts import CreativeHandoffError
try:
    current_execution_pin("characters")
except CreativeHandoffError as error:
    assert error.code == "execution_pin_missing"
else:
    raise AssertionError("wheel resources invented native execution authority")
direction="Continuous natural window light"
brief=freeze_brief_style(direction)
data=json.loads(Path(sys.argv[2]).read_text())
print(json.dumps({"brief":brief,"f5":freeze_storyboard_brief_style(brief),
    "cast":freeze_cast_style("realistic",direction),"art":freeze_art_style("realistic",direction),
    "literal":literal_policy_identity(),"language":freeze_language_candidate(
        CreativeHandoffRequest.model_validate(data["original"]),data["candidate"])}))
"""
    result = subprocess.run([sys.executable, "-I", "-c", probe, str(installed.parent), str(request_file)],
        cwd=installed.parent.parent, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize("damage", ["changed", "missing", "escaped", "manifest", "bundle-link", "manifest-link"])
def test_installed_resources_refuse_damage_without_searching_cwd(installed, tmp_path, monkeypatch, damage):
    root = resources.validation_resource_root()
    target = root / "scripts/brief-art-style.mjs"
    if damage == "changed":
        target.write_text("untrusted replacement")
    elif damage == "missing":
        target.unlink()
    elif damage == "escaped":
        outside = tmp_path / "outside.mjs"
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
    elif damage == "manifest":
        (root / "manifest.json").unlink()
    elif damage == "manifest-link":
        manifest = root / "manifest.json"
        outside = tmp_path / "outside-manifest.json"
        outside.write_bytes(manifest.read_bytes())
        manifest.unlink()
        manifest.symlink_to(outside)
    else:
        outside = tmp_path / "outside-bundle"
        root.rename(outside)
        root.symlink_to(outside, target_is_directory=True)
    monkeypatch.chdir(ROOT)
    with pytest.raises((ValueError, FileNotFoundError)):
        resources.validation_resource_root()


def test_source_edits_change_brief_identity_instead_of_using_bundled_bytes(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("")
    package = tmp_path / "src/plotloom"
    package.mkdir(parents=True)
    for name in resources.RESOURCE_FILES:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    monkeypatch.setattr(resources, "_PACKAGE_ROOT", package)
    original = freeze_brief_style("source-owned direction")
    adapter = tmp_path / "scripts/brief-art-style.mjs"
    adapter.write_text(adapter.read_text() + "\n// changed source dependency\n")
    changed = freeze_brief_style("source-owned direction")
    assert changed["validatorHashes"]["artAdapter"] != original["validatorHashes"]["artAdapter"]
    assert changed["contentHash"] != original["contentHash"]


def test_policy_resource_does_not_allow_unowned_paths(installed):
    with pytest.raises(ValueError, match="outside the owned inventory"):
        resources.policy_resource("../credentials")


def test_installed_python_policy_cannot_escape_owning_package(installed, tmp_path):
    policy = installed / "outline_echoes.py"
    outside = tmp_path / "external-policy.py"
    outside.write_bytes(policy.read_bytes())
    policy.unlink()
    policy.symlink_to(outside)
    with pytest.raises(ValueError, match="escaped its owning package"):
        resources.policy_resource("src/plotloom/outline_echoes.py")


def test_generated_bundle_matches_current_checkout():
    subprocess.run([sys.executable, str(ROOT / "scripts/sync_validation_resources.py"), "--check"],
        cwd=ROOT, check=True, capture_output=True)
