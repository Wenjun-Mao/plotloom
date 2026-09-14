"""Regression guard for the breaking removal of the shared runtime."""

from __future__ import annotations

import importlib.util

import plotloom
import plotloom.api
import plotloom.persistence


RETIRED_MODULES = (
    "plotloom.persistence.legacy_repository",
    "plotloom.api.application",
    "plotloom.api.projects",
    "plotloom.api.generation",
    "plotloom.api.image_jobs",
    "plotloom.api.managed_media",
    "plotloom.api.video",
    "plotloom.media_jobs",
)


def test_shipped_and_tooling_import_surface_has_no_shared_runtime_facade() -> None:
    for module_name in RETIRED_MODULES:
        assert importlib.util.find_spec(module_name) is None
    assert not hasattr(plotloom, "SQLiteRepository")
    assert not hasattr(plotloom, "create_app")
    assert not hasattr(plotloom.persistence, "SQLiteRepository")
    assert not hasattr(plotloom.api, "create_app")
