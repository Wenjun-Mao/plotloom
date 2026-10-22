"""Runtime-owned QA authority using existing nonportable store grant storage."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from pathlib import Path

from ..delegated_qa import project_scope, require_scope
from ..delegated_qa_contracts import AgentQaAttribution
from ..exceptions import InvalidTransitionError
from ..persistence.codec import stable_hash
from .video_batch_grants import VideoBatchGrants

_command = ContextVar("delegated_qa_command", default=None)


def grant_key(scope):
    return "qa-scope:" + scope.id


def bind_original_qa_scope(store, application):
    """Trusted operator preflight in the app runtime; never exposed as an API.

    The operator must verify this is the original disposable home first. Binding
    is immutable and uses this runtime's path/stat view, including in containers.
    """
    from ..domain import StageName
    scope = project_scope(store.manifest.project_id)
    if scope is None or store.authoring.get_stage_head(scope.project_id, StageName.STORYBOARD).content_hash != scope.storyboard_hash:
        raise InvalidTransitionError("no exact owner-granted QA storyboard")
    assets = {item["id"]: item for item in store.media.list_managed_assets(scope.project_id)}
    if any(item.asset_id not in assets or assets[item.asset_id]["originalHash"] != item.original_hash for item in scope.materials):
        raise InvalidTransitionError("owner-granted QA originals differ")
    from ..delegated_qa import NativeMaterialQaScope, require_native_bundle
    if isinstance(scope, NativeMaterialQaScope):
        from ..persistence.project.autopilot_handoff import review_material
        current = review_material(store)
        require_native_bundle(scope, current["bundle"], current["bundleHash"])
    VideoBatchGrants(application).authorize(store, grant_key(scope), stable_hash(asdict(scope)))


def browser_qa_context(store, application):
    """Read-only discovery; explicit browser opt-in still supplies every actor."""
    from ..domain import StageName
    from ..project_storage.format import ProjectStorageError
    scope = project_scope(store.manifest.project_id)
    if scope is None:
        return {"eligible": False, "attribution": None, "required": False, "reason": None}
    actor = AgentQaAttribution(scope_id=scope.id)
    try:
        require_runtime_grant(store, application, actor)
        head = store.authoring.get_stage_head(scope.project_id, StageName.STORYBOARD)
        assets = {item["id"]: item for item in store.media.list_managed_assets(scope.project_id)}
        if head.content_hash != scope.storyboard_hash or any(
                item.asset_id not in assets or assets[item.asset_id]["originalHash"] != item.original_hash for item in scope.materials):
            raise InvalidTransitionError("QA source differs from grant")
        from ..delegated_qa import NativeMaterialQaScope, require_native_bundle
        if isinstance(scope, NativeMaterialQaScope):
            from ..persistence.project.autopilot_handoff import review_material, handoff_is_current
            with store.repository._read() as session:
                run = store.repository.autopilot.row(session, scope.project_id)
                if run is None or run.id != scope.run_id:
                    raise InvalidTransitionError("QA native run differs from grant")
                if run.state == "handed_off":
                    if not handoff_is_current(session, store.repository, run):
                        raise InvalidTransitionError("QA native material handoff is stale")
                else:
                    current = review_material(store)
                    require_native_bundle(scope, current["bundle"], current["bundleHash"])
    except (InvalidTransitionError, ProjectStorageError):
        return {"eligible": False, "attribution": None, "required": True,
            "reason": "此项目需要代理 QA 身份，但原始运行时授权或当前素材尚未核实；不能改为创作者确认。"}
    return {"eligible": True, "attribution": actor.model_dump(mode="json", by_alias=True), "required": True, "reason": None}


def require_runtime_grant(store, application, attribution):
    scope = require_scope(store.manifest.project_id, attribution)
    VideoBatchGrants(application, initialize=False).require(store, grant_key(scope), stable_hash(asdict(scope)))
    return scope


@contextmanager
def qa_command(store, application, attribution):
    if not isinstance(attribution, AgentQaAttribution) and not isinstance(attribution, dict):
        yield
        return
    if isinstance(attribution, dict) and attribution.get("kind") != "agent_operated_qa":
        yield
        return
    scope = require_runtime_grant(store, application, attribution)
    info = store.database_path.stat()
    token = _command.set((scope.id, store.database_path.resolve(), info.st_dev, info.st_ino))
    try:
        yield
    finally:
        _command.reset(token)


def require_command_context(connection, scope):
    path = Path(next(row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"))
    info = path.stat()
    if _command.get() != (scope.id, path.resolve(), info.st_dev, info.st_ino):
        raise InvalidTransitionError("QA writes require the app-owned original runtime incarnation grant")
