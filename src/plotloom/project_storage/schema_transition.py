"""Honest destination-upgrade provenance; original snapshot hashes stay intact."""
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field

from plotloom.domain_base import CamelModel
from .format import (
    ProjectStorageCorruptionError,
    _canonical_json,
    _read_json,
    _write_new_file,
    parse_project_manifest,
)
from .schema_upgrade import PRIOR_LAYOUT_HASH, SERIAL_EXEC_LAYOUT_HASH
from .snapshot_files import _safe_regular

FILENAME = "schema-transition.json"


class RestoredSchemaTransition(CamelModel):
    version: Literal[1] = 1
    origin: Literal["verified_restore_destination"] = "verified_restore_destination"
    project_id: str
    prior_layout_hash: Literal[PRIOR_LAYOUT_HASH, SERIAL_EXEC_LAYOUT_HASH] = PRIOR_LAYOUT_HASH
    source_database_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    current_layout_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retained_rows_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    omitted_creative_manifests: dict[str, str] = Field(default_factory=dict)


def write_schema_transition(root, receipt):
    _write_new_file(root / FILENAME, (_canonical_json(receipt.model_dump(mode="json", by_alias=True)) + "\n").encode())


def schema_transition_path(root):
    path = root / FILENAME
    if not path.exists() and not path.is_symlink():
        return None
    _safe_regular(path, label="restore schema transition")
    try:
        receipt = RestoredSchemaTransition.model_validate(_read_json(path))
        manifest = parse_project_manifest(_read_json(root / "project.json"))
        if receipt.project_id != manifest.project_id:
            raise ValueError("schema transition identity changed")
    except ValueError as error:
        raise ProjectStorageCorruptionError("restore schema transition is invalid") from error
    return PurePosixPath(FILENAME)


def restored_creative_omissions(root):
    if schema_transition_path(root) is None:
        return {}
    return RestoredSchemaTransition.model_validate(_read_json(root / FILENAME)).omitted_creative_manifests
