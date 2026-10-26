"""Secret-free repeatable acceptance runs for saved text-provider profiles.

This module is intentionally a caller of the production pipeline, not a
parallel test pipeline. It reads only public application profiles, then gives
each sample a disposable project folder and application store.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .story_workloads import FIXED_CHINESE_BRIEF
from .acceptance_metrics import (
    SAFE_ISSUE_CODE as _SAFE_ISSUE_CODE,
    first_pass_stats,
    maximum_attempts_per_work_unit,
    public_token_usage,
    stable_issue_codes,
)
from .config import PlotloomSettings
from plotloom.stage_contracts import STAGE_ORDER, StageStatus
from plotloom.run_contracts import RunKind
from plotloom.generation.planning_contracts import PLANNING_POLICY_VERSION
from .generation.prompts import PromptRepository, canonical_json, sha256_text
from plotloom.generation.story_graph_content_contracts import STORY_GRAPH_CONTENT_FILL_SCHEMA_ID
from plotloom.generation.story_graph_topology_contracts import STORY_GRAPH_TOPOLOGY_VERSION
from .generation.work_unit_contracts import (
    SCENE_BEATS_FRAGMENT_SCHEMA_ID,
    STORYBOARD_FRAGMENT_SCHEMA_ID,
    WORK_UNIT_PROMPT_CONTRACT_VERSION,
)
from .jobs import LifecycleJobRunner
from plotloom.pipeline import PipelineEngine
from plotloom.runtime_secrets import RunSecretBroker
from plotloom.text_provider_resolution import SnapshotTextProviderResolver, TextProviderResolver
from .project_storage import ProjectFolderStorage, ProjectStore
from .project_storage.application_profile_snapshot import load_saved_text_profiles
from .provider_profiles import TextProviderProfileSnapshot
from .providers import ProviderPorts
from .runtime import RunContext

DEFAULT_SAMPLE_COUNT = 3
M15_REQUIRED_PROFILE_COUNT = 2
CONFORMANCE_WORKLOAD_VERSION = "fixed_chinese_interactive_story.v8"


def conformance_workload_hash() -> str:
    """Fingerprint the exact fixed brief and generation contracts under test."""

    prompt_repository = PromptRepository()
    prompt_hashes = {
        prompt_id: prompt_repository.load(prompt_id)[1]
        for prompt_id in (
            "story_bible",
            "story_graph_content_fill",
            "scene_beats_fragment",
            "storyboard_fragment",
            "work_unit_correction",
        )
    }
    return sha256_text(
        canonical_json(
            {
                "workloadVersion": CONFORMANCE_WORKLOAD_VERSION,
                "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
                "stages": [stage.value for stage in STAGE_ORDER],
                "planningPolicyVersion": PLANNING_POLICY_VERSION,
                "topologyPlannerVersion": STORY_GRAPH_TOPOLOGY_VERSION,
                "workUnitPromptContractVersion": WORK_UNIT_PROMPT_CONTRACT_VERSION,
                "schemaIds": [
                    STORY_GRAPH_CONTENT_FILL_SCHEMA_ID,
                    SCENE_BEATS_FRAGMENT_SCHEMA_ID,
                    STORYBOARD_FRAGMENT_SCHEMA_ID,
                ],
                "promptHashes": prompt_hashes,
            }
        )
    )


def _conformance_invariant_codes(
    store: ProjectStore,
    *,
    run_id: str,
    trace: Any,
) -> set[str]:
    """Audit lifecycle invariants without exporting canonical model content."""

    run = store.generation.get_run(run_id)
    envelopes = store.authoring.list_stage_envelopes(run.project_id)
    installed = [
        envelope
        for envelope in envelopes
        if envelope.head.status == StageStatus.READY and envelope.payload is not None
    ]
    codes: set[str] = set()
    if run.status.value == "succeeded":
        if len(installed) != len(STAGE_ORDER) or len(run.result_revision_ids) != len(
            STAGE_ORDER
        ):
            codes.add("conformance.canonical_install_incomplete")
    elif installed or run.result_revision_ids:
        codes.add("conformance.partial_canonical_install")
    if maximum_attempts_per_work_unit(trace) > 3:
        codes.add("conformance.attempt_limit_exceeded")
    if any(attempt.outcome_unknown for attempt in trace.attempts):
        codes.add("provider.outcome_unknown")
    return codes


def _receipt_for(
    store: ProjectStore,
    *,
    run_id: str,
    profile: TextProviderProfileSnapshot,
    duration_milliseconds: int,
    workload_hash: str,
    sample_ordinal: int,
) -> dict[str, Any]:
    """Return the deliberately narrow, secret-free conformance receipt."""

    completed = store.generation.get_run(run_id)
    trace = store.generation.get_run_trace(run_id)
    plan = store.generation.get_generation_plan(run_id)
    topology = store.generation.get_story_graph_topology(run_id)
    issue_codes = set(stable_issue_codes(trace))
    if (
        isinstance(completed.failure_code, str)
        and _SAFE_ISSUE_CODE.fullmatch(completed.failure_code)
    ):
        issue_codes.add(completed.failure_code)
    issue_codes.update(
        _conformance_invariant_codes(store, run_id=run_id, trace=trace)
    )
    return {
        "profileId": profile.profile_id,
        "profileHash": profile.profile_hash,
        "workloadHash": workload_hash,
        "sampleOrdinal": sample_ordinal,
        "runHash": plan.plan_hash,
        "topologyHash": topology.topology_hash if topology is not None else None,
        "status": completed.status.value,
        "issueCodes": sorted(issue_codes),
        "durationMilliseconds": duration_milliseconds,
        "tokens": public_token_usage(trace),
        "firstPass": first_pass_stats(store.generation.get_run_execution_trace(run_id), trace, stage_order=STAGE_ORDER),
        "maxAttemptsPerWorkUnit": maximum_attempts_per_work_unit(trace),
    }


def qualification_issue_codes(
    receipts: Iterable[dict[str, Any]],
    *,
    profile_ids: Iterable[str],
    sample_count: int,
) -> list[str]:
    """Evaluate the model-neutral M1.5 gate from secret-free receipts only."""

    grouped: dict[str, list[dict[str, Any]]] = {
        profile_id: [] for profile_id in profile_ids
    }
    for receipt in receipts:
        profile_id = receipt.get("profileId")
        if profile_id in grouped:
            grouped[profile_id].append(receipt)
    issues: list[str] = []
    for profile_id, samples in grouped.items():
        prefix = f"qualification.{profile_id}"
        if len(samples) != sample_count:
            issues.append(f"{prefix}.sample_count")
            continue
        expected_ordinals = set(range(1, sample_count + 1))
        if {sample.get("sampleOrdinal") for sample in samples} != expected_ordinals:
            issues.append(f"{prefix}.sample_identity")
        if len({sample.get("runHash") for sample in samples}) != sample_count:
            issues.append(f"{prefix}.duplicate_run")
        if {
            sample.get("workloadHash") for sample in samples
        } != {conformance_workload_hash()}:
            issues.append(f"{prefix}.workload_identity")
        if any(sample.get("status") != "succeeded" for sample in samples):
            issues.append(f"{prefix}.run_completion")
        # Corrected extraction/schema/semantic issue codes remain useful audit
        # evidence and are already charged against the first-pass threshold.
        # Only a conformance invariant breach or ambiguous provider outcome is
        # independently disqualifying here.
        if any(
            any(
                isinstance(code, str)
                and (
                    code.startswith("conformance.")
                    or code == "provider.outcome_unknown"
                )
                for code in sample.get("issueCodes", [])
            )
            for sample in samples
        ):
            issues.append(f"{prefix}.invariant")
        if any(sample.get("maxAttemptsPerWorkUnit", 0) > 3 for sample in samples):
            issues.append(f"{prefix}.attempt_limit")
        total_stages = sum(
            int(sample.get("firstPass", {}).get("total", 0)) for sample in samples
        )
        accepted_stages = sum(
            int(sample.get("firstPass", {}).get("accepted", 0))
            for sample in samples
        )
        required_first_pass = math.ceil(total_stages * 5 / 6)
        if total_stages != len(STAGE_ORDER) * sample_count:
            issues.append(f"{prefix}.stage_count")
        elif accepted_stages < required_first_pass:
            issues.append(f"{prefix}.first_pass")
    return sorted(issues)


def m15_qualification_issue_codes(
    receipts: Iterable[dict[str, Any]],
    *,
    profile_ids: Iterable[str],
) -> list[str]:
    """Evaluate the fixed two-profile, three-sample M1.5 release gate."""

    selected_ids = list(profile_ids)
    if (
        len(selected_ids) != M15_REQUIRED_PROFILE_COUNT
        or len(set(selected_ids)) != M15_REQUIRED_PROFILE_COUNT
    ):
        return ["qualification.m15.profile_identity"]
    return qualification_issue_codes(
        receipts,
        profile_ids=selected_ids,
        sample_count=DEFAULT_SAMPLE_COUNT,
    )


def _load_named_profiles(
    application_data_dir: Path,
    profile_ids: Iterable[str],
) -> list[TextProviderProfileSnapshot]:
    """Read exactly the requested current application profiles without writes."""

    return load_saved_text_profiles(application_data_dir, profile_ids)


def run_conformance(
    *,
    application_data_dir: Path,
    profile_ids: Iterable[str],
    sample_count: int = DEFAULT_SAMPLE_COUNT,
    provider_resolver: TextProviderResolver | None = None,
    server_key_resolver: Callable[[str], str | None] | None = None,
    parallel_profiles: bool = False,
) -> list[dict[str, Any]]:
    """Run every named saved profile against the same fixed four-stage brief.

    ``provider_resolver`` is an explicit test seam.  Production callers leave
    it unset and therefore use the normal OpenAI-compatible resolver.  Tests
    must inject a fake adapter; this function never selects a fake provider by
    itself.
    """

    if sample_count < 1:
        raise ValueError("sample_count must be at least 1")
    selected_ids = list(profile_ids)
    if not selected_ids:
        raise ValueError("at least one named profile is required")
    if len(set(selected_ids)) != len(selected_ids):
        raise ValueError("profile_ids must be unique")
    profiles = _load_named_profiles(application_data_dir, selected_ids)
    resolver = provider_resolver or SnapshotTextProviderResolver()
    if server_key_resolver is None:
        settings = PlotloomSettings.from_env()

        def key_resolver(profile_id: str) -> str | None:
            key = settings.text_api_key_for_profile(profile_id)
            return key.get_secret_value() if key is not None else None

    else:
        key_resolver = server_key_resolver
    workload_hash = conformance_workload_hash()

    # The context manager removes every temporary project home, SQLite file,
    # and project-owned evidence even when a provider sample fails.
    with tempfile.TemporaryDirectory(prefix="plotloom-conformance-") as temporary_root:
        root = Path(temporary_root)
        outputs_root = root / "outputs"
        application_root = root / "application"
        outputs_root.mkdir()
        application_root.mkdir()
        storage = ProjectFolderStorage(
            outputs_root=outputs_root,
            application_data_root=application_root,
        )

        # Prepare every independently leased project on the caller thread;
        # provider execution may then overlap across profiles without sharing
        # project content, evidence, or mutable application profile state.
        prepared_samples: dict[
            str,
            list[ProjectStore],
        ] = {}
        try:
            for profile in profiles:
                profile_samples: list[ProjectStore] = []
                prepared_samples[profile.profile_id] = profile_samples
                for _sample_index in range(sample_count):
                    profile_samples.append(
                        storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(deep=True))
                    )
        except BaseException:
            for samples in prepared_samples.values():
                for store in samples:
                    store.close()
            raise

        def run_profile(profile: TextProviderProfileSnapshot) -> list[dict[str, Any]]:
            profile_receipts: list[dict[str, Any]] = []
            for sample_index, store in enumerate(prepared_samples[profile.profile_id]):
                secrets = RunSecretBroker(server_key_resolver=key_resolver)
                runner: LifecycleJobRunner | None = None
                try:
                    with store.generation.admit_provider_snapshot(
                        profile.model_dump(mode="json", by_alias=True)
                    ):
                        run = store.generation.create_run(
                            store.manifest.project_id,
                            RunKind.PIPELINE,
                            STAGE_ORDER,
                            provider_snapshot=profile.model_dump(mode="json", by_alias=True),
                        )
                    runner = LifecycleJobRunner(
                        store.generation,
                        PipelineEngine(store.generation, resolver, secrets),
                        RunContext(
                            providers=ProviderPorts(),
                            artifacts=store.run_artifacts(run.id),
                        ),
                        max_workers=1,
                        secret_registrar=secrets,
                    )
                    started = time.perf_counter()
                    runner.submit(run.id).result()
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    profile_receipts.append(
                        _receipt_for(
                            store,
                            run_id=run.id,
                            profile=profile,
                            duration_milliseconds=elapsed_ms,
                            workload_hash=workload_hash,
                            sample_ordinal=sample_index + 1,
                        )
                    )
                finally:
                    if runner is not None:
                        runner.close()
                    secrets.close()
            return profile_receipts

        try:
            if parallel_profiles and len(profiles) > 1:
                # Samples and work units stay serial within each profile. Only
                # independent qualification profiles overlap, so this does not
                # exceed either profile's frozen concurrency ceiling.
                with ThreadPoolExecutor(
                    max_workers=min(M15_REQUIRED_PROFILE_COUNT, len(profiles)),
                    thread_name_prefix="plotloom-conformance-profile",
                ) as executor:
                    futures = [executor.submit(run_profile, profile) for profile in profiles]
                    receipts = [
                        receipt
                        for future in futures
                        for receipt in future.result()
                    ]
            else:
                receipts = [
                    receipt
                    for profile in profiles
                    for receipt in run_profile(profile)
                ]
        finally:
            for samples in prepared_samples.values():
                for store in samples:
                    store.close()
    return receipts


def _parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run secret-free Plotloom profile conformance samples.")
    parser.add_argument(
        "--profile",
        action="append",
        dest="profile_ids",
        required=True,
        help="saved text-provider profile ID; repeat for multiple profiles",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_SAMPLE_COUNT,
        help="samples per profile (default: 3)",
    )
    parser.add_argument(
        "--qualify-m15",
        action="store_true",
        help="enforce the release gate: exactly two distinct profiles and three runs each",
    )
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """CLI entry point. stdout is JSONL receipts and deliberately nothing else."""

    options = _parse_arguments(arguments)
    if options.qualify_m15 and (
        options.runs != DEFAULT_SAMPLE_COUNT
        or len(options.profile_ids) != M15_REQUIRED_PROFILE_COUNT
        or len(set(options.profile_ids)) != M15_REQUIRED_PROFILE_COUNT
    ):
        print(
            "M1.5 qualification requires exactly two distinct profiles and three runs each.",
            file=sys.stderr,
        )
        return 2
    settings = PlotloomSettings.from_env()
    try:
        receipts = run_conformance(
            application_data_dir=settings.application_data_dir,
            profile_ids=options.profile_ids,
            sample_count=options.runs,
            server_key_resolver=lambda profile_id: (
                key.get_secret_value()
                if (key := settings.text_api_key_for_profile(profile_id)) is not None
                else None
            ),
            parallel_profiles=options.qualify_m15,
        )
    except Exception:  # Do not expose provider URLs, credentials, or evidence on a CLI failure.
        print(
            "Conformance setup failed; inspect local configuration. Temporary evidence was removed.",
            file=sys.stderr,
        )
        return 2
    for receipt in receipts:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    qualification_issues = (
        m15_qualification_issue_codes(
            receipts,
            profile_ids=options.profile_ids,
        )
        if options.qualify_m15
        else qualification_issue_codes(
            receipts,
            profile_ids=options.profile_ids,
            sample_count=options.runs,
        )
    )
    if qualification_issues:
        print(
            "Conformance qualification failed: " + ", ".join(qualification_issues),
            file=sys.stderr,
        )
        return 1
    if not options.qualify_m15:
        print(
            "Probe batch passed; this is not the two-profile M1.5 qualification gate.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
