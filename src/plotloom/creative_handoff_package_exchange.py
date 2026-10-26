"""Frozen creative package verification and write-once publication."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .creative_handoff_identity import TEMPLATE_FILENAME, canonical_json, request_hash
from .creative_exchange_files import _read_regular, _write_once
from .creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest


def _json_file_limit(request: CreativeHandoffRequest) -> int:
    if request.stage in {"bridge-intent", "bridge-presentation"}:
        from .native_bridge_request import MAX_NATIVE_BRIDGE_PACKAGE_JSON_BYTES

        return MAX_NATIVE_BRIDGE_PACKAGE_JSON_BYTES
    return 1_000_000


class CreativeHandoffPackageExchangeMixin:
    """Own immutable package projection checks and first publication."""

    def _verify_frozen_package(
        self,
        request: CreativeHandoffRequest,
        execution_pin: dict[str, str],
        *,
        executor_backend: str = "specialist_chat",
        plotloom_code_revision: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        """Confirm every specialist-consumed package file still matches its projection."""
        job_root = self._job_root(request.job_id)
        package = job_root / "package"
        projected, instructions, template, expected = self._projection(
            request,
            execution_pin,
            executor_backend=executor_backend,
            plotloom_code_revision=plotloom_code_revision,
        )
        names = self._names(package, package=True)
        if names != expected:
            raise CreativeHandoffError("package_conflict", "existing package has unexpected entries")
        json_limit = _json_file_limit(request)
        if _read_regular(package / "request.json", max_bytes=json_limit, package=True) != canonical_json(projected):
            raise CreativeHandoffError("package_conflict", "existing package differs from frozen request")
        if _read_regular(package / "COPY_ASSIGNMENT.txt", max_bytes=20_000, package=True) != instructions:
            raise CreativeHandoffError("package_conflict", "existing package instructions differ from frozen request")
        if executor_backend == "specialist_chat" and _read_regular(
            package / TEMPLATE_FILENAME, max_bytes=20_000, package=True
        ) != template:
            raise CreativeHandoffError("package_conflict", "existing package template differs from frozen request")
        inputs = package / "inputs"
        if self._names(inputs, package=True) != set(request.input_artifacts):
            raise CreativeHandoffError("package_conflict", "existing package inputs differ from frozen request")
        for filename, payload in request.input_artifacts.items():
            if _read_regular(inputs / filename, max_bytes=json_limit, package=True) != canonical_json(payload):
                raise CreativeHandoffError("package_conflict", "existing package input differs from frozen request")
        return job_root, projected

    def verified_package_paths(
        self,
        request: CreativeHandoffRequest,
        execution_pin: dict[str, str],
        *,
        executor_backend: str = "specialist_chat",
        plotloom_code_revision: str | None = None,
    ) -> dict[str, str]:
        """Recover an existing handoff without creating or repairing frozen files."""
        request.assert_secret_free()
        job_root, _ = self._verify_frozen_package(
            request,
            execution_pin,
            executor_backend=executor_backend,
            plotloom_code_revision=plotloom_code_revision,
        )
        self._assert_outline_report_schema(request)
        return {"packagePath": str(job_root / "package"), "deliveryPath": str(job_root / "delivery")}

    def write_package(
        self,
        request: CreativeHandoffRequest,
        execution_pin: dict[str, str],
        *,
        executor_backend: str = "specialist_chat",
        plotloom_code_revision: str | None = None,
    ) -> dict[str, str]:
        """Publish the exact frozen package once, then verify its complete projection."""
        request.assert_secret_free()
        job_root = self._job_root(request.job_id)
        package = job_root / "package"
        projected, instructions, template, _expected = self._projection(
            request,
            execution_pin,
            executor_backend=executor_backend,
            plotloom_code_revision=plotloom_code_revision,
        )
        self._names(package, package=True)
        if package.exists():
            self._verify_frozen_package(
                request,
                execution_pin,
                executor_backend=executor_backend,
                plotloom_code_revision=plotloom_code_revision,
            )
            self._assert_outline_report_schema(request)
            return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}
        self._assert_outline_report_schema(request)
        from .creative_package_publication import publish_package

        files = {
            **{f"inputs/{filename}": canonical_json(payload) for filename, payload in request.input_artifacts.items()},
            "request.json": canonical_json(projected),
            "COPY_ASSIGNMENT.txt": instructions,
        }
        if executor_backend == "specialist_chat":
            files[TEMPLATE_FILENAME] = template
        if request.stage in {"bridge-intent", "bridge-presentation"} and any(
            len(content) > _json_file_limit(request)
            for name, content in files.items() if name.endswith(".json")
        ):
            raise CreativeHandoffError("package_conflict", "native bridge package JSON exceeds its file limit")
        publish_package(package, digest=request_hash(request), files=files, write_once=_write_once)
        self._verify_frozen_package(
            request,
            execution_pin,
            executor_backend=executor_backend,
            plotloom_code_revision=plotloom_code_revision,
        )
        return {"packagePath": str(package), "deliveryPath": str(job_root / "delivery")}

    @staticmethod
    def _assert_outline_report_schema(request: CreativeHandoffRequest) -> None:
        if request.stage == "outline":
            from .outline_report_metadata import assert_outline_report_schema_current

            assert_outline_report_schema_current(request.input_artifacts)
