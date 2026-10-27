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


@pytest.mark.parametrize("fail_after", [1, 2, 3])
def test_terminal_publication_fault_reopens_installed_project_without_dispatch(tmp_path, monkeypatch, fail_after):
    from plotloom import alpha_campaign
    storage, registry, original, run, _calls = environment(tmp_path, monkeypatch, early_references=True)
    with AutopilotTextPrefix(storage, registry) as prefix:
        for _ in range(60):
            view = prefix.step(run.project_id)
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
        assert registry._codex_exec_test_host.admissions == admissions == 8
        assert not registry._codex_exec_test_host.image_calls
    original.close()
