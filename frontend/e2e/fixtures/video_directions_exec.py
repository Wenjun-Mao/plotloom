"""Synthetic draft/check host for browser transport tests, never live semantic QA."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from tests.autopilot_controller_fixtures import PIN
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.codex_exec_fixtures import install_profile
from tests.video_fidelity_fixtures import fidelity_for


def install(app):
    registry = app.state.specialists
    if getattr(registry, "_browser_video_directions_host", None):
        return
    install_profile(registry)
    original_pin = CreativeHandoffExchange.current_execution_pin
    CreativeHandoffExchange.current_execution_pin = lambda owner, stage: PIN if stage == "video-directions" else original_pin(owner, stage)

    def candidate(_store, request):
        if request.source.get("operation") == "fidelity-check":
            return fidelity_for(request)
        return {"version": "video-directions.draft.v1", "targets": [
            {"shotId": target["shotId"], "sourceHash": target["sourceHash"], "fields": [
                {"path": item["path"], "english": item["text"] if item["text"].isascii()
                    else "Preserve the frozen visual or sound requirement exactly. Add no speech or text."}
                for item in target["sources"]]}
            for target in request.input_artifacts["video-targets.json"]["targets"]]}

    host = FakeCodexExecHost(app.state.project_folder_storage, registry, candidate_factory=candidate)
    registry.codex_exec_admit, registry.codex_exec_status = host.admit, host.status
    registry.codex_exec_cancel, registry.codex_exec_suspend = host.cancel, host.suspend
    registry.codex_exec_resume = host.admit
    registry._browser_video_directions_host = host
    app.state.video_batch_runtime.interval_seconds = 0.1
