"""Shared fixed-registry original process and checked-QA receiver launch."""


def launch(kind, qa):
    import argparse
    import os
    import shutil
    import sys
    import tempfile
    import time
    from pathlib import Path

    from handoff_files import canonical, digest, publish_record, read_record, require
    from handoff_phase import RECEIVERS, REGISTRY, B, R, load_phase, validate_intent
    from handoff_process import current

    require(kind in REGISTRY and kind in RECEIVERS, "unregistered fixed launcher/receiver")
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase-root", required=True)
    parser.add_argument("--phase-sha", required=True)
    args = parser.parse_args()
    refused = ("PYTHONPATH", "UV_PROJECT_ENVIRONMENT", "UV_PYTHON", "UV_PROJECT", "UV_WORKING_DIRECTORY")
    require(not any(os.environ.get(key) for key in refused), "ambient interpreter/root overrides refused")
    sys.path.insert(0, str(R / "src"))
    phase = load_phase(args.phase_root, args.phase_sha, expected_kind=kind)
    authority = {'paid_outline':'paid_outline_once','qualification_pair':'qualification_pair_once'}.get(kind,'provider_free_handoff')
    require(phase["authority"] == authority, "wrong registered launcher authority")
    root = Path(args.phase_root)
    intent = read_record(root, "invocation-intent.json")
    require(intent is not None, "missing committed invocation intent")
    validate_intent(intent[0], phase, args.phase_sha)
    argv = [qa["executable"], "-B", str(B / REGISTRY[kind]),
        "--phase-root", str(root), "--phase-sha", args.phase_sha]
    require(intent[0]["argvSha256"] == digest(canonical(argv)), "invocation command changed")
    require({p.name for p in root.iterdir()} == {"phase.json", "invocation-intent.json",
        "invocation-intent.json.ready-" + intent[1]}, "runtime already launched or contaminated")
    uv = shutil.which("uv")
    require(uv == "/opt/homebrew/bin/uv", "normal pinned uv entrypoint required")
    prefix = {'paid_outline':'plotloom-outline-paid-transport-','qualification_pair':'plotloom-pair-transport-'}.get(kind,'plotloom-outline-handoff-proof-')
    temp = Path(tempfile.mkdtemp(prefix=prefix, dir="/private/tmp"))
    temp.chmod(0o700)
    for name in ("tmp", "cache", "uv-cache", "pycache"):
        (temp / name).mkdir(mode=0o700)
    info = temp.lstat()
    marker = publish_record(temp, "owner.json", {"purpose": authority + "_transport",
        "phaseSha256": args.phase_sha, "allocationSha256": phase["allocationSha256"],
        "device": info.st_dev, "inode": info.st_ino, "uid": info.st_uid})
    try:
        os.setsid()
    except PermissionError:
        require(os.getpid() == os.getpgrp(), "original native process group unavailable")
    parent = current()
    exec_argv = [uv, "run", "--locked", "--no-sync", "python", "-B", str(B / RECEIVERS[kind]),
        "--phase-root", str(root), "--phase-sha", args.phase_sha]
    value = {**parent, "phaseSha256": args.phase_sha, "intentSha256": intent[1],
        "startedMonotonicNs": str(time.monotonic_ns()), "startedWallMs": time.time_ns() // 1_000_000,
        "execArgv": exec_argv, "outerQA": qa, "ownedTemporaryRoot": str(temp),
        "temporaryRootIdentity": [info.st_dev, info.st_ino, info.st_uid], "ownerMarkerSha256": marker}
    publish_record(root, "launch.json", value)
    fd = os.open(root / "driver.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    os.close(fd)
    env = os.environ | {"TMPDIR": str(temp / "tmp"), "UV_CACHE_DIR": str(temp / "uv-cache"),
        "XDG_CACHE_HOME": str(temp / "cache"), "PYTHONPYCACHEPREFIX": str(temp / "pycache"),
        "PYTHONDONTWRITEBYTECODE": "1"}
    os.chdir(R)
    os.execvpe(uv, exec_argv, env)
