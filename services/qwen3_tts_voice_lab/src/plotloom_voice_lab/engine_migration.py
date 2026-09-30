"""Add execution provenance without changing retained media or old identities."""

from __future__ import annotations

import json
import sqlite3


def migrate_engines(db: sqlite3.Connection) -> None:
    db.execute("BEGIN IMMEDIATE")
    for statement in (
        "ALTER TABLE candidate_slots ADD COLUMN engine_id TEXT NOT NULL DEFAULT 'qwen_design'",
        "ALTER TABLE candidate_slots ADD COLUMN design_binding TEXT",
        "ALTER TABLE generations ADD COLUMN engine_id TEXT NOT NULL DEFAULT 'qwen_design'",
        "ALTER TABLE generations ADD COLUMN snapshot_json TEXT",
        "ALTER TABLE generations ADD COLUMN audio_details TEXT",
        "ALTER TABLE clone_trials ADD COLUMN engine_id TEXT NOT NULL DEFAULT 'qwen_base'",
        "ALTER TABLE clone_trials ADD COLUMN snapshot_json TEXT",
        "ALTER TABLE clone_trials ADD COLUMN delivery_json TEXT NOT NULL DEFAULT '{\"mode\":\"none\"}'",
        "ALTER TABLE clone_trials ADD COLUMN execution_details TEXT",
        "ALTER TABLE clone_trials ADD COLUMN audio_details TEXT",
        "ALTER TABLE voices ADD COLUMN engine_id TEXT NOT NULL DEFAULT 'qwen_design'",
        "ALTER TABLE voices ADD COLUMN snapshot_json TEXT",
        "ALTER TABLE voices ADD COLUMN audio_details TEXT",
    ):
        db.execute(statement)
    # A migrated evidence record is not a retrospectively executed V3 snapshot.
    # Keep its exact old model identity, and interrupt outstanding jobs at startup.
    for table, engine in (("generations", "qwen_design"), ("clone_trials", "qwen_base"), ("voices", "qwen_design")):
        for row in db.execute(f"SELECT id,model_id,model_revision FROM {table}").fetchall():
            preserved = {"schemaVersion": 0, "engineId": engine,
                         "modelId": row["model_id"], "modelRevision": row["model_revision"]}
            db.execute(f"UPDATE {table} SET snapshot_json=? WHERE id=?", (json.dumps(preserved), row["id"]))
    db.execute("PRAGMA user_version=3")
    db.commit()
