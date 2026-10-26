from __future__ import annotations

from hashlib import sha256
from typing import Any

from ..exceptions import (
    InvalidTransitionError,
)
from ..image_job_contracts import (
    NativeTaskBinding,
)
from ..image_exchange_references import PackageReference
from ..specialist_settings import ImageSpecialist


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
            raise InvalidTransitionError("frozen image reference bytes are unavailable")
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


def current_task_binding() -> NativeTaskBinding:
    return NativeTaskBinding(mode="current_task")


def delivery_task_binding(
    image_dispatcher: ImageSpecialist | None, job_id: str, request: dict | None = None
) -> NativeTaskBinding:
    if image_dispatcher is None:
        return current_task_binding()
    execution_contract = (request or {}).get("executionContract") or (
        request or {}
    ).get("specialistPreflight", {}).get("executionContract")
    require_bound = execution_contract == "codex_specialist.v3"
    return image_dispatcher.delivery_task_binding(job_id, require_bound=require_bound)
