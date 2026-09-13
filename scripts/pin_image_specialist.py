"""Pin a supported Plotloom image-specialist checkout before ImageGen runs.

The delivery directory is untrusted, but this preflight makes the operating
boundary explicit: a specialist records the exact checkout and repository skill
before generation, and Refresh rejects a completion whose provenance differs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


SUPPORTED_EXECUTION_CONTRACT = "codex_specialist.v2"
SUPPORTED_PREFLIGHT_VERSION = "p1.5-pin.v1"
SUPPORTED_SKILL_VERSION = "plotloom-image-specialist.v3"
SKILL_PATH = Path(".agents/skills/plotloom-image-specialist/SKILL.md")
PINNED_SOURCES = (SKILL_PATH, Path("scripts/cleanup_imagegen_staging.py"), Path("scripts/pin_image_specialist.py"), Path("src/plotloom/image_job_exchange.py"), Path("src/plotloom/image_job_contracts.py"), Path("src/plotloom/persistence.py"))


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _private_directory(path: Path, *, label: str) -> None:
    """Create the specialist's mutable transaction directories as private."""

    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    details = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISDIR(details.st_mode)
        or details.st_uid != os.geteuid()
        or stat.S_IMODE(details.st_mode) & (stat.S_IRWXG | stat.S_IRWXO)
        or (stat.S_IMODE(details.st_mode) & stat.S_IRWXU) != stat.S_IRWXU
    ):
        raise SystemExit(f"Unsupported delivery: {label} must be a private current-user directory.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pin a supported Plotloom image-specialist package before generation.")
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    request_path = package / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    preflight = request.get("specialistPreflight")
    if not isinstance(preflight, dict):
        raise SystemExit("Unsupported package: missing specialistPreflight.")
    if request.get("schemaVersion") != 3 or request.get("packageVersion") != 4:
        raise SystemExit("Unsupported package: expected schema version 3 and package version 4.")
    if preflight.get("version") != SUPPORTED_PREFLIGHT_VERSION or preflight.get("skillVersion") != SUPPORTED_SKILL_VERSION:
        raise SystemExit("Unsupported specialist preflight version or skill version.")
    if request.get("executionContract") != SUPPORTED_EXECUTION_CONTRACT or preflight.get("executionContract") != SUPPORTED_EXECUTION_CONTRACT:
        raise SystemExit(f"Unsupported execution contract: {request.get('executionContract')!r}.")
    skill_version = preflight.get("skillVersion")
    if skill_version != SUPPORTED_SKILL_VERSION:
        raise SystemExit("Unsupported package: unsupported specialist skill version.")
    repository = Path(__file__).resolve().parents[1]
    skill = repository / SKILL_PATH
    if not skill.is_file():
        raise SystemExit("Unsupported checkout: Plotloom image-specialist skill is missing.")
    revision = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
    for source in PINNED_SOURCES:
        if subprocess.call(
            ["git", "-C", str(repository), "cat-file", "-e", f"{revision}:{source.as_posix()}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ) != 0:
            raise SystemExit("Unsupported checkout: pinned specialist source is not committed at HEAD.")
    if subprocess.call(["git", "-C", str(repository), "diff", "--quiet", "HEAD", "--", *(str(item) for item in PINNED_SOURCES)]) != 0:
        raise SystemExit("Unsupported checkout: pinned specialist code or skill has uncommitted changes.")
    pin = {
        "jobId": request["jobId"],
        "requestHash": request["requestHash"],
        "executionContract": SUPPORTED_EXECUTION_CONTRACT,
        "skillVersion": skill_version,
        "codeRevision": revision,
        "skillHash": hashlib.sha256(skill.read_bytes()).hexdigest(),
    }
    delivery = package.parent / "delivery"
    _private_directory(delivery, label="delivery")
    _private_directory(delivery / "outputs", label="delivery outputs")
    target = delivery / "executor-pin.json"
    try:
        with target.open("x", encoding="utf-8") as output:
            output.write(canonical_json(pin))
    except FileExistsError as error:
        raise SystemExit("Executor pin already exists; do not overwrite or re-pin a prepared delivery.") from error
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
