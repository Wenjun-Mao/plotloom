from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from plotloom.creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
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
            "skillHash": "a" * 64,
            "model": "gpt-5.6-terra",
            "reasoningEffort": "high",
        },
        "limitations": ["Candidate only; no canonical installation occurred."],
    }
    (delivery / "completion.json").write_bytes(canonical_json(manifest))


def test_self_contained_package_is_idempotent_and_keeps_upstream_inputs(tmp_path: Path) -> None:
    request = _request().model_copy(update={"input_artifacts": {"cast.json": {"source": "Ferry", "characters": []}}})
    exchange = CreativeHandoffExchange(tmp_path / "project" / "outputs" / "creative-handoff")

    copied = exchange.write_package(request)
    package = Path(copied["packagePath"])

    assert json.loads((package / "request.json").read_text()) ["upstreamSkillPath"] == "third_party/shuohao-skills/skills/novel-outline/SKILL.md"
    assert json.loads((package / "inputs" / "cast.json").read_text()) == {"source": "Ferry", "characters": []}
    assert exchange.write_package(request) == copied


def test_malformed_delivery_never_admits_or_mutates_accepted_work(tmp_path: Path) -> None:
    request = _request()
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    copied = exchange.write_package(request)
    delivery = Path(copied["deliveryPath"])
    delivery.mkdir()
    accepted = {"revision": 3, "payload": {"source": "accepted"}}
    (delivery / "outline.json").write_text("{}")
    (delivery / "report.html").write_text("<html></html>")
    (delivery / "completion.json").write_text("not-json")

    with pytest.raises(CreativeHandoffError, match="completion manifest") as error:
        exchange.read_delivery(request)

    assert error.value.code == "delivery_manifest_invalid"
    assert accepted == {"revision": 3, "payload": {"source": "accepted"}}


def test_stale_delivery_is_rejected_before_the_existing_owner_can_install_it(tmp_path: Path) -> None:
    request = _request(revision=3)
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    _complete(exchange, request)
    delivery = exchange.read_delivery(request)
    assert delivery is not None
    accepted = {"revision": 4, "payload": {"source": "newer accepted work"}}

    with pytest.raises(CreativeHandoffError, match="stale") as error:
        exchange.assert_current(delivery, current_stage_revision=accepted["revision"])

    assert error.value.code == "delivery_stale"
    assert accepted == {"revision": 4, "payload": {"source": "newer accepted work"}}


def test_delivery_requires_exact_derived_report_and_candidate_set(tmp_path: Path) -> None:
    request = _request()
    exchange = CreativeHandoffExchange(tmp_path / "exchange")
    _complete(exchange, request)
    delivery = tmp_path / "exchange" / "jobs" / request.job_id / "delivery"
    (delivery / "extra.txt").write_text("unexpected")

    with pytest.raises(CreativeHandoffError, match="exactly") as error:
        exchange.read_delivery(request)

    assert error.value.code == "delivery_partial"
