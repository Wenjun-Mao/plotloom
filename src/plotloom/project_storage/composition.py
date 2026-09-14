"""Application-facing composition of project and installation storage."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..domain import GenerationRun
from .application_store import ApplicationStore
from .format import ProjectStorageConfinementError
from .registry import ProjectDirectoryRegistry

if TYPE_CHECKING:
    from ..pipeline import RunSecretBroker, TextProviderResolver


class ProjectFolderStorage:
    """Explicit composition root for the project/application ownership split."""

    def __init__(self, *, outputs_root: Path, application_data_root: Path) -> None:
        resolved_outputs = outputs_root.expanduser().resolve()
        resolved_application = application_data_root.expanduser().resolve()
        if (
            resolved_outputs == resolved_application
            or resolved_outputs.is_relative_to(resolved_application)
            or resolved_application.is_relative_to(resolved_outputs)
        ):
            raise ProjectStorageConfinementError(
                "outputs and application data roots must be separate, non-overlapping directories"
            )
        self.projects = ProjectDirectoryRegistry(outputs_root)
        self.application = ApplicationStore(application_data_root)

    def execute_selected_text_pipeline(
        self,
        project_id: str,
        *,
        provider_resolver: "TextProviderResolver",
        exact_repair: bool = False,
        secret_broker: "RunSecretBroker | None" = None,
        session_api_key: str | None = None,
    ) -> GenerationRun:
        """Run the selected public profile against the project-owned database."""
        from ..project_generation_storage import ProjectPipelineExecutor

        return ProjectPipelineExecutor(provider_resolver).execute(
            self.projects.open(project_id),
            profile=self.application.selected_text_profile(),
            exact_repair=exact_repair,
            secret_broker=secret_broker,
            session_api_key=session_api_key,
        )
