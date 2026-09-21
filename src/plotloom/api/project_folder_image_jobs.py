from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from fastapi import FastAPI, status

from ..exceptions import (
    InvalidTransitionError,
)
from ..managed_media import publish_import
from ..image_job_contracts import (
    CharacterReferenceProposalCancellationRequest,
    CharacterReferenceDecisionRequest,
    CharacterReferenceProposalRequest,
    CharacterReferenceRevocationRequest,
    ImageJobError,
    SamePersonReviewRequest,
)
from ..image_job_exchange import PackageReference
from ..codex_image_dispatch import NativeCodexImageDispatcher
from .models import (
    ImageJobCancellationRequest,
    ProjectFolderImageJobCreateRequest,
)


def register_project_folder_image_job_routes(
    app: FastAPI,
    opened_project: Callable[[str], Any],
    *,
    image_job_target_id: Callable[[ProjectFolderImageJobCreateRequest], str],
    require_media_draft_scope: Callable[..., Any],
    project_h3_target: Callable[[str], dict[str, Any]],
    image_dispatcher: NativeCodexImageDispatcher | None = None,
) -> None:
    def package_references(
        store: Any, sources: list[dict[str, Any]], *, character_roles: bool = False
    ) -> list[PackageReference]:
        references: list[PackageReference] = []
        for index, reference in enumerate(sources):
            try:
                content = store.artifacts.get(reference["originalUri"])
            except (FileNotFoundError, KeyError, OSError, ValueError) as error:
                raise InvalidTransitionError(
                    "frozen image reference bytes are unavailable"
                ) from error
            if sha256(content).hexdigest() != reference["contentHash"]:
                raise InvalidTransitionError(
                    "frozen image reference bytes are unavailable"
                )
            suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
            role = reference["role"]
            if (
                character_roles
                and role == "character_identity"
                and reference.get("characterId")
            ):
                role = f"character_identity:{reference['characterId']}"
            references.append(
                PackageReference(
                    role=role,
                    filename=f"reference-{index + 1}-{reference['contentHash'][:16]}{suffix}",
                    content_hash=reference["contentHash"],
                    content=content,
                )
            )
        return references

    def delivery_outputs(delivery: Any) -> list[dict[str, Any]]:
        return [
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

    @app.get("/api/v2/projects/{project_id}/character-references")
    def get_project_character_references(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.list_character_reference_decisions(project_id)

    @app.post(
        "/api/v2/projects/{project_id}/character-references",
        status_code=status.HTTP_201_CREATED,
    )
    def select_project_character_reference(
        project_id: str, body: CharacterReferenceDecisionRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.create_character_reference_decision(
                project_id, **body.model_dump(mode="python", by_alias=False)
            )

    @app.post(
        "/api/v2/projects/{project_id}/character-references/{character_id}/revoke"
    )
    def revoke_project_character_reference(
        project_id: str, character_id: str, body: CharacterReferenceRevocationRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.revoke_character_reference_decision(
                project_id,
                character_id=character_id,
                **body.model_dump(mode="python", by_alias=False),
            )

    @app.get("/api/v2/projects/{project_id}/character-reference-proposals")
    def get_project_character_reference_proposals(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {
                "configured": True,
                "proposals": store.media.list_character_reference_proposals(
                    project_id
                ),
            }

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals",
        status_code=status.HTTP_201_CREATED,
    )
    def prepare_project_character_reference_proposal(
        project_id: str, body: CharacterReferenceProposalRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.prepare_character_reference_proposal(
                project_id, **body.model_dump(mode="python", by_alias=False)
            )

    def send_character_reference_proposal(
        project_id: str, proposal_id: str
    ) -> dict[str, Any]:
        if image_dispatcher is None:
            raise ImageJobError(
                "image_dispatch_unavailable",
                "native image specialist dispatch is not configured",
            )
        with opened_project(project_id) as store:
            source = store.media.character_reference_proposal_package_sources(
                project_id, proposal_id
            )
            proposal = source["proposal"]
            package = store.image_exchange_for(proposal).write_package(
                job_id=proposal_id,
                request=proposal["request"],
                request_hash=proposal["requestHash"],
                references=package_references(store, source["references"]),
            )
            proposal = store.media.mark_character_reference_proposal_exported(
                project_id, proposal_id
            )
            image_dispatcher.dispatch(
                job_id=proposal_id,
                package_path=package["packagePath"],
                delivery_path=package["deliveryPath"],
            )
            return {
                "proposal": proposal,
                "packagePath": package["packagePath"],
                "deliveryPath": package["deliveryPath"],
            }

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/send"
    )
    def send_project_character_reference_proposal(
        project_id: str, proposal_id: str
    ) -> dict[str, Any]:
        return send_character_reference_proposal(project_id, proposal_id)

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/cancel"
    )
    def cancel_project_character_reference_proposal(
        project_id: str,
        proposal_id: str,
        body: CharacterReferenceProposalCancellationRequest,
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            proposal = store.media.cancel_character_reference_proposal(
                project_id, proposal_id, body.reason
            )
            return proposal

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/refresh"
    )
    def refresh_project_character_reference_proposal(
        project_id: str, proposal_id: str
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            repository = store.media
            context = repository.character_reference_proposal_delivery_context(
                project_id, proposal_id
            )
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
            exchange = store.image_exchange_for(context)
            try:
                exchange.verify_package(
                    job_id=proposal_id,
                    request=context["request"],
                    request_hash=context["requestHash"],
                    references=references,
                )
                delivery = exchange.read_delivery(
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
                }:
                    repository.record_character_reference_proposal_rejection(
                        project_id, proposal_id, error.code, publication_phase=error.publication_phase,
                    )
                raise
            if delivery is None:
                return {
                    "state": "awaiting_delivery",
                    "candidates": [],
                    "idempotent": False,
                }
            result = repository.record_character_reference_proposal_delivery(
                project_id,
                proposal_id,
                delivery_id=delivery.manifest.delivery_id,
                manifest=delivery.manifest.model_dump(mode="json", by_alias=True),
                manifest_hash=delivery.manifest_hash,
                outputs=delivery_outputs(delivery),
                publish=lambda output: publish_import(
                    store.artifacts, output["content"], output["observed"]
                ),
            )
            if image_dispatcher is not None:
                image_dispatcher.complete(proposal_id)
            return result

    @app.get("/api/v2/projects/{project_id}/same-person-reviews")
    def get_project_same_person_reviews(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.list_same_person_reviews(project_id)

    @app.post(
        "/api/v2/projects/{project_id}/same-person-reviews",
        status_code=status.HTTP_201_CREATED,
    )
    def record_project_same_person_review(
        project_id: str, body: SamePersonReviewRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.record_same_person_review(
                project_id,
                binding_id=body.binding_id,
                expected_review_revision=body.expected_review_revision,
                reviewer=body.reviewer,
                comparisons=[
                    item.model_dump(mode="json", by_alias=True)
                    for item in body.comparisons
                ],
                notes=body.notes,
            )

    @app.get("/api/v2/projects/{project_id}/image-jobs")
    def get_project_image_jobs(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {
                "configured": True,
                "jobs": store.media.list_image_jobs(project_id),
            }

    @app.post(
        "/api/v2/projects/{project_id}/image-jobs", status_code=status.HTTP_201_CREATED
    )
    def prepare_project_image_job(
        project_id: str, body: ProjectFolderImageJobCreateRequest
    ) -> dict[str, Any]:
        target_id = image_job_target_id(body)
        required_entity_id = f"{body.shot_id}:{target_id}"
        require_media_draft_scope(
            body.consumed_draft,
            required_scope="image_direction",
            required_entity_id=required_entity_id,
        )
        draft_payload = {
            "shotId": body.shot_id,
            "targetId": target_id,
            "contextId": body.context_id,
            "presentationChange": body.presentation_change,
        }
        adaptation = (
            {"targetProfile": project_h3_target(body.keyframe_adaptation_profile_id)}
            if body.keyframe_adaptation_profile_id is not None
            else None
        )
        with opened_project(project_id) as store:
            return store.media.prepare_image_job(
                project_id,
                approval_id=body.approval_id,
                shot_id=body.shot_id,
                storyboard_revision=body.storyboard_revision,
                parent_candidate_asset_id=body.parent_candidate_asset_id,
                keyframe_adaptation=adaptation,
                presentation_change=body.presentation_change,
                contract_version=body.contract_version,
                consumed_draft=(
                    body.consumed_draft.entity_id,
                    body.consumed_draft.draft_revision,
                    draft_payload,
                ),
            )

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/copy")
    def copy_project_image_job(project_id: str, job_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            source = store.media.image_job_package_sources(project_id, job_id)
            exchange = store.image_exchange_for(source["job"])
            package = exchange.write_package(
                job_id=job_id,
                request=source["job"]["request"],
                request_hash=source["job"]["requestHash"],
                references=package_references(
                    store, source["references"], character_roles=True
                ),
            )
            job = store.media.mark_image_job_exported(project_id, job_id)
            if image_dispatcher is not None:
                image_dispatcher.dispatch(
                    job_id=job_id,
                    package_path=package["packagePath"],
                    delivery_path=package["deliveryPath"],
                )
            return {
                "job": job,
                "assignment": f"Codex image specialist assignment for {job_id}: read {package['packagePath']}/request.json; use built-in imagegen; write JPEG/PNG outputs and completion.json only under {package['deliveryPath']}.",
                "packagePath": package["packagePath"],
                "deliveryPath": package["deliveryPath"],
            }

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/refresh")
    def refresh_project_image_job(project_id: str, job_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            repository = store.media
            context = repository.image_job_delivery_context(project_id, job_id)
            references: list[tuple[str, str, str]] = []
            identity_hashes: list[str] = []
            for index, reference in enumerate(
                item
                for item in context["request"]["frozenSnapshot"].get("references", [])
                if item.get("role")
                in {"parent_output", "source_keyframe", "character_identity"}
            ):
                role = (
                    f"character_identity:{reference['characterId']}"
                    if reference["role"] == "character_identity"
                    and reference.get("characterId")
                    else reference["role"]
                )
                suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
                references.append(
                    (
                        role,
                        f"reference-{index + 1}-{reference['originalHash'][:16]}{suffix}",
                        reference["originalHash"],
                    )
                )
                if reference["role"] == "character_identity":
                    identity_hashes.append(reference["originalHash"])
            exchange = store.image_exchange_for(context)
            try:
                exchange.verify_package(
                    job_id=job_id,
                    request=context["request"],
                    request_hash=context["requestHash"],
                    references=references,
                )
                delivery = exchange.read_delivery(
                    job_id=job_id,
                    request_hash=context["requestHash"],
                    required_reference_hashes=identity_hashes,
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
                if error.code not in {
                    "image_exchange_not_configured",
                    "image_exchange_invalid",
                    "invalid_job_id",
                    "delivery_manifest_secret",
                }:
                    repository.record_image_job_delivery_rejection(
                        project_id, job_id, error.code
                    )
                raise
            if delivery is None:
                return {
                    "state": "awaiting_delivery",
                    "candidates": [],
                    "idempotent": False,
                }
            adaptation = (
                context["request"].get("frozenSnapshot", {}).get("keyframeAdaptation")
            )
            if adaptation is not None:
                contract = adaptation.get("outputContract")
                if not isinstance(contract, dict):
                    repository.record_image_job_delivery_rejection(
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
                        repository.record_image_job_delivery_rejection(
                            project_id, job_id, "delivery_geometry_mismatch"
                        )
                        raise ImageJobError(
                            "delivery_geometry_mismatch",
                            "keyframe adaptation delivery must use the frozen role and exact profile dimensions",
                        )
            result = repository.record_image_job_delivery(
                project_id,
                job_id,
                delivery_id=delivery.manifest.delivery_id,
                manifest=delivery.manifest.model_dump(mode="json", by_alias=True),
                manifest_hash=delivery.manifest_hash,
                outputs=delivery_outputs(delivery),
                publish=lambda output: publish_import(
                    store.artifacts, output["content"], output["observed"]
                ),
            )
            if image_dispatcher is not None:
                image_dispatcher.complete(job_id)
            return result

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/cancel")
    def cancel_project_image_job(
        project_id: str, job_id: str, body: ImageJobCancellationRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            job = store.media.cancel_image_job(project_id, job_id, body.reason)
            return job

    return app
