"""Synchronize the explicit wheel validation bundle; never copies runtime data."""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from plotloom.validation_resources import RESOURCE_FILES, RESOURCE_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="copy current owned source bytes")
    parser.add_argument("--check", action="store_true", help="verify without writing (the default)")
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("choose --write or --check")
    bundle = ROOT / "src/plotloom/_validation"
    hashes = {}
    failures = []
    for name in RESOURCE_FILES:
        content = (ROOT / name).read_bytes()
        hashes[name] = sha256(content).hexdigest()
        destination = bundle / name
        if args.write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        elif not destination.is_file() or destination.read_bytes() != content:
            failures.append(name)
    expected = json.dumps({"version": RESOURCE_VERSION, "files": hashes}, sort_keys=True, indent=2) + "\n"
    manifest = bundle / "manifest.json"
    if args.write:
        manifest.write_text(expected, encoding="utf-8")
    elif not manifest.is_file() or manifest.read_text(encoding="utf-8") != expected:
        failures.append("manifest.json")
    actual = {str(path.relative_to(bundle)) for path in bundle.rglob("*") if path.is_file()}
    failures.extend(sorted(actual - set(RESOURCE_FILES) - {"manifest.json"}))
    if failures:
        raise SystemExit("validation bundle differs from current owned source: " + ", ".join(failures))
    print(f"validation resource bundle: {len(RESOURCE_FILES)} exact source files")


if __name__ == "__main__":
    main()
