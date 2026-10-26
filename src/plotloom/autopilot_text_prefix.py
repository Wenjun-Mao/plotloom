"""Qualification ownership of the production text controller's install prefix."""
from contextlib import closing

from .autopilot_contracts import RunControlRequest
from .autopilot_service import AutopilotService
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError


class AutopilotTextPrefix:
    """Hold the existing process lease before any ordinary runtime starts.

    The caller must shut down the ordinary runtime before leaving this owner.
    Only the existing text controller advances; image owners are never invoked.
    Successful installation is durably paused before the lease can be released.
    """
    def __init__(self, storage, registry):
        self.service = AutopilotService(storage, registry)
        self.storage = storage

    def __enter__(self):
        if not self.service.acquire_controller():
            raise InvalidTransitionError("another production controller owns this installation")
        return self

    def __exit__(self, *_error):
        self.service.release_controller()

    def launch(self, project_id, request):
        if self.service._descriptor is None:
            raise InvalidTransitionError("text prefix requires its process lease")
        return self.service.launch(project_id, request)

    def step(self, project_id):
        if self.service._descriptor is None:
            raise InvalidTransitionError("text prefix requires its process lease")
        with closing(self.storage.projects.open(project_id)) as store:
            view = store.repository.autopilot.current(project_id)
            if view is None:
                raise InvalidTransitionError("text prefix requires an existing launch")
            if any(c["operationKey"] == "installation" for c in view.checkpoints):
                installation = store.production_bridge_state().installation
                if installation is None or installation.status != "current":
                    raise InvalidTransitionError("installed text is no longer current")
                installed = True
            elif self.service._can_advance(store, project_id):
                installed = False
                store.repository.autopilot.claim(project_id, self.service.claim)
                view = store.repository.autopilot.current(project_id)
                try:
                    self.service.controller.advance(store, view, self.service.claim)
                except ImageJobError as error:
                    waiting = error.code in {"codex_exec_capacity_deferred", "codex_exec_outcome_unknown"}
                    store.repository.autopilot.blocker(project_id, code=error.code, message=str(error), waiting=waiting)
                except (InvalidTransitionError, ValueError) as error:
                    store.repository.autopilot.blocker(project_id, code="contract_blocked", message=str(error))
                view = store.repository.autopilot.current(project_id)
                installed = any(c["operationKey"] == "installation" for c in view.checkpoints)
            else:
                installed = False
        if installed:
            self.pause(project_id)
        with closing(self.storage.projects.open(project_id)) as store:
            return store.repository.autopilot.current(project_id)

    def pause(self, project_id):
        with closing(self.storage.projects.open(project_id)) as store:
            view = store.repository.autopilot.current(project_id)
        if view is not None and view.state in {"running", "waiting"}:
            return self.service.control(project_id,
                RunControlRequest(action="pause", expected_revision=view.revision), expected_run_id=view.id)
        return view
