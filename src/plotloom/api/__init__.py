"""Public API composition façade with independent factory imports."""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    """Load the retained or direct factory only when its caller requests it.

    The project-folder factory must remain usable when the temporary retained
    application repository has been retired. Importing this public package is
    therefore not permission to initialize that compatibility composition.
    """

    if name == "create_app":
        from .application import create_app

        globals()[name] = create_app
        return create_app
    if name == "create_project_folder_authoring_app":
        from .project_folder import create_project_folder_authoring_app

        globals()[name] = create_project_folder_authoring_app
        return create_project_folder_authoring_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_app", "create_project_folder_authoring_app"]
