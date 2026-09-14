"""Local operator commands for portable project-folder recovery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .format import ProjectStorageError
from .recovery import ProjectRecoveryService
from .registry import ProjectDirectoryRegistry


def restore_command(arguments: Sequence[str]) -> int:
    """Restore one explicitly selected closed folder or Plotloom snapshot.

    This command intentionally has no application-store, provider, credential,
    or network argument.  Recovery validates and publishes only project-owned
    bytes; users configure any fresh installation-level capabilities separately.
    """

    parser = argparse.ArgumentParser(
        prog="plotloom restore",
        description="Restore a verified Plotloom project folder into an empty destination identity.",
    )
    parser.add_argument("--source", required=True, type=Path, help="Closed project folder or Plotloom snapshot directory")
    parser.add_argument("--outputs-dir", required=True, type=Path, help="Destination installation outputs directory")
    parsed = parser.parse_args(arguments)
    registry = ProjectDirectoryRegistry(parsed.outputs_dir)
    recovery = ProjectRecoveryService(registry.outputs_root, registry)
    try:
        restored = recovery.restore(parsed.source)
    except ProjectStorageError as error:
        parser.exit(2, f"plotloom restore: {error}\n")
    print(json.dumps({"status": "restored", "location": str(restored)}, sort_keys=True))
    return 0
