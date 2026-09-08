"""Secret-free repeatable acceptance runs for saved text-provider profiles.

This module is intentionally a caller of the production pipeline, not a
parallel test pipeline.  It copies no project data and never writes to the
source database: each sample gets a disposable repository and artifact root.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import re
import sys
import tempfile
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .artifacts import LocalArtifactStore
from .config import PlotloomSettings
from .domain import (
    ArtifactKind,
    AttemptStatus,
    GenerationAttemptKind,
    ProjectBrief,
    RunKind,
    STAGE_ORDER,
    StageStatus,
)
from .jobs import LifecycleJobRunner
from .persistence import SQLiteRepository
from .pipeline import (
    PipelineEngine,
    RunSecretBroker,
    SnapshotTextProviderResolver,
    TextProviderResolver,
)
from .provider_profiles import TextProviderProfileSnapshot
from .providers import ProviderPorts
from .runtime import RunContext
from .generation.planning import PLANNING_POLICY_VERSION
from .generation.prompts import PromptRepository, canonical_json, sha256_text
from .generation.story_graph_topology import (
    STORY_GRAPH_CONTENT_FILL_SCHEMA_ID,
    STORY_GRAPH_TOPOLOGY_VERSION,
)
from .generation.work_units import (
    SCENE_BEATS_FRAGMENT_SCHEMA_ID,
    STORYBOARD_FRAGMENT_SCHEMA_ID,
    WORK_UNIT_PROMPT_CONTRACT_VERSION,
)


DEFAULT_SAMPLE_COUNT = 3
M15_REQUIRED_PROFILE_COUNT = 2
CONFORMANCE_WORKLOAD_VERSION = "fixed_chinese_interactive_story.v8"
# The fixed workload exercises the complete topology contract: three endings,
# two decisions on every path, and one explicit JOIN. It is still bounded at
# nine nodes and four shots per scene so repeated operator probes stay
# practical without forcing several atomic beats into a single shot.
FIXED_CHINESE_BRIEF = ProjectBrief(
    title="雾港回声",
    synopsis="失忆的摆渡人黎明前在雾港收到一封来自未来自己的信，必须决定交出船钟还是带它穿过封港线。",
    genre="悬疑",
    visual_style="克制的东方水墨电影感",
    language="zh-CN",
    target_playthrough_seconds=60,
    decision_points_per_path=2,
    ending_count=3,
    node_budget=9,
    max_out_degree=3,
    desired_join_count=1,
    shots_per_scene_min=1,
    shots_per_scene_max=4,
)

_SAFE_ISSUE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")


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


def _public_token_usage(trace: Any) -> dict[str, int]:
    """Aggregate only numeric provider usage recorded in the temporary trace."""

    input_tokens = 0
    output_tokens = 0
    for artifact in trace.artifacts:
        if artifact.kind != ArtifactKind.RESPONSE or not isinstance(artifact.content, dict):
            continue
        usage = artifact.content.get("usage")
        if not isinstance(usage, dict):
            continue
        for field, total_name in (("inputTokens", "input"), ("outputTokens", "output")):
            value = usage.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                if total_name == "input":
                    input_tokens += value
                else:
                    output_tokens += value
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": input_tokens + output_tokens,
    }


def _stable_issue_codes(trace: Any) -> list[str]:
    """Extract machine-readable codes without exporting temporary evidence."""

    codes: set[str] = set()
    for artifact in trace.artifacts:
        if artifact.kind != ArtifactKind.VALIDATION or not isinstance(artifact.content, dict):
            continue
        issues = artifact.content.get("issues")
        if not isinstance(issues, list):
            continue
        for issue in issues:
            code = issue.get("code") if isinstance(issue, dict) else None
            if isinstance(code, str) and _SAFE_ISSUE_CODE.fullmatch(code):
                codes.add(code)
    # These outcomes are application-owned lifecycle codes.  Include them for
    # a provider failure that has no validation artifact, but never include an
    # arbitrary provider-provided string in the public receipt.
    for attempt in trace.attempts:
        code = attempt.outcome_code
        if (
            attempt.status != AttemptStatus.SUCCEEDED
            and isinstance(code, str)
            and (code.startswith("provider.") or code.startswith("contract."))
            and _SAFE_ISSUE_CODE.fullmatch(code)
        ):
            codes.add(code)
    return sorted(codes)


def _first_pass_stats(repository: SQLiteRepository, run_id: str, trace: Any) -> dict[str, int]:
    """Count first-pass *stages*, not individual sharded work units.

    Scene Beats and Storyboard can each contain many work units.  The M1.5
    acceptance contract gives either stage one first-pass credit only when
    every one of its units succeeds on its primary attempt.
    """

    execution = repository.get_run_execution_trace(run_id)
    accepted = rejected = outcome_unknown = cancelled = not_run = 0
    for stage in STAGE_ORDER:
        unit_ids = {
            unit.id for unit in execution.work_units if unit.stage == stage
        }
        stage_attempts = [
            attempt for attempt in trace.attempts if attempt.work_unit_id in unit_ids
        ]
        primary_by_unit = {
            attempt.work_unit_id: attempt
            for attempt in stage_attempts
            if attempt.attempt_kind == GenerationAttemptKind.PRIMARY
        }
        if unit_ids and set(primary_by_unit) == unit_ids and all(
            attempt.status == AttemptStatus.SUCCEEDED
            for attempt in primary_by_unit.values()
        ):
            accepted += 1
        elif any(attempt.outcome_unknown for attempt in stage_attempts):
            outcome_unknown += 1
        elif any(
            attempt.status == AttemptStatus.FAILED and not attempt.outcome_unknown
            for attempt in primary_by_unit.values()
        ):
            rejected += 1
        elif any(
            attempt.status == AttemptStatus.CANCELLED for attempt in stage_attempts
        ):
            cancelled += 1
        else:
            not_run += 1
    return {
        "total": len(STAGE_ORDER),
        "accepted": accepted,
        "rejected": rejected,
        "outcomeUnknown": outcome_unknown,
        "cancelled": cancelled,
        "notRun": not_run,
    }


def _maximum_attempts_per_work_unit(trace: Any) -> int:
    counts: dict[str, int] = {}
    for attempt in trace.attempts:
        if attempt.work_unit_id is not None:
            counts[attempt.work_unit_id] = counts.get(attempt.work_unit_id, 0) + 1
    return max(counts.values(), default=0)


def _conformance_invariant_codes(
    repository: SQLiteRepository,
    *,
    run_id: str,
    trace: Any,
) -> set[str]:
    """Audit lifecycle invariants without exporting canonical model content."""

    run = repository.get_run(run_id)
    envelopes = repository.list_stage_envelopes(run.project_id)
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
    if _maximum_attempts_per_work_unit(trace) > 3:
        codes.add("conformance.attempt_limit_exceeded")
    if any(attempt.outcome_unknown for attempt in trace.attempts):
        codes.add("provider.outcome_unknown")
    return codes


def _receipt_for(
    repository: SQLiteRepository,
    *,
    run_id: str,
    profile: TextProviderProfileSnapshot,
    duration_milliseconds: int,
    workload_hash: str,
    sample_ordinal: int,
) -> dict[str, Any]:
    """Return the deliberately narrow, secret-free conformance receipt."""

    completed = repository.get_run(run_id)
    trace = repository.get_run_trace(run_id)
    plan = repository.get_generation_plan(run_id)
    topology = repository.get_story_graph_topology(run_id)
    issue_codes = set(_stable_issue_codes(trace))
    if (
        isinstance(completed.failure_code, str)
        and _SAFE_ISSUE_CODE.fullmatch(completed.failure_code)
    ):
        issue_codes.add(completed.failure_code)
    issue_codes.update(
        _conformance_invariant_codes(repository, run_id=run_id, trace=trace)
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
        "tokens": _public_token_usage(trace),
        "firstPass": _first_pass_stats(repository, run_id, trace),
        "maxAttemptsPerWorkUnit": _maximum_attempts_per_work_unit(trace),
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
    source_database_url: str,
    profile_ids: Iterable[str],
) -> list[TextProviderProfileSnapshot]:
    """Read exactly the requested public profiles, without creating defaults."""

    source = SQLiteRepository(source_database_url)
    try:
        profiles = [source.get_text_provider_profile(profile_id) for profile_id in profile_ids]
        disabled = [profile.profile_id for profile in profiles if not profile.enabled]
        if disabled:
            raise ValueError(
                "disabled text provider profiles cannot start qualification: "
                + ", ".join(disabled)
            )
        return [profile.configuration for profile in profiles]
    finally:
        source.close()


def run_conformance(
    *,
    source_database_url: str,
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
    profiles = _load_named_profiles(source_database_url, selected_ids)
    resolver = provider_resolver or SnapshotTextProviderResolver()
    if server_key_resolver is None:
        settings = PlotloomSettings.from_env()

        def key_resolver(profile_id: str) -> str | None:
            key = settings.text_api_key_for_profile(profile_id)
            return key.get_secret_value() if key is not None else None

    else:
        key_resolver = server_key_resolver
    workload_hash = conformance_workload_hash()

    # The context manager removes SQLite evidence, its journal files, and the
    # otherwise-unused local artifact root even when a provider sample fails.
    with tempfile.TemporaryDirectory(prefix="plotloom-conformance-") as temporary_root:
        root = Path(temporary_root)

        # Alembic's EnvironmentContext uses process-global proxies and is not
        # safe to initialize concurrently in threads.  Prepare every isolated
        # repository on the caller thread; provider execution may then overlap
        # across profiles without sharing a database or migration context.
        prepared_samples: dict[
            str,
            list[tuple[SQLiteRepository, Path]],
        ] = {}
        try:
            for profile in profiles:
                profile_samples: list[tuple[SQLiteRepository, Path]] = []
                prepared_samples[profile.profile_id] = profile_samples
                for sample_index in range(sample_count):
                    sample_name = f"{profile.profile_id}-{sample_index + 1}"
                    database_path = root / f"{sample_name}.sqlite3"
                    artifact_root = root / f"{sample_name}-artifacts"
                    profile_samples.append(
                        (
                            SQLiteRepository(f"sqlite:///{database_path}"),
                            artifact_root,
                        )
                    )
        except BaseException:
            for samples in prepared_samples.values():
                for repository, _artifact_root in samples:
                    repository.close()
            raise

        def run_profile(profile: TextProviderProfileSnapshot) -> list[dict[str, Any]]:
            profile_receipts: list[dict[str, Any]] = []
            for sample_index, (repository, artifact_root) in enumerate(
                prepared_samples[profile.profile_id]
            ):
                secrets = RunSecretBroker(server_key_resolver=key_resolver)
                runner: LifecycleJobRunner | None = None
                try:
                    project = repository.create_project(FIXED_CHINESE_BRIEF.model_copy(deep=True))
                    run = repository.create_run(
                        project.id,
                        RunKind.PIPELINE,
                        STAGE_ORDER,
                        provider_snapshot=profile.model_dump(mode="json", by_alias=True),
                    )
                    runner = LifecycleJobRunner(
                        repository,
                        PipelineEngine(repository, resolver, secrets),
                        RunContext(
                            providers=ProviderPorts(),
                            artifacts=LocalArtifactStore(artifact_root),
                        ),
                        max_workers=1,
                        secret_registrar=secrets,
                    )
                    started = time.perf_counter()
                    runner.submit(run.id).result()
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    profile_receipts.append(
                        _receipt_for(
                            repository,
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
                for repository, _artifact_root in samples:
                    repository.close()
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
        "--source-database-url",
        help="existing Plotloom database URL; defaults to the configured database",
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
            source_database_url=options.source_database_url or settings.database_url,
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
