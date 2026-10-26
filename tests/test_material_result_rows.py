"""Fresh Result metadata/processed rows preserve the existing material byte owner."""
import json
from contextlib import ExitStack, closing
from datetime import datetime
from hashlib import sha256

import pytest
from sqlalchemy import event, select

from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.persistence.project import autopilot_closure as closure
from plotloom.persistence.project.autopilot_handoff import (
    record_handoff,
    review_material,
)
from plotloom.persistence.schema import Base, ProjectRow
from plotloom.project_storage import ProjectFolderStorage
from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed
from tests.material_result_fixtures import MaterialResult
from tests.test_autopilot_handoff import observation


def canonical_bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def legacy_table_bytes(session, project_id, name):
    """Independent pre-adapter SQL/mappings/normalization/canonical-byte oracle."""
    table = Base.metadata.tables[name]
    result = session.execute(select(table).where(table.c.project_id == project_id)
        if "project_id" in table.c else select(table).where(table.c.id == project_id))
    keys = tuple(result.keys())
    values = [{key: value.isoformat() if isinstance(value, datetime) else value
               for key, value in row.items()} for row in result.mappings()]
    values.sort(key=lambda row: sha256(canonical_bytes(row)).hexdigest())
    return canonical_bytes({name: values}), keys, len(values)


@pytest.mark.parametrize("empty", [False, True])
def test_each_fresh_result_owns_one_metadata_read_even_when_empty(empty):
    results = []

    class Result(MaterialResult):
        reads = 0

        def keys(self):
            self.reads += 1
            assert self.reads == 1
            return super().keys()

        def mappings(self):
            pytest.fail("material rows should not construct mapping adapters")

    class Session:
        def execute(self, _statement):
            value_key = f"value{len(results)}"
            result = Result((value_key, "id"), [] if empty else [
                {"id": "z", value_key: {"中文": [None, True, -0.0]}},
                {"id": "a", value_key: None},
            ])
            results.append(result)
            return result

    session = Session()
    for index in range(2):
        payload = closure._material_payload(session, "project", ("v2_projects",))
        expected = [] if empty else sorted([
            {"id": "z", f"value{index}": {"中文": [None, True, -0.0]}},
            {"id": "a", f"value{index}": None},
        ], key=lambda row: sha256(canonical_bytes(row)).hexdigest())
        assert closure._material_bytes(payload) == canonical_bytes({"v2_projects": expected})
    assert len(results) == 2 and all(result.reads == 1 for result in results)


def test_processed_ordered_values_need_no_mapping_or_per_key_lookup():
    stamp = datetime(2026, 10, 17, 12, 34, 56)

    class Row:
        def __iter__(self):
            return iter((stamp, {"中": [None, 1.5]}, "p"))

        def __getitem__(self, _key):
            pytest.fail("processed Row values need no per-key lookup")

        @property
        def _mapping(self):
            pytest.fail("processed Row values need no mapping adapter")

    class Result:
        def keys(self):
            return ("created_at", "nested", "id")

        def __iter__(self):
            yield Row()

    class Session:
        def execute(self, _statement):
            return Result()

    payload = closure._material_payload(Session(), "p", ("v2_projects",))
    assert closure._material_bytes(payload) == canonical_bytes({"v2_projects": [
        {"created_at": "2026-10-17T12:34:56", "nested": {"中": [None, 1.5]}, "id": "p"}]})


def test_metadata_failure_keeps_identity_and_precedes_iteration_or_next_select():
    failure, calls = OSError("result metadata unavailable"), []

    class Result:
        def keys(self):
            raise failure

        def __iter__(self):
            pytest.fail("iteration preceded result metadata")

    class Session:
        def execute(self, statement):
            calls.append(statement.get_final_froms()[0].name)
            return Result()

    with pytest.raises(OSError) as caught:
        closure._material_payload(Session(), "p", ("v2_projects", "v2_stage_heads"))
    assert caught.value is failure and calls == ["v2_projects"]


def test_actual_database_mapping_and_ordered_row_bytes_match_every_material_table(
    tmp_path, awaiting_handoff_seed,
):
    from plotloom.autopilot_handoff_contracts import HumanHandoffRequest

    storage, view, retained_image_ids = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "copy")
    assert len(retained_image_ids) == 8
    with closing(storage.projects.open(view.project_id)) as store:
        record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
        traces, populated = [], set()

        def trace(_connection, _cursor, statement, parameters, _context, _many):
            if statement.lstrip().upper().startswith("SELECT"):
                traces.append((statement, parameters))

        with store.repository._read() as session:
            session.connection()
            event.listen(store.repository.engine, "before_cursor_execute", trace)
            try:
                for project in (view.project_id, "missing-project"):
                    for name in closure.MATERIAL_TABLES:
                        traces.clear()
                        expected, keys, count = legacy_table_bytes(session, project, name)
                        original_trace = list(traces)
                        assert keys == tuple(Base.metadata.tables[name].columns.keys())
                        traces.clear()
                        actual = closure._material_payload(session, project, (name,))
                        assert closure._material_bytes(actual) == expected, (project, name)
                        assert traces == original_trace and len(traces) == 1, name
                        if project == "missing-project":
                            assert count == 0 and expected == canonical_bytes({name: []})
                        elif count:
                            populated.add(name)
            finally:
                event.remove(store.repository.engine, "before_cursor_execute", trace)
        assert {"v2_projects", "v2_managed_assets", "v2_same_person_reviews"} <= populated


def test_pending_writes_and_nested_independent_calls_keep_fresh_result_values(tmp_path, monkeypatch):
    with ExitStack() as stack:
        stores = []
        for name in ("outer", "inner"):
            storage = ProjectFolderStorage(outputs_root=tmp_path / name / "outputs",
                application_data_root=tmp_path / name / "application")
            stores.append(stack.enter_context(closing(storage.projects.create(FIXED_CHINESE_BRIEF))))
        outer, inner = stores
        outer_id, inner_id = (store.manifest.project_id for store in stores)
        outer_session = stack.enter_context(outer.repository._write())
        inner_session = stack.enter_context(inner.repository._write())
        stack.enter_context(outer_session.no_autoflush)
        stack.enter_context(inner_session.no_autoflush)
        outer_row, inner_row = outer_session.get(ProjectRow, outer_id), inner_session.get(ProjectRow, inner_id)
        outer_row.brief = outer_row.brief | {"title": "外层待写"}
        inner_row.brief = inner_row.brief | {"title": "内层待写"}
        nested, original = [], closure._json_text

        def text(value):
            if isinstance(value, dict) and value.get("id") == outer_id:
                nested.append(closure.material_closure(inner_session, inner_id,
                    tables=("v2_projects",), include_cancellations=False))
            return original(value)

        monkeypatch.setattr(closure, "_json_text", text)
        first = closure.material_closure(outer_session, outer_id, tables=("v2_projects",), include_cancellations=False)
        assert first == sha256(legacy_table_bytes(outer_session, outer_id, "v2_projects")[0]).hexdigest()
        assert nested == [sha256(legacy_table_bytes(inner_session, inner_id, "v2_projects")[0]).hexdigest()]
        assert "外层待写" in legacy_table_bytes(outer_session, outer_id, "v2_projects")[0].decode()
        assert "内层待写" in legacy_table_bytes(inner_session, inner_id, "v2_projects")[0].decode()
        outer_row.brief = outer_row.brief | {"title": "第二次外层"}
        inner_row.brief = inner_row.brief | {"title": "第二次内层"}
        second = closure.material_closure(outer_session, outer_id, tables=("v2_projects",), include_cancellations=False)
        assert second != first and len(nested) == 2 and nested[0] != nested[1]
        assert second == sha256(legacy_table_bytes(outer_session, outer_id, "v2_projects")[0]).hexdigest()
        assert nested[1] == sha256(legacy_table_bytes(inner_session, inner_id, "v2_projects")[0]).hexdigest()
