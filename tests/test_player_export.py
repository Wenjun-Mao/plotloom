"""Installed graph + normal API selection + immutable standalone export."""
import json
from contextlib import closing
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select

from plotloom.persistence.schema import PlayerExportRow, VideoCandidateSelectionRow

pytest_plugins = ("tests.player_export_fixtures",)


def test_export_real_installed_source_api_selection_reopen_and_snapshot(exportable_bridge, tmp_path, monkeypatch):
    storage, client, project, request, replace_first_slot = exportable_bridge
    result = client.post(f"/api/v2/projects/{project}/player-exports", json=request)
    assert result.status_code == 200, result.text
    assert result.headers["content-type"] == "application/zip"
    receipt_uri = result.headers["x-plotloom-build-receipt"]
    with ZipFile(BytesIO(result.content)) as archive:
        assert {"index.html", "player.js", "player.css"} <= set(archive.namelist())
        assert all(not name.startswith("/") and ".." not in name for name in archive.namelist())
        html = archive.read("index.html").decode()
        public = json.loads(html.split('type="application/json">')[1].split("</script>")[0])
        assert public["gameId"] == request["gameId"]
        assert len(public["nodes"]) == 4
        assert not next(node for node in public["nodes"] if node["id"] == "choose")["clips"]
        assert all(node["clips"] for node in public["nodes"] if node["id"] != "choose")
        assert any(node["edges"] for node in public["nodes"])
        assert "admissionId" not in html and "sourceBinding" not in html and "assets/" not in html
        archive.extractall(tmp_path / "standalone")
    with closing(storage.projects.open(project)) as store:
        receipt = json.loads(store.artifacts.get(receipt_uri))
        assert receipt["archiveHash"] == sha256(result.content).hexdigest()
        assert receipt["presentation"]["admissionId"] == request["admissionId"]
        with store.repository._read() as session:
            assert session.scalar(select(PlayerExportRow)).receipt_uri == receipt_uri
    # Re-export is deterministic and does not ask for quality observations.
    again = client.post(f"/api/v2/projects/{project}/player-exports", json=receipt["presentation"])
    assert again.status_code == 200, again.text
    assert again.content == result.content
    assert client.get(f"/api/v2/projects/{project}/player-export-presentation").json() == receipt["presentation"]
    snapshot = storage.recovery.create_snapshot(project)
    captured = {item.relative_path for item in snapshot.manifest.files}
    assert receipt_uri in captured and receipt["archiveUri"] in captured
    assert (Path(snapshot.location) / receipt["archiveUri"]).read_bytes() == result.content
    replace_first_slot()
    replaced = client.post(f"/api/v2/projects/{project}/player-exports", json=request)
    assert replaced.status_code == 200, replaced.text
    with ZipFile(BytesIO(replaced.content)) as archive:
        updated = json.loads(archive.read("index.html").decode().split('type="application/json">')[1].split("</script>")[0])
        assert updated["storyRevision"] == public["storyRevision"]
        assert updated["assetVersion"] != public["assetVersion"]
        changed = [(old["slot"], old["src"], new["src"]) for old_node, new_node in zip(public["nodes"], updated["nodes"], strict=True)
            for old, new in zip(old_node["clips"], new_node["clips"], strict=True) if old["src"] != new["src"]]
        assert len(changed) == 1 and changed[0][0] == "opening-first"
        for node in updated["nodes"]:
            for item in node["clips"]:
                item["src"] = next(old for old_node in public["nodes"] for old in old_node["clips"] if old["slot"] == item["slot"])["src"]
        updated["assetVersion"] = public["assetVersion"]
        assert updated == public  # All graph, text, choices, dialogue and slot identities stay exact.
        with ZipFile(BytesIO(result.content)) as original_archive:
            assert archive.read("player.js") == original_archive.read("player.js")
            assert archive.read("player.css") == original_archive.read("player.css")
        archive.extractall(tmp_path / "standalone-updated")
    # A real selection change while media is read cannot publish a mixed build.
    import plotloom.player_export as exporting
    check = exporting._check_media
    mutated = False
    def change_during_copy(content, frames):
        nonlocal mutated
        check(content, frames)
        if not mutated:
            mutated = True
            with closing(storage.projects.open(project)) as store, store.repository._write() as session:
                session.scalar(select(VideoCandidateSelectionRow)).revision += 1
    monkeypatch.setattr(exporting, "_check_media", change_during_copy)
    raced = client.post(f"/api/v2/projects/{project}/player-exports", json=request)
    assert raced.status_code in {404, 409}, raced.text
    with closing(storage.projects.open(project)) as store, store.repository._read() as session:
        assert len(list(session.scalars(select(PlayerExportRow)))) == 2
    with closing(storage.projects.open(project)) as store, store.repository._write() as session:
        selection = session.scalar(select(VideoCandidateSelectionRow))
        restore_revision = selection.revision
        selection.selected_video_job_id = None
    refused = client.post(f"/api/v2/projects/{project}/player-exports", json=request)
    assert refused.status_code == 409, refused.text
    # Leave a complete disposable fixture for the normal workbench download.
    with closing(storage.projects.open(project)) as store:
        replacement_receipt = json.loads(store.artifacts.get(replaced.headers["x-plotloom-build-receipt"]))
    selected = client.post(f"/api/v2/projects/{project}/video-segments/{replacement_receipt['media'][0]['segmentId']}/select",
        json={"expectedSelectionRevision": restore_revision})
    assert selected.status_code == 201, selected.text
