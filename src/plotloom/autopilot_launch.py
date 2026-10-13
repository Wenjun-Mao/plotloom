"""Server-owned bounded launch and same-host execution admission."""
from hashlib import sha256
from pathlib import Path

from .autopilot_contracts import LaunchPolicy, POLICY_VERSION, PREVIOUS_POLICY_VERSION
from .art_style import freeze_art_style
from .cast_style import freeze_cast_style
from .exceptions import InvalidTransitionError
from .source_structures import planned_structure

CREATIVE_STAGES = ("outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation")
GEOMETRY = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1024, 1024)}


def frozen_bindings(registry):
    settings = registry.view()
    bindings = {role: settings[role]["taskId"] for role in ("text", "image")}
    if any(not value for value in bindings.values()) or len(set(bindings.values())) != 2:
        raise InvalidTransitionError("请先配置两个不同的 Codex 文字和图像助手。")
    return bindings


def image_execution_pin(code_revision):
    root = Path(__file__).resolve().parents[2]
    return {"version": "p1.5-pin.v1", "skillVersion": "plotloom-image-specialist.v3", "executionContract": "codex_specialist.v2",
        "codeRevision": code_revision, "skillHash": sha256((root / ".agents/skills/plotloom-image-specialist/SKILL.md").read_bytes()).hexdigest()}


def freeze_launch_policy(store, registry, request):
    brief = store.project().brief
    planned_structure(store.manifest.project_id, brief)
    if request.style_authority == "brief":
        if request.render_style is not None or request.art_render_style is not None:
            raise InvalidTransitionError("简报画风模式不能附带独立预设。")
        render_style = art_render_style = None
    else:
        if request.render_style is None or request.art_render_style is None or request.render_style != request.art_render_style:
            raise InvalidTransitionError("人物和美术需使用一致的画风。")
        freeze_cast_style(request.render_style, brief.visual_direction)
        freeze_art_style(request.art_render_style, brief.visual_direction)
        render_style, art_render_style = request.render_style, request.art_render_style
    if brief.aspect_ratio not in GEOMETRY:
        raise InvalidTransitionError("自动素材包仅支持 16:9、9:16 或 1:1 画面比例；简报仍保留。")
    pins = {stage: store.creative_handoff_exchange().current_execution_pin(stage) for stage in CREATIVE_STAGES}
    code_revision = pins["bridge-intent"]["upstreamRevision"]
    if pins["bridge-presentation"]["upstreamRevision"] != code_revision:
        raise InvalidTransitionError("原生文字执行版本不一致。")
    pins["image"] = image_execution_pin(code_revision)
    width, height = GEOMETRY[brief.aspect_ratio]
    return LaunchPolicy(style_authority=request.style_authority, render_style=render_style, art_render_style=art_render_style,
        max_images=request.max_images, max_jobs=request.max_jobs, image_width=width, image_height=height,
        code_revision=code_revision, specialist_bindings=frozen_bindings(registry), execution_pins=pins,
        brief=brief.model_dump(mode="json", by_alias=False))


def assert_frozen_execution(store, registry, policy):
    if policy.version not in {PREVIOUS_POLICY_VERSION, POLICY_VERSION}:
        raise InvalidTransitionError("旧冻结策略只保留证据；请接管或创建新的自动素材运行。")
    if policy.version == POLICY_VERSION and store.project().brief.model_dump(mode="json", by_alias=False) != policy.brief:
        raise InvalidTransitionError("已保存简报与本次冻结策略不同；请接管原素材运行。")
    from .geometry_preparation import geometry_policy
    if policy.geometry_preparation != geometry_policy():
        raise InvalidTransitionError("冻结几何处理运行版本已变化；请接管已有素材。")
    if frozen_bindings(registry) != policy.specialist_bindings:
        raise InvalidTransitionError("生成助手配置已变化；冻结运行不会改用新的助手。")
    assert_frozen_pins(store, policy)


def assert_frozen_pins(store, policy):
    if set(policy.execution_pins) != {*CREATIVE_STAGES, "image"}:
        raise InvalidTransitionError("冻结执行版本不完整。")
    for stage in CREATIVE_STAGES:
        if store.creative_handoff_exchange().current_execution_pin(stage) != policy.execution_pins[stage]:
            raise InvalidTransitionError("执行版本已变化；请接管或恢复原冻结版本。")
    if image_execution_pin(policy.code_revision) != policy.execution_pins["image"]:
        raise InvalidTransitionError("图像执行合同已变化。")


def require_job_capacity(view):
    counted = sum(item["evidence"].get("jobId") is not None for item in view.checkpoints)
    if counted >= view.policy.max_jobs:
        raise InvalidTransitionError("已达到冻结任务上限；请接管检查已保留的素材。")
