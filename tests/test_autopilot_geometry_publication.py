"""Writer death during actual derivative publication rolls back and retries locally."""

import signal
from contextlib import closing
from hashlib import sha256

import pytest
from PIL import Image

from plotloom.autopilot_service import AutopilotService
from plotloom.geometry_preparation import prepare_geometry
from plotloom.persistence.schema import ManagedAssetRow
from tests.artifact_publication_fixtures import child_process, kill_at_publication
from tests.autopilot_image_fixtures import image_environment
from tests.test_autopilot_geometry import mismatch, original_ready
from tests.test_autopilot_images import current


@pytest.mark.parametrize(
    "boundary", ["partial_write", "before_promotion", "after_promotion"]
)
def test_killed_derivative_writer_retries_same_identity_without_native_work(
    tmp_path, monkeypatch, boundary
):
    # Earlier uniform references otherwise have the exact prepared frame bytes,
    # so publication correctly reuses them and never reaches the write boundary.
    create_image = Image.new

    def distinct_frame(mode, size, color=0):
        image = create_image(mode, size, color)
        if size == (941, 1672):
            image.paste((190, 30, 70), (200, 400, 700, 1200))
        return image

    monkeypatch.setattr(Image, "new", distinct_frame)
    storage, registry, service, view, calls, text_calls = image_environment(
        tmp_path, monkeypatch, geometry=mismatch
    )
    try:
        retained, original = original_ready(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository._read() as session:
                source = session.get(
                    ManagedAssetRow, original["evidence"]["result"]["assetId"]
                )
                raw = store.artifacts.get(source.original_uri)
            prepared, _observed, _recipe = prepare_geometry(
                raw,
                width=retained.policy.image_width,
                height=retained.policy.image_height,
            )
            digest = sha256(prepared).hexdigest()
            canonical = store.home / "assets" / digest[:2] / digest
            assert not canonical.exists(), "fixture must exercise a new publication"
            with store.repository.engine.connect() as connection:
                counts = tuple(
                    connection.exec_driver_sql(f"SELECT count(*) FROM {table}").scalar()
                    for table in [
                        "v2_managed_assets",
                        "v2_image_jobs",
                        "v2_image_job_candidates",
                    ]
                )
        native_before = (tuple(calls), tuple(text_calls), len(retained.checkpoints))
        service.release_controller()

        def interrupted():
            kill_at_publication(boundary)
            child = AutopilotService(storage, registry)
            assert child.acquire_controller()
            child.step(view.project_id)
            raise AssertionError(
                "new derivative publication did not reach the injected boundary"
            )

        assert child_process(interrupted) == -signal.SIGKILL
        assert canonical.exists() == (boundary == "after_promotion")
        if canonical.exists():
            assert canonical.read_bytes() == prepared and canonical.stat().st_nlink == 1
        stages = list(storage.projects.outputs_root.glob(".artifact-publish-*"))
        assert len(stages) == 1
        preserved = {file.name: file.read_bytes() for file in stages[0].iterdir()}
        after_crash = current(storage, view)
        assert not after_crash.frames
        assert len(after_crash.checkpoints) == native_before[2]
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository.engine.connect() as connection:
                assert (
                    tuple(
                        connection.exec_driver_sql(
                            f"SELECT count(*) FROM {table}"
                        ).scalar()
                        for table in [
                            "v2_managed_assets",
                            "v2_image_jobs",
                            "v2_image_job_candidates",
                        ]
                    )
                    == counts
                )
            assert store.artifacts.get(source.original_uri) == raw
        assert service.acquire_controller()
        service.step(view.project_id)
        recovered = current(storage, view)
        assert len(recovered.frames) == 1
        record = recovered.frames[0].geometry_preparation
        assert (
            record.output.original_hash == digest and canonical.read_bytes() == prepared
        )
        assert (tuple(calls), tuple(text_calls)) == native_before[:2]
        assert (
            len(
                [
                    item
                    for item in recovered.checkpoints
                    if item["evidence"]["owner"] == "geometry-preparation"
                ]
            )
            == 1
        )
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository.engine.connect() as connection:
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM v2_image_jobs"
                    ).scalar()
                    == counts[1]
                )
                assert (
                    connection.exec_driver_sql(
                        "SELECT count(*) FROM v2_image_job_candidates"
                    ).scalar()
                    == counts[2]
                )
            assert store.artifacts.get(source.original_uri) == raw
        assert preserved == {
            file.name: file.read_bytes() for file in stages[0].iterdir()
        }
        # A prior sibling stage cannot poison snapshot inventory after a successful retry.
        service.close()
        from plotloom.autopilot_contracts import RunControlRequest

        service.control(
            view.project_id,
            RunControlRequest(expected_revision=recovered.revision, action="pause"),
        )
        snapshot = storage.recovery.create_snapshot(view.project_id)
        assert snapshot.location
    finally:
        service.close()
