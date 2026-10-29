"""Synthetic semantic verdicts with real frozen native receipts; never live QA."""
from contextlib import closing
from hashlib import sha256
from unittest.mock import patch

from plotloom.creative_handoff_exchange import CreativeHandoffExchange
from plotloom.video_directions_contract import candidate_identity
from plotloom.video_fidelity_contracts import CHECK_DIMENSIONS
from tests.autopilot_controller_fixtures import PIN
from tests.autopilot_fake_exec_host import FakeCodexExecHost
from tests.codex_exec_fixtures import install_profile


def fidelity_for(request, *, reject=False):
    return {"version": "video-directions.fidelity.v1", "targets": [
        {"shotId": item["shotId"], "sourceHash": item["sourceHash"],
            "candidateHash": candidate_identity(item["directions"]),
            "compiledPromptSha256": sha256(item["compiledPrompt"].encode()).hexdigest(),
            "verdict": "reject" if reject else "pass", "checkedPaths": [field["path"] for field in item["directions"]["fields"]],
            "checkedDimensions": list(CHECK_DIMENSIONS),
            "findings": [{"path": "shot.action", "code": "negation", "message": "候选遗漏了来源的否定要求。"}] if reject else []}
        for item in request.input_artifacts["video-targets.json"]["targets"]]}


def checked_batch(service, project_id, view, draft):
    install_profile(service.registry)
    if not hasattr(service.registry, "_video_fidelity_test_host"):
        host = FakeCodexExecHost(service.storage, service.registry, candidate_factory=lambda _store, request: fidelity_for(request))
        service.registry.codex_exec_admit = host.admit
        service.registry.codex_exec_status = host.status
        service.registry.codex_exec_cancel = host.cancel
        service.registry.codex_exec_suspend = host.suspend
        service.registry._video_fidelity_test_host = host
    with patch.object(CreativeHandoffExchange, "current_execution_pin", return_value=PIN):
        view = service.edit_directions(project_id, view["revision"], draft)
        for _ in range(4):
            from plotloom.video_batch_directions import advance_directions
            with closing(service.storage.projects.open(project_id)) as store:
                advance_directions(store, service.registry, service.grants, view, checking=True)
            view = service.current(project_id)
            if view["state"] in {"ready", "translation_rejected", "blocked"}:
                break
    assert view["state"] == "ready", view["execution"].get("error")
    return view
