"""Complete canonical bytes and original closure read/error boundaries."""
import json
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace

import pytest

from plotloom.persistence.project import autopilot_closure as closure

CANCELLATIONS = ("v2_image_jobs", "v2_character_reference_proposals", "v2_art_reference_proposals")


def canonical_bytes(value):
    """Independent stdlib oracle; never call a production encoding/hash helper."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def expected_rows(rows):
    return sorted(rows, key=lambda row: sha256(canonical_bytes(row)).hexdigest())


class ByteSession:
    def __init__(self, rows=None, preparations=()):
        self.rows = rows or {}
        self.preparations = preparations
        self.cancelled = {name: ["中", "a"] for name in CANCELLATIONS}
        self.events = []

    def flush(self):
        self.events.append("flush")

    def execute(self, statement):
        name = statement.get_final_froms()[0].name
        self.events.append(name)
        return SimpleNamespace(mappings=lambda: self.rows.get(name, []), all=lambda: self.preparations)

    def scalars(self, statement):
        name = statement.get_final_froms()[0].name
        self.events.append(name)
        return self.cancelled[name]


@pytest.mark.parametrize("tables", [(), ("v2_projects",), ("v2_stage_heads", "v2_projects"),
    ("v2_projects", "v2_stage_heads", "v2_projects")])
@pytest.mark.parametrize("extras", [False, True])
def test_complete_bytes_match_independent_payload_for_empty_subset_and_duplicate_tables(tables, extras):
    stamp = datetime(2026, 10, 15, 12, 34, 56, 789, tzinfo=timezone.utc)
    source = {"id": "中\"\\\n\t\u0000\u2028😀", "created_at": stamp,
        "nested": {"z": [None, True, False, -0.0, 1e-20, float("inf"), float("-inf"), float("nan")],
            "a": {"x": "é", "y": "/"}}, "integer": 10**80}
    normalized = {"id": "中\"\\\n\t\u0000\u2028😀", "created_at": "2026-10-15T12:34:56.000789+00:00",
        "nested": {"z": [None, True, False, -0.0, 1e-20, float("inf"), float("-inf"), float("nan")],
            "a": {"x": "é", "y": "/"}}, "integer": 10**80}
    preparations = [("z", {"geometryPreparation": {"width": 1280}}),
        ("a", {"geometryPreparation": {"width": 720}}), ("null", {"geometryPreparation": None})]
    session = ByteSession({"v2_projects": [source, {"id": "a", "created_at": None}]}, preparations)
    payload = closure._material_payload(session, "project", tables)
    expected = {name: expected_rows([normalized, {"id": "a", "created_at": None}])
        if name == "v2_projects" else [] for name in tables}
    if extras:
        closure._add_material_extras(session, "project", payload)
        expected["geometryPreparations"] = expected_rows([
            {"checkpointId": "z", "geometryPreparation": {"width": 1280}},
            {"checkpointId": "a", "geometryPreparation": {"width": 720}}])
        expected["imageCancellations"] = {name: ["a", "中"] for name in CANCELLATIONS}
    oracle = canonical_bytes(expected)
    assert closure._material_bytes(payload) == oracle
    assert closure._hash_material(payload) == sha256(oracle).hexdigest()
    assert session.events == [*tables, *(["v2_autopilot_checkpoints", *CANCELLATIONS] if extras else [])]


def test_receipt_aggregate_uses_fresh_row_bytes_once_across_its_two_hashes(monkeypatch):
    session = ByteSession({"v2_projects": [{"id": "p", "value": {"title": "原文"}}],
        "v2_managed_assets": [{"id": "asset", "value": "a"}]})
    original_text, original_hash = closure._json_text, closure._hash_material
    encoded_rows, aggregates = [], []

    def text(value):
        if isinstance(value, dict) and "id" in value:
            encoded_rows.append(value["id"])
        return original_text(value)

    def hashing(payload):
        aggregates.append(closure._material_bytes(payload))
        return original_hash(payload)

    monkeypatch.setattr(closure, "_json_text", text)
    monkeypatch.setattr(closure, "_hash_material", hashing)
    before = closure._receipt_material_closures(session, "project")
    protected = {name: ([{"id": "p", "value": {"title": "原文"}}] if name == "v2_projects" else [])
        for name in closure.MATERIAL_TABLES if name != "v2_managed_assets"}
    full = protected | {"v2_managed_assets": [{"id": "asset", "value": "a"}],
        "imageCancellations": {name: ["a", "中"] for name in CANCELLATIONS}}
    assert aggregates == [canonical_bytes(protected), canonical_bytes(full)]
    assert encoded_rows == ["p", "asset"]
    session.rows["v2_projects"][0]["value"]["title"] = "新文"
    session.rows["v2_managed_assets"][0]["value"] = "b"
    after = closure._receipt_material_closures(session, "project")
    assert before[0] != after[0] and before[1] != after[1]
    assert encoded_rows == ["p", "asset", "p", "asset"]
    assert aggregates[:2] == [canonical_bytes(protected), canonical_bytes(full)]
    protected["v2_projects"][0]["value"]["title"] = "新文"
    full["v2_managed_assets"][0]["value"] = "b"
    assert aggregates[2:] == [canonical_bytes(protected), canonical_bytes(full)]


def test_digest_ties_preserve_original_row_order(monkeypatch):
    rows = [{"id": "z"}, {"id": "a"}, {"id": "z"}]
    monkeypatch.setattr(closure, "sha256", lambda _: SimpleNamespace(hexdigest=lambda: "0" * 64))
    payload = closure._material_payload(ByteSession({"v2_projects": rows}), "project", ("v2_projects",))
    assert closure._material_bytes(payload) == canonical_bytes({"v2_projects": rows})


def test_table_is_consumed_and_normalized_before_row_encoding_and_sort_before_next_select(monkeypatch):
    session = ByteSession()
    events = session.events

    class Stamp(datetime):
        def isoformat(self):
            events.append("normalize")
            return "2026-10-15T00:00:00"

    class Digest(str):
        def __lt__(self, other):
            events.append("sort")
            return super().__lt__(other)

    def rows():
        for name in ("z", "a"):
            events.append("consume:" + name)
            yield {"id": name, "created_at": Stamp(2026, 10, 15)}
        events.append("exhausted")

    original_text = closure._json_text

    def text(value):
        events.append("encode:" + value["id"])
        return original_text(value)

    def hashing(data):
        name = json.loads(data)["id"]
        events.append("hash:" + name)
        return SimpleNamespace(hexdigest=lambda: Digest(name))

    session.rows["v2_projects"] = rows()
    monkeypatch.setattr(closure, "_json_text", text)
    monkeypatch.setattr(closure, "sha256", hashing)
    closure._material_payload(session, "project", ("v2_projects", "v2_stage_heads"))
    assert events == ["v2_projects", "consume:z", "normalize", "consume:a", "normalize", "exhausted",
        "encode:z", "hash:z", "encode:a", "hash:a", "sort", "v2_stage_heads"]


@pytest.mark.parametrize("stage", ["iteration", "normalization", "json", "utf8", "hash"])
def test_row_failure_keeps_original_phase_and_prevents_next_table_read(monkeypatch, stage):
    session = ByteSession()
    failure = OSError(stage)
    events = session.events

    class BrokenStamp(datetime):
        def isoformat(self):
            raise failure

    def rows():
        yield {"id": "first"}
        if stage == "iteration":
            raise failure
        yield {"id": "second", "value": BrokenStamp(2026, 10, 15) if stage == "normalization" else 2}

    original_text = closure._json_text

    def text(value):
        events.append("encode:" + value["id"])
        if stage == "json":
            raise failure
        return "\ud800" if stage == "utf8" else original_text(value)

    def hashing(_):
        events.append("hash")
        raise failure

    session.rows["v2_projects"] = rows()
    monkeypatch.setattr(closure, "_json_text", text)
    if stage == "hash":
        monkeypatch.setattr(closure, "sha256", hashing)
    with pytest.raises(UnicodeEncodeError if stage == "utf8" else OSError) as caught:
        closure._material_payload(session, "project", ("v2_projects", "v2_stage_heads"))
    if stage != "utf8":
        assert caught.value is failure
    assert events == ["v2_projects", *(["encode:first", "hash"] if stage == "hash"
        else ["encode:first"] if stage in {"json", "utf8"} else [])]


@pytest.mark.parametrize("bad", [object(), b"untrusted bytes", {"mixed": {1: "a", "1": "b"}}])
def test_unsupported_rows_fail_before_later_table(bad):
    session = ByteSession({"v2_projects": [{"id": "first", "value": bad}]})
    with pytest.raises(TypeError):
        canonical_bytes({"id": "first", "value": bad})
    with pytest.raises(TypeError):
        closure._material_payload(session, "project", ("v2_projects", "v2_stage_heads"))
    assert session.events == ["v2_projects"]


def test_geometry_encoding_failure_precedes_cancellation_reads():
    session = ByteSession(preparations=[("x", {"geometryPreparation": object()})])
    with pytest.raises(TypeError):
        closure.material_closure(session, "project", tables=())
    assert session.events == ["flush", "v2_autopilot_checkpoints"]


def test_cancellation_sort_failure_precedes_aggregate_hash(monkeypatch):
    session = ByteSession()
    session.cancelled[CANCELLATIONS[0]] = ["a", None]
    monkeypatch.setattr(closure, "_hash_material", lambda _: pytest.fail("aggregate preceded cancellation failure"))
    with pytest.raises(TypeError):
        closure.material_closure(session, "project", tables=())
    assert session.events == ["flush", "v2_autopilot_checkpoints", CANCELLATIONS[0]]


@pytest.mark.parametrize("payload,error", [({"a": "\ud800", "z": object()}, TypeError),
    ({"a": "\ud800", "z": b"untrusted"}, TypeError), ({"a": "\ud800"}, UnicodeEncodeError)])
def test_all_ordinary_json_serialization_precedes_utf8_encoding(payload, error):
    with pytest.raises(error) as expected:
        canonical_bytes(payload)
    with pytest.raises(error) as actual:
        closure._material_bytes(payload)
    assert str(actual.value) == str(expected.value)


def test_surrogate_exception_retains_complete_input_and_offsets_with_encoded_rows():
    session = ByteSession({"v2_projects": [{"id": "中"}]})
    payload = closure._material_payload(session, "project", ("v2_projects",))
    payload["z"] = "\ud800"
    with pytest.raises(UnicodeEncodeError) as expected:
        canonical_bytes({"v2_projects": [{"id": "中"}], "z": "\ud800"})
    with pytest.raises(UnicodeEncodeError) as actual:
        closure._material_bytes(payload)
    assert actual.value.args == expected.value.args
