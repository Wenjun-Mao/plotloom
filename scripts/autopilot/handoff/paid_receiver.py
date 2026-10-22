"""Registered checked-QA child: real attendance, exact paid execution, HOLD."""
from handoff_qa import admit


def main(argv=None):
    admit("inner")
    import argparse
    import json
    import sys
    from pathlib import Path

    from handoff_files import publish_record, read_owned, read_record, require
    from handoff_phase import B, R, load_phase
    from handoff_process import child_tree

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-root", required=True)
    parser.add_argument("--phase-sha", required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(R / "src"))
    phase = load_phase(args.phase_root, args.phase_sha, expected_kind="paid_outline")
    root = Path(args.phase_root)
    launch = read_record(root, "launch.json")
    require(launch is not None, "missing committed paid transport launch")
    tree = child_tree(launch[0], launch[1], json.loads(read_owned(B / "qa-interpreter.json")))
    publish_record(root, "driver-process.json", tree)
    from paid_outline_run import run_paid_outline
    result = run_paid_outline(phase, args.phase_sha, launch[0], tree,
        json.loads(read_owned(B / "qa-interpreter.json")))
    return 0 if result.get("held") else 1


if __name__ == "__main__":
    raise SystemExit(main())
