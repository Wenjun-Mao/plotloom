"""Global rendering context must not become every reference's entity inventory."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from plotloom.autopilot_brief_style import (
    EMPTY_DIRECTION,
    freeze_brief_style,
    image_style_guidance,
)
from plotloom.autopilot_contracts import POLICY_VERSION
from plotloom.autopilot_image_controller import AutopilotImageController
from plotloom.autopilot_image_guidance import (
    IMAGE_CONTENT_OWNERSHIP_CONTRACT,
    IMAGE_CONTENT_OWNERSHIP_INSTRUCTION,
)
from plotloom.codex_exec_prompts import assignment_prompt
from plotloom.story_workloads import FIXED_CHINESE_BRIEF


@pytest.mark.parametrize("direction", ["2D 动画；白色背景；黄色向日葵；稳定构图", "Watercolor; red lantern; quiet street",
                                       "纸雕\n保留文字与人物", None])
def test_global_context_is_preserved_without_reclassifying_subject_ownership(tmp_path, direction):
    before = freeze_brief_style(direction)
    guidance = assignment_prompt(job_id="ij_" + "a" * 24, package_path=tmp_path / "package",
                                 delivery_path=tmp_path / "delivery", domain="image")
    assert IMAGE_CONTENT_OWNERSHIP_CONTRACT in guidance
    assert IMAGE_CONTENT_OWNERSHIP_INSTRUCTION in guidance
    assert image_style_guidance(direction, follows_brief=True) == (direction if direction else EMPTY_DIRECTION)
    assert "accepted Cast character owns included and excluded entities" in guidance
    assert "accepted Art subject" in guidance and "prompt, sheet and negative prompt" in guidance
    assert "own visible content, action and composition" in guidance
    assert "saved-Brief direction or an explicitly selected preset" in guidance
    assert "empty saved-Brief direction" in guidance
    assert "stop and report the exact conflict" in guidance
    assert freeze_brief_style(direction) == before


@pytest.mark.parametrize("owner,field", [("character-reference", "visual_direction"),
                                         ("art-reference", "render_direction"), ("image", "presentation_change")])
@pytest.mark.parametrize("authority,raw", [("brief", "2D 动画；白色背景；黄色向日葵；稳定构图"),
                                          ("brief", None), ("preset", "Watercolor; red lantern"), ("preset", None)])
def test_automatic_owner_preserves_direction_under_each_style_authority(monkeypatch, owner, field, authority, raw):
    import plotloom.autopilot_image_controller as module
    brief = FIXED_CHINESE_BRIEF.model_copy(update={"visual_style": raw, "visual_style_selections": []})
    pin = {"version": "p1.5-pin.v2", "codeRevision": "a" * 40}
    policy = SimpleNamespace(version=POLICY_VERSION, max_jobs=16, max_images=8, brief=brief.model_dump(mode="json"),
                             effective_style_authority=authority, execution_pins={"image": pin})
    view = SimpleNamespace(id="run", project_id="project", lifetime_jobs=0, lifetime_images=0, checkpoints=[], policy=policy)
    store = MagicMock()
    context = {"id": "ij_" + "a" * 24, "requestHash": "b" * 64, "request": {"specialistPreflight": pin}}
    store.media.prepare_character_reference_proposal.return_value = {"proposal": context}
    store.media.prepare_art_reference_proposal.return_value = {"proposal": context}
    store.media.prepare_image_job.return_value = {"job": context}
    subject = SimpleNamespace(owner=owner, id="subject", consumer_character_id="C01", subject_type="scene")
    inventory = SimpleNamespace(cast_revision=1, storyboard_revision=1, entity_revision_id="entity", storyboard_hash="c" * 64,
                                production_hash="d" * 64)
    controller = AutopilotImageController(MagicMock())
    monkeypatch.setattr(controller, "command", lambda *_args: nullcontext())
    monkeypatch.setattr(module, "image_package", lambda *_args: None)
    controller.prepare(store, view, "claim", subject, inventory, "operation")
    method = {"character-reference": "prepare_character_reference_proposal", "art-reference": "prepare_art_reference_proposal",
              "image": "prepare_image_job"}[owner]
    actual = getattr(store.media, method).call_args.kwargs[field]
    expected = image_style_guidance(raw, follows_brief=authority == "brief")
    prefix = {"character-reference": "按冻结人物形象生成一张清晰身份参考图；",
              "art-reference": "按冻结美术方案生成一张独立参考图；",
              "image": "按冻结镜头动作与构图生成一张首帧；"}[owner]
    assert actual == prefix + expected
    assert IMAGE_CONTENT_OWNERSHIP_CONTRACT not in actual
    prompt = assignment_prompt(job_id=context["id"], package_path=Path("/frozen/package"),
                               delivery_path=Path("/frozen/delivery"), domain="image")
    assert IMAGE_CONTENT_OWNERSHIP_INSTRUCTION in prompt
    assert store.repository.autopilot.checkpoint.call_args.kwargs["evidence"].execution_pin == pin


def test_real_automatic_owner_path_freezes_rule_without_changing_accepted_stage_bytes(
    tmp_path, monkeypatch, compact_two_cut_text_prefix,
):
    from contextlib import closing

    from plotloom.image_commands import image_context
    from plotloom.persistence.codec import stable_hash
    from tests.autopilot_compact_text_fixtures import compact_safety_image_environment
    from tests.autopilot_image_fixtures import run_pack

    storage, _registry, service, view, images, _text = compact_safety_image_environment(
        tmp_path, monkeypatch, compact_two_cut_text_prefix)
    try:
        with closing(storage.projects.open(view.project_id)) as store:
            accepted_before = (store.cast_state().accepted_cast.model_dump(mode="json"),
                               store.art_state().accepted_art.model_dump(mode="json"))
        complete = run_pack(storage, service, view)
        assert complete.state == "awaiting_review" and complete.handoff is None
        owners = set()
        with closing(storage.projects.open(view.project_id)) as store:
            for checkpoint in complete.checkpoints:
                owner = checkpoint["evidence"]["owner"]
                if owner not in {"character-reference", "art-reference", "image"}:
                    continue
                owners.add(owner)
                context = image_context(store, owner, checkpoint["evidence"]["jobId"])
                snapshot = context["request"]["frozenSnapshot"]
                direction = (snapshot["visualDirection"] if owner == "character-reference" else
                             snapshot["renderDirection"] if owner == "art-reference" else
                             snapshot["creatorDirection"]["presentationChange"])
                # Creator-visible fields and retained package projection remain
                # original data; the native invocation owns receiving guidance.
                assert IMAGE_CONTENT_OWNERSHIP_CONTRACT not in direction
                prompt = assignment_prompt(job_id=context["id"], package_path=Path("/frozen/package"),
                                           delivery_path=Path("/frozen/delivery"), domain="image")
                assert IMAGE_CONTENT_OWNERSHIP_INSTRUCTION in prompt
                assert stable_hash(context["request"]) == checkpoint["evidence"]["requestHash"]
            assert (store.cast_state().accepted_cast.model_dump(mode="json"),
                    store.art_state().accepted_art.model_dump(mode="json")) == accepted_before
        assert owners == {"character-reference", "art-reference", "image"} and len(images) == 8
    finally:
        service.close()
