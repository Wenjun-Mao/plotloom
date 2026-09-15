"""Stable exchange projections retained across image package versions."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

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
