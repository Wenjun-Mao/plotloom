"""Stable test-only Popen anchor, captured before the requested command starts."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4


def exclusive(path, value):
    # ready/go are read by another process as soon as their name appears.
    # Publish complete bytes atomically; existence must never expose partial JSON.
    pending = path.with_name(path.name + ".pending")
    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, path)
    pending.unlink()
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def prepare_guard(root, command):
    parent = root / "process-commands"
    parent.mkdir(mode=0o700, exist_ok=True)
    directory = parent / uuid4().hex
    directory.mkdir(mode=0o700)
    exclusive(directory / "command.json", [os.fspath(value) for value in command])
    return directory, [sys.executable, "-B", str(Path(__file__).resolve()), str(directory), str(root)]


def release_guard(directory, process, *, identify, remember, timeout):
    until = time.monotonic() + min(timeout, 10)
    while not (directory / "ready.json").exists():
        if process.poll() is not None or time.monotonic() >= until:
            raise RuntimeError("owned command guard did not establish its identity")
        time.sleep(0.01)
    announced = json.loads((directory / "ready.json").read_bytes())
    actual = identify(process.pid)
    if announced != actual or announced["pid"] != process.pid:
        raise RuntimeError("owned command guard identity did not match actual Popen")
    remember(actual)
    exclusive(directory / "go.json", {"pid": process.pid, "birth": actual["birth"]})


def target_returncode(directory, process):
    terminal = json.loads((directory / "terminal.json").read_bytes())
    code = terminal["exitCode"]
    if type(code) is not int or process.returncode != (code if code >= 0 else 128 - code):
        raise RuntimeError("owned command guard terminal differs from actual child exit")
    return code


def main():
    # Imports occur inside main so the parent can use preparation helpers without
    # a circular lifecycle import or launching any command.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.paid_outline_processes import journal_spawn, process_identity

    directory, root = map(Path, sys.argv[1:])
    command = json.loads((directory / "command.json").read_bytes())
    identity = process_identity(os.getpid())
    if identity is None:
        raise RuntimeError("owned guard has no live process identity")
    exclusive(directory / "ready.json", identity)
    until = time.monotonic() + 10
    while not (directory / "go.json").exists():
        if time.monotonic() >= until:
            raise RuntimeError("owned guard was never released")
        time.sleep(0.01)
    if json.loads((directory / "go.json").read_bytes()) != {"pid": os.getpid(), "birth": identity["birth"]}:
        raise RuntimeError("owned guard release identity differs")
    # Keep the direct command unreaped until its birth/command has been observed.
    # A rapid exit remains observable as this parent's zombie, not a reused PID.
    child = subprocess.Popen(command)
    journal_spawn(root, child.pid, new_session=False)
    code = child.wait()
    exclusive(directory / "terminal.json", {"pid": child.pid, "exitCode": code})
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    raise SystemExit(main())
