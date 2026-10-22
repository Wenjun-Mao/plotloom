"""Disposable source/CLI fixtures; no operator allocation or real provider."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

from tests.cli_handoff_fixtures import (
    ROOT,
    ReadOnlyLoader,
    builder,
    current_test_qa,
    exclusive,
    private_directory,
)
from tests.codex_exec_platform_fixtures import provider_free_host_runtime
from tests.codex_exec_runtime_fixtures import (
    CLI_FIXTURE_VERSION,
    build_codex_exec_test_source,
)
from tests.paid_outline_cli_runtime import cli_shebang
from tests.paid_outline_processes import owned_processes

NATIVE_FIXTURE = ROOT / "tests/paid_outline_native_fixture.py"
CAPSULE_FIXTURE = ROOT / "tests/paid_outline_capsule_fixture.mjs"

@pytest.fixture(scope="session", name="paid_source")
def paid_source(tmp_path_factory):
    """Commit only the disposable copied fixture, never the task checkout."""
    ownership = tmp_path_factory.mktemp("paid-source-processes").resolve()
    ownership.chmod(0o700)
    with owned_processes(ownership) as processes:
        source = build_codex_exec_test_source(tmp_path_factory, run=processes.run)
        for name in builder.INPUT_FILES:
            target = source / "scripts/autopilot/handoff" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(builder.SOURCE / name, target)
        shutil.copyfile(ROOT / "scripts/autopilot/handoff_bundle.py", source / "scripts/autopilot/handoff_bundle.py")
        _commit_fixture(source, processes)
    return source


def _commit_fixture(source, processes):
    """Create the independent fixture revision required by ADR 0178.

    Paid and generic fixture HEADs must differ even when copied source bytes
    match. An intentional empty snapshot preserves that identity contract.
    """
    environment = os.environ | {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Synthetic fixture", "GIT_COMMITTER_NAME": "Synthetic fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
    processes.run(["git", "-C", str(source), "add", "--", "src/plotloom", "services", "scripts", ".agents", "pyproject.toml", "uv.lock"],
        env=environment, check=True, capture_output=True, timeout=15)
    processes.run(["git", "-C", str(source), "-c", "commit.gpgsign=false", "commit", "--allow-empty", "--quiet", "-m", "Synthetic paid Outline source fixture"],
        env=environment, check=True, capture_output=True, timeout=15)


@pytest.fixture(name="paid_case")
def paid_case(tmp_path, paid_source):
    tmp_path.chmod(0o700)
    with owned_processes(tmp_path.resolve()) as processes:
        yield make_case(tmp_path, paid_source, processes)


@pytest.fixture(scope="module", name="paid_schema_case")
def paid_schema_case(tmp_path_factory, paid_source):
    root = tmp_path_factory.mktemp("paid-schema").resolve()
    root.chmod(0o700)
    with owned_processes(root) as processes:
        yield make_case(root, paid_source, processes)


def make_case(tmp_path, paid_source, processes):
    tmp_path = tmp_path.resolve()
    tmp_path.chmod(0o700)
    qa = json.loads(current_test_qa())
    shebang = cli_shebang(qa["entrypoint"])
    exclusive(tmp_path / "fixture-owner.json", builder.canonical({"syntheticEvidence": True,
        "qualification": False, "purpose": "source-unit-only"}))
    for name in ("data", "bundle", "phase", "auth-home"):
        private_directory(tmp_path / name)
    qa["projectRoot"] = str(paid_source)
    exclusive(tmp_path / "qa.json", builder.canonical(qa))
    executable = tmp_path / "fake-codex"
    wrapper = ("import sys\nfrom pathlib import Path\n"
        + "sys.path.insert(0, " + repr(str(ROOT)) + ")\n"
        + "from tests.paid_outline_cli_runtime import observe_startup\n"
        + "observe_startup(Path(__file__).resolve(), sys.argv[1:])\n"
        + "from tests.paid_outline_cli_fixture import main\n"
        + "raise SystemExit(main(Path(__file__).resolve(), sys.argv[1:], " + repr(CLI_FIXTURE_VERSION) + "))\n")
    exclusive(executable, shebang + wrapper.encode())
    executable.chmod(0o700)
    example = paid_source / "third_party/shuohao-skills/skills/novel-outline/examples/渡口-outline.json"
    exclusive(tmp_path / "provider-output.json", example.read_bytes())
    provider_free_host_runtime(tmp_path / "provider-free-host", paid_source)
    context = {"root": tmp_path, "source": paid_source, "qa": qa, "executable": executable, "processes": processes,
        "environment": os.environ | {"CODEX_HOME": str(tmp_path / "auth-home"), "PYTHONDONTWRITEBYTECODE": "1"}}
    _native(context, ["prepare"])
    context["allocation"] = json.loads((tmp_path / "bundle/paid-allocation.json").read_bytes())
    context["packet"] = json.loads((tmp_path / "transport.json").read_bytes())
    return context


def _native(case, action):
    command = [sys.executable, "-B", str(NATIVE_FIXTURE), *action,
        "--case-root", str(case["root"]), "--source-root", str(case["source"])]
    label = "-".join(action).replace("/", "_")
    log = case["root"] / "receipts" / (label + ".log")
    exclusive(log, b"")
    with log.open("wb") as output:
        result = case["processes"].run(command, cwd=ROOT, env=case["environment"], stdout=output,
            stderr=subprocess.STDOUT, timeout=45, check=False)
    if result.returncode != 0:
        raise AssertionError(log.read_text())
    return result


def run_capsule(case, *, mode="success"):
    command = [shutil.which("node"), str(CAPSULE_FIXTURE), str(case["root"]), sys.executable,
        str(NATIVE_FIXTURE), str(case["source"]), mode]
    log = case["root"] / "receipts" / ("capsule-" + mode + ".log")
    exclusive(log, b"")
    with log.open("wb") as output:
        result = case["processes"].run(command, cwd=ROOT, env=case["environment"], stdout=output,
            stderr=subprocess.STDOUT, timeout=60, check=False)
    assert result.returncode == 0, log.read_text()
    return json.loads((case["root"] / ("capsule-result-" + mode + ".json")).read_bytes())


def allocation_model(case):
    path = case["root"] / "bundle/paid_outline_contracts.py"
    loader = ReadOnlyLoader("_paid_outline_schema_tests", str(path))
    spec = importlib.util.spec_from_file_location("_paid_outline_schema_tests", path, loader=loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module.PaidOutlineAllocation


def rebind_allocation(case, change, *, filename="paid-allocation.json"):
    """Adversarial synthetic DATA with matching outer hashes, never source code."""
    root = case["root"]
    assert json.loads((root / "fixture-owner.json").read_bytes())["syntheticEvidence"] is True
    assert filename in {"paid-allocation.json", "pair-allocation.json"}
    allocation = json.loads((root / "bundle" / filename).read_bytes())
    change(allocation)
    raw = builder.canonical(allocation)
    (root / "bundle" / filename).write_bytes(raw)
    controls = json.loads((root / "bundle/source-controls.json").read_bytes())
    controls["files"][filename] = builder.digest(raw)
    control_raw = builder.canonical(controls)
    (root / "bundle/source-controls.json").write_bytes(control_raw)
    packet = json.loads((root / "transport.json").read_bytes())
    phase = packet["phase"]
    phase["allocationSha256"], phase["controlsSha256"] = builder.digest(raw), builder.digest(control_raw)
    phase_raw = builder.canonical(phase)
    (root / "phase/phase.json").write_bytes(phase_raw)
    phase_sha = builder.digest(phase_raw)
    plan = json.loads(packet["planText"])
    plan.update(phaseSha256=phase_sha, allocationSha256=phase["allocationSha256"], controlsSha256=phase["controlsSha256"])
    plan["argv"] = [phase_sha if item == "@PHASE_SHA256@" else item for item in phase["entryArgvTemplate"]]
    plan["argvSha256"] = builder.digest(builder.canonical(plan["argv"]))
    plan["execArgs"]["cmd"] = " ".join("'" + item.replace("'", "'\\''") + "'" for item in plan["argv"])
    packet["phaseSha256"], packet["planText"] = phase_sha, builder.canonical(plan).decode()
    anchor = json.loads(packet["anchorText"])
    anchor.update(phaseSha256=phase_sha, allocationSha256=phase["allocationSha256"],
        controlsSha256=phase["controlsSha256"], planSha256=builder.digest(packet["planText"].encode()))
    packet["anchorText"] = builder.canonical(anchor).decode()
    packet["anchorSha256"] = builder.digest(packet["anchorText"].encode())
    (root / "transport.json").write_bytes(builder.canonical(packet))
    case["packet"] = packet
