from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from fastapi import FastAPI, status

from ..exceptions import (
    InvalidTransitionError,
)
from ..persistence import SQLiteRepository
from ..managed_media import (
    ManagedMediaError,
    publish_import,
)
from ..image_job_contracts import (
    CharacterReferenceDecisionRequest,
    CharacterReferenceProposalRequest,
    CharacterReferenceRevocationRequest,
    ImageJobCreateRequest,
    ImageJobError,
    SamePersonReviewRequest,
)
from ..image_job_exchange import PackageReference


from .models import ImageJobCancellationRequest


def register_image_job_routes(
    app: FastAPI,
    repo: SQLiteRepository,
    selectable_h3_target: Callable[[str], dict[str, Any]],
) -> None:
    @app.get("/api/v2/projects/{project_id}/image-jobs")
    def get_image_jobs(project_id: str) -> dict[str, Any]:
        return {
            "configured": app.state.image_job_exchange.configured,
            "jobs": repo.list_image_jobs(project_id),
        }

    @app.get("/api/v2/projects/{project_id}/character-references")
    def get_character_references(project_id: str) -> dict[str, Any]:
        return repo.list_character_reference_decisions(project_id)

    @app.post(
        "/api/v2/projects/{project_id}/character-references",
        status_code=status.HTTP_201_CREATED,
    )
    def select_character_reference(
        project_id: str, body: CharacterReferenceDecisionRequest
    ) -> dict[str, Any]:
        return repo.create_character_reference_decision(
            project_id, **body.model_dump(mode="python", by_alias=False)
        )

    @app.post(
        "/api/v2/projects/{project_id}/character-references/{character_id}/revoke"
    )
    def revoke_character_reference(
        project_id: str, character_id: str, body: CharacterReferenceRevocationRequest
    ) -> dict[str, Any]:
        return repo.revoke_character_reference_decision(
            project_id,
            character_id=character_id,
            **body.model_dump(mode="python", by_alias=False),
        )

    @app.get("/api/v2/projects/{project_id}/character-reference-proposals")
    def get_character_reference_proposals(project_id: str) -> dict[str, Any]:
        return {
            "configured": app.state.image_job_exchange.configured,
            "proposals": repo.list_character_reference_proposals(project_id),
        }

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals",
        status_code=status.HTTP_201_CREATED,
    )
    def prepare_character_reference_proposal(
        project_id: str, body: CharacterReferenceProposalRequest
    ) -> dict[str, Any]:
        app.state.image_job_exchange.validate_configured()
        return repo.prepare_character_reference_proposal(
            project_id, **body.model_dump(mode="python", by_alias=False)
        )

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/copy"
    )
    def copy_character_reference_proposal(
        project_id: str, proposal_id: str
    ) -> dict[str, Any]:
        source = repo.character_reference_proposal_package_sources(
            project_id, proposal_id
        )
        references: list[PackageReference] = []
        for index, reference in enumerate(source["references"]):
            try:
                content = app.state.artifact_store.get(reference["originalUri"])
            except (FileNotFoundError, KeyError, OSError, ValueError) as error:
                raise InvalidTransitionError(
                    "frozen proposal reference bytes are unavailable"
                ) from error
            if sha256(content).hexdigest() != reference["contentHash"]:
                raise InvalidTransitionError(
                    "frozen proposal reference bytes are unavailable"
                )
            suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
            references.append(
                PackageReference(
                    role=reference["role"],
                    filename=f"reference-{index + 1}-{reference['contentHash'][:16]}{suffix}",
                    content_hash=reference["contentHash"],
                    content=content,
                )
            )
        proposal = source["proposal"]
        package = app.state.image_job_exchange.write_package(
            job_id=proposal_id,
            request=proposal["request"],
            request_hash=proposal["requestHash"],
            references=references,
        )
        proposal = repo.mark_character_reference_proposal_exported(
            project_id, proposal_id
        )
        return {
            "proposal": proposal,
            "assignment": (
                f"Codex character-reference proposal assignment for {proposal_id}: read {package['packagePath']}/request.json "
                f"and {package['packagePath']}/completion-manifest.example.json; use built-in imagegen; write JPEG/PNG outputs "
                f"and completion.json only under {package['deliveryPath']}. This is exploratory and cannot approve a reference."
            ),
            "packagePath": package["packagePath"],
            "deliveryPath": package["deliveryPath"],
        }

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/refresh"
    )
    def refresh_character_reference_proposal(
        project_id: str, proposal_id: str
    ) -> dict[str, Any]:
        context = repo.character_reference_proposal_delivery_context(
            project_id, proposal_id
        )
        try:
            references: list[tuple[str, str, str]] = []
            for index, reference in enumerate(
                context["request"]["frozenSnapshot"].get("references", [])
            ):
                suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
                references.append(
                    (
                        reference["role"],
                        f"reference-{index + 1}-{reference['originalHash'][:16]}{suffix}",
                        reference["originalHash"],
                    )
                )
            app.state.image_job_exchange.verify_package(
                job_id=proposal_id,
                request=context["request"],
                request_hash=context["requestHash"],
                references=references,
            )
            delivery = app.state.image_job_exchange.read_delivery(
                job_id=proposal_id,
                request_hash=context["requestHash"],
                require_executor_provenance=True,
                require_executor_pin=context["request"]
                .get("specialistPreflight", {})
                .get("version")
                == "p1.5-pin.v1",
                expected_executor_skill_version=context["request"]
                .get("specialistPreflight", {})
                .get("skillVersion"),
            )
        except ImageJobError as error:
            if error.code not in {
                "image_exchange_not_configured",
                "image_exchange_invalid",
                "invalid_job_id",
                "delivery_manifest_secret",
            }:
                repo.record_character_reference_proposal_rejection(
                    project_id, proposal_id, error.code
                )
            raise
        if delivery is None:
            return {"state": "awaiting_delivery", "candidates": [], "idempotent": False}
        outputs = [
            {
                "filename": output.filename,
                "role": output.role,
                "originalHash": output.observed.content_hash,
                "displayHash": output.observed.display_hash,
                "mimeType": output.observed.mime_type,
                "byteSize": output.observed.byte_size,
                "width": output.observed.width,
                "height": output.observed.height,
                "content": output.content,
                "observed": output.observed,
            }
            for output in delivery.outputs
        ]

        def publish_under_admission(output: dict[str, Any]) -> tuple[str, str]:
            try:
                return publish_import(
                    app.state.artifact_store, output["content"], output["observed"]
                )
            except (ManagedMediaError, OSError, KeyError, ValueError) as error:
                raise ImageJobError(
                    "delivery_storage_failed",
                    "validated proposal delivery could not be stored",
                ) from error

        return repo.record_character_reference_proposal_delivery(
            project_id,
            proposal_id,
            delivery_id=delivery.manifest.delivery_id,
            manifest=delivery.manifest.model_dump(mode="json", by_alias=True),
            manifest_hash=delivery.manifest_hash,
            outputs=outputs,
            publish=publish_under_admission,
        )

    @app.get("/api/v2/projects/{project_id}/same-person-reviews")
    def get_same_person_reviews(project_id: str) -> dict[str, Any]:
        return repo.list_same_person_reviews(project_id)

    @app.post(
        "/api/v2/projects/{project_id}/same-person-reviews",
        status_code=status.HTTP_201_CREATED,
    )
    def record_same_person_review(
        project_id: str, body: SamePersonReviewRequest
    ) -> dict[str, Any]:
        # The persisted comparison receipt deliberately mirrors the frozen
        # package's camel-case character identity map.
        return repo.record_same_person_review(
            project_id,
            binding_id=body.binding_id,
            expected_review_revision=body.expected_review_revision,
            reviewer=body.reviewer,
            comparisons=[
                item.model_dump(mode="json", by_alias=True) for item in body.comparisons
            ],
            notes=body.notes,
        )

    @app.post(
        "/api/v2/projects/{project_id}/image-jobs", status_code=status.HTTP_201_CREATED
    )
    def prepare_image_job(
        project_id: str, body: ImageJobCreateRequest
    ) -> dict[str, Any]:
        # A job is useful only with its explicitly configured same-host
        # transport. This check happens before durable admission, so a missing
        # operator setting never creates a misleading copyable job.
        app.state.image_job_exchange.validate_configured()
        adaptation = (
            {"targetProfile": selectable_h3_target(body.keyframe_adaptation_profile_id)}
            if body.keyframe_adaptation_profile_id is not None
            else None
        )
        return repo.prepare_image_job(
            project_id,
            approval_id=body.approval_id,
            shot_id=body.shot_id,
            storyboard_revision=body.storyboard_revision,
            parent_candidate_asset_id=body.parent_candidate_asset_id,
            keyframe_adaptation=adaptation,
            presentation_change=body.presentation_change,
            contract_version=body.contract_version,
        )

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/copy")
    def copy_image_job(project_id: str, job_id: str) -> dict[str, Any]:
        source = repo.image_job_package_sources(project_id, job_id)
        references: list[PackageReference] = []
        for index, reference in enumerate(source["references"]):
            try:
                content = app.state.artifact_store.get(reference["originalUri"])
            except (FileNotFoundError, KeyError, OSError, ValueError) as error:
                raise InvalidTransitionError(
                    "frozen image-job reference bytes are unavailable"
                ) from error
            if sha256(content).hexdigest() != reference["contentHash"]:
                raise InvalidTransitionError(
                    "frozen image-job reference bytes are unavailable"
                )
            suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
            references.append(
                PackageReference(
                    role=(
                        f"character_identity:{reference['characterId']}"
                        if reference["role"] == "character_identity"
                        and reference.get("characterId")
                        else reference["role"]
                    ),
                    filename=f"reference-{index + 1}-{reference['contentHash'][:16]}{suffix}",
                    content_hash=reference["contentHash"],
                    content=content,
                )
            )
        package = app.state.image_job_exchange.write_package(
            job_id=job_id,
            request=source["job"]["request"],
            request_hash=source["job"]["requestHash"],
            references=references,
        )
        job = repo.mark_image_job_exported(project_id, job_id)
        completion_template = (
            f" and {package['packagePath']}/completion-manifest.example.json"
            if job["request"].get("schemaVersion") == 2
            else ""
        )
        return {
            "job": job,
            "assignment": (
                f"Codex image specialist assignment for {job_id}: read {package['packagePath']}/request.json"
                f"{completion_template}; "
                f"use built-in imagegen; write JPEG/PNG outputs and completion.json only under {package['deliveryPath']}."
            ),
            "packagePath": package["packagePath"],
            "deliveryPath": package["deliveryPath"],
        }

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/refresh")
    def refresh_image_job(project_id: str, job_id: str) -> dict[str, Any]:
        context = repo.image_job_delivery_context(project_id, job_id)
        try:
            # Copy is a same-user filesystem handoff, not a security boundary.
            # Rebuild the exact package projection from the frozen database
            # request before treating a delivery as attributable to this job.
            # This closes the interval between Copy and Refresh without giving
            # the browser or specialist authority over the canonical request.
            references: list[tuple[str, str, str]] = []
            frozen_references = context["request"]["frozenSnapshot"].get(
                "references", []
            )
            identity_reference_hashes: list[str] = []
            for index, reference in enumerate(
                item
                for item in frozen_references
                if item.get("role")
                in {"parent_output", "source_keyframe", "character_identity"}
            ):
                suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
                references.append(
                    (
                        (
                            f"character_identity:{reference['characterId']}"
                            if reference["role"] == "character_identity"
                            and reference.get("characterId")
                            else reference["role"]
                        ),
                        f"reference-{index + 1}-{reference['originalHash'][:16]}{suffix}",
                        reference["originalHash"],
                    )
                )
                if reference["role"] == "character_identity":
                    identity_reference_hashes.append(reference["originalHash"])
            app.state.image_job_exchange.verify_package(
                job_id=job_id,
                request=context["request"],
                request_hash=context["requestHash"],
                references=references,
            )
            delivery = app.state.image_job_exchange.read_delivery(
                job_id=job_id,
                request_hash=context["requestHash"],
                required_reference_hashes=identity_reference_hashes,
                require_executor_provenance=context["request"].get("schemaVersion")
                == 3,
                require_executor_pin=context["request"]
                .get("specialistPreflight", {})
                .get("version")
                == "p1.5-pin.v1",
                expected_executor_skill_version=context["request"]
                .get("specialistPreflight", {})
                .get("skillVersion"),
            )
        except ImageJobError as error:
            # A manifest/path failure and a malformed or over-limit raster are
            # all untrusted delivery attempts worth preserving for the creator.
            # Exchange configuration/identifier failures happen before any
            # delivery can be read, so they are operator diagnostics instead.
            if error.code not in {
                "image_exchange_not_configured",
                "image_exchange_invalid",
                "invalid_job_id",
                "delivery_manifest_secret",
            }:
                repo.record_image_job_delivery_rejection(project_id, job_id, error.code)
            raise
        if delivery is None:
            # Copy intentionally creates no completion marker. This is not a
            # rejected delivery and must not manufacture immutable history.
            return {"state": "awaiting_delivery", "candidates": [], "idempotent": False}
        adaptation = (
            context["request"].get("frozenSnapshot", {}).get("keyframeAdaptation")
        )
        if adaptation is not None:
            contract = adaptation.get("outputContract")
            if not isinstance(contract, dict):
                repo.record_image_job_delivery_rejection(
                    project_id, job_id, "delivery_geometry_contract_invalid"
                )
                raise ImageJobError(
                    "delivery_geometry_contract_invalid",
                    "keyframe adaptation has no usable frozen output contract",
                )
            expected = (contract.get("width"), contract.get("height"))
            for output in delivery.outputs:
                if (
                    output.role != "keyframe_adaptation"
                    or (output.observed.width, output.observed.height) != expected
                ):
                    repo.record_image_job_delivery_rejection(
                        project_id, job_id, "delivery_geometry_mismatch"
                    )
                    raise ImageJobError(
                        "delivery_geometry_mismatch",
                        "keyframe adaptation delivery must use the frozen role and exact profile dimensions",
                    )
        outputs: list[dict[str, Any]] = []
        for output in delivery.outputs:
            outputs.append(
                {
                    "filename": output.filename,
                    "role": output.role,
                    "originalHash": output.observed.content_hash,
                    "displayHash": output.observed.display_hash,
                    "mimeType": output.observed.mime_type,
                    "byteSize": output.observed.byte_size,
                    "width": output.observed.width,
                    "height": output.observed.height,
                    "content": output.content,
                    "observed": output.observed,
                }
            )

        def publish_under_admission(output: dict[str, Any]) -> tuple[str, str]:
            try:
                return publish_import(
                    app.state.artifact_store, output["content"], output["observed"]
                )
            except (ManagedMediaError, OSError, KeyError, ValueError) as error:
                raise ImageJobError(
                    "delivery_storage_failed", "validated delivery could not be stored"
                ) from error

        return repo.record_image_job_delivery(
            project_id,
            job_id,
            delivery_id=delivery.manifest.delivery_id,
            manifest=delivery.manifest.model_dump(mode="json", by_alias=True),
            manifest_hash=delivery.manifest_hash,
            outputs=outputs,
            publish=publish_under_admission,
        )

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/cancel")
    def cancel_image_job(
        project_id: str, job_id: str, body: ImageJobCancellationRequest
    ) -> dict[str, Any]:
        return repo.cancel_image_job(project_id, job_id, body.reason)
