"""Only host acknowledgment/one erasure fault are offline seams; routes are real."""
import json
import shutil
from pathlib import Path

from plotloom.project_abandonment_contracts import AbandonmentPreview


def install(app, application_root):
    path = application_root / "prior-abandonment-fixture.json"

    def load():
        return json.loads(path.read_text(encoding="utf-8"))

    def save(value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def host(packet, *, revoke=False):
        value = load()
        assert packet.project_id == value["projectId"] and packet.project_home == value["home"]
        assert [attempt.model_dump(mode="json", by_alias=True) for attempt in sorted(packet.attempts, key=lambda item: str(item.attempt_id))] == value["attempts"]
        value["calls"].append("revoke" if revoke else "preview")
        if revoke:
            assert packet.expected_preview_hash == value["previewHash"] and not value["blocked"]
            value["revoked"] = True
        save(value)
        return AbandonmentPreview(project_id=packet.project_id, preview_hash=value["previewHash"],
            eligible=not value["blocked"], blockers=["exact-original-task: local ownership unresolved"] if value["blocked"] else [],
            unknown_attempt_ids=[str(attempt.attempt_id) for attempt in packet.attempts if attempt.state not in {"completed", "failed", "settled"}],
            revoked=value["revoked"])

    app.state.autopilot_service.registry.codex_exec_abandonment = host
    original = shutil.rmtree

    def erase(target, *args, **kwargs):
        value = load()
        if Path(target) == Path(value["home"]) and value["fault"] and not value["faultConsumed"]:
            assert value["revoked"]
            value["faultConsumed"] = True
            save(value)
            raise PermissionError("test-owned fault after ACK and manifest withdrawal")
        return original(target, *args, **kwargs)

    erase.avoids_symlink_attacks = original.avoids_symlink_attacks
    shutil.rmtree = erase
