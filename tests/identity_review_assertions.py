"""Real offline API regressions over an ingested, exact-binding image candidate."""

import json
import sqlite3
from copy import deepcopy

from tests.video_prompt_fixtures import reviewed_h3_body


def assert_explicit_identity_decisions(client, project_id, preview_body, binding, passed, preview,
                                      provider, database_path, accepted_cast):
    url = f"/api/v2/projects/{project_id}"
    review_body = {
        "bindingId": binding["id"], "expectedReviewRevision": passed["stateRevision"],
        "reviewer": "Human fixture reviewer", "notes": "Explicit uncertainty policy fixture.",
        "comparisons": [{"characterId": "fixture-hero", "judgment": "unassessable",
                         "identityNotes": "Hands alone cannot identify this person.",
                         "stateNotes": "The frozen hand-only crop remains intentional."}],
    }
    video_body = {
        "approvalId": preview_body["approvalId"], "shotId": binding["shotId"],
        "storyboardRevision": preview_body["storyboardRevision"],
        "expectedSelectionRevision": preview_body["expectedSelectionRevision"],
        "idempotencyKey": "explicit-review-fixture", "aspectPolicy": "contain_pad",
        "allowLetterbox": True, "seed": 31, "playbackIntent": "segment_required",
    }
    frozen_pass_video = client.post(f"{url}/video-jobs", json=reviewed_h3_body(client, project_id, video_body))
    assert frozen_pass_video.status_code == 201, frozen_pass_video.text
    frozen_pass_video = frozen_pass_video.json()
    assert frozen_pass_video["snapshot"]["samePersonReviewId"] == passed["id"]

    def reviews():
        return client.get(f"{url}/same-person-reviews").json()

    def frozen_projections_are_refused():
        old_preview = next(item for item in client.get(f"{url}/still-previews").json()["previews"] if item["id"] == preview["id"])
        assert old_preview["state"] == "stale"
        assert old_preview["manifest"] == preview["manifest"]
        jobs = client.get(f"{url}/video-jobs").json()["jobs"]
        old = next(item for item in jobs if item["id"] == frozen_pass_video["id"])
        assert old["snapshot"] == frozen_pass_video["snapshot"]
        assert old["inputStatus"] == "current"  # source facts have not changed
        assert old["productionEligible"] is False and old["current"] is False
        assert client.post(f"{url}/video-jobs/{old['id']}/submit").status_code == 409

    for additions in [{}, {"productionDecision": "authorize"},
                      {"uncertaintyReason": "Intentional hand-only framing."},
                      {"productionDecision": "authorize", "uncertaintyReason": "   "}]:
        invalid = deepcopy(review_body)
        invalid["comparisons"][0].update(additions)
        assert client.post(f"{url}/same-person-reviews", json=invalid).status_code == 422
        assert reviews()["revision"] == passed["stateRevision"]

    for judgment, decision in [("fail", None), ("unassessable", "hold"), ("unassessable", "authorize")]:
        body = deepcopy(review_body)
        body["comparisons"][0]["judgment"] = judgment
        if decision:
            body["comparisons"][0].update(productionDecision=decision,
                                         uncertaintyReason="Intentional hand-only crop; reviewer accepts that face and stable identity are not observable.")
        saved = client.post(f"{url}/same-person-reviews", json=body)
        assert saved.status_code == 201, saved.text
        saved = saved.json()
        review_body["expectedReviewRevision"] = saved["stateRevision"]
        assert saved["current"] and saved["latest"]
        assert saved["productionEligible"] is (decision == "authorize")
        older_pass = next(item for item in reviews()["reviews"] if item["id"] == passed["id"])
        assert older_pass["current"] and not older_pass["latest"] and not older_pass["productionEligible"]
        frozen_projections_are_refused()
        if decision != "authorize":
            assert client.post(f"{url}/still-previews", json=preview_body).status_code == 409
            assert client.post(f"{url}/video-jobs/prompt-preview", json=video_body).status_code == 409
            assert client.post(f"{url}/video-jobs", json=video_body).status_code == 409
        else:
            accepted = saved

    accepted_preview = client.post(f"{url}/still-previews", json=preview_body).json()
    assert accepted_preview["manifest"]["frames"][0]["identityReviewId"] == accepted["id"]
    fresh_video = client.post(f"{url}/video-jobs", json=reviewed_h3_body(client, project_id, {
        **video_body, "idempotencyKey": "explicit-authorized-review-fixture",
    }))
    assert fresh_video.status_code == 201, fresh_video.text
    fresh_video = fresh_video.json()
    assert fresh_video["snapshot"]["samePersonReviewId"] == accepted["id"]
    assert fresh_video["snapshotHash"] != frozen_pass_video["snapshotHash"]
    assert fresh_video["current"] and fresh_video["productionEligible"]
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0

    # Mutate only fixture-owned input records, then restore exact bytes: currentness
    # must be a source fact independent of which judgment authorized production.
    for table, column, row_id, value in [
        ("v2_managed_assets", "original_hash", binding["assetId"], "0" * 64),
        ("v2_reviewed_shot_bindings", "visual_intent_revision", binding["id"], 999),
    ]:
        with sqlite3.connect(database_path) as connection:
            original = connection.execute(f"SELECT {column} FROM {table} WHERE id=?", (row_id,)).fetchone()[0]
            connection.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (value, row_id))
        assert not reviews()["reviews"][0]["current"]
        assert client.post(f"{url}/still-previews", json=preview_body).status_code == 409
        assert client.post(f"{url}/video-jobs/prompt-preview", json=video_body).status_code == 409
        with sqlite3.connect(database_path) as connection:
            connection.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (original, row_id))
    with sqlite3.connect(database_path) as connection:
        head_id, source_hash = connection.execute("SELECT id, content_hash FROM v2_stage_heads WHERE stage='storyboard'").fetchone()
        connection.execute("UPDATE v2_stage_heads SET content_hash=? WHERE id=?", ("0" * 64, head_id))
    assert not reviews()["reviews"][0]["current"]
    assert client.post(f"{url}/video-jobs/prompt-preview", json=video_body).status_code == 409
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE v2_stage_heads SET content_hash=? WHERE id=?", (source_hash, head_id))
    cast_before = deepcopy(accepted_cast)
    accepted_cast["contentHash"] = "d" * 64
    assert not reviews()["reviews"][0]["current"]
    assert not client.get(f"{url}/video-jobs").json()["jobs"][0]["current"]
    accepted_cast.update(cast_before)
    assert reviews()["reviews"][0]["productionEligible"]

    # Tampering with the immutable request cannot be repaired by a valid review.
    with sqlite3.connect(database_path) as connection:
        stored = connection.execute("SELECT snapshot FROM v2_video_jobs WHERE id=?", (fresh_video["id"],)).fetchone()[0]
        changed = json.loads(stored)
        changed["samePersonReviewId"] = passed["id"]
        connection.execute("UPDATE v2_video_jobs SET snapshot=? WHERE id=?", (json.dumps(changed), fresh_video["id"]))
    invalid = next(item for item in client.get(f"{url}/video-jobs").json()["jobs"] if item["id"] == fresh_video["id"])
    assert invalid["inputStatus"] == "invalid" and not invalid["productionEligible"]
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE v2_video_jobs SET snapshot=? WHERE id=?", (stored, fresh_video["id"]))
    refusal = deepcopy(review_body)
    refusal["comparisons"][0].update(productionDecision="hold", uncertaintyReason="Identity uncertainty is no longer accepted.")
    refused = client.post(f"{url}/same-person-reviews", json=refusal)
    assert refused.status_code == 201, refused.text
    assert refused.json()["current"] and not refused.json()["productionEligible"]
    retained = next(item for item in client.get(f"{url}/video-jobs").json()["jobs"] if item["id"] == fresh_video["id"])
    assert retained["inputStatus"] == "current" and not retained["productionEligible"]
    assert retained["snapshot"] == fresh_video["snapshot"]
    retained_preview = next(item for item in client.get(f"{url}/still-previews").json()["previews"] if item["id"] == accepted_preview["id"])
    assert retained_preview["state"] == "stale" and retained_preview["manifest"] == accepted_preview["manifest"]
    assert client.post(f"{url}/video-jobs/{fresh_video['id']}/submit").status_code == 409
    assert provider.preflight_calls == provider.upload_calls == len(provider.submits) == 0
