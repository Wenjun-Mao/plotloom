"""Editable project and candidate-slot state, separate from frozen audio."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .store import new_id, now

if TYPE_CHECKING:
    from .store import Store


class ProjectRepository:
    def __init__(self, store: Store):
        self.store = store

    def list(self) -> list[dict]:
        with self.store.connection() as db:
            rows = db.execute("""SELECT p.*, COUNT(c.id) AS candidate_count
                FROM projects p LEFT JOIN candidate_slots c ON c.project_id=p.id
                GROUP BY p.id ORDER BY p.created_at DESC,p.id DESC""").fetchall()
            return [self._summary(row) for row in rows]

    @staticmethod
    def _summary(row) -> dict:
        return {"projectId": row["id"], "name": row["name"],
                "revision": row["revision"], "candidateCount": row["candidate_count"],
                "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    def create(self, name: str) -> dict:
        project_id, stamp = new_id("vp"), now()
        with self.store.connection() as db:
            db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)", (
                project_id, name, "", "", 1, None, stamp, stamp,
            ))
        return self.get(project_id)

    def get(self, project_id: str) -> dict:
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if row is None:
                raise ValueError("project.not_found")
            candidates = db.execute("SELECT * FROM candidate_slots WHERE project_id=? ORDER BY ordinal", (project_id,)).fetchall()
            result = {"projectId": row["id"], "name": row["name"], "brief": row["brief"],
                      "auditionText": row["audition_text"], "revision": row["revision"],
                      "selectedGenerationId": row["selected_generation_id"],
                      "createdAt": row["created_at"], "updatedAt": row["updated_at"],
                      "candidates": []}
            for candidate in candidates:
                latest = db.execute("SELECT id,status,error_code FROM generations WHERE candidate_id=? ORDER BY rowid DESC LIMIT 1", (candidate["id"],)).fetchone()
                current = db.execute("SELECT * FROM generations WHERE id=?", (candidate["current_generation_id"],)).fetchone()
                result["candidates"].append({
                    "candidateId": candidate["id"], "ordinal": candidate["ordinal"],
                    "direction": candidate["direction"], "revision": candidate["revision"],
                    "currentGeneration": self.store.generations.public(current) if current else None,
                    "latestGeneration": {"generationId": latest["id"], "status": latest["status"],
                                         "errorCode": latest["error_code"]} if latest else None,
                })
            return result

    @staticmethod
    def _require_project(db, project_id: str, expected_revision: int | None = None):
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise ValueError("project.not_found")
        if expected_revision is not None and row["revision"] != expected_revision:
            raise ValueError("project.revision_conflict")
        return row

    def update(self, project_id: str, expected_revision: int, name: str, brief: str, audition_text: str) -> dict:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_project(db, project_id, expected_revision)
            db.execute("""UPDATE projects SET name=?,brief=?,audition_text=?,
                revision=revision+1,updated_at=? WHERE id=?""", (
                name, brief, audition_text, now(), project_id,
            ))
        return self.get(project_id)

    def add_candidate(self, project_id: str, expected_revision: int, direction: str) -> dict:
        candidate_id, stamp = new_id("vc"), now()
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._require_project(db, project_id, expected_revision)
            count, ordinal = db.execute("SELECT COUNT(*),COALESCE(MAX(ordinal),0)+1 FROM candidate_slots WHERE project_id=?", (project_id,)).fetchone()
            if count >= 64:
                raise ValueError("project.candidate_limit")
            db.execute("INSERT INTO candidate_slots VALUES (?,?,?,?,?,?,?,?)", (
                candidate_id, project_id, ordinal, direction, 1, None, stamp, stamp,
            ))
            db.execute("UPDATE projects SET revision=revision+1,updated_at=? WHERE id=?", (stamp, project_id))
        return self.get(project_id)

    def edit_candidate(self, candidate_id: str, project_revision: int, candidate_revision: int, direction: str) -> dict:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (candidate_id,)).fetchone()
            if candidate is None:
                raise ValueError("candidate.not_found")
            self._require_project(db, candidate["project_id"], project_revision)
            if candidate["revision"] != candidate_revision:
                raise ValueError("candidate.revision_conflict")
            stamp = now()
            db.execute("UPDATE candidate_slots SET direction=?,revision=revision+1,updated_at=? WHERE id=?", (
                direction, stamp, candidate_id,
            ))
            db.execute("UPDATE projects SET revision=revision+1,updated_at=? WHERE id=?", (stamp, candidate["project_id"]))
            project_id = candidate["project_id"]
        return self.get(project_id)

    def delete_candidate(self, candidate_id: str, project_revision: int, candidate_revision: int) -> dict:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            candidate = db.execute("SELECT * FROM candidate_slots WHERE id=?", (candidate_id,)).fetchone()
            if candidate is None:
                raise ValueError("candidate.not_found")
            project = self._require_project(db, candidate["project_id"], project_revision)
            if candidate["revision"] != candidate_revision:
                raise ValueError("candidate.revision_conflict")
            if db.execute("SELECT 1 FROM generations WHERE candidate_id=? AND status IN ('queued','running')", (candidate_id,)).fetchone() or db.execute("SELECT 1 FROM clone_trials WHERE candidate_id=? AND status IN ('queued','running')", (candidate_id,)).fetchone():
                raise ValueError("candidate.busy")
            paths = [value for row in db.execute("SELECT source_path,h3_path FROM generations WHERE candidate_id=?", (candidate_id,)) for value in row]
            paths.extend(value for row in db.execute("SELECT reference_path,audio_path FROM clone_trials WHERE candidate_id=?", (candidate_id,)) for value in row)
            self.store.enqueue_cleanup(db, paths)
            db.execute("DELETE FROM clone_trials WHERE candidate_id=?", (candidate_id,))
            db.execute("DELETE FROM selections WHERE candidate_id=?", (candidate_id,))
            db.execute("DELETE FROM candidate_slots WHERE id=?", (candidate_id,))
            selected = project["selected_generation_id"]
            if selected and not db.execute("SELECT 1 FROM generations WHERE id=?", (selected,)).fetchone():
                db.execute("UPDATE projects SET selected_generation_id=NULL WHERE id=?", (candidate["project_id"],))
            db.execute("UPDATE projects SET revision=revision+1,updated_at=? WHERE id=?", (now(), candidate["project_id"]))
            project_id = candidate["project_id"]
        self.store.run_cleanup()
        return self.get(project_id)

    def delete(self, project_id: str, expected_revision: int, confirm_name: str) -> None:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            project = self._require_project(db, project_id, expected_revision)
            if project["name"] != confirm_name:
                raise ValueError("project.name_confirmation_mismatch")
            if db.execute("""SELECT 1 FROM generations g JOIN candidate_slots c ON c.id=g.candidate_id
                WHERE c.project_id=? AND g.status IN ('queued','running')""", (project_id,)).fetchone() or db.execute("SELECT 1 FROM clone_trials WHERE project_id=? AND status IN ('queued','running')", (project_id,)).fetchone():
                raise ValueError("project.busy")
            paths = [value for row in db.execute("""SELECT g.source_path,g.h3_path FROM generations g
                JOIN candidate_slots c ON c.id=g.candidate_id WHERE c.project_id=?""", (project_id,)) for value in row]
            paths.extend(value for row in db.execute("SELECT reference_path,audio_path FROM clone_trials WHERE project_id=?", (project_id,)) for value in row)
            self.store.enqueue_cleanup(db, paths)
            db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        self.store.run_cleanup()
