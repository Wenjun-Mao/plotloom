"""Explicit rejected-take succession, retaining exact native evidence and CAS."""
import json

from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash


def assert_rejected_take_mutable(session, project_id, job_id):
    """A superseded take is immutable evidence, even after its successor ends."""
    from sqlalchemy import select

    from .persistence.schema import VideoBatchRow
    manifests = session.scalars(select(VideoBatchRow.manifest).where(VideoBatchRow.project_id == project_id))
    if any(fact["jobId"] == job_id for manifest in manifests for fact in manifest.get("rejectedHistory", [])):
        raise InvalidTransitionError("superseded rejected take is frozen batch history; inspect its successor")


def evidence_reader(session):
    return lambda sql, params: session.connection().exec_driver_sql(sql, params).fetchall()


def rejected_fact(read, project_id, job_id):
    """Hash native rows, including proposals and claims; never delete or rewrite them.

    Both runtime and portable admission read the same SQLite values. Selection
    pointers are separate CAS facts and may change when the successor is selected.
    """
    jobs = read("SELECT * FROM v2_video_jobs WHERE project_id=? AND id=?", (project_id, job_id))
    if len(jobs) != 1:
        raise InvalidTransitionError("replacement rejected job is missing")
    reviews = read("SELECT * FROM v2_video_reviews WHERE video_job_id=? ORDER BY created_at,id", (job_id,))
    segments = read("SELECT * FROM v2_video_segments WHERE video_job_id=? ORDER BY id", (job_id,))
    claims = read("SELECT * FROM v2_project_video_dispatches WHERE video_job_id=? ORDER BY video_job_id", (job_id,))
    identity = read("SELECT state,snapshot,output_hash FROM v2_video_jobs WHERE id=?", (job_id,))[0]
    latest = read("SELECT id,decision FROM v2_video_reviews WHERE video_job_id=? ORDER BY created_at DESC,id DESC LIMIT 1", (job_id,))
    snapshot = json.loads(identity[1])
    if identity[0] != "ingested" or not identity[2] or not latest or latest[0][1] != "reject":
        raise InvalidTransitionError("replacement requires a terminal ingested rejected take")
    shot_id = snapshot["shot"]["id"]
    selected = read("SELECT selected_video_job_id FROM v2_video_candidate_selections WHERE project_id=? AND shot_id=?", (project_id, shot_id))
    if selected and selected[0][0] == job_id:
        raise InvalidTransitionError("a selected take cannot be excluded as rejected history")
    return {"jobId": job_id, "shotId": shot_id, "rejectionId": latest[0][0],
        "evidenceHash": stable_hash({"job": [list(row) for row in jobs], "reviews": [list(row) for row in reviews],
            "segments": [list(row) for row in segments], "claims": [list(row) for row in claims]})}


def assert_rejected_history(read, project_id, manifest):
    """Validate explicit lineage as well as every frozen rejected native record."""
    replacement = manifest.get("replacement")
    history = manifest.get("rejectedHistory", [])
    if replacement is None:
        if history:
            raise InvalidTransitionError("rejected history requires explicit replacement authority")
        return
    if set(replacement) != {"batchId", "revision", "manifestHash", "rejectedJobIds"}:
        raise InvalidTransitionError("invalid rejected replacement identity")
    prior = read("SELECT revision,state,manifest,manifest_hash,execution FROM v2_video_batches WHERE project_id=? AND id=?",
        (project_id, replacement["batchId"]))
    if (len(prior) != 1 or prior[0][0] != replacement["revision"] or prior[0][1] != "cancelled"
            or prior[0][3] != replacement["manifestHash"]):
        raise InvalidTransitionError("cancelled replacement predecessor changed")
    prior_manifest, execution = json.loads(prior[0][2]), json.loads(prior[0][4])
    if stable_hash(prior_manifest) != prior[0][3] or execution.get("authorizedManifestHash") != prior[0][3]:
        raise InvalidTransitionError("replacement predecessor has no exact English authorization")
    identifiers = replacement["rejectedJobIds"]
    inherited = prior_manifest.get("rejectedHistory", [])
    inherited_ids = {fact["jobId"] for fact in inherited}
    if (not identifiers or len(identifiers) != len(set(identifiers))
            or set(identifiers) & inherited_ids or not set(identifiers).issubset(execution["jobs"].values())):
        raise InvalidTransitionError("replacement must name distinct rejected predecessor jobs")
    added = [rejected_fact(read, project_id, identifier) for identifier in identifiers]
    expected = sorted([*inherited, *added], key=lambda fact: fact["jobId"])
    if history != expected or len({fact["jobId"] for fact in history}) != len(history):
        raise InvalidTransitionError("frozen rejected history changed")
    for fact in inherited:
        if rejected_fact(read, project_id, fact["jobId"]) != fact:
            raise InvalidTransitionError("inherited rejected history changed")
    generated = {target["shotId"] for target in manifest["targets"] if target["mode"] == "generate" and target["jobId"] is None}
    if not {fact["shotId"] for fact in added}.issubset(generated):
        raise InvalidTransitionError("each newly rejected take must have one fresh successor target")


def replacement_inventory(store, video, predecessor, request):
    from .video_batch_inventory import inventory
    if (predecessor is None or predecessor["id"] != request.batch_id
            or predecessor["revision"] != request.expected_revision or predecessor["state"] != "cancelled"):
        raise InvalidTransitionError("cancel the exact current predecessor and use its current revision")
    draft = predecessor["execution"].get("draft")
    if draft and draft["attempt"]["state"] not in {"completed", "failed", "settled"}:
        raise InvalidTransitionError("replacement predecessor directions are unsettled")
    jobs = {job["id"]: job for job in video.jobs(store)}
    for identifier in request.rejected_job_ids:
        if identifier not in jobs or not jobs[identifier]["current"]:
            raise InvalidTransitionError("replacement requires current rejected predecessor sources")
    with store.repository._read() as session:
        read = evidence_reader(session)
        assert_rejected_history(read, store.manifest.project_id, predecessor["manifest"])
        facts = [rejected_fact(read, store.manifest.project_id, identifier) for identifier in request.rejected_job_ids]
    history = sorted([*predecessor["manifest"].get("rejectedHistory", []), *facts], key=lambda fact: fact["jobId"])
    manifest = inventory(store, video, request.setup, rejected_history=history)
    manifest |= {"rejectedHistory": history, "replacement": {"batchId": predecessor["id"],
        "revision": predecessor["revision"], "manifestHash": predecessor["manifestHash"],
        "rejectedJobIds": sorted(request.rejected_job_ids)}}
    with store.repository._read() as session:
        assert_rejected_history(evidence_reader(session), store.manifest.project_id, manifest)
    if manifest["blockers"]:
        raise InvalidTransitionError("resolve all other batch conflicts before rejected-take replacement")
    return manifest
