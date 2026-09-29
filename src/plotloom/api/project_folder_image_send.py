"""Explicit shot-image dispatch, separate from manual package export."""
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI

from ..image_job_contracts import ImageJobError


def register_image_send_route(app: FastAPI, opened_project: Callable, dispatcher: Any, package_references: Callable) -> None:
    @app.post("/api/v2/projects/{project_id}/image-jobs/{job_id}/send")
    def send_project_image_job(project_id: str, job_id: str) -> dict[str, Any]:
        if dispatcher is None:
            raise ImageJobError("image_dispatch_unavailable", "请先配置图像生成助手。")
        with opened_project(project_id) as store:
            source = store.media.image_job_package_sources(project_id, job_id)
            package = store.image_exchange_for(source["job"]).write_package(
                job_id=job_id, request=source["job"]["request"], request_hash=source["job"]["requestHash"],
                references=package_references(store, source["references"], character_roles=True),
            )
            exported = []
            dispatcher.dispatch(job_id=job_id, package_path=package["packagePath"], delivery_path=package["deliveryPath"],
                before_send=lambda: exported.append(store.media.mark_image_job_exported(project_id, job_id, require_prepared=True)))
            return {"job": exported[0], **package}
