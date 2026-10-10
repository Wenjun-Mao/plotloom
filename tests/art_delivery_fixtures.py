"""Art package and reference fixtures shared by isolated tests."""

from __future__ import annotations

import json
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image

from plotloom.art_contracts import (
    ArtBinding,
)
from plotloom.creative_handoff_contracts import CreativeHandoffRequest
from plotloom.creative_handoff_exchange import canonical_json


def _binding(revision: int = 1) -> ArtBinding:
    return ArtBinding(
        source_revision=revision,
        source_content_hash="a" * 64,
        outline_revision=1,
        outline_content_hash="b" * 64,
        section_map_revision=1,
        section_map_content_hash="c" * 64,
        graph_revision=1,
        graph_content_hash="d" * 64,
        cast_revision=1,
        cast_content_hash="e" * 64,
        section_ids=["opening", "ending-a", "ending-b"],
    )


def _context(
    revision: int = 1,
) -> tuple[
    ArtBinding,
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
]:
    return (
        _binding(revision),
        {"title": "Tide Light", "text": "Lin chooses the beacon or dock."},
        {"source": "Tide Light", "episodes": []},
        {
            "sections": [
                {"sectionId": "opening"},
                {"sectionId": "ending-a"},
                {"sectionId": "ending-b"},
            ]
        },
        {
            "source": "Tide Light",
            "summary": "Shared cast",
            "characters": [{"id": "C01", "name": "Lin"}],
        },
    )


def _deliver(store: object, request: CreativeHandoffRequest) -> object:
    exchange = store.creative_handoff_exchange()  # type: ignore[attr-defined]
    pin = store.creative_handoff_execution_pin(request)  # type: ignore[attr-defined]
    paths = exchange.write_package(request, pin)
    package = json.loads((Path(paths["packagePath"]) / "request.json").read_text())
    delivery = Path(paths["deliveryPath"])
    delivery.mkdir()
    render = "Semi-realistic environment concept art, painterly rendering with visible brush texture, grounded architectural perspective, cinematic depth"
    art = canonical_json(
        {
            "source": "Tide Light",
            "style": "realistic",
            "scenes": [
                {
                    "id": "S01",
                    "name": "航标室",
                    "primary": True,
                    "summary": "choice pressure",
                    "anchors": [
                        {"name": "铜灯", "desc": "old brass"},
                        {"name": "窗", "desc": "salted glass"},
                        {"name": "桌", "desc": "worn wood"},
                    ],
                    "lighting": [
                        {"state": "dawn", "prompt": "cold dawn through a window"}
                    ],
                    "image": {
                        "prompt": render + ", empty beacon room",
                        "negativePrompt": "people, human figures",
                        "sheet": render,
                        "tags": [],
                    },
                }
            ],
            "props": [],
            "sectionUsage": [
                {"sectionId": section["sectionId"], "sceneIds": ["S01"], "propIds": []}
                for section in request.input_artifacts["section-map.json"]["sections"]
            ],
        }
    )
    report = b"<!doctype html><html><body>art report</body></html>"
    (delivery / "art.json").write_bytes(art)
    (delivery / "report.html").write_bytes(report)
    manifest = {
        "schemaVersion": 1,
        "jobId": request.job_id,
        "requestHash": package["requestHash"],
        "deliveryId": "art-fixture",
        "stage": "art",
        "candidate": {"filename": "art.json", "sha256": sha256(art).hexdigest()},
        "report": {"filename": "report.html", "sha256": sha256(report).hexdigest()},
        "executorProvenance": {
            "codeRevision": "abcdef0",
            "skillVersion": "fixture",
            "skillHash": package["executionPin"]["specialistSkillHash"],
            "upstreamRevision": package["executionPin"]["upstreamRevision"],
            "upstreamSkillHash": package["executionPin"]["upstreamSkillHash"],
            "model": "fixture",
            "reasoningEffort": "high",
        },
        "limitations": ["no images"],
    }
    (delivery / "completion.json").write_text(json.dumps(manifest))
    result = exchange.read_delivery(request, pin)
    assert result is not None
    return result


def _reference_png() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 24), (42, 72, 84)).save(output, format="PNG")
    return output.getvalue()


def _write_art_reference_delivery(
    delivery_path: Path, proposal: dict[str, object]
) -> None:
    request = proposal["request"]
    assert isinstance(request, dict)
    request_hash = proposal["requestHash"]
    assert isinstance(request_hash, str)
    content = _reference_png()
    provenance = {
        "codeRevision": "a" * 40,
        "skillVersion": "plotloom-image-specialist.v3",
        "skillHash": "b" * 64,
    }
    delivery_path.mkdir(exist_ok=True)
    (delivery_path / "outputs").mkdir()
    (delivery_path / "outputs" / "study.png").write_bytes(content)
    (delivery_path / "executor-pin.json").write_text(
        json.dumps(
            {
                "jobId": proposal["id"],
                "requestHash": request_hash,
                "executionContract": "codex_specialist.v2",
                **provenance,
            }
        )
    )
    (delivery_path / "completion.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "jobId": proposal["id"],
                "requestHash": request_hash,
                "deliveryId": "art-study-001",
                "actualPrompt": "Cinematic realism environment study, no people and no hands.",
                "outputs": [
                    {
                        "filename": "study.png",
                        "sha256": sha256(content).hexdigest(),
                        "role": "art_reference",
                    }
                ],
                "toolEvidence": {
                    "tool": "codex_imagegen",
                    "taskId": "art-reference-fixture",
                    "available": True,
                },
                "executorProvenance": provenance,
                "limitations": ["fixture bytes only"],
            }
        )
    )
