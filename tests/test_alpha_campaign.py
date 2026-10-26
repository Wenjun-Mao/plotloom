"""Freeze-before-admission, exact workload and blind publication failure contracts."""
import json
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom import alpha_campaign, alpha_provenance, alpha_publication
from plotloom.alpha_campaign import NativeCampaign, write_private_json
from plotloom.alpha_review_templates import SCORE_SHEET_SUFFIX
from plotloom.alpha_workloads import ALPHA_STORIES, SAMPLE_KEYS, REVIEW_SAMPLE_KEYS
from tests.alpha_acceptance_support import native_receipts


def frozen_campaign(tmp_path, monkeypatch):
    source = {"commit": "a" * 40, "profileHash": "c" * 64, "executionPins": {}}
    proof = {"test": "provider-free fixture, never native qualification"}
    monkeypatch.setattr(alpha_campaign, "source_snapshot", lambda *_: source)
    monkeypatch.setattr(alpha_campaign, "require_preflight", lambda *_: "d" * 64)
    path = tmp_path / "proof.json"
    path.write_text(json.dumps(proof))
    root = tmp_path / "private-campaign"
    source["sourceRoot"] = str(tmp_path / "source")
    source["cliPath"] = "/not-a-native-executable"
    campaign = alpha_campaign.prepare_campaign(root, source["cliPath"], path)
    return root, campaign


def test_freezes_exact_nine_workload_bytes_before_any_project_or_model_admission(tmp_path, monkeypatch):
    root, campaign = frozen_campaign(tmp_path, monkeypatch)
    assert tuple(s.sample_id for s in campaign.samples) == SAMPLE_KEYS
    assert len({s.project_id for s in campaign.samples}) == 9
    assert not list((root / "data/outputs").iterdir())
    assert not (root / "private/codex-exec").exists()
    assert (root / "private/token").stat().st_mode & 0o777 == 0o600
    assert root.stat().st_mode & 0o777 == 0o700
    assert all(sample.brief == story.brief for sample, story in
        zip(campaign.samples, (s for s in ALPHA_STORIES for _ in range(3)), strict=True))
    with pytest.raises(ValueError, match="fresh absolute"):
        alpha_campaign.prepare_campaign(root, "ignored", root / "preflight.json")
    raw = campaign.model_dump(mode="json", by_alias=True)
    raw["samples"][0]["brief"]["title"] = "Changed workload"
    with pytest.raises(ValueError, match="Brief bytes"):
        NativeCampaign.model_validate(raw)
    raw = campaign.model_dump(mode="json", by_alias=True)
    raw["samples"][1]["projectId"] = raw["samples"][0]["projectId"]
    with pytest.raises(ValueError, match="nine distinct"):
        NativeCampaign.model_validate(raw)


def test_actual_preflight_requires_matching_runtime_and_all_pairs_and_denials(tmp_path, monkeypatch):
    snapshot = {key: ch * 64 for key, ch in [("profileHash", "a"), ("cliSha256", "b"), ("pythonEnvironmentHash", "c")]}
    snapshot["commit"] = "a" * 40
    identities = {f"/preflight/{case}": (*pair, "d" * 64, snapshot["commit"])
        for case, pair in alpha_provenance.PREFLIGHT_CASES.items()}
    monkeypatch.setattr(alpha_provenance, "preflight_plan_identity", lambda path: identities[path])
    proof = snapshot | {"validatorCommands": [{"case": case, "stage": pair[0], "route": pair[1],
        "planHash": "d" * 64, "packagePath": f"/preflight/{case}", "step": step, "exitCode": 0}
        for case, pair in alpha_provenance.PREFLIGHT_CASES.items() for step in ("validate", "render")],
        "negativeControls": [{"name": name, "exitCode": 0 if name == "imports" else 1}
        for name in ["imports", "python-sibling", "node-sibling", "python-auth", "node-auth", "original-venv-metadata", "uv-alias"]]}
    proof.pop("commit")
    path = tmp_path / "proof.json"
    path.write_text(json.dumps(proof))
    assert len(alpha_provenance.require_preflight(path, snapshot)) == 64
    for mutation in ("identity", "missing-pair", "unexpected-success", "replacement", "wrong-route", "wrong-plan", "wrong-stage"):
        raw = json.loads(json.dumps(proof))
        if mutation == "identity": raw["cliSha256"] = "e" * 64
        if mutation == "missing-pair": raw["validatorCommands"].pop()
        if mutation == "unexpected-success": raw["negativeControls"][-1]["exitCode"] = 0
        if mutation == "replacement":
            raw["validatorCommands"][0]["case"] = raw["validatorCommands"][1]["case"] = "unsupported-case"
        if mutation == "wrong-route": raw["validatorCommands"][0]["route"] = "saved_brief"
        if mutation == "wrong-plan": raw["validatorCommands"][0]["planHash"] = "f" * 64
        if mutation == "wrong-stage": raw["validatorCommands"][0]["stage"] = "art"
        path.write_text(json.dumps(raw))
        with pytest.raises(ValueError):
            alpha_provenance.require_preflight(path, snapshot)


def prepare_publication(root, campaign):
    rows = {r["sampleId"]: r for r in native_receipts()}
    for sample_id in REVIEW_SAMPLE_KEYS:
        evidence = root / "evidence" / sample_id / "outcome"
        evidence.mkdir(parents=True)
        row = rows[sample_id] | {"contractHash": campaign.contract_hash}
        content = {name: {"text": sample_id} for name in ["storyBible", "storyGraph", "sceneBeats", "storyboard"]}
        write_private_json(evidence / "content.json", content)
        row["contentHash"] = sha256((evidence / "content.json").read_bytes()).hexdigest()
        write_private_json(evidence / "receipt.json", row)


def test_blind_publication_is_atomic_opaque_content_only_and_mapping_stays_private(tmp_path, monkeypatch):
    root, campaign = frozen_campaign(tmp_path, monkeypatch)
    prepare_publication(root, campaign)
    public = tmp_path / "reading-set"
    paths, mapping = alpha_publication.publish_native_review_pack(root, public)
    assert len(paths) == 3 and len(list(public.iterdir())) == 6
    assert mapping.parent == root / "private" and mapping.stat().st_mode & 0o777 == 0o600
    manifest = alpha_publication.load_private_review_manifest(mapping, campaign_root=root)
    assert {item.review_id for item in manifest.samples} == {path.stem for path in paths}
    for item in manifest.samples:
        path = public / (item.review_id + ".json")
        assert sha256(path.read_bytes()).hexdigest() == item.content_hash
        assert set(json.loads(path.read_bytes())) == {"storyBible", "storyGraph", "sceneBeats", "storyboard"}
        draft = json.loads((public / (item.review_id + SCORE_SHEET_SUFFIX)).read_bytes())
        assert draft["fatalContradiction"] == "PENDING"
    with pytest.raises(ValueError, match="empty"):
        alpha_publication.publish_native_review_pack(root, public)


def test_blind_failure_never_publishes_partial_pack_or_overwrites_foreign_mapping(tmp_path, monkeypatch):
    root, campaign = frozen_campaign(tmp_path, monkeypatch)
    prepare_publication(root, campaign)
    public = tmp_path / "reading-set"
    def fail(*_args): raise OSError("simulated publication race")
    monkeypatch.setattr(alpha_publication, "_publish_review_directory", fail)
    with pytest.raises(OSError): alpha_publication.publish_native_review_pack(root, public)
    assert not public.exists() and not (root / "private/review-mapping.private.json").exists()
    write_private_json(root / "private/review-mapping.private.json", {"foreign": True})
    with pytest.raises(FileExistsError): alpha_publication.publish_native_review_pack(root, public)
    assert json.loads((root / "private/review-mapping.private.json").read_bytes()) == {"foreign": True}
    assert not public.exists()


def test_source_provenance_refuses_dirty_checkout_before_cli_or_admission(tmp_path, monkeypatch):
    monkeypatch.setattr(alpha_provenance, "source_checkout_root", lambda: tmp_path)
    monkeypatch.setattr(alpha_provenance, "_git", lambda *_: " M src/plotloom/changed.py")
    monkeypatch.setattr(alpha_provenance, "build_codex_exec_profile", lambda *_args, **_kwargs: pytest.fail("dirty source reached CLI"))
    with pytest.raises(ValueError, match="uncommitted changes"):
        alpha_provenance.source_snapshot("unused", alpha_campaign.NATIVE_POOL_LIMITS)


def test_source_checkout_resolution_uses_module_owner_and_rejects_foreign_root(tmp_path, monkeypatch):
    source = tmp_path / "source"
    module = source / "src/plotloom/alpha_provenance.py"
    monkeypatch.setattr(alpha_provenance, "__file__", str(module))
    monkeypatch.setattr(alpha_provenance, "_git", lambda root, *_: str(root))
    assert alpha_provenance.source_checkout_root() == source
    monkeypatch.setattr(alpha_provenance, "_git", lambda *_: str(tmp_path))
    with pytest.raises(ValueError, match="owning source"):
        alpha_provenance.source_checkout_root()


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "story-rebound", "content-rebound", "receipt-rebound", "content-bytes"])
def test_private_mapping_binds_exact_repeat_one_coverage_and_retained_content(tmp_path, monkeypatch, mutation):
    root, campaign = frozen_campaign(tmp_path, monkeypatch)
    prepare_publication(root, campaign)
    _paths, mapping = alpha_publication.publish_native_review_pack(root, tmp_path / "reading-set")
    raw = json.loads(mapping.read_bytes())
    if mutation == "duplicate":
        raw["entries"][1].update(storyId=raw["entries"][0]["storyId"], sampleId=raw["entries"][0]["sampleId"])
    if mutation == "missing": raw["entries"].pop()
    if mutation == "story-rebound": raw["entries"][0]["storyId"] = "story-99"
    if mutation == "content-rebound": raw["entries"][0]["contentHash"] = "f" * 64
    if mutation == "content-bytes":
        path = root / "evidence" / raw["entries"][0]["sampleId"] / "outcome/content.json"
        content = json.loads(path.read_bytes())
        content["storyBible"] = {"text": "changed"}
        write_private_json(path, content, replace=True)
    if mutation == "receipt-rebound":
        path = root / "evidence" / raw["entries"][0]["sampleId"] / "outcome/receipt.json"
        receipt = json.loads(path.read_bytes())
        receipt["sampleId"] = "story-03-repeat-02"
        write_private_json(path, receipt, replace=True)
    write_private_json(mapping, raw, replace=True)
    with pytest.raises(ValueError):
        alpha_publication.load_private_review_manifest(mapping, campaign_root=root)


def test_preflight_identity_recomputes_retained_production_plan_and_rejects_tampering(tmp_path):
    from plotloom.creative_handoff_contracts import CreativeHandoffRequest
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    request = CreativeHandoffRequest(job_id="ch_" + "a" * 32, project_id="provider-free-plan",
        section_id="test", stage="branches", expected_stage_revision=0,
        source={"kind": "test-owned"}, input_artifacts={}, creative_brief="provider-free plan identity test")
    pin = {"upstreamRevision": "a" * 40, "upstreamSkillHash": "b" * 64, "specialistSkillHash": "c" * 64}
    paths = CreativeHandoffExchange(tmp_path / "exchange").write_package(request, pin,
        executor_backend="codex_exec", plotloom_code_revision="d" * 40)
    package = paths["packagePath"]
    identity = alpha_provenance.preflight_plan_identity(package)
    assert identity[:2] == ("branches", "plotloom_native") and identity[3] == "d" * 40
    path = Path(package) / "request.json"
    payload = json.loads(path.read_bytes())
    payload["validationPlanHash"] = "f" * 64
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="does not match"):
        alpha_provenance.preflight_plan_identity(package)
