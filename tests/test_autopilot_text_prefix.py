"""Real lease/claim/controller/adoption prefix, fake native transport only."""
from contextlib import closing
import pytest
from plotloom.autopilot_service import AutopilotService
from plotloom.autopilot_text_prefix import AutopilotTextPrefix
from plotloom.alpha_receipts import installed_text_readback
from plotloom.exceptions import InvalidTransitionError
from tests.autopilot_controller_fixtures import environment


def test_prefix_excludes_ordinary_owner_and_stops_before_all_images(tmp_path, monkeypatch):
    storage, registry, original, run, calls = environment(tmp_path, monkeypatch, early_references=True)
    ordinary = AutopilotService(storage, registry)
    with AutopilotTextPrefix(storage, registry) as prefix:
        assert not ordinary.acquire_controller()
        monkeypatch.setattr(prefix.service.image_controller, "advance", lambda *_: pytest.fail("prefix invoked images"))
        for _ in range(60):
            view = prefix.step(run.project_id)
            assert view.state in {"running", "waiting", "paused"}, view.blocker
            assert registry._codex_exec_test_host.image_calls == []
            if any(c["operationKey"] == "installation" for c in view.checkpoints):
                break
        else:
            pytest.fail("fake text transport did not reach current installation")
        assert view.state == "paused"
        assert len([c for c in view.checkpoints if c["operationKey"] in {
            "outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"}]) == 8
        with closing(storage.projects.open(run.project_id)) as store:
            before = installed_text_readback(store)
            from plotloom.content_language_persistence import check_rows, verified_check
            with store.repository._read() as session:
                checks = [verified_check(row) for row in check_rows(session, run.project_id)]
            assert {item[0].stage for item in checks} == {
                "outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"}
            assert all(attempt.state == "completed" and receipt is not None and result.verdict == "pass"
                for _request, _data, attempt, _profile, receipt, result in checks)
            creation_ids = {c["evidence"]["executorAttemptId"] for c in view.checkpoints if c["evidence"].get("executorAttemptId")}
            assert len(creation_ids) == len(checks) == 8
            assert creation_ids.isdisjoint({str(item[2].attempt_id) for item in checks})
            assert registry._codex_exec_test_host.admissions == len(calls) == 16
        with closing(storage.projects.open(run.project_id)) as reopened:
            assert installed_text_readback(reopened) == before
        assert not view.frames and not view.handoff
    assert ordinary.acquire_controller()
    ordinary.step(run.project_id)
    with closing(storage.projects.open(run.project_id)) as store:
        assert store.repository.autopilot.current(run.project_id).state == "paused"
    assert registry._codex_exec_test_host.image_calls == []
    ordinary.close()
    original.close()


def test_prefix_refuses_existing_controller_lease_and_unowned_step(tmp_path, monkeypatch):
    storage, registry, original, run, _calls = environment(tmp_path, monkeypatch)
    prefix = AutopilotTextPrefix(storage, registry)
    with pytest.raises(InvalidTransitionError, match="process lease"):
        prefix.step(run.project_id)
    assert original.acquire_controller()
    with pytest.raises(InvalidTransitionError, match="another production controller"):
        with prefix:
            pytest.fail("competing lease admitted")
    original.close()


@pytest.mark.parametrize("version,accepted", [("dialogue.bilingual.v2", True), ("dialogue.default.v1", False), ("unknown", False)])
def test_prefix_f5_receiver_agrees_with_current_frozen_timing_profile(tmp_path, version, accepted):
    import json
    import subprocess
    from hashlib import sha256
    from pathlib import Path
    from plotloom.creative_handoff_identity import canonical_json
    from plotloom.production_dialogue_timing import freeze_f5_dialogue_timing
    script = {"episodes": []}
    timing = freeze_f5_dialogue_timing(script, script_content_hash="a"*64, language="zh-CN").model_dump(mode="json", by_alias=True)
    timing["profileVersion"] = version
    timing["contentHash"] = sha256(canonical_json({key: value for key, value in timing.items() if key != "contentHash"})).hexdigest()
    request = {"stage": "storyboard", "source": {"acceptedScriptRevision": 1, "acceptedScriptContentHash": "a"*64},
        "inputArtifacts": {"script.json": script, "dialogue-timing-contract.json": timing,
            "storyboard-admission.json": {"scriptRevision": 1, "scriptContentHash": "a"*64,
                "sectionBindings": [{"sectionId": "opening", "episode": 1}],
                "completeRouteSectionIds": [["opening"]], "routeOnlySectionIds": [], "targetPlaythroughSeconds": 10,
                "reviewTiming": {"minCutSeconds": 2, "maxCutSeconds": 8, "maxSegmentSeconds": 15}}}}
    path = tmp_path / "request.json"
    path.write_bytes(canonical_json(request))
    validator = Path(__file__).resolve().parents[1] / "scripts/storyboard-dialogue-timing.mjs"
    program = f"import {{frozenF5DialogueTiming}} from {json.dumps(validator.as_uri())}; import {{readFileSync}} from 'node:fs'; frozenF5DialogueTiming(JSON.parse(readFileSync(process.argv[1],'utf8')));"
    result = subprocess.run(["node", "--input-type=module", "--eval", program, str(path)], capture_output=True, check=False)
    assert (result.returncode == 0) is accepted, result.stderr.decode()
    if not accepted:
        assert b"profile/language is invalid" in result.stderr


@pytest.mark.parametrize("fail_after", [1, 2, 3])
def test_terminal_publication_fault_reopens_installed_project_without_dispatch(tmp_path, monkeypatch, fail_after):
    from plotloom import alpha_campaign
    storage, registry, original, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    with AutopilotTextPrefix(storage, registry) as prefix:
        for _ in range(60):
            view = prefix.step(run.project_id)
            assert view.state in {"running", "waiting", "paused"}, view.blocker
            if view.state == "paused": break
        assert any(c["operationKey"] == "installation" for c in view.checkpoints)
        admissions = registry._codex_exec_test_host.admissions
        with closing(storage.projects.open(run.project_id)) as store:
            readback = installed_text_readback(store)
        evidence = tmp_path / "sample-evidence"
        evidence.mkdir(mode=0o700)
        values = {"receipt": {"status": "installed"}, "bindings": readback,
            "content": {"canonical": "retained"}}
        write = alpha_campaign.write_private_json
        count = 0
        def interrupt_after_write(*args, **kwargs):
            nonlocal count
            write(*args, **kwargs)
            count += 1
            if count == fail_after: raise OSError("interrupted terminal publication")
        with monkeypatch.context() as fault:
            fault.setattr(alpha_campaign, "write_private_json", interrupt_after_write)
            with pytest.raises(OSError, match="interrupted"):
                alpha_campaign.publish_sample_outcome(evidence, **values)
        assert not (evidence / "outcome").exists()
        assert prefix.step(run.project_id).state == "paused"
        with closing(storage.projects.open(run.project_id)) as reopened:
            assert installed_text_readback(reopened) == readback
        alpha_campaign.publish_sample_outcome(evidence, **values)
        alpha_campaign.publish_sample_outcome(evidence, **values)
        with pytest.raises(ValueError, match="bytes differ"):
            alpha_campaign.publish_sample_outcome(evidence, **(values | {"content": {"canonical": "changed"}}))
        assert registry._codex_exec_test_host.admissions == admissions == 16
        assert not registry._codex_exec_test_host.image_calls
    original.close()
