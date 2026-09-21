from __future__ import annotations

import io
import subprocess

import pytest

from plotloom.codex_image_dispatch import NativeCodexImageDispatcher
import plotloom.codex_image_dispatch as codex_image_dispatch
from plotloom.image_job_contracts import ImageJobError
from plotloom.image_job_contracts import ImageReferenceUse


REAL_THREAD_STATUS = NativeCodexImageDispatcher._thread_status


@pytest.fixture(autouse=True)
def unreadable_worker_status(monkeypatch) -> None:
    """Keep dispatch unit tests isolated from the local Codex app server."""

    monkeypatch.setattr(NativeCodexImageDispatcher, "_thread_status", lambda _self: None)


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


def test_authoritative_idle_reconciliation_releases_only_the_matching_lease(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "Queued", ""),
    )
    monkeypatch.setattr(NativeCodexImageDispatcher, "_thread_status", lambda _self: "idle")
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/one", delivery_path="/one-delivery")
    assert dispatcher.reconcile_idle_worker() is True
    assert not (tmp_path / "inflight.json").exists()
    dispatcher.dispatch(job_id="ij_bcdefghijklmnopqrstu", package_path="/two", delivery_path="/two-delivery")


def test_non_idle_or_unreadable_status_never_releases_the_lease(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "Queued", ""),
    )
    monkeypatch.setattr(NativeCodexImageDispatcher, "_thread_status", lambda _self: "active")
    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)
    dispatcher.dispatch(job_id="ij_abcdefghijklmnopqrst", package_path="/one", delivery_path="/one-delivery")
    assert dispatcher.reconcile_idle_worker() is False
    assert (tmp_path / "inflight.json").is_file()


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


def test_app_server_idle_status_is_the_only_reconciliation_signal(tmp_path, monkeypatch) -> None:
    class ProxyProcess:
        stdin = io.StringIO()
        stdout = io.StringIO(
            '{"id":1,"result":{}}\n'
            '{"id":2,"result":{"thread":{"status":{"type":"idle"}}}}\n'
        )

        def terminate(self) -> None:
            pass

        def wait(self, *, timeout: int) -> None:
            assert timeout == 1

    process = ProxyProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(
        codex_image_dispatch.select,
        "select",
        lambda streams, *_args: (streams, [], []),
    )
    monkeypatch.setattr(NativeCodexImageDispatcher, "_thread_status", REAL_THREAD_STATUS)

    dispatcher = NativeCodexImageDispatcher("task-local", tmp_path)

    assert dispatcher._thread_status() == "idle"
    assert '"method": "thread/read"' in process.stdin.getvalue()


def test_empty_reference_attestation_is_valid_only_for_reference_free_packages() -> None:
    assert ImageReferenceUse(viewedReferenceHashes=[], identityNotes="No identity references.").viewed_reference_hashes == []
