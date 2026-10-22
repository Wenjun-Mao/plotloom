"""Retired canonical schemas fail closed before current evidence is decoded."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from plotloom.domain import EntityRevision, StageHead, StageName
from plotloom.exceptions import SchemaResetRequiredError
from plotloom.persistence.project.repository_codecs import (
    decode_stage_payload, entity_revision_from_row, stage_head_from_row,
)
from tests.backend_core.conftest import make_story_graph


@pytest.mark.parametrize("version", [None, 1, 3])
def test_retired_or_unknown_stage_evidence_is_never_decoded(version):
    payload = make_story_graph().model_dump(mode="json", by_alias=True)
    with pytest.raises(SchemaResetRequiredError):
        decode_stage_payload(StageName.STORY_GRAPH, payload, version)
    row = SimpleNamespace(stage="story_graph", schema_version=version)
    with pytest.raises(SchemaResetRequiredError):
        stage_head_from_row(row)
    with pytest.raises(SchemaResetRequiredError):
        entity_revision_from_row(row)


def test_current_graph_evidence_requires_explicit_footage_membership():
    graph = make_story_graph()
    payload = graph.model_dump(mode="json", by_alias=True)
    assert decode_stage_payload(StageName.STORY_GRAPH, payload, 2) == graph
    del payload["nodes"][0]["footageMode"]
    with pytest.raises(ValidationError, match="footageMode"):
        decode_stage_payload(StageName.STORY_GRAPH, payload, 2)


@pytest.mark.parametrize("model,payload", [
    (StageHead, {"stage": "story_graph"}),
    (EntityRevision, {"projectId": "project", "stage": "story_graph", "revision": 1,
        "contentHash": "current-evidence", "payload": {}}),
])
def test_snapshot_evidence_has_no_implicit_schema_version(model, payload):
    with pytest.raises(ValidationError) as missing:
        model.model_validate(payload)
    assert {error["loc"] for error in missing.value.errors()} == {("schemaVersion",)}
    with pytest.raises(ValidationError, match="Input should be 2"):
        model.model_validate(payload | {"schemaVersion": 1})
    assert model.model_validate(payload | {"schemaVersion": 2}).schema_version == 2
