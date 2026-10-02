"""Stable exchange projections retained across image package versions."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.image_job_exchange import ImageJobExchange
from plotloom.managed_media import ManagedMediaLimits


def test_legacy_v1_package_remains_recheckable_without_a_template(tmp_path: Path) -> None:
    """Historic package bytes remain readable without reviving a V1 runtime."""

    request = {
        "schemaVersion": 1,
        "jobId": "ij_" + "a" * 20,
        "kind": "original",
    }
    request_hash = sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())

    copied = exchange.write_package(
        job_id=request["jobId"],
        request=request,
        request_hash=request_hash,
        references=[],
    )
    package = Path(copied["packagePath"])

    assert {item.name for item in package.iterdir()} == {
        "COPY_ASSIGNMENT.txt",
        "request.json",
    }
    exchange.verify_package(
        job_id=request["jobId"],
        request=request,
        request_hash=request_hash,
        references=[],
    )


@pytest.mark.parametrize(
    ("schema_version", "kind", "target", "manifest_version"),
    [
        (2, "original", "image_job", 1),
        (3, "original", "image_job", 2),
        (3, "character_reference", "character_reference_proposal", 2),
        (3, "art_reference", "art_reference_proposal", 2),
    ],
)
def test_emitted_package_requires_returned_basename_in_both_primary_instructions(
    tmp_path: Path, schema_version: int, kind: str, target: str, manifest_version: int
) -> None:
    request = {
        "schemaVersion": schema_version,
        "jobId": "ij_" + "b" * 20,
        "kind": kind,
        "target": target,
        "specialistPreflight": {
            "version": "p1.5-pin.v1",
            "skillVersion": "plotloom-image-specialist.v3",
        },
    }
    request_hash = sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    exchange = ImageJobExchange(tmp_path / "exchange", limits=ManagedMediaLimits())
    arguments = {
        "job_id": request["jobId"],
        "request": request,
        "request_hash": request_hash,
        "references": [],
    }
    copied = exchange.write_package(**arguments)
    package = Path(copied["packagePath"])
    emitted = json.loads((package / "request.json").read_text())
    assignment = (package / "COPY_ASSIGNMENT.txt").read_text()
    template = json.loads((package / "completion-manifest.example.json").read_text())

    for instruction in (emitted["deliveryInstruction"], assignment):
        assert "unchanged using its exact returned basename" in instruction
        assert "declare that same basename in outputs[].filename" in instruction
        assert "placeholders, never required output names" in instruction
    assert template["outputs"] == [{
        "filename": "replace-with-exact-returned-basename.png",
        "sha256": "0" * 64,
        "role": kind,
    }]
    assert template["schemaVersion"] == manifest_version
    assert template["jobId"] == request["jobId"]
    assert template["requestHash"] == request_hash
    assert emitted["packageVersion"] == (2 if schema_version == 2 else 4)
    assert exchange.write_package(**arguments) == copied
    exchange.verify_package(**arguments)
