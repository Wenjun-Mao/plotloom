"""Stdlib-only launch contract and observations for the synthetic Python CLI."""
import json
import os
import sys
from pathlib import Path

# Include '#!', '-B' and the newline in a conservative 127-byte limit.
# Direct kernel launch avoids a shell exec racing supervisor command identity.
SHEBANG_MAX_BYTES = 127


def cli_shebang(entrypoint):
    if (not isinstance(entrypoint, str) or not entrypoint
            or not Path(entrypoint).is_absolute() or "\0" in entrypoint
            or any(character.isspace() for character in entrypoint)):
        raise ValueError("fake CLI requires an absolute QA path without NUL or whitespace")
    header = ("#!" + entrypoint + " -B\n").encode("utf-8")
    if len(header) > SHEBANG_MAX_BYTES:
        raise ValueError("fake CLI QA shebang exceeds 127 encoded bytes including delimiters")
    return header


def runtime_facts():
    return {"executable": sys.executable,
        "physicalExecutable": str(Path(sys.executable).resolve(strict=True)),
        "prefix": sys.prefix, "physicalPrefix": str(Path(sys.prefix).resolve(strict=True)),
        "basePrefix": sys.base_prefix,
        "physicalBasePrefix": str(Path(sys.base_prefix).resolve(strict=True)),
        "implementation": sys.implementation.name, "majorMinor": list(sys.version_info[:2]),
        "version": list(sys.version_info[:3]), "dontWriteBytecode": sys.dont_write_bytecode}


def assert_qa_runtime(qa, facts):
    assert facts.get("dontWriteBytecode") is True, facts
    for field in ("physicalExecutable", "physicalBasePrefix", "implementation", "majorMinor"):
        assert facts[field] == qa[field], (field, facts, qa)
    assert facts["executable"] == qa["entrypoint"], facts
    assert facts["physicalPrefix"] == qa["prefix"], facts


def _record(case, stage, facts):
    target = case / "receipts" / f"cli-{stage}-runtime-{os.getpid()}.json"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(json.dumps(facts, sort_keys=True).encode())
        stream.flush()
        os.fsync(stream.fileno())


def observe_startup(executable, arguments):
    case = executable.parent
    invocation = ("sandbox" if arguments[:1] == ["sandbox"] else
        "version" if arguments == ["--version"] else
        "login" if arguments[-2:] == ["login", "status"] else "exec")
    facts = runtime_facts() | {"pid": os.getpid(), "invocation": invocation,
        "wrapper": str(executable), "runtimeSupportImport": str(Path(__file__).resolve())}
    # Preserve startup facts even when a later import/assertion fails.
    _record(case, "startup", facts)
    assert_qa_runtime(json.loads((case / "qa.json").read_bytes()), facts)


def observe_sandbox_imports(case, source, cli_support):
    qa = json.loads((case / "qa.json").read_bytes())
    facts = runtime_facts()
    assert_qa_runtime(qa, facts)
    expected = {
        "plotloom.config": source / "src/plotloom/config.py",
        "plotloom.codex_exec_profile": source / "src/plotloom/codex_exec_profile.py",
        "codex_exec_supervisor_environment": source / "services/creator_workbench/codex_exec_supervisor_environment.py",
        "codex_exec_supervisor_validation": source / "services/creator_workbench/codex_exec_supervisor_validation.py",
    }
    imports = {name: str(Path(sys.modules[name].__file__)) for name in (*expected, "dotenv")}
    for name, path in expected.items():
        assert Path(imports[name]) == path, imports
    assert Path(imports["dotenv"]).resolve(strict=True).is_relative_to(Path(qa["prefix"])), imports
    assert Path(cli_support).resolve() == Path(__file__).with_name("paid_outline_cli_fixture.py").resolve()
    _record(case, "sandbox", facts | {"pid": os.getpid(), "imports": imports,
        "cliSupportImport": str(Path(cli_support).resolve())})
