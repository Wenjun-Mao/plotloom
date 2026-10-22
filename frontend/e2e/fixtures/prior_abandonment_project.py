"""Build a valued, stopped UNKNOWN prior home using finite offline fixtures."""
import argparse
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from plotloom.autopilot_contracts import RunControlRequest
from tests.autopilot_compact_text_fixtures import (
    build_compact_two_cut_text_prefix,
    compact_safety_image_environment,
)
from tests.autopilot_continuation_layout_fixtures import retain_pre_continuation_layout
from tests.test_autopilot_image_safety import reach


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--application", type=Path, required=True)
    parser.add_argument("--fault", action="store_true")
    parser.add_argument("--refresh-title", action="store_true")
    parser.add_argument("--current-state", choices=("cancelled", "paused"))
    args = parser.parse_args()
    args.outputs = args.outputs.resolve()
    args.application = args.application.resolve()
    if args.refresh_title:
        path = args.application / "prior-abandonment-fixture.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        home = Path(fixture["home"])
        assert home.parent == args.outputs and not home.is_symlink()
        with sqlite3.connect(home / "project.sqlite3") as connection:
            brief = json.loads(connection.execute("SELECT brief FROM v2_projects WHERE id=?", (fixture["projectId"],)).fetchone()[0])
            fixture["title"] = brief["title"] + " · 新预览"
            connection.execute("UPDATE v2_projects SET brief=?,revision=revision+1 WHERE id=?",
                (json.dumps(brief | {"title": fixture["title"]}, ensure_ascii=False), fixture["projectId"]))
        path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        return
    root = args.application / ".prior-abandonment-fixture"
    seed = build_compact_two_cut_text_prefix(root / "seed")
    with pytest.MonkeyPatch.context() as patch:
        storage, _registry, service, view, _images, _text = compact_safety_image_environment(root / "copy", patch, seed, auto_deliver=False)
        try:
            sent, _checkpoint = reach(storage, service, view, "character-reference", "sent")
            service.control(view.project_id, RunControlRequest(expected_revision=sent.revision,
                action="pause" if args.current_state == "paused" else "cancel"))
            with closing(storage.projects.open(view.project_id)) as store:
                home, project = store.home, store.project()
                with store.repository.engine.connect() as connection:
                    attempts = [json.loads(row[0]) for row in connection.exec_driver_sql("SELECT snapshot FROM v2_autopilot_exec_attempts ORDER BY id")]
        finally:
            service.close()
    if args.current_state is None:
        retain_pre_continuation_layout(home)
    destination = args.outputs / home.name
    shutil.move(str(home), destination)
    fixture = {"projectId": project.id, "title": project.brief.title, "home": str(destination),
        "attempts": attempts, "previewHash": "a" * 64, "revoked": False, "calls": [],
        "fault": args.fault, "faultConsumed": False, "blocked": False,
        "currentState": args.current_state, "cancelAttemptIds": [], "eraseCount": 0}
    (args.application / "prior-abandonment-fixture.json").write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"projectId": project.id, "title": project.brief.title, "home": str(destination)}))


if __name__ == "__main__":
    main()
