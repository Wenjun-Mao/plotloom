"""Explicit, non-publishing settlement for all three image request owners."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import FastAPI

from ..image_job_contracts import ImageJobError
from ..image_terminal_outcome import ImageTerminalReview, read_blocked_outcome, review_record
from ..specialist_settings import SpecialistRegistry

Target = Literal["image_job", "character_reference_proposal", "art_reference_proposal"]
OWNERS = {
    "image_job": "image_job_delivery_context",
    "character_reference_proposal": "character_reference_proposal_delivery_context",
    "art_reference_proposal": "art_reference_proposal_delivery_context",
}


def register_image_terminal_routes(app: FastAPI, opened_project: Callable[[str], Any], registry: SpecialistRegistry):
    def inspect(store, project_id, target, job_id):
        context = getattr(store.media, OWNERS[target])(project_id, job_id)
        exchange = store.image_exchange_for(context)
        references = []
        for index, reference in enumerate(item for item in context["request"]["frozenSnapshot"].get("references", [])
                                          if item.get("role") in {"parent_output", "source_keyframe", "character_identity"}):
            role = reference["role"]
            if role == "character_identity" and reference.get("characterId"):
                role = f"character_identity:{reference['characterId']}"
            suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
            references.append((role, f"reference-{index + 1}-{reference['originalHash'][:16]}{suffix}", reference["originalHash"]))
        exchange.verify_package(job_id=job_id, request=context["request"], request_hash=context["requestHash"], references=references)
        return read_blocked_outcome(exchange, context)

    @app.get("/api/v2/projects/{project_id}/image-terminal/{target}/{job_id}")
    def preview(project_id: str, target: Target, job_id: str):
        with opened_project(project_id) as store:
            outcome = inspect(store, project_id, target, job_id)
            registry.assert_image_terminal_identity(job_id, outcome["marker"]["taskId"])
            return outcome

    @app.post("/api/v2/projects/{project_id}/image-terminal/{target}/{job_id}/settle")
    def settle(project_id: str, target: Target, job_id: str, body: ImageTerminalReview):
        with opened_project(project_id) as store:
            outcome = inspect(store, project_id, target, job_id)
            record = review_record(project_id, target, outcome, body)
            registry.settle_image_blocked(job_id, record)
            return {"state": "completed", "outcome": "blocked", "candidates": []}
