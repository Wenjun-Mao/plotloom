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
