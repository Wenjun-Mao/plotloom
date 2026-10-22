from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage import ProjectFolderStorage, ProjectStorageError
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.project_storage.operational_state import ProjectAccessLease, ProjectBusyError
from plotloom.project_storage.project_handle import ProjectStore


@pytest.fixture
def known_home(tmp_path: Path):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, home = store.project().id, store.home
    store.close()
    return storage, project_id, home


def test_known_busy_home_remains_busy_instead_of_missing(known_home) -> None:
    storage, project_id, home = known_home
    lease = ProjectAccessLease.acquire(home, mode="exclusive")
    try:
        assert storage.projects.discover() == []
        with pytest.raises(ProjectBusyError, match="project_busy"):
            storage.projects.open(project_id)
        response = TestClient(create_project_folder_authoring_app(storage)).get(
            f"/api/v2/projects/{project_id}",
        )
        assert response.status_code == 409
        assert response.json()["code"] == "project_busy"
    finally:
        lease.close()
    reopened = storage.projects.open(project_id)
    assert reopened.project().id == project_id
    reopened.close()


def test_known_home_preserves_store_admission_failure(known_home, monkeypatch) -> None:
    storage, project_id, _home = known_home

    def unavailable(*_args, **_kwargs):
        raise ProjectStorageCorruptionError("known home failed admission")

    monkeypatch.setattr(ProjectStore, "open", unavailable)
    assert storage.projects.discover() == []
    with pytest.raises(ProjectStorageCorruptionError, match="known home failed admission"):
        storage.projects.open(project_id)


def test_known_home_open_does_not_admit_unrelated_stores(known_home, monkeypatch) -> None:
    storage, project_id, home = known_home
    other = storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"title": "Other"}))
    other.close()
    admitted = []
    original = ProjectStore.open

    def tracked(path, *args, **kwargs):
        admitted.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(ProjectStore, "open", tracked)
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert admitted == [home]


def test_truly_absent_identity_remains_missing(known_home) -> None:
    storage, _project_id, _home = known_home
    with pytest.raises(ProjectStorageError, match="project not found"):
        storage.projects.open("absent-project")


def test_duplicate_manifest_identity_is_refused(known_home) -> None:
    storage, project_id, home = known_home
    shutil.copytree(home, home.parent / "duplicate-home")
    with pytest.raises(ProjectStorageCorruptionError, match="multiple project homes"):
        storage.projects.open(project_id)
