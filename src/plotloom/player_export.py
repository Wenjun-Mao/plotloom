"""Static game archive publication with a private, immutable project build receipt."""
import json
from hashlib import sha256
from html import escape
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from sqlalchemy import select

from .contract_identity import utc_now
from .exceptions import InvalidTransitionError
from .persistence.codec import stable_hash
from .persistence.project.player_export import capture_player_export
from .persistence.project.selected_media_policy import selected_playback_policy
from .persistence.schema import PlayerExportRow
from .player_export_contracts import PlayerExportRequest, assert_public_player_data
from .video_segments import VideoSegmentError, _probe


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def current_export_presentation(store):
    project_id = store.manifest.project_id
    with selected_playback_policy(project_id), store.repository._read() as session:
        installed = store.repository.production_bridge.installation_in_session(session, project_id)
        if installed is None or installed.status != "current":
            raise InvalidTransitionError("standalone presentation requires a current installed production")
        rows = list(session.scalars(select(PlayerExportRow).where(PlayerExportRow.project_id == project_id)
            .order_by(PlayerExportRow.created_at.desc(), PlayerExportRow.receipt_hash.desc())))
    for row in rows:
        receipt = json.loads(store.artifacts.get(row.receipt_uri))
        if receipt["projectId"] != project_id or receipt["archiveHash"] != row.archive_hash or receipt["archiveUri"] != row.archive_uri:
            raise InvalidTransitionError("standalone build receipt does not match its inventory")
        presentation = PlayerExportRequest.model_validate(receipt["presentation"])
        if presentation.admission_id == installed.admission_id:
            return presentation
    return PlayerExportRequest(admission_id=installed.admission_id, game_id=f"project-{project_id}")


def _check_media(content, expected_frames, *, whole_take=False):
    with TemporaryDirectory(prefix="plotloom-player-probe-") as directory:
        path = Path(directory) / "segment.mp4"
        path.write_bytes(content)
        observed = _probe(path, strict_container=not whole_take)
        if observed.frame_count != expected_frames or (not whole_take and (observed.video_start != 0 or observed.audio_start != 0)):
            raise VideoSegmentError("exported segment differs from its exact selected timeline")
        return round(observed.format_duration * 1000)


def export_player(store, request):
    assert_public_player_data(request)
    snapshot = capture_player_export(store.repository, store.manifest.project_id, request)
    story, private = snapshot["public"], snapshot["private"]
    assert_public_player_data(story)
    files = {}
    verified_sources, timelines = set(), {}
    for media in private["media"]:
        for source in [{"uri": media["originalUri"], "hash": media["originalHash"]}, *media["sourceArtifacts"]]:
            identity = (source["uri"], source["hash"])
            if identity not in verified_sources:
                if sha256(store.artifacts.get(source["uri"])).hexdigest() != source["hash"]:
                    raise InvalidTransitionError("selected media source bytes differ from their provenance")
                verified_sources.add(identity)
        whole = media["hash"] == media["originalHash"]
        frames = media["outFrame"] - media["inFrame"]
        measured_ms = media.get("playbackDurationUnits", media["durationUnits"])
        if media["path"] in files:
            if timelines[media["path"]] != (frames, measured_ms):
                raise InvalidTransitionError("identical selected bytes cannot claim different frame counts")
            continue
        content = store.artifacts.get(media["uri"])
        if sha256(content).hexdigest() != media["hash"]:
            raise InvalidTransitionError("selected media bytes changed during standalone export")
        try:
            actual_ms = _check_media(content, frames, whole_take=whole)
            if whole and actual_ms != measured_ms:
                raise VideoSegmentError("whole take duration differs from selected playback evidence")
        except VideoSegmentError as error:
            raise InvalidTransitionError(str(error)) from error
        files[media["path"]] = content
        timelines[media["path"]] = (frames, measured_ms)
    static = Path(__file__).with_name("player_static")
    for name in ("player.js", "player.css"):
        files[name] = (static / name).read_bytes()
    files["favicon.svg"] = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#111417"/><path d="M12 8l13 8-13 8z" fill="#d8a15c"/></svg>'
    # A JSON script is data, but must still escape HTML's script closing syntax.
    embedded = _json(story).replace("<", "\\u003c").replace("&", "\\u0026")
    files["index.html"] = ("<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'; style-src \'self\'; media-src \'self\'; img-src \'self\'; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">'
        f"<title>{escape(story['title'])}</title><link rel=\"icon\" href=\"favicon.svg\"><link rel=\"stylesheet\" href=\"player.css\">"
        '<main id="game"></main><noscript>请启用 JavaScript 来游玩。</noscript>'
        f'<script id="story" type="application/json">{embedded}</script>'
        '<script src="player.js" defer></script></html>').encode()
    files["README.txt"] = "解压后打开 index.html，或在此目录使用任意静态 HTTP 服务器。无需 Plotloom。\n".encode()
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    content = output.getvalue()
    # Identity comparison includes all sources, presentation and exact selections.
    # Immutable artifact publication occurs while the final source lock is held.
    with store.repository._lifecycle_write() as session:
        current = capture_player_export(store.repository, store.manifest.project_id, request, in_session=session)
        if stable_hash(current) != stable_hash(snapshot):
            raise InvalidTransitionError("production changed before standalone publication")
        archive_uri = store.artifacts.put(content)
        receipt = private | {"archiveUri": archive_uri, "archiveHash": sha256(content).hexdigest(),
            "files": {name: sha256(data).hexdigest() for name, data in sorted(files.items())}}
        receipt_uri = store.artifacts.put(_json(receipt).encode())
        receipt_hash = receipt_uri.rsplit("/", 1)[-1]
        if session.get(PlayerExportRow, receipt_hash) is None:
            session.add(PlayerExportRow(receipt_hash=receipt_hash, project_id=store.manifest.project_id,
                receipt_uri=receipt_uri, archive_uri=archive_uri, archive_hash=receipt["archiveHash"], created_at=utc_now()))
    return content, receipt_uri
