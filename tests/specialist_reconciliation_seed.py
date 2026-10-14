"""A closed accepted Script project; dispatch state is always built per case."""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from pathlib import Path
import shutil

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
from plotloom.project_storage import ProjectFolderStorage
from plotloom.project_storage.operational_state import close_blockers
from tests.autopilot_seed_fixtures import seed_files
from tests.creative_delivery_fixtures import _accepted_f4_script


@dataclass(frozen=True)
class AcceptedScriptSeed:
    home: Path
    project_id: str
    files: tuple[tuple[str, str], ...]


@contextmanager
def _exclusive_project(seed):
    with (seed.home / ".project-operation.lock").open("rb") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("accepted Script seed still has active resources") from error
        yield


def build_accepted_script_seed(root):
    storage = ProjectFolderStorage(outputs_root=root / "outputs", application_data_root=root / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        source = store.source_outline_state()
        assert source.source and source.accepted_outline and source.accepted_section_map
        assert source.graph_admission.status == "current" and not source.graph_admission.stale_reasons
        assert not source.section_map_stale_reasons
        for state in (store.cast_state(), store.art_state(), store.script_state()):
            assert state.accepted_review_state.status == "current" and not state.stale_reasons
        assert not close_blockers(store)
        with store.repository.engine.connect() as connection:
            for model in set(CANDIDATE_ROWS.values()):
                table = model.__table__.name
                assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}" WHERE status != \'accepted\'').scalar() == 0
            for table in (
                "v2_autopilot_runs", "v2_autopilot_exec_attempts", "v2_generation_runs",
                "v2_media_tasks", "v2_video_jobs", "v2_image_jobs",
                "v2_character_reference_proposals", "v2_art_reference_proposals",
                "v2_production_bridge_intent_jobs",
            ):
                assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
        home, project = store.home, store.manifest.project_id
    finally:
        store.close()
    assert not (storage.application.root / "specialists").exists()
    seed = AcceptedScriptSeed(home, project, seed_files(home))
    with _exclusive_project(seed):
        assert seed_files(home) == seed.files
    return seed


def open_accepted_script_copy(storage, seed):
    if seed_files(seed.home) != seed.files:
        raise ValueError("accepted Script seed changed after closure")
    destination = storage.projects.outputs_root / seed.home.name
    with _exclusive_project(seed):
        if seed_files(seed.home) != seed.files:
            raise ValueError("accepted Script seed changed after closure")
        shutil.copytree(seed.home, destination)
        if seed_files(destination) != seed.files:
            raise ValueError("accepted Script copy differs from complete seed")
        for relative, _digest in seed.files:
            source, copied = (seed.home / relative).stat(), (destination / relative).stat()
            if (source.st_dev, source.st_ino) == (copied.st_dev, copied.st_ino):
                raise ValueError("accepted Script copy shares a seed file")
    store = storage.projects.open(seed.project_id)
    try:
        assert store.home == destination
        assert store.script_state().accepted_review_state.status == "current"
    except BaseException:
        store.close()
        raise
    return store
