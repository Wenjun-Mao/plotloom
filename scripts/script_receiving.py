"""Fixed opted-in F4 receiver; upstream report bytes remain unchanged."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "src"))

from plotloom.script_receiving import ScriptAdmission, upstream_timing_stats, validate_script_receiving


def _absolute_file(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("script receiving requires absolute frozen regular files")
    return path.resolve(strict=True)


def _pinned_node() -> str:
    raw = os.environ.get("PLOTLOOM_NODE")
    if not raw:
        raise ValueError("script receiving requires explicitly pinned PLOTLOOM_NODE")
    path = _absolute_file(raw)
    if str(path) != raw or not os.access(path, os.X_OK):
        raise ValueError("script receiving Node identity is not a physical executable")
    return str(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("candidate")
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        candidate, request_path = _absolute_file(args.candidate), _absolute_file(args.request)
        request = json.loads(request_path.read_bytes())
        if request.get("stage") != "script":
            raise ValueError("script receiving requires a frozen Script request")
        artifacts = request["inputArtifacts"]
        admission = ScriptAdmission.model_validate(artifacts["script-admission.json"])
        if admission.planned_storyboard_dialogue is None:
            raise ValueError("opted-in script receiving requires its planned storyboard dialogue requirement")
        inputs = request_path.parent / "inputs"
        for name, value in artifacts.items():
            if Path(name).name != name or json.loads(_absolute_file(str(inputs / name)).read_bytes()) != value:
                raise ValueError("script receiving frozen input differs from its request")
        node = _pinned_node()
        upstream = SOURCE / "third_party/shuohao-skills/skills/novel-script/scripts/novel-script.mjs"
        common = [str(candidate), "--outline", str(inputs / "outline.json"), "--art", str(inputs / "art.json")]
        typed = request.get("contentValidationContract") == "plotloom.typed-content-result.v1"
        checked = subprocess.run(
            [node, str(SOURCE / "scripts/script-content-validation.mjs"), str(candidate), str(request_path)]
            if typed and args.command == "validate" else [node, str(upstream), "validate", *common],
            capture_output=True, check=False)
        if typed and args.command == "validate" and checked.returncode == 42:
            sys.stdout.buffer.write(checked.stdout)
            return 42
        if checked.returncode:
            raise ValueError((checked.stderr or checked.stdout).decode("utf-8", "replace").strip())
        stats = upstream_timing_stats(candidate, upstream, node=node)
        validate_script_receiving(json.loads(candidate.read_bytes()), admission, stats)
        if args.command == "validate":
            sys.stdout.buffer.write(checked.stdout)
        else:
            # Upstream validation chatter is captured above, never report stdout.
            rendered = subprocess.run([node, str(upstream), "render", *common, "--html", "--cast", str(inputs / "cast.json")],
                capture_output=True, check=False)
            if rendered.returncode:
                raise ValueError((rendered.stderr or rendered.stdout).decode("utf-8", "replace").strip())
            sys.stdout.buffer.write(rendered.stdout)
        return 0
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
