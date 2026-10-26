"""Prior-reader compatibility boundary, exercised only on disposable project homes."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from tests.working_input_preservation import preservation_inventory


def test_prior_reader_refuses_new_data_and_current_reader_preserves_exact_rows(tmp_path: Path):
    prior = tmp_path / "prior-reader"
    prior.mkdir()
    archive = subprocess.run(["git", "archive", "4c6db5ff", "src/plotloom"], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(prior, filter="data")
    storage = ProjectFolderStorage(outputs_root=tmp_path / "data" / "outputs", application_data_root=tmp_path / "data" / "application")
    blank = storage.projects.create(None)
    blank_home = blank.home
    blank.close()
    current = storage.projects.create(FIXED_CHINESE_BRIEF)
    current_home = current.home
    raw = FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)
    raw["targetPlaythroughSeconds"] = ""
    saved = current.save_authoring_draft(editor_scope="brief", entity_id="root", base_canonical_revision=1, expected_draft_revision=0, payload=raw)
    current.close()
    before = preservation_inventory(tmp_path / "data")
    probe = '''
import json, sys
from pathlib import Path
import plotloom
from plotloom.project_storage import ProjectStore
from plotloom.persistence.project.drafts import ProjectDraftPersistence
assert str(Path(plotloom.__file__).resolve()).startswith(sys.argv[1])
result = {}
for name, home in [("nullBrief", sys.argv[2]), ("workingPayload", sys.argv[3])]:
    try:
        store = ProjectStore.open(Path(home), read_only=True, admission="authority")
        try:
            if name == "nullBrief":
                store.project()
            else:
                draft = store.authoring_drafts()[0]
                ProjectDraftPersistence._validate_authoring_draft_payload(draft.editor_scope, draft.payload)
        finally:
            store.close()
    except Exception as error:
        result[name] = {"refused": True, "type": type(error).__name__, "message": str(error)}
    else:
        raise AssertionError(name + " unexpectedly accepted by prior reader")
print(json.dumps(result))
'''
    env = {**os.environ, "PYTHONPATH": str(prior / "src")}
    completed = subprocess.run([sys.executable, "-c", probe, str(prior), str(blank_home), str(current_home)], cwd=prior, env=env, check=True, capture_output=True, text=True)
    refusal = json.loads(completed.stdout)
    assert refusal["nullBrief"]["refused"] and refusal["workingPayload"]["refused"]
    assert preservation_inventory(tmp_path / "data") == before
    reopened = ProjectStore.open(blank_home, read_only=True, admission="authority")
    try:
        assert reopened.project().brief is None
    finally:
        reopened.close()
    reopened = ProjectStore.open(current_home, read_only=True, admission="authority")
    try:
        assert reopened.project().brief == FIXED_CHINESE_BRIEF
        assert reopened.authoring_drafts()[0] == saved
    finally:
        reopened.close()
    assert preservation_inventory(tmp_path / "data") == before
    print(json.dumps({"prior": "4c6db5ff", "refusal": refusal, "logicalRowsAndFilesUnchanged": True}, ensure_ascii=False))
