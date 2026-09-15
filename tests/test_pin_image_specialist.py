"""Regression coverage for the source boundary of the ImageGen preflight."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _git(repository: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _request(package: Path) -> None:
    package.mkdir(parents=True)
    (package / "request.json").write_text(
        json.dumps(
            {
                "schemaVersion": 3,
                "packageVersion": 4,
                "jobId": "ij_1234567890abcdefghij",
                "requestHash": "a" * 64,
                "executionContract": "codex_specialist.v2",
                "specialistPreflight": {
                    "version": "p1.5-pin.v1",
                    "skillVersion": "plotloom-image-specialist.v3",
                    "executionContract": "codex_specialist.v2",
                },
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def modular_checkout(tmp_path: Path) -> tuple[Path, Path]:
    """Create the smallest committed modern layout accepted by the preflight."""

    repository = tmp_path / "checkout"
    repository.mkdir()
    shutil.copytree(ROOT / "scripts", repository / "scripts")
    source_files = {
        ".gitignore": "*.generated.py\n",
        ".agents/skills/plotloom-image-specialist/SKILL.md": "# fixture skill\n",
        "src/plotloom/api/__init__.py": "",
        "src/plotloom/api/project_folder_image_jobs.py": "# image route owner\n",
        "src/plotloom/persistence/__init__.py": "",
        "src/plotloom/persistence/project/media_image_delivery.py": "# delivery owner\n",
        "src/plotloom/image_job_contracts.py": "# image contract owner\n",
        "src/plotloom/image_job_exchange.py": "# exchange owner\n",
    }
    for name, content in source_files.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    _git(repository, "init")
    _git(repository, "config", "user.email", "fixture@example.test")
    _git(repository, "config", "user.name", "Fixture")
    _git(repository, "add", ".")
    _git(repository, "commit", "-m", "modern modular image pin fixture")
    package = repository / "exchange" / "jobs" / "ij_1234567890abcdefghij" / "package"
    _request(package)
    return repository, package


def _run_pin(repository: Path, package: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repository / "scripts" / "pin_image_specialist.py"), "--package", str(package)],
        cwd=repository,
        capture_output=True,
        text=True,
    )


def test_pin_accepts_current_modular_layout_and_preserves_its_provenance(
    modular_checkout: tuple[Path, Path],
) -> None:
    repository, package = modular_checkout
    # An unrelated working note must not become a hidden preflight dependency.
    note = repository / "docs" / "operator-note.md"
    note.parent.mkdir()
    note.write_text("outside the execution boundary\n", encoding="utf-8")

    result = _run_pin(repository, package)

    assert result.returncode == 0, result.stderr
    pin = json.loads((package.parent / "delivery" / "executor-pin.json").read_text())
    assert pin["codeRevision"] == subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()
    assert pin["skillHash"] == sha256(
        (repository / ".agents/skills/plotloom-image-specialist/SKILL.md").read_bytes()
    ).hexdigest()

    repeat = _run_pin(repository, package)
    assert repeat.returncode != 0
    assert "already exists" in repeat.stderr


@pytest.mark.parametrize(
    ("relative_path", "operation"),
    [
        ("src/plotloom/api/project_folder_image_jobs.py", "dirty"),
        ("src/plotloom/persistence/project/media_image_delivery.py", "staged_delete"),
        ("src/plotloom/api/new_image_delivery_guard.py", "untracked"),
        ("src/plotloom/api/new_image_delivery_guard.generated.py", "ignored"),
    ],
)
def test_pin_rejects_all_dirty_modular_execution_sources(
    modular_checkout: tuple[Path, Path], relative_path: str, operation: str
) -> None:
    repository, package = modular_checkout
    path = repository / relative_path
    if operation == "dirty":
        path.write_text("# changed route owner\n", encoding="utf-8")
    elif operation == "staged_delete":
        _git(repository, "rm", relative_path)
    else:
        path.write_text("# new uncommitted guard\n", encoding="utf-8")

    result = _run_pin(repository, package)

    assert result.returncode != 0
    assert "pinned specialist source has uncommitted changes" in result.stderr
    assert json.dumps(relative_path) in result.stderr
    assert not (package.parent / "delivery" / "executor-pin.json").exists()


def test_pin_rejects_a_missing_committed_modular_source(
    modular_checkout: tuple[Path, Path],
) -> None:
    repository, package = modular_checkout
    relative_path = "src/plotloom/image_job_exchange.py"
    _git(repository, "rm", relative_path)
    _git(repository, "commit", "-m", "remove required image exchange source")

    result = _run_pin(repository, package)

    assert result.returncode != 0
    assert "pinned specialist source is not committed at HEAD" in result.stderr
    assert json.dumps(relative_path) in result.stderr
    assert not (package.parent / "delivery" / "executor-pin.json").exists()
