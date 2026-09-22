"""User-reachable, explicit F5 proposal review and canonical installation."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI

from ..production_bridge_contracts import ProductionBridgeAcceptRequest, ProductionBridgeState


def register_project_folder_production_bridge_routes(app: FastAPI, opened_project: Callable[[str], Any]) -> None:
    @app.get("/api/v2/projects/{project_id}/production-bridge", response_model=ProductionBridgeState)
    def get_production_bridge(project_id: str) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return store.production_bridge_state()

    @app.post("/api/v2/projects/{project_id}/production-bridge/proposals", response_model=ProductionBridgeState)
    def prepare_production_bridge(project_id: str) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return store.prepare_production_bridge()

    @app.post("/api/v2/projects/{project_id}/production-bridge/accept", response_model=ProductionBridgeState)
    def accept_production_bridge(project_id: str, body: ProductionBridgeAcceptRequest) -> ProductionBridgeState:
        with opened_project(project_id) as store:
            return store.accept_production_bridge(body)
