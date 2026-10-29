"""Revoked-project GC must prove absence without erasing uncertain evidence."""
from pathlib import Path

import pytest
from codex_exec_supervisor_errors import CodexExecSupervisorError
from tests.services.creator_workbench.test_project_garbage_collection import deleted_project, allow


def test_inaccessible_original_home_is_not_positive_absence(supervisor, monkeypatch):
    original, evidence, request = deleted_project(supervisor)
    home = supervisor.outputs_root / ("deleted__" + str(original.project_id))
    original_lstat = Path.lstat

    def inaccessible(path, *args, **kwargs):
        if path == home:
            raise PermissionError("controlled inaccessible home")
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", inaccessible)
    with pytest.raises(CodexExecSupervisorError, match="revoked project home"):
        supervisor.project_gc_preview(request)
    assert (evidence / "private.log").read_text() == "private historical evidence"
    assert supervisor._row(original.attempt_id) is not None


@pytest.mark.parametrize("change", ["missing", "symlink", "replaced"])
def test_outputs_identity_change_invalidates_existing_gc_preview(supervisor, tmp_path, change):
    original, evidence, request = deleted_project(supervisor)
    request = allow(supervisor, request)
    outputs = supervisor.outputs_root
    retained = tmp_path / "retained-outputs"
    outputs.rename(retained)
    if change == "symlink":
        outputs.symlink_to(retained, target_is_directory=True)
    elif change == "replaced":
        outputs.mkdir()
    with pytest.raises((CodexExecSupervisorError, OSError)):
        supervisor.collect_deleted_project(request)
    assert retained.is_dir()
    assert (evidence / "private.log").read_text() == "private historical evidence"
    assert supervisor._row(original.attempt_id) is not None
