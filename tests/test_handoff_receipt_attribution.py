"""Receipt versions discriminate actor data, never a similarly named method."""
from copy import deepcopy

import pytest

from plotloom.autopilot_handoff_contracts import parse_handoff_receipt
from plotloom.persistence.codec import stable_hash

ACTOR = {"kind": "agent_operated_qa", "scopeId": "synthetic-receipt-contract"}


def receipt(version):
    # Schema-only evidence: no runtime grant, material adoption or media claim.
    bundle = {"runId": "run", "materialClosure": "closure", "references": [], "frames": [], "story": {},
        "inventory": {"entityRevisionId": "board", "storyboardRevision": 1, "storyboardHash": "a" * 64,
            "productionHash": "b" * 64, "castRevision": 1, "artRevision": 1, "subjects": [], "routeCount": 1}}
    observation = {"expectedRunRevision": 1, "bundleHash": "a" * 64, "frames": [], "endorsedReferenceIds": []}
    raw = {"version": version, "id": "receipt", "runId": "run", "projectId": "project",
        "bundleHash": "a" * 64, "bundle": bundle, "approvalId": "approval", "approvalOrigin": "created",
        "bindings": [], "materialClosure": "closure", "observation": observation}
    if version == "pre-video.handoff.v1":
        observation.update(reviewer="Historical named reviewer", notes="Retained historical observation.")
    else:
        raw["attribution"] = ACTOR if version.endswith("v4") else {"kind": "unnamed_creator"}
        if version.endswith(("v3", "v4")):
            observation["basis"] = "whole-pack-material.v1"
        if version.endswith("v4"):
            observation["attribution"] = deepcopy(ACTOR)
    return raw


@pytest.mark.parametrize("version", [f"pre-video.handoff.v{n}" for n in range(1, 5)])
def test_exact_actor_contract_is_readable_and_roundtrip_stable(version):
    parsed = parse_handoff_receipt(receipt(version))
    raw = parsed.model_dump(mode="json", by_alias=True)
    assert stable_hash(parse_handoff_receipt(raw).model_dump(mode="json", by_alias=True)) == stable_hash(raw)
    if version.endswith("v1"):
        assert "attribution" not in type(parsed.observation).model_fields
        assert callable(parsed.observation.attribution)
        assert parsed.stored_reviewer == "Historical named reviewer"


@pytest.mark.parametrize("version", ["pre-video.handoff.v2", "pre-video.handoff.v3"])
def test_creator_receipts_never_admit_smuggled_qa_observation(version):
    raw = receipt(version)
    raw["observation"]["attribution"] = ACTOR
    with pytest.raises(ValueError, match="creator receipt cannot retain an agent QA observation"):
        parse_handoff_receipt(raw)


@pytest.mark.parametrize("actor", [None, ACTOR | {"scopeId": "other-scope"}])
def test_v4_requires_the_exact_same_observation_actor(actor):
    raw = receipt("pre-video.handoff.v4")
    raw["observation"]["attribution"] = actor
    with pytest.raises(ValueError, match="QA handoff observation attribution differs"):
        parse_handoff_receipt(raw)
