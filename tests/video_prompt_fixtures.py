"""Offline, source-grounded H3 review packages for fixture-only video tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


_FIXTURE_ENGLISH = {
    "交代选择": "The shot establishes a choice.",
    "角色握紧信件。": "The character tightens their grip on the letter.",
    "稳定推进": "The camera advances steadily.",
}


def reviewed_h3_body(client: TestClient, project_id: str, body: dict) -> dict:
    endpoint = f"/api/v2/projects/{project_id}/video-jobs/prompt-preview"
    sources_response = client.post(endpoint, json=body)
    assert sources_response.status_code == 200, sources_response.text
    sources = sources_response.json()
    fields = []
    for source in sources["sources"]:
        path, text = source["path"], source["text"]
        if path == "reviewedSoundscape":
            english = "A soft paper rustle accompanies the visible hand movement."
        elif text in _FIXTURE_ENGLISH:
            english = _FIXTURE_ENGLISH[text]
        else:
            assert text.isascii(), f"fixture lacks an English rendering for {path}: {text}"
            english = text
        fields.append({"path": path, "english": english})
    reviewed = {"sourceHash": sources["sourceHash"], "reviewedEnglish": True, "fields": fields}
    preview_response = client.post(endpoint, json={**body, "reviewedDirections": reviewed})
    assert preview_response.status_code == 200, preview_response.text
    reviewed["promptSha256"] = preview_response.json()["compiledPromptSha256"]
    return {**body, "reviewedDirections": reviewed}
