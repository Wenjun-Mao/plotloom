from __future__ import annotations

from typing import Any

from plotloom.provider_contracts import ProviderSnapshot

from .provider_profiles import (
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
)


def validate_public_provider_snapshot(value: Any) -> dict[str, Any]:
    """Validate the secret-free provider contract frozen into a durable run.

    Snapshots without ``profileSchemaVersion`` are historical V1 values.  They
    must continue through the exact pre-M1.5 Pydantic/hash path: adding V2
    defaults while merely reading an old run would change its plan and seal
    evidence.  Only explicitly versioned V2 snapshots use the named-profile
    contract.
    """

    candidate = {} if value is None else value
    if isinstance(candidate, dict) and (
        candidate.get("profileSchemaVersion") in {2, 3}
        or candidate.get("profile_schema_version") in {2, 3}
    ):
        snapshot = (
            TextProviderProfileSnapshotV3.model_validate(candidate)
            if candidate.get(
                "profileSchemaVersion", candidate.get("profile_schema_version")
            )
            == 3
            else TextProviderProfileSnapshot.model_validate(candidate)
        )
        return snapshot.model_dump(mode="json", by_alias=True)
    snapshot = ProviderSnapshot.model_validate(candidate)
    return snapshot.model_dump(mode="json", by_alias=True)
