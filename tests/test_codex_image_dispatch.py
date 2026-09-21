from __future__ import annotations

import subprocess

import pytest

from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
from plotloom.image_job_contracts import ImageJobError
from plotloom.image_job_contracts import ImageReferenceUse


def test_native_dispatch_queues_one_frozen_package_and_releases_after_delivery(
    tmp_path, monkeypatch
) -> None:
    seen: list[list[str]] = []

    def queued(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, "Queued message", "")

    monkeypatch.setattr(subprocess, "run", queued)
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/package", delivery_path="/delivery")
    assert seen[0][:5] == ["codex", "queue", "--thread", "task-local", "--message"]
    assert "Frozen Plotloom image package assignment" in seen[0][-1]
    with pytest.raises(ImageJobError, match="already has a native dispatch attempt"):
        dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/package", delivery_path="/delivery")
    dispatcher.complete("ij_abcdefghijklmnopqrst")
    dispatcher.dispatch(job_id="ij_bcdefghijklmnopqrstu", package_path="/package-2", delivery_path="/delivery-2")


def test_uncertain_dispatch_is_reserved_and_never_retried(tmp_path, monkeypatch) -> None:
    def unavailable(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("codex", 30)

    monkeypatch.setattr(subprocess, "run", unavailable)
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    with pytest.raises(ImageJobError, match="outcome is unknown"):
        dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/package", delivery_path="/delivery")


def test_nonzero_queue_exit_is_ambiguous_and_keeps_the_worker_lease(tmp_path, monkeypatch) -> None:
    def queue(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "")

    monkeypatch.setattr(subprocess, "run", queue)
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    with pytest.raises(ImageJobError, match="outcome is unknown"):
        dispatcher.dispatch(
            job_id="ij_abcdefghijklmnopqrst",
            package_path="/package-one",
            delivery_path="/delivery-one",
        )
    assert (tmp_path / "inflight.json").is_file()
    assert (tmp_path / "ij_abcdefghijklmnopqrst" / "receipt.json").is_file()
    assert "outcome_unknown" in (tmp_path / "ij_abcdefghijklmnopqrst" / "receipt.json").read_text()
    with pytest.raises(ImageJobError, match="already has a native dispatch attempt"):
        dispatcher.dispatch(
            job_id="ij_abcdefghijklmnopqrst",
            package_path="/package-one",
            delivery_path="/delivery-one",
        )
    with pytest.raises(ImageJobError, match="already in flight"):
        dispatcher.dispatch(
            job_id="ij_bcdefghijklmnopqrstu",
            package_path="/package-two",
            delivery_path="/delivery-two",
        )


def test_busy_dispatch_does_not_reserve_an_unqueued_job(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "Queued", ""),
    )
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail(
            "a runtime status query cannot release an accepted queued assignment"
        ),
    )
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/one", delivery_path="/one-delivery")
    with pytest.raises(ImageJobError, match="already in flight"):
        dispatcher.dispatch(job_id="ij_bcdefghijklmnopqrstu", package_path="/two", delivery_path="/two-delivery")
    assert not (tmp_path / "ij_bcdefghijklmnopqrstu").exists()
    dispatcher.complete("ij_abcdefghijklmnopqrst")
    dispatcher.dispatch(job_id="ij_bcdefghijklmnopqrstu", package_path="/two", delivery_path="/two-delivery")
    assert (tmp_path / "ij_abcdefghijklmnopqrst" / "receipt.json").is_file()
    with pytest.raises(ImageJobError, match="already has a native dispatch attempt"):
        dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/package", delivery_path="/delivery")


def test_stale_completion_cannot_release_a_replacement_lease(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "Queued", ""),
    )
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    first_job = "ij_abcdefghijklmnopqrst"
    second_job = "ij_bcdefghijklmnopqrstu"
    dispatcher.dispatch(job_id=first_job, package_path="/one", delivery_path="/one-delivery")
    dispatcher.complete(first_job)
    dispatcher.dispatch(job_id=second_job, package_path="/two", delivery_path="/two-delivery")

    dispatcher.complete(first_job)

    assert (tmp_path / "inflight.json").is_file()
    assert "ij_bcdefghijklmnopqrstu" in (tmp_path / "inflight.json").read_text()
def test_empty_reference_attestation_is_valid_only_for_reference_free_packages() -> None:
    assert ImageReferenceUse(viewedReferenceHashes=[], identityNotes="No identity references.").viewed_reference_hashes == []
