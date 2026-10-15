"""No-work exact QA child; shared acceptance witness then natural exit."""
from handoff_qa import admit


def main():
    qa = admit("inner")
    import argparse
    import json
    from pathlib import Path

    from handoff_files import publish_record, read_owned, read_record, require
    from handoff_phase import B, load_phase
    from handoff_process import child_tree
    from handoff_receiver import accept_attendance

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-root", required=True)
    parser.add_argument("--phase-sha", required=True)
    args = parser.parse_args()
    phase = load_phase(args.phase_root, args.phase_sha, expected_kind="handoff_proof_only")
    require(phase["authority"] == "provider_free_handoff", "genuine proof authority required")
    root = Path(args.phase_root)
    launch = read_record(root, "launch.json")
    require(launch is not None, "missing committed launch")
    tree = child_tree(launch[0], launch[1], json.loads(read_owned(B / "qa-interpreter.json", private=False)))
    publish_record(root, "driver-process.json", tree)
    _attendance, _witness = accept_attendance(phase, args.phase_sha, launch[0], tree)
    publish_record(root, "proof-result.json", {"version": 2, "phaseSha256": args.phase_sha,
        "handoffOnly": True, "generationDispatches": 0, "productionAuthority": False,
        "providerAuthority": False, "innerQA": qa, "nativeTerminalMustBeObservedByParent": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
