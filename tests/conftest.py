"""Fixtures shared across test modules."""

from pathlib import Path

import pytest

from tests.graph_authoring_fixtures import (
    AcceptedSourceProjectSeed,
    build_accepted_source_project_seed,
    create_accepted_source_project,
)


@pytest.fixture(scope="session")
def accepted_source_project_seed(
    tmp_path_factory: pytest.TempPathFactory,
) -> AcceptedSourceProjectSeed:
    """Build one closed accepted-source seed for graph-command test copies."""
    seed_root = tmp_path_factory.mktemp("accepted-graph-source-seed")
    return build_accepted_source_project_seed(seed_root)


@pytest.fixture
def source_project(
    tmp_path: Path,
):
    """Preserve function-scoped setup for graph contracts outside commands."""
    store = create_accepted_source_project(tmp_path)
    try:
        yield store
    finally:
        store.close()


@pytest.fixture(scope="session")
def geometry_frame_seed(tmp_path_factory):
    """One fully closed current-contract seed; consumers only open case copies."""
    from tests.autopilot_geometry_fixtures import build_geometry_frame_seed

    return build_geometry_frame_seed(tmp_path_factory.mktemp("geometry-frame-seed"))


@pytest.fixture(scope="session")
def awaiting_handoff_seed(tmp_path_factory):
    """Completed machine material only; human facts remain copy-local."""
    from tests.autopilot_handoff_seed_fixtures import build_awaiting_handoff_seed

    return build_awaiting_handoff_seed(tmp_path_factory.mktemp("awaiting-handoff-seed"))


@pytest.fixture(scope="session")
def accepted_script_reconciliation_seed(tmp_path_factory):
    """No registry/dispatch is copied; selected cases build those afresh."""
    from tests.specialist_reconciliation_seed import build_accepted_script_seed

    return build_accepted_script_seed(tmp_path_factory.mktemp("reconciliation-script-seed"))


@pytest.fixture(scope="session")
def pending_native_bridge_seed(tmp_path_factory):
    """Closed nine-shot pending proposal only; native authority stays per case."""
    from tests.native_bridge_seed_fixtures import build_pending_bridge_seed

    return build_pending_bridge_seed(tmp_path_factory.mktemp("pending-native-bridge-seed"))
