"""Exact explicit identity for a rejected single-shot successor."""
import json

from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash


def single_replacement_setup(prior, setup, facts):
    """A new key is explicit input; generation settings remain source-bound."""
    old = prior["setup"].get("singleRequest")
    new = setup.get("singleRequest")
    if old is None and new is None:
        return None
    if not old or not new or len(facts) != 1:
        raise InvalidTransitionError("单镜头重做必须沿用原单镜头范围，并明确提供新的请求身份。")
    shot_id = facts[0]["shotId"]
    if (old["shotId"] != shot_id or new["shotId"] != shot_id
            or prior["scopeShotIds"] != [shot_id] or setup.get("shotIds") != [shot_id]):
        raise InvalidTransitionError("单镜头重做不可使用其他镜头或扩大制作范围。")
    key = new["idempotencyKey"]
    if key == old["idempotencyKey"]:
        raise InvalidTransitionError("单镜头重做必须明确提供新的幂等请求身份，不能重用原任务身份。")
    if new.get("seed") is None or new.get("reviewedDirections") is not None:
        raise InvalidTransitionError("单镜头重做需要明确保留已审阅的种子和设置；原英文检查或授权不可复制。")
    return shot_id, key


def assert_fresh_single_replacement(read, project_id, prior, setup, facts):
    identity = single_replacement_setup(prior, setup, facts)
    if identity is None:
        return
    _shot_id, key = identity
    if read("SELECT id FROM v2_video_jobs WHERE project_id=? AND idempotency_key=?", (project_id, key)):
        raise InvalidTransitionError("此幂等请求身份已属于现有视频任务；请为本次重做明确选择新的身份。")
    for (raw,) in read("SELECT manifest FROM v2_video_batches WHERE project_id=?", (project_id,)):
        old = json.loads(raw)["setup"].get("singleRequest")
        if old and old["idempotencyKey"] == key:
            raise InvalidTransitionError("此幂等请求身份已冻结于另一个单镜头请求；不能重用或转移。")


def assert_single_replacement_manifest(read, project_id, prior, manifest, facts):
    """Shared runtime/portable admission; retained jobs are never rewritten."""
    identity = single_replacement_setup(prior, manifest["setup"], facts)
    if identity is None:
        return
    shot_id, key = identity
    old_targets = [item for item in prior["targets"] if item["shotId"] == shot_id]
    targets = manifest["targets"]
    if (len(old_targets) != 1 or len(targets) != 1 or targets[0]["shotId"] != shot_id
            or targets[0]["mode"] != "generate" or targets[0]["jobId"] is not None):
        raise InvalidTransitionError("单镜头重做必须只冻结一个明确的新候选。")
    target, original = targets[0], old_targets[0]
    if (target["snapshot"] != original["snapshot"] or target["sourceHash"] != original["sourceHash"]
            or target["args"]["idempotency_key"] != key):
        raise InvalidTransitionError("单镜头重做的来源或可见设置已改变；请回到原来源和设置重新审阅。")
    rejected = read("SELECT idempotency_key FROM v2_video_jobs WHERE project_id=? AND id=?", (project_id, facts[0]["jobId"]))
    if len(rejected) != 1 or rejected[0][0] != prior["setup"]["singleRequest"]["idempotencyKey"]:
        raise InvalidTransitionError("被拒绝原任务的幂等身份与冻结的单镜头请求不同。")
    history = {item["jobId"] for item in manifest["rejectedHistory"]}
    # A prepared successor may already own this key when portable admission is
    # called. Only its exact source and immutable manifest endorsement qualify.
    for identifier, raw in read("SELECT id,snapshot FROM v2_video_jobs WHERE project_id=? AND idempotency_key=?", (project_id, key)):
        snapshot = json.loads(raw)
        frozen = {name: value for name, value in snapshot.items() if name not in {"reviewedDirections", "compiledPrompt"}}
        basis = (snapshot.get("reviewedDirections") or {}).get("reviewBasis") or {}
        if identifier in history or frozen != target["snapshot"] or basis.get("manifestHash") != stable_hash(manifest):
            raise InvalidTransitionError("单镜头重做身份已被其他镜头或原任务占用。")


def known_single_successor(session, owner, project_id, request):
    """An exact replay reads its original successor without reopening any work."""
    if request.setup.single_request is None:
        return None
    from sqlalchemy import select

    from .persistence.schema import VideoBatchRow
    from .video_batch_replacement import assert_rejected_history, evidence_reader
    payload = request.model_dump(mode="json", by_alias=True)
    rows = session.scalars(select(VideoBatchRow).where(VideoBatchRow.project_id == project_id)).all()
    matches = [row for row in rows if row.execution.get("singleReplacementRequest") == payload]
    if not matches:
        return None
    if len(matches) != 1:
        raise InvalidTransitionError("同一单镜头重做意图存在多个后继记录；请核对原任务。")
    row = matches[0]
    reference = row.manifest.get("replacement") or {}
    if (row.manifest["setup"] != payload["setup"] or reference.get("batchId") != request.batch_id
            or reference.get("revision") != request.expected_revision
            or reference.get("rejectedJobIds") != sorted(request.rejected_job_ids)):
        raise InvalidTransitionError("已保存的单镜头重做意图与原始来源身份不一致。")
    assert_rejected_history(evidence_reader(session), project_id, row.manifest)
    return owner.view(row)
