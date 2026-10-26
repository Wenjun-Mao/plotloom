from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, status

from ..image_job_contracts import (
    CharacterImportedAppearanceRequest,
    CharacterReferenceDecisionRequest,
    CharacterReferenceProposalCancellationRequest,
    CharacterReferenceProposalRequest,
    CharacterReferenceRevocationRequest,
    ImageJobError,
)
from ..managed_media import publish_import
from ..specialist_settings import ImageSpecialist
from .image_projections import (
    delivery_outputs,
    delivery_task_binding,
    package_references,
)


def register_project_character_reference_routes(
    app: FastAPI,
    opened_project: Callable[[str], Any],
    *,
    image_dispatcher: ImageSpecialist | None = None,
) -> None:
    @app.get("/api/v2/projects/{project_id}/character-references")
    def get_project_character_references(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return store.media.list_character_reference_decisions(project_id)

    @app.get("/api/v2/projects/{project_id}/character-imported-appearances")
    def get_imported_character_appearances(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {
                "appearances": store.media.list_imported_character_appearances(
                    project_id
                )
            }

    @app.post(
        "/api/v2/projects/{project_id}/character-imported-appearances",
        status_code=status.HTTP_201_CREATED,
    )
    def attach_imported_character_appearance(
        project_id: str, body: CharacterImportedAppearanceRequest
    ) -> dict[str, Any]:
        # assetId belongs to the existing managed-import owner; this endpoint
        # only establishes subject/context membership and never selects it.
        with opened_project(project_id) as store:
            return store.media.attach_imported_character_appearance(
                project_id,
                character_id=body.character_id,
                asset_id=body.asset_id,
                label=body.label,
                expected_cast_revision=body.expected_cast_revision,
            )

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
                "proposals": store.media.list_character_reference_proposals(project_id),
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

    @app.post(
        "/api/v2/projects/{project_id}/character-reference-proposals/{proposal_id}/send"
    )
    def send_project_character_reference_proposal(
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
            native_task_binding = image_dispatcher.configured_task_binding()
            image_dispatcher.bind_delivery(proposal_id, native_task_binding)
            package = store.image_exchange_for(proposal).write_package(
                job_id=proposal_id,
                request=proposal["request"],
                request_hash=proposal["requestHash"],
                references=package_references(store, source["references"]),
                native_task_binding=native_task_binding,
            )
            exported = []
            image_dispatcher.dispatch(
                context={"projectId": project_id, "stage": "character-reference"},
                job_id=proposal_id,
                package_path=package["packagePath"],
                delivery_path=package["deliveryPath"],
                before_send=lambda: exported.append(
                    store.media.mark_character_reference_proposal_exported(
                        project_id, proposal_id, require_prepared=True
                    )
                ),
                expected_task_id=str(native_task_binding.task_id),
            )
            return {
                "proposal": exported[0],
                "packagePath": package["packagePath"],
                "deliveryPath": package["deliveryPath"],
            }

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
            native_task_binding = delivery_task_binding(
                image_dispatcher, proposal_id, context["request"]
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
                    native_task_binding=native_task_binding,
                )
                delivery = exchange.read_delivery(
                    job_id=proposal_id,
                    request_hash=context["requestHash"],
                    require_executor_provenance=True,
                    require_executor_pin=context["request"]
                    .get("specialistPreflight", {})
                    .get("version")
                    in {"p1.5-pin.v1", "p1.5-pin.v2"},
                    expected_executor_skill_version=context["request"]
                    .get("specialistPreflight", {})
                    .get("skillVersion"),
                    expected_executor_contract=context["request"]
                    .get("specialistPreflight", {})
                    .get("executionContract", "codex_specialist.v2"),
                    expected_native_task_binding=native_task_binding,
                )
            except ImageJobError as error:
                if error.code not in {
                    "image_exchange_not_configured",
                    "image_exchange_invalid",
                    "invalid_job_id",
                }:
                    repository.record_character_reference_proposal_rejection(
                        project_id,
                        proposal_id,
                        error.code,
                        publication_phase=error.publication_phase,
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
                manifest=delivery.manifest.canonical_payload(),
                manifest_hash=delivery.manifest_hash,
                outputs=delivery_outputs(delivery),
                publish=lambda output: publish_import(
                    store.artifacts, output["content"], output["observed"]
                ),
            )
            if image_dispatcher is not None:
                image_dispatcher.complete(proposal_id)
            return result
