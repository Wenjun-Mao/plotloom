"""Frozen creative package verification and write-once publication."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest


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
        from .creative_handoff_exchange import (
            TEMPLATE_FILENAME,
            _read_regular,
            canonical_json,
        )

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
        if _read_regular(package / "request.json", max_bytes=1_000_000, package=True) != canonical_json(projected):
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
            if _read_regular(inputs / filename, max_bytes=1_000_000, package=True) != canonical_json(payload):
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
        from .creative_handoff_exchange import (
            TEMPLATE_FILENAME,
            _write_once,
            canonical_json,
            request_hash,
        )

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
