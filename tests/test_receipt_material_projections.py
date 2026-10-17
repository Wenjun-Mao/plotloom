"""Receipt segments share row construction, never authority across boundaries."""
import json
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from plotloom.autopilot_contracts import OperationScope
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.codec import stable_hash
from plotloom.persistence.project import autopilot_closure as closure
from plotloom.persistence.schema import ProjectRow
from plotloom.project_storage import ProjectFolderStorage

PROTECTED = tuple(name for name in closure.MATERIAL_TABLES if name != "v2_managed_assets")
CANCELLATIONS = ("v2_image_jobs", "v2_character_reference_proposals", "v2_art_reference_proposals")


class ProjectionSession:
    """Deterministic full-row results with independent canonical expectations."""
    def __init__(self, *, populated, geometry):
        self.events = []
        stamp = datetime(2026, 10, 14, 12, 34, 56, 789, tzinfo=timezone.utc)
        self.rows = {name: [
            {"id": "z", "created_at": stamp, "value": {"中文": [None, True, 7]}},
            {"id": "a", "created_at": None, "value": {"nested": {"b": 2, "a": 1}}},
        ] if populated else [] for name in closure.MATERIAL_TABLES}
        self.preparations = [("z", {"geometryPreparation": {"width": 1280}}),
            ("a", {"geometryPreparation": {"width": 720}}), ("null", {"geometryPreparation": None})] if geometry else []
        self.cancelled = {name: ["z", "a"] if populated else [] for name in CANCELLATIONS}
        self.expected = {name: sorted([
            {"id": "z", "created_at": "2026-10-14T12:34:56.000789+00:00", "value": {"中文": [None, True, 7]}},
            {"id": "a", "created_at": None, "value": {"nested": {"b": 2, "a": 1}}},
        ], key=stable_hash) if populated else [] for name in closure.MATERIAL_TABLES}
        self.extras = {"imageCancellations": {name: ["a", "z"] if populated else [] for name in CANCELLATIONS}}
        if geometry:
            self.extras["geometryPreparations"] = sorted([
                {"checkpointId": "z", "geometryPreparation": {"width": 1280}},
                {"checkpointId": "a", "geometryPreparation": {"width": 720}},
            ], key=stable_hash)

    def flush(self):
        self.events.append("flush")

    def execute(self, statement):
        table = statement.get_final_froms()[0]
        self.events.append(table.name)
        assert "project" in statement.compile().params.values()
        if table.name == "v2_autopilot_checkpoints":
            assert list(statement.selected_columns.keys()) == ["id", "evidence"]
            return SimpleNamespace(all=lambda: self.preparations)
        assert list(statement.selected_columns) == list(table.columns)
        column = table.c.project_id if "project_id" in table.c else table.c.id
        assert statement.whereclause.left is column
        return SimpleNamespace(mappings=lambda: self.rows[table.name])

    def scalars(self, statement):
        name = statement.get_final_froms()[0].name
        self.events.append(name)
        assert list(statement.selected_columns.keys()) == ["id"]
        assert set(statement.compile().params.values()) == {"project", "cancelled"}
        return self.cancelled[name]


@pytest.mark.parametrize("populated", [False, True])
@pytest.mark.parametrize("geometry", [False, True])
def test_exact_public_and_receipt_hashes_and_one_projection_per_segment(populated, geometry):
    session = ProjectionSession(populated=populated, geometry=geometry)
    protected = stable_hash({name: session.expected[name] for name in PROTECTED})
    full = stable_hash(session.expected | session.extras)
    assert closure.material_closure(session, "project") == full
    assert session.events == ["flush", *closure.MATERIAL_TABLES, "v2_autopilot_checkpoints", *CANCELLATIONS]
    session.events.clear()
    assert closure.material_closure(session, "project", tables=PROTECTED, include_cancellations=False) == protected
    assert session.events == ["flush", *PROTECTED]
    for expected in (None, protected):
        session.events.clear()
        assert closure._receipt_material_closures(session, "project", expected_protected=expected) == (protected, full)
        assert session.events == ["flush", *PROTECTED, "v2_managed_assets", "v2_autopilot_checkpoints", *CANCELLATIONS]
    session.events.clear()
    assert closure.material_closure(session, "project", tables=("v2_managed_assets",), include_cancellations=False) == stable_hash({"v2_managed_assets": session.expected["v2_managed_assets"]})
    assert session.events == ["flush", "v2_managed_assets"]


@pytest.mark.parametrize("expected", ["", "0" * 64])
def test_protected_mismatch_precedes_all_asset_extras_reads_and_full_hash(monkeypatch, expected):
    session = ProjectionSession(populated=True, geometry=True)
    original = session.execute

    def protected_only(statement):
        assert statement.get_final_froms()[0].name in PROTECTED, "read allowed extras before protected refusal"
        return original(statement)

    def protected_hash(payload):
        assert set(payload) == set(PROTECTED), "full hashing preceded protected refusal"
        return real_hash(payload)

    monkeypatch.setattr(session, "execute", protected_only)
    monkeypatch.setattr(session, "scalars", lambda *_: pytest.fail("read cancellations before protected refusal"))
    real_hash = closure._hash_material
    monkeypatch.setattr(closure, "_hash_material", protected_hash)
    with pytest.raises(InvalidTransitionError) as caught:
        closure._receipt_material_closures(session, "project", expected_protected=expected)
    assert str(caught.value) == "receipt reconciliation cannot change creative or human authority"
    assert session.events == ["flush", *PROTECTED]


@pytest.fixture
def store(tmp_path):
    from plotloom.conformance import FIXED_CHINESE_BRIEF
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as owned:
        yield owned


def test_pending_writes_and_successive_calls_are_fresh_even_without_autoflush(store):
    project_id = store.manifest.project_id
    with store.repository._write() as session, session.no_autoflush:
        project = session.get(ProjectRow, project_id)
        before = closure._receipt_material_closures(session, project_id)
        project.brief = project.brief | {"title": "待写入的新标题"}
        after = closure._receipt_material_closures(session, project_id)
        assert after[0] != before[0] and after[1] != before[1]
        assert json.loads(session.connection().exec_driver_sql("SELECT brief FROM v2_projects").scalar())["title"] == "待写入的新标题"
        assert after == (closure.material_closure(session, project_id, tables=PROTECTED, include_cancellations=False),
            closure.material_closure(session, project_id))
        session.rollback()
    with store.repository._read() as session:
        assert closure._receipt_material_closures(session, project_id) == before


def test_command_segments_and_subsequent_commands_project_fresh_rows(store, monkeypatch):
    from tests.autopilot_fixtures import authority, start_run
    run = start_run(store)
    segments, original = [], closure._material_payload
    phase = "before"

    def observed(session, project_id, tables):
        segments.append((phase, tuple(tables)))
        return original(session, project_id, tables)

    monkeypatch.setattr(closure, "_material_payload", observed)
    for command in range(2):
        phase = f"pre{command}"
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)) as session:
            phase = f"post{command}"
            row = store.repository.autopilot.row(session, store.manifest.project_id)
            row.blocker = {"code": str(command), "message": "transport-only write"}
    assert Counter(segments) == Counter({(f"{side}{command}", tables): 1
        for command in range(2) for side in ("pre", "post") for tables in (PROTECTED, ("v2_managed_assets",))})
    assert store.repository._command_context.get() is None


def test_ordinary_command_never_uses_receipt_projection_and_receipt_noop_keeps_revision(store, monkeypatch):
    from tests.autopilot_fixtures import authority, exact_source, start_run
    run = start_run(store)
    original = closure._receipt_material_closures
    monkeypatch.setattr(closure, "_receipt_material_closures", lambda *_args, **_kwargs: pytest.fail("ordinary command used receipt projection"))
    with store.repository.autopilot_command(authority(run)):
        store.save_source_material(expected_source_revision=0, material=exact_source(store))
    monkeypatch.setattr(closure, "_receipt_material_closures", original)
    before = store.repository.autopilot.current(store.manifest.project_id)
    with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)):
        pass
    after = store.repository.autopilot.current(store.manifest.project_id)
    assert after == before


def test_pending_protected_command_write_refuses_before_extras_and_rolls_back(store, monkeypatch):
    from tests.autopilot_fixtures import authority, start_run
    run = start_run(store)
    original = closure._material_payload
    after_yield = False

    def guarded(session, project_id, tables):
        if after_yield:
            assert tuple(tables) == PROTECTED, "post-command full projection preceded refusal"
        return original(session, project_id, tables)

    monkeypatch.setattr(closure, "_material_payload", guarded)
    with pytest.raises(InvalidTransitionError, match="cannot change creative or human authority"):
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)) as session, session.no_autoflush:
            after_yield = True
            project = session.get(ProjectRow, store.manifest.project_id)
            project.brief = project.brief | {"title": "must roll back"}
    assert store.repository._command_context.get() is None
    assert store.project().brief.title != "must roll back"


def test_post_segment_flush_failure_rolls_back_transport_write_and_cleans_context(store, monkeypatch):
    from tests.autopilot_fixtures import authority, start_run
    run = start_run(store)
    failure = OSError("pending flush unavailable")

    def unavailable(*_):
        raise failure

    with pytest.raises(OSError) as caught:
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)) as session:
            store.repository.autopilot.row(session, store.manifest.project_id).blocker = {"code": "failure", "message": "rollback"}
            session.flush()
            monkeypatch.setattr(session, "flush", unavailable)
    assert caught.value is failure and store.repository._command_context.get() is None
    assert store.repository.autopilot.current(store.manifest.project_id).blocker is None


@pytest.mark.parametrize("failure_stage", ["protected", "assets", "geometry", "protected_hash", "full_hash"])
def test_unexpected_post_projection_or_hash_failure_rolls_back_and_cleans_context(store, monkeypatch, failure_stage):
    from tests.autopilot_fixtures import authority, start_run
    run = start_run(store)
    original_payload, original_extras, original_hash = closure._material_payload, closure._add_material_extras, closure._hash_material
    after_yield = False
    failure = OSError(f"unreadable {failure_stage}")

    def payload(session, project_id, tables):
        if after_yield and ((failure_stage == "protected" and tuple(tables) == PROTECTED)
                or (failure_stage == "assets" and tuple(tables) == ("v2_managed_assets",))):
            raise failure
        return original_payload(session, project_id, tables)

    def extras(*args):
        if after_yield and failure_stage == "geometry":
            raise failure
        return original_extras(*args)

    def hashing(value):
        if after_yield and ((failure_stage == "protected_hash" and set(value) == set(PROTECTED))
                or (failure_stage == "full_hash" and "imageCancellations" in value)):
            raise failure
        return original_hash(value)

    monkeypatch.setattr(closure, "_material_payload", payload)
    monkeypatch.setattr(closure, "_add_material_extras", extras)
    monkeypatch.setattr(closure, "_hash_material", hashing)
    with pytest.raises(OSError) as caught:
        with store.repository.autopilot_command(authority(run, OperationScope.EVIDENCE)) as session:
            row = store.repository.autopilot.row(session, store.manifest.project_id)
            row.blocker = {"code": "failure", "message": "must roll back"}
            session.flush()
            after_yield = True
    assert caught.value is failure and store.repository._command_context.get() is None
    after_yield = False
    assert store.repository.autopilot.current(store.manifest.project_id).blocker is None
