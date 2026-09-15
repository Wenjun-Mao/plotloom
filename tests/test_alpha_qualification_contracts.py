from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from plotloom import alpha_acceptance

from tests.project_storage_fixtures import FixtureResolver
from tests.test_alpha_acceptance import (
    _application_data_dir,
    _external_review,
    _fixture_provenance,
    _review_pack,
)


def _complete_alpha_receipts() -> list[dict[str, Any]]:
    return [
        {
            "commit": "a" * 40,
            "contractHash": alpha_acceptance.alpha_contract_hash(),
            "profileId": profile_id,
            "storyId": story.alias,
            "sampleId": f"{story.alias}-repeat-{repeat_ordinal:02d}",
            "status": "succeeded",
            "issueCodes": [],
            "durationMilliseconds": 0,
            "tokens": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
            "scores": {
                "firstPass": {
                    "total": 4,
                    "accepted": 4,
                    "rejected": 0,
                    "outcomeUnknown": 0,
                    "cancelled": 0,
                    "notRun": 0,
                },
                "maxAttemptsPerWorkUnit": 1,
            },
        }
        for profile_id in ("profile-01", "profile-02")
        for story in alpha_acceptance.ALPHA_STORIES
        for repeat_ordinal in range(1, 4)
    ]


def test_alpha_qualification_fails_closed_for_missing_incomplete_and_non_success_samples() -> None:
    complete = _complete_alpha_receipts()
    assert alpha_acceptance.alpha_qualification_issue_codes(complete) == []

    unknown = [dict(receipt) for receipt in complete]
    unknown[0]["issueCodes"] = ["provider.outcome_unknown"]
    assert alpha_acceptance.alpha_qualification_issue_codes(unknown) == [
        "alpha.matrix.invariant"
    ]

    for terminal_status in ("cancelled", "quarantined"):
        non_success = [dict(receipt) for receipt in complete]
        non_success[0]["status"] = terminal_status
        assert alpha_acceptance.alpha_qualification_issue_codes(non_success) == [
            "alpha.matrix.run_completion"
        ]

    missing = complete[:-1]
    assert {
        "alpha.matrix.run_count",
        "alpha.matrix.sample_identity",
        "alpha.profile-02.stage_count",
    } <= set(alpha_acceptance.alpha_qualification_issue_codes(missing))

    incomplete = [dict(receipt) for receipt in complete]
    incomplete[0]["scores"] = {"firstPass": {"total": 4, "accepted": 4}}
    assert "alpha.receipt.schema" in alpha_acceptance.alpha_qualification_issue_codes(
        incomplete
    )


def test_alpha_qualification_counts_corrections_against_each_profile_first_pass_budget() -> None:
    boundary = _complete_alpha_receipts()
    for receipt in boundary[:6]:
        receipt["issueCodes"] = ["semantic.corrected"]
        receipt["scores"] = {
            **receipt["scores"],
            "firstPass": {**receipt["scores"]["firstPass"], "accepted": 3},
            "maxAttemptsPerWorkUnit": 2,
        }
    assert alpha_acceptance.alpha_qualification_issue_codes(boundary) == []

    below_threshold = [dict(receipt) for receipt in boundary]
    below_threshold[6]["scores"] = {
        **below_threshold[6]["scores"],
        "firstPass": {
            **below_threshold[6]["scores"]["firstPass"],
            "accepted": 3,
        },
    }
    assert alpha_acceptance.alpha_qualification_issue_codes(below_threshold) == [
        "alpha.profile-01.first_pass"
    ]


def test_alpha_invariant_codes_require_an_atomic_four_stage_install() -> None:
    def store_for(
        *, status: str, installed_count: int, result_revision_ids: tuple[str, ...]
    ) -> SimpleNamespace:
        return SimpleNamespace(
            generation=SimpleNamespace(
                get_run=lambda _run_id: SimpleNamespace(
                    status=SimpleNamespace(value=status),
                    project_id="fixture-project",
                    result_revision_ids=result_revision_ids,
                )
            ),
            authoring=SimpleNamespace(
                list_stage_envelopes=lambda _project_id: [
                    SimpleNamespace(
                        head=SimpleNamespace(status=alpha_acceptance.StageStatus.READY),
                        payload={},
                    )
                    for _index in range(installed_count)
                ]
            ),
        )

    trace = SimpleNamespace(attempts=[])
    assert alpha_acceptance._invariant_codes(  # noqa: SLF001 - direct receipt invariant
        store_for(status="succeeded", installed_count=3, result_revision_ids=("a", "b", "c")),
        run_id="run",
        trace=trace,
    ) == {"conformance.canonical_install_incomplete"}
    assert alpha_acceptance._invariant_codes(  # noqa: SLF001 - direct receipt invariant
        store_for(status="failed", installed_count=1, result_revision_ids=("a",)),
        run_id="run",
        trace=trace,
    ) == {"conformance.partial_canonical_install"}


def test_alpha_never_publishes_a_partial_review_pack_after_late_qualification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_data_dir, _profiles = _application_data_dir(tmp_path)
    _fixture_provenance(monkeypatch, tmp_path)
    review_directory = tmp_path / "review-pack"
    original_receipt_for = alpha_acceptance._receipt_for
    receipt_count = 0

    def late_failure(*args: object, **kwargs: object) -> dict[str, Any]:
        nonlocal receipt_count
        receipt_count += 1
        receipt = original_receipt_for(*args, **kwargs)
        return {**receipt, "status": "failed"} if receipt_count == 18 else receipt

    monkeypatch.setattr(alpha_acceptance, "_receipt_for", late_failure)
    result = alpha_acceptance.run_alpha_acceptance(
        application_data_dir=application_data_dir,
        profile_ids=["real_looking_a", "real_looking_b"],
        review_directory=review_directory,
        provider_resolver=FixtureResolver(),
        commit_sha="a" * 40,
    )

    assert "alpha.matrix.run_completion" in result.qualification_issues
    assert result.review_paths == ()
    assert not review_directory.exists()
    assert not list(tmp_path.glob(".review-pack.plotloom-stage-*"))


def test_alpha_provenance_is_bound_to_the_running_checkout_and_clean_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout_root = tmp_path / "source-checkout"
    checkout_root.mkdir()
    head = "a" * 40
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(alpha_acceptance, "_source_checkout_root", lambda: checkout_root)

    def clean_git(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == checkout_root
        calls.append(tuple(command))
        if command[1] == "status":
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=f"{head}\n", stderr="")

    monkeypatch.setattr(alpha_acceptance.subprocess, "run", clean_git)
    expected = alpha_acceptance._AlphaSourceProvenance(checkout_root, head)
    assert alpha_acceptance._resolve_alpha_source_provenance(None) == expected
    assert alpha_acceptance._resolve_alpha_source_provenance(head.upper()) == expected
    assert calls == [
        ("git", "status", "--porcelain", "--untracked-files=all"),
        ("git", "rev-parse", "--verify", "HEAD^{commit}"),
        ("git", "status", "--porcelain", "--untracked-files=all"),
        ("git", "rev-parse", "--verify", "HEAD^{commit}"),
    ]

    monkeypatch.setattr(
        alpha_acceptance.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, stdout="?? src/plotloom/untracked_runtime.py\n", stderr=""
        ),
    )
    with pytest.raises(ValueError, match="source checkout has uncommitted changes"):
        alpha_acceptance._resolve_alpha_source_provenance(head)

    monkeypatch.setattr(alpha_acceptance.subprocess, "run", clean_git)
    with pytest.raises(ValueError, match="explicit commit does not match"):
        alpha_acceptance._resolve_alpha_source_provenance("b" * 40)


def test_alpha_source_checkout_is_derived_from_the_running_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source-checkout"
    module_path = source_root / "src" / "plotloom" / "alpha_acceptance.py"
    module_path.parent.mkdir(parents=True)
    module_path.touch()
    monkeypatch.setattr(alpha_acceptance, "__file__", str(module_path))
    monkeypatch.setattr(
        alpha_acceptance.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            0,
            stdout=f"{kwargs['cwd']}\n",
            stderr="",
        ),
    )
    assert alpha_acceptance._source_checkout_root() == source_root

    unrelated_root = tmp_path / "unrelated-checkout"
    monkeypatch.setattr(
        alpha_acceptance.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, stdout=f"{unrelated_root}\n", stderr=""
        ),
    )
    with pytest.raises(ValueError, match="owning source checkout"):
        alpha_acceptance._source_checkout_root()


def test_alpha_provenance_failure_precedes_review_output_and_cli_rejects_bad_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    review_directory = tmp_path / "outside-checkout-review"
    monkeypatch.setattr(
        alpha_acceptance,
        "_resolve_alpha_source_provenance",
        lambda _commit: (_ for _ in ()).throw(ValueError("private checkout path")),
    )
    with pytest.raises(ValueError, match="private checkout path"):
        alpha_acceptance.run_alpha_acceptance(
            application_data_dir=tmp_path / "unused-application",
            profile_ids=["one", "two"],
            review_directory=review_directory,
            provider_resolver=FixtureResolver(),
        )
    assert not review_directory.exists()

    with pytest.raises(SystemExit) as exit_error:
        alpha_acceptance.main(
            [
                "--profile",
                "one",
                "--profile",
                "two",
                "--review-directory",
                str(review_directory),
                "--commit",
                "not-a-commit",
            ]
        )
    assert exit_error.value.code == 2
    assert "40-character hexadecimal Git commit SHA" in capsys.readouterr().err


def test_alpha_cli_hides_setup_details_and_reports_qualification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    failed_receipt = _complete_alpha_receipts()[0] | {"status": "failed"}
    monkeypatch.setattr(
        alpha_acceptance,
        "run_alpha_acceptance",
        lambda **_kwargs: alpha_acceptance.AlphaAcceptanceResult(
            (failed_receipt,), (), ("alpha.matrix.run_completion",)
        ),
    )
    assert alpha_acceptance.main(
        [
            "--profile",
            "one",
            "--profile",
            "two",
            "--review-directory",
            str(tmp_path / "review"),
            "--commit",
            "a" * 40,
        ]
    ) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == failed_receipt
    assert "Alpha qualification failed: alpha.matrix.run_completion" in captured.err

    monkeypatch.setattr(
        alpha_acceptance,
        "run_alpha_acceptance",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("private checkout path")),
    )
    assert alpha_acceptance.main(
        [
            "--profile",
            "one",
            "--profile",
            "two",
            "--review-directory",
            str(tmp_path / "other-review"),
        ]
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Alpha setup failed; inspect local configuration. Temporary evidence was removed.\n"
    )
    assert "private checkout path" not in captured.err


def test_external_engineering_review_is_not_a_product_approval_or_human_acceptance() -> None:
    pack = _review_pack()
    reviews = [_external_review(sample) for sample in pack.samples]
    receipt = alpha_acceptance.codex_external_review_receipt(
        reviews, review_pack=pack
    ).model_dump(mode="json", by_alias=True)

    assert set(receipt) == {
        "receipt",
        "commit",
        "contractHash",
        "rubricVersion",
        "reviewer",
        "reviews",
        "gate",
    }
    assert receipt["receipt"] == "codex_external_review"
    serialized = json.dumps(receipt).lower()
    for forbidden in ("approval", "human", "acceptance", "profile", "story", "run", "prompt"):
        assert forbidden not in serialized

    different_pack = alpha_acceptance.ReviewPackManifest(
        commit="c" * 40,
        contract_hash=pack.contract_hash,
        samples=pack.samples,
    )
    gate = alpha_acceptance.codex_external_review_gate(
        reviews, review_pack=different_pack
    )
    rebound_receipt = alpha_acceptance.codex_external_review_receipt(
        reviews, review_pack=different_pack
    )
    assert gate.commit == different_pack.commit
    assert "codex_external_review.commit_identity" in gate.issue_codes
    assert rebound_receipt.commit == different_pack.commit
    assert rebound_receipt.gate.passed is False
