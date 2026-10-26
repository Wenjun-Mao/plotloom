from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI, status

from ..managed_media import publish_import
from ..image_job_contracts import (
    ImageJobError,
)
from ..same_person_review_contracts import SamePersonReviewRequest
from ..specialist_settings import ImageSpecialist
from .project_folder_image_send import register_image_send_route
from plotloom.api.contracts import ImageJobCancellationRequest


from .image_projections import (
    package_references,
    delivery_outputs,
    current_task_binding,
    delivery_task_binding,
)


def register_project_folder_image_job_routes(
    app: FastAPI,
    opened_project: Callable[[str], Any],
    *,
    require_media_draft_scope: Callable[..., Any],
    project_h3_target: Callable[[str], dict[str, Any]],
    image_dispatcher: ImageSpecialist | None = None,
) -> None:
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
                    item.model_dump(mode="json", by_alias=True, exclude_none=True)
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

    from .project_folder_image_prepare import (
        register_image_prepare_route,
        image_job_target_id,
    )

    register_image_prepare_route(
        app,
        opened_project,
        image_job_target_id,
        require_media_draft_scope,
        project_h3_target,
    )

    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/copy")
    def copy_project_image_job(project_id: str, job_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            source = store.media.image_job_package_sources(project_id, job_id)
            exchange = store.image_exchange_for(source["job"])
            native_task_binding = current_task_binding()
            if image_dispatcher is not None:
                image_dispatcher.bind_delivery(job_id, native_task_binding)
            package = exchange.write_package(
                job_id=job_id,
                request=source["job"]["request"],
                request_hash=source["job"]["requestHash"],
                references=package_references(
                    store, source["references"], character_roles=True
                ),
                native_task_binding=native_task_binding,
            )
            job = store.media.mark_image_job_exported(project_id, job_id)
            return {
                "job": job,
                "assignment": f"Codex image specialist assignment for {job_id}: read {package['packagePath']}/request.json and follow {package['packagePath']}/COPY_ASSIGNMENT.txt exactly; use built-in imagegen and deliver only under {package['deliveryPath']}.",
                "packagePath": package["packagePath"],
                "deliveryPath": package["deliveryPath"],
            }

    register_image_send_route(app, opened_project, image_dispatcher, package_references)

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
                in {
                    "parent_output",
                    "source_keyframe",
                    "character_identity",
                    "scene_continuity",
                }
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
                if reference["role"] in {"character_identity", "scene_continuity"}:
                    identity_hashes.append(reference["originalHash"])
            exchange = store.image_exchange_for(context)
            native_task_binding = delivery_task_binding(
                image_dispatcher, job_id, context["request"]
            )
            try:
                exchange.verify_package(
                    job_id=job_id,
                    request=context["request"],
                    request_hash=context["requestHash"],
                    references=references,
                    native_task_binding=native_task_binding,
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
            from ..persistence.project.image_adaptation_source import (
                validate_adaptation_outputs,
            )

            try:
                validate_adaptation_outputs(
                    context["request"], delivery_outputs(delivery)
                )
            except ImageJobError as error:
                repository.record_image_job_delivery_rejection(
                    project_id, job_id, error.code
                )
                raise
            result = repository.record_image_job_delivery(
                project_id,
                job_id,
                delivery_id=delivery.manifest.delivery_id,
                manifest=delivery.manifest.canonical_payload(),
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
