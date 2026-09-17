from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest

from plotloom.creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
import plotloom.creative_handoff_exchange as creative_handoff_exchange
from plotloom.creative_handoff_exchange import CreativeHandoffExchange, canonical_json, request_hash


def _request(*, revision: int = 3) -> CreativeHandoffRequest:
    return CreativeHandoffRequest.model_validate({
        "jobId": "ch_" + "a" * 20,
        "projectId": "project-demo",
        "sectionId": "section-opening",
        "stage": "outline",
        "expectedStageRevision": revision,
        "source": {"kind": "synopsis", "text": "A ferryman faces one irreversible choice."},
        "inputArtifacts": {},
        "creativeBrief": "Create a one-episode outline candidate; do not claim approval.",
    })


def _complete(exchange: CreativeHandoffExchange, request: CreativeHandoffRequest) -> None:
    paths = exchange.write_package(request)
    package_request = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    candidate = canonical_json({"source": "Ferry", "params": {"episodes": 1}})
    report = b"<!doctype html><html><body>derived report</body></html>"
    (delivery / "outline.json").write_bytes(candidate)
    (delivery / "report.html").write_bytes(report)
    manifest = {
        "schemaVersion": 1,
        "jobId": request.job_id,
        "requestHash": request_hash(request),
        "deliveryId": "terra-demo-1",
        "stage": request.stage,
        "candidate": {"filename": "outline.json", "sha256": sha256(candidate).hexdigest()},
        "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()},
        "executorProvenance": {
            "codeRevision": "5add328ff8423f0e4ab31cce1459e208712ff20f",
            "skillVersion": "plotloom-shuohao-specialist.v1",
            "skillHash": package_request["executionPin"]["specialistSkillHash"],
            "upstreamRevision": package_request["executionPin"]["upstreamRevision"],
            "upstreamSkillHash": package_request["executionPin"]["upstreamSkillHash"],
            "model": "gpt-5.6-terra",
            "reasoningEffort": "high",
        },
        "limitations": ["Candidate only; no canonical installation occurred."],
    }
    (delivery / "completion.json").write_bytes(canonical_json(manifest))


def _file_snapshot(directory: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(directory)): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def test_self_contained_package_is_idempotent_and_keeps_upstream_inputs(tmp_path: Path) -> None:
    request = _request().model_copy(update={"input_artifacts": {"cast.json": {"source": "Ferry", "characters": []}}})
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")

    copied = exchange.write_package(request)
    package = Path(copied["packagePath"])

    assert json.loads((package / "request.json").read_text()) ["upstreamSkillPath"] == "third_party/shuohao-skills/skills/novel-outline/SKILL.md"
    assert json.loads((package / "inputs" / "cast.json").read_text()) == {"source": "Ferry", "characters": []}
    assert exchange.write_package(request) == copied


def test_malformed_delivery_is_rejected_without_mutating_the_handoff_files(tmp_path: Path) -> None:
    request = _request()
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    copied = exchange.write_package(request)
    delivery = Path(copied["deliveryPath"])
    delivery.mkdir()
    (delivery / "outline.json").write_text("{}")
    (delivery / "report.html").write_text("<html></html>")
    (delivery / "completion.json").write_text("not-json")
    before_read = _file_snapshot(tmp_path / "exchange" / "jobs" / request.job_id)

    with pytest.raises(CreativeHandoffError, match="completion manifest") as error:
        exchange.read_delivery(request)

    assert error.value.code == "delivery_manifest_invalid"
    assert _file_snapshot(tmp_path / "exchange" / "jobs" / request.job_id) == before_read


def test_stale_delivery_is_rejected_without_mutating_the_candidate(tmp_path: Path) -> None:
    request = _request(revision=3)
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    _complete(exchange, request)
    delivery = exchange.read_delivery(request)
    assert delivery is not None
    before_currentness_check = _file_snapshot(tmp_path / "exchange" / "jobs" / request.job_id)

    with pytest.raises(CreativeHandoffError, match="stale") as error:
        exchange.assert_current(delivery, current_stage_revision=4)

    assert error.value.code == "delivery_stale"
    assert _file_snapshot(tmp_path / "exchange" / "jobs" / request.job_id) == before_currentness_check


@pytest.mark.parametrize(
    ("target", "replacement"),
    [
        ("COPY_ASSIGNMENT.txt", b"altered specialist instructions\n"),
        ("inputs/cast.json", canonical_json({"source": "altered"})),
    ],
)
def test_candidate_read_rejects_any_altered_specialist_consumed_package_file(
    tmp_path: Path, target: str, replacement: bytes,
) -> None:
    request = _request().model_copy(update={"input_artifacts": {"cast.json": {"source": "Ferry"}}})
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    package = Path(exchange.write_package(request)["packagePath"])
    (package / target).write_bytes(replacement)
    before_read = _file_snapshot(package)

    with pytest.raises(CreativeHandoffError, match="existing package") as error:
        exchange.read_delivery(request)

    assert error.value.code == "package_conflict"
    assert _file_snapshot(package) == before_read


def test_delivery_requires_exact_derived_report_and_candidate_set(tmp_path: Path) -> None:
    request = _request()
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    _complete(exchange, request)
    delivery = tmp_path / "exchange" / "jobs" / request.job_id / "delivery"
    (delivery / "extra.txt").write_text("unexpected")

    with pytest.raises(CreativeHandoffError, match="exactly") as error:
        exchange.read_delivery(request)

    assert error.value.code == "delivery_partial"


def test_delivery_cannot_claim_an_unpinned_specialist_or_upstream_skill(tmp_path: Path) -> None:
    request = _request()
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    _complete(exchange, request)
    manifest_path = tmp_path / "exchange" / "jobs" / request.job_id / "delivery" / "completion.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["executorProvenance"]["upstreamSkillHash"] = "b" * 64
    manifest_path.write_bytes(canonical_json(manifest))

    with pytest.raises(CreativeHandoffError, match="pinned specialist") as error:
        exchange.read_delivery(request)

    assert error.value.code == "delivery_execution_mismatch"


def test_package_requires_checked_out_revision_to_match_recorded_submodule_gitlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_revision = "a" * 40
    arbitrary_checkout = "b" * 40

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if "ls-tree" in args:
            return subprocess.CompletedProcess(args, 0, f"160000 commit {recorded_revision}\tthird_party/shuohao-skills\n", "")
        return subprocess.CompletedProcess(args, 0, f"{arbitrary_checkout}\n", "")

    monkeypatch.setattr(creative_handoff_exchange.subprocess, "run", fake_run)
    exchange = CreativeHandoffExchange(tmp_path / "exchange")

    with pytest.raises(CreativeHandoffError, match="does not match") as error:
        exchange.write_package(_request())

    assert error.value.code == "execution_pin_missing"


def test_package_preparation_is_explicitly_a_repository_checkout_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        creative_handoff_exchange,
        "__file__",
        str(tmp_path / "site-packages" / "plotloom" / "creative_handoff_exchange.py"),
    )
    exchange = CreativeHandoffExchange(tmp_path / "exchange")

    with pytest.raises(CreativeHandoffError, match="repository checkout") as error:
        exchange.write_package(_request())

    assert error.value.code == "execution_pin_missing"
