"""One authorized target owns one idempotent job, even on the direct API path."""
from .exceptions import InvalidTransitionError
from .persistence.schema import VideoBatchRow


def target_idempotency_key(view, target):
    if view["manifest"]["setup"].get("singleRequest"):
        return target["args"]["idempotency_key"]
    return f"batch-{view['id']}-{target['shotId']}"


def preparation_owner(session, snapshot, idempotency_key):
    basis = snapshot["reviewedDirections"].get("reviewBasis") or {}
    row = session.get(VideoBatchRow, basis.get("batchId"))
    if row is None or row.state != "running":
        raise InvalidTransitionError("制作授权批次已暂停、取消或尚未开始。")
    targets = [item for item in row.manifest["targets"] if item["shotId"] == basis.get("shotId")]
    if len(targets) != 1 or targets[0]["mode"] != "generate":
        raise InvalidTransitionError("制作授权未允许本镜头创建新任务。")
    expected = target_idempotency_key({"id": row.id, "manifest": row.manifest}, targets[0])
    if idempotency_key != expected:
        raise InvalidTransitionError("单镜头授权仅允许原始幂等任务；不可更换身份重复创建。")
    return row


def link_prepared_job(row, job, now):
    links = row.execution["jobs"]
    shot_id = job.snapshot["shot"]["id"]
    if links.get(shot_id) not in {None, job.id}:
        raise InvalidTransitionError("本镜头已绑定另一个不可重复的原任务。")
    row.execution = row.execution | {"jobs": links | {shot_id: job.id}}
    row.revision += 1
    row.updated_at = now
