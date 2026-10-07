"""All image candidate readers preserve the managed asset declaration contract."""

import json
import sqlite3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import utc_now
from plotloom.persistence.project.media_art_reference_proposals import ArtReferenceProposalPersistence
from plotloom.persistence.project.media_image_delivery import ImageJobDeliveryPersistence
from plotloom.persistence.project.media_reference_proposals import CharacterReferenceProposalPersistence
from plotloom.persistence.schema import (
    ArtReferenceProposalCandidateRow, CharacterReferenceProposalCandidateRow, ImageJobCandidateRow,
    ManagedAssetProvenanceRow,
)
from plotloom.project_storage import ProjectFolderStorage


@pytest.mark.parametrize("row_type,reader", [
    (ArtReferenceProposalCandidateRow, ArtReferenceProposalPersistence._candidate_dict),
    (CharacterReferenceProposalCandidateRow, CharacterReferenceProposalPersistence._proposal_candidate_dict),
    (ImageJobCandidateRow, ImageJobDeliveryPersistence.image_candidate_dict),
])
@pytest.mark.parametrize("declaration", [
    {"origin": "manual", "rights": "unknown", "limitations": ["QA only"]},
    {"origin": "manual", "rights": "known", "rightsNote": "owner supplied", "declaredAdditions": ["lamp"]},
    None,
    {"origin": "manual", "rights": "invented"},
])
def test_candidate_embeds_exact_public_asset_without_rewriting_declaration(
    tmp_path: Path, row_type, reader, declaration,
) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    data = b"immutable candidate projection fixture"
    uri = store.artifacts.put(data)
    asset = store.media.record_managed_import(
        project_id, original_hash=sha256(data).hexdigest(), display_hash=sha256(data).hexdigest(),
        mime_type="image/png", byte_size=len(data), width=1, height=1,
        declaration={"origin": "manual"}, publish=lambda: (uri, uri),
    )
    database = store.home / "project.sqlite3"
    store.close()
    encoded = json.dumps(declaration) if declaration is not None else None
    with sqlite3.connect(database) as connection:
        if encoded is None:
            connection.execute("DELETE FROM v2_managed_asset_provenance WHERE asset_id=?", (asset["id"],))
        else:
            connection.execute("UPDATE v2_managed_asset_provenance SET declaration=? WHERE asset_id=?", (encoded, asset["id"]))
    owner = {"job_id": "job"} if row_type is ImageJobCandidateRow else {"proposal_id": "proposal"}
    candidate = row_type(id="candidate", asset_id=asset["id"], output_filename="fixture.png",
                         output_hash=asset["originalHash"], role="original", created_at=utc_now(), **owner)
    engine = create_engine(f"sqlite:///{database}")
    try:
        with Session(engine) as session:
            if declaration and declaration.get("rights") == "invented":
                with pytest.raises(ValidationError):
                    reader(session, candidate)
            else:
                embedded = reader(session, candidate)["asset"]
                opened = storage.projects.open(project_id)
                try:
                    assert embedded == opened.media.list_managed_assets(project_id)[0]
                finally:
                    opened.close()
                assert embedded["provenance"] == (
                    {"rights": "unknown", "rightsNote": None, "declaredAdditions": [], **declaration}
                    if declaration else None)
            candidate.asset_id = "absent"
            assert reader(session, candidate)["asset"] is None
    finally:
        engine.dispose()
    with sqlite3.connect(database) as connection:
        retained = connection.execute("SELECT declaration FROM v2_managed_asset_provenance WHERE asset_id=?", (asset["id"],)).fetchone()
    assert retained == ((encoded,) if encoded is not None else None)


@pytest.mark.parametrize("row_type,reader", [
    (ArtReferenceProposalCandidateRow, ArtReferenceProposalPersistence._candidate_dict),
    (CharacterReferenceProposalCandidateRow, CharacterReferenceProposalPersistence._proposal_candidate_dict),
    (ImageJobCandidateRow, ImageJobDeliveryPersistence.image_candidate_dict),
])
def test_candidate_provenance_uses_earliest_declaration_with_id_tie_break(
    tmp_path: Path, row_type, reader,
) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    data = b"ordered provenance fixture"
    uri = store.artifacts.put(data)
    asset = store.media.record_managed_import(
        project_id, original_hash=sha256(data).hexdigest(), display_hash=sha256(data).hexdigest(),
        mime_type="image/png", byte_size=len(data), width=1, height=1,
        declaration={"origin": "manual"}, publish=lambda: (uri, uri),
    )
    database = store.home / "project.sqlite3"
    store.close()
    engine = create_engine(f"sqlite:///{database}")
    owner = {"job_id": "job"} if row_type is ImageJobCandidateRow else {"proposal_id": "proposal"}
    candidate = row_type(id="candidate", asset_id=asset["id"], output_filename="fixture.png",
                         output_hash=asset["originalHash"], role="original", created_at=utc_now(), **owner)
    try:
        with Session(engine) as session:
            session.query(ManagedAssetProvenanceRow).filter_by(asset_id=asset["id"]).delete()
            # Insert out of order: a smaller ID cannot beat an earlier date;
            # equal dates resolve by ID rather than insertion order.
            for identity, day in [("000-later", 2), ("zzz-earliest", 1), ("aaa-earliest", 1)]:
                session.add(ManagedAssetProvenanceRow(
                    id=identity, project_id=project_id, asset_id=asset["id"],
                    created_at=datetime(2026, 10, day, tzinfo=timezone.utc),
                    declaration={"origin": "manual", "rightsNote": identity},
                ))
            session.commit()
            assert reader(session, candidate)["asset"]["provenance"]["rightsNote"] == "aaa-earliest"
            assert session.query(ManagedAssetProvenanceRow).filter_by(asset_id=asset["id"]).count() == 3
        opened = storage.projects.open(project_id)
        try:
            assert opened.media.list_managed_assets(project_id)[0]["provenance"]["rightsNote"] == "aaa-earliest"
        finally:
            opened.close()
    finally:
        engine.dispose()
