"""Published identity is independent of immutable line-specific results."""

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from plotloom_voice_lab.contracts import TakeCreate
from plotloom_voice_lab.media import file_sha256, persist_candidate, persist_reference_file
from plotloom_voice_lab.store import Store


def published_voice(store):
    p = store.projects.create("technical fixture")
    p = store.projects.update(p["projectId"], p["revision"], p["name"], "direction", "参考台词。")
    p = store.projects.add_candidate(p["projectId"], p["revision"], "low female voice", "moss_design")
    c = p["candidates"][0]
    g = store.generations.create(c["candidateId"], p["revision"], c["revision"], 123)
    store.generations.mark_running(g["generationId"])
    media = persist_candidate(store.data_dir, c["candidateId"], g["generationId"], np.full(48000, .1), 24000)
    store.generations.complete(g["generationId"], media)
    store.generations.select(p["projectId"], g["generationId"])
    return store.voices.publish(p["projectId"], g["generationId"]), p


def test_takes_survive_project_deletion_and_never_replace_identity(tmp_path):
    store = Store(tmp_path)
    voice, project = published_voice(store)
    body = TakeCreate(voiceId=voice["voiceId"], text="别打开门。", engineId="index_base", seed=1,
                      delivery={"mode": "text", "description": "坚定、果断"})
    first, second = store.takes.create(body), store.takes.create(body)
    assert first["takeId"] != second["takeId"]
    for take in (first, second):
        store.takes.mark(take["takeId"], "running")
        store.takes.record_execution(take["takeId"], {"mode": "text", "rawVector": [0] * 8,
                                                    "effectiveVector": [0] * 8, "classifierSeconds": .1})
        native = tmp_path / f"{take['takeId']}.wav"
        sf.write(native, np.full(44100, .2), 22050, subtype="PCM_16")
        result = persist_reference_file(tmp_path / "takes" / take["takeId"], native, 22050)
        store.takes.mark(take["takeId"], "completed", media=result)
    before = store.takes.get(first["takeId"], private=True)
    store.projects.delete(project["projectId"], project["revision"], project["name"])
    assert store.voices.get(voice["voiceId"])["sourceSha256"] == voice["sourceSha256"]
    assert store.takes.get(first["takeId"], private=True) == before
    assert sf.info(before["h3Path"]).samplerate == 32000
    assert file_sha256(Path(before["sourcePath"])) == before["sourceSha256"]
    with pytest.raises(ValueError, match="not_appendable"):
        store.takes.mark(first["takeId"], "completed", media=result)
    store.takes.delete(first["takeId"], first["takeId"])
    assert store.takes.get(first["takeId"])["status"] == "deleted"
    assert not Path(before["sourcePath"]).exists()
    assert store.takes.get(second["takeId"])["status"] == "completed"
    assert Store(tmp_path).voices.get(voice["voiceId"]) == voice


def test_bad_reference_and_controls_admit_nothing(tmp_path):
    store = Store(tmp_path)
    voice, _ = published_voice(store)
    with pytest.raises(ValueError):
        TakeCreate(voiceId=voice["voiceId"], text="你好", engineId="qwen_base",
                   delivery={"mode": "text", "description": "坚定"})
    private = store.voices.get(voice["voiceId"], private=True)
    Path(private["sourcePath"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="corrupt"):
        store.takes.create(TakeCreate(voiceId=voice["voiceId"], text="你好", engineId="index_base"))
    assert store.takes.list(voice["voiceId"]) == []


def test_outbox_is_transactional_and_takes_delete_is_guarded(tmp_path):
    store = Store(tmp_path)
    voice, _ = published_voice(store)
    take = store.takes.create(TakeCreate(voiceId=voice["voiceId"], text="你好", engineId="index_base"))
    with store.connection() as db:
        assert db.execute("SELECT kind FROM dispatch_outbox WHERE job_id=?", (take["takeId"],)).fetchone()[0] == "take"
    with pytest.raises(ValueError, match="confirmation"):
        store.takes.delete(take["takeId"], "wrong")
    with pytest.raises(ValueError, match="busy"):
        store.takes.delete(take["takeId"], take["takeId"])
    assert not any("Path" in key for key in take)


def test_h3_ineligible_native_take_remains_available(tmp_path):
    native = tmp_path / "native.wav"
    sf.write(native, np.full(24000 * 11, .1), 24000)
    media = persist_reference_file(tmp_path / "take", native, 24000)
    assert media["h3Eligible"] is False and media["h3IssueCode"] == "h3.duration_out_of_range"
    assert file_sha256(native) == media["sourceSha256"]


def test_v3_migration_preserves_existing_voice_and_terminal_json(tmp_path):
    store = Store(tmp_path)
    voice, _ = published_voice(store)
    with store.connection() as db:
        original = [tuple(row) for row in db.execute("SELECT * FROM voices")]
        for trigger in ("generation_dispatch", "clone_dispatch", "take_dispatch"):
            db.execute(f"DROP TRIGGER {trigger}")
        for table in ("voice_takes", "dispatch_outbox", "execution_grants"):
            db.execute(f"DROP TABLE {table}")
        db.execute("PRAGMA user_version=3")
    reopened = Store(tmp_path)
    with reopened.connection() as db:
        assert original == [tuple(row) for row in db.execute("SELECT * FROM voices")]
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
    assert reopened.voices.get(voice["voiceId"]) == voice
