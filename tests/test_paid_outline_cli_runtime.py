"""Current raw QA shebang contract and independently retained startup facts."""
import json
from pathlib import Path

import pytest

from tests import paid_outline_fixtures
from tests.cli_handoff_fixtures import ROOT, current_test_qa, exclusive
from tests.paid_outline_cli_runtime import cli_shebang
from tests.paid_outline_processes import owned_processes


@pytest.mark.parametrize("entrypoint", ["", "relative/python", "/tmp/a b/python",
    "/tmp/a\tpython", "/tmp/a\u2003python", "/tmp/python\nextra", "/tmp/a\0python", "/" + "x" * 124,
    "/" + "é" * 62, "/" + "x" * 121, "/" + "é" * 60 + "x"])
def test_unsupported_raw_qa_path_refused_before_wrapper_or_allocation(tmp_path, monkeypatch, entrypoint):
    qa = json.loads(current_test_qa()) | {"entrypoint": entrypoint}
    monkeypatch.setattr(paid_outline_fixtures, "current_test_qa", lambda: json.dumps(qa))
    with pytest.raises(ValueError, match="fake CLI"):
        paid_outline_fixtures.make_case(tmp_path, tmp_path / "unused-source", None)
    assert not (tmp_path / "fake-codex").exists()
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize("entrypoint", ["/venv/bin/python", "/" + "x" * 120,
    "/" + "é" * 59 + "xx"])
def test_shebang_preserves_raw_path_and_counts_encoded_delimiters(entrypoint):
    result = cli_shebang(entrypoint)
    assert result == ("#!" + entrypoint + " -B\n").encode()
    assert len(result) <= 127


def test_startup_record_survives_later_import_failure(tmp_path):
    tmp_path.chmod(0o700)
    qa = json.loads(current_test_qa())
    exclusive(tmp_path / "qa.json", json.dumps(qa).encode())
    executable = tmp_path / "fake-codex"
    body = ("import sys\nfrom pathlib import Path\n"
        + "sys.path.insert(0, " + repr(str(ROOT)) + ")\n"
        + "from tests.paid_outline_cli_runtime import observe_startup\n"
        + "observe_startup(Path(__file__).resolve(), sys.argv[1:])\n"
        + "import deliberately_absent_paid_fixture_dependency\n")
    exclusive(executable, cli_shebang(qa["entrypoint"]) + body.encode())
    executable.chmod(0o700)
    with owned_processes(tmp_path) as processes:
        result = processes.run([str(executable), "sandbox"], capture_output=True, timeout=10)
        assert result.returncode != 0
        assert b"deliberately_absent_paid_fixture_dependency" in result.stderr
    records = list((tmp_path / "receipts").glob("cli-startup-runtime-*.json"))
    assert len(records) == 1
    facts = json.loads(records[0].read_bytes())
    assert records[0].name == f"cli-startup-runtime-{facts['pid']}.json"
    assert facts["executable"] == qa["entrypoint"]
    assert facts["physicalExecutable"] == qa["physicalExecutable"]
    assert facts["physicalPrefix"] == qa["prefix"]
    assert facts["physicalBasePrefix"] == qa["physicalBasePrefix"]
    assert facts["majorMinor"] == qa["majorMinor"]
    assert facts["implementation"] == qa["implementation"]
    assert facts["dontWriteBytecode"] is True
    assert facts["invocation"] == "sandbox"
    assert Path(facts["wrapper"]) == executable
    assert not list((tmp_path / "receipts").glob("cli-sandbox-runtime-*.json"))
    settlement = json.loads((tmp_path / "process-settlement.json").read_bytes())
    assert not settlement["remaining"] and not settlement["errors"]
