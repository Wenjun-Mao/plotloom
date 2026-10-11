"""Reusable source and outline fixture builders for project storage tests."""

from __future__ import annotations

import json
import subprocess
from hashlib import sha256
from pathlib import Path

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.domain import ProjectBrief
from plotloom.outline_settings import OUTLINE_SETTINGS_FILENAME, outline_settings
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.source_outline_contracts import SourceMaterial
from plotloom.source_structures import planned_structure


def _material(kind: str = "synopsis") -> SourceMaterial:
    return SourceMaterial(
        kind=kind,
        title="渡口的信",
        text="一位船夫必须在暴风雨前决定把最后一封信交给谁。",
        attribution="作者本人提供的 F1A 测试材料",
        rights_declaration="作者声明拥有用于此测试的改编许可；系统不作法律确认。",
        adaptation_intent="保留不可逆选择，并允许为互动形式补充一条分支后果。",
        invented_additions="可以增加一位目击者。",
    )


def _storage(tmp_path: Path) -> ProjectFolderStorage:
    return ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )


def _request(
    project_id: str,
    source: SourceMaterial,
    expected_outline_revision: int = 0,
    job_suffix: str = "a",
    brief: ProjectBrief | None = None,
) -> CreativeHandoffRequest:
    selected_brief = brief or FIXED_CHINESE_BRIEF
    return CreativeHandoffRequest(
        job_id="ch_" + job_suffix * 32,
        project_id=project_id,
        section_id="story",
        stage="outline",
        expected_stage_revision=expected_outline_revision,
        source=source.model_dump(mode="json", by_alias=True),
        input_artifacts={
            OUTLINE_SETTINGS_FILENAME: outline_settings(selected_brief),
            "story-topology.json": planned_structure(
                project_id, selected_brief
            ).model_dump(mode="json", by_alias=True),
        },
        creative_brief="Produce one upstream-shaped review candidate only.",
    )


def _deliver(store: object, request: CreativeHandoffRequest) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    pin = store.creative_handoff_execution_pin(request)  # type: ignore[attr-defined]
    paths = exchange.write_package(request, pin)
    package_request = json.loads(
        (Path(paths["packagePath"]) / "request.json").read_text()
    )
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    outline = canonical_json(
        {"source": "渡口的信", "params": {"episodes": 1}, "episodes": []}
    )
    report = b"<!doctype html><html><body>derived outline</body></html>"
    (delivery / "outline.json").write_bytes(outline)
    (delivery / "report.html").write_bytes(report)
    manifest = {
        "schemaVersion": 1,
        "jobId": request.job_id,
        "requestHash": package_request["requestHash"],
        "deliveryId": "f1a-fixture-1",
        "stage": "outline",
        "candidate": {
            "filename": "outline.json",
            "sha256": sha256(outline).hexdigest(),
        },
        "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()},
        "executorProvenance": {
            "codeRevision": subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip(),
            "skillVersion": "fixture",
            "skillHash": package_request["executionPin"]["specialistSkillHash"],
            "upstreamRevision": package_request["executionPin"]["upstreamRevision"],
            "upstreamSkillHash": package_request["executionPin"]["upstreamSkillHash"],
            "model": "fixture",
            "reasoningEffort": "high",
        },
        "limitations": ["fixture candidate"],
    }
    (delivery / "completion.json").write_text(json.dumps(manifest))
    result = exchange.read_delivery(request, pin)
    assert result is not None
    return result
