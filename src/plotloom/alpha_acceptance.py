"""Disposable, blinded Alpha acceptance runs over saved provider profiles.

The Alpha runner intentionally calls the same production ``PipelineEngine``
and ``LifecycleJobRunner`` as normal generation.  It does not write projects,
runs, or artifacts into the source profile database.  Temporary evidence is
deleted; the caller explicitly chooses the only durable output directory for
the six content-only review samples.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from .artifacts import LocalArtifactStore
from .config import PlotloomSettings
from .domain import (
    ArtifactKind,
    AttemptStatus,
    GenerationAttemptKind,
    ProjectBrief,
    RunKind,
    STAGE_ORDER,
    StageName,
    StageStatus,
)
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


ALPHA_ACCEPTANCE_VERSION = "alpha_chinese_three_story.v1"
ALPHA_PROFILE_COUNT = 2
ALPHA_STORY_COUNT = 3
ALPHA_REPEATS_PER_STORY = 3
ALPHA_EXPECTED_RUN_COUNT = ALPHA_PROFILE_COUNT * ALPHA_STORY_COUNT * ALPHA_REPEATS_PER_STORY
ALPHA_REQUIRED_FIRST_PASS_STAGES_PER_PROFILE = 30
ALPHA_TOTAL_STAGES_PER_PROFILE = ALPHA_STORY_COUNT * ALPHA_REPEATS_PER_STORY * len(STAGE_ORDER)
_SAFE_ISSUE_CODE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
_RECEIPT_FIELDS = frozenset({
    "commit",
    "contractHash",
    "profileId",
    "storyId",
    "sampleId",
    "status",
    "issueCodes",
    "durationMilliseconds",
    "tokens",
    "scores",
})
_TOKEN_FIELDS = frozenset({"inputTokens", "outputTokens", "totalTokens"})
_SCORE_FIELDS = frozenset({"firstPass", "maxAttemptsPerWorkUnit"})
_FIRST_PASS_FIELDS = frozenset({"total", "accepted", "rejected", "outcomeUnknown", "cancelled", "notRun"})
_SQLITE_PENDING_BYTE = 0x40000000
_SQLITE_WAL_LOCK_OFFSET = 120


@dataclass(frozen=True)
class AlphaStory:
    """A versioned Chinese brief whose stable alias never names a provider."""

    alias: str
    version: str
    brief: ProjectBrief


def _brief(*, title: str, synopsis: str, genre: str, visual_style: str) -> ProjectBrief:
    return ProjectBrief(
        title=title,
        synopsis=synopsis,
        genre=genre,
        visual_style=visual_style,
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


ALPHA_STORIES: tuple[AlphaStory, ...] = (
    AlphaStory(
        alias="story-01",
        version="v1",
        brief=_brief(
            title="雾港回声",
            synopsis="失忆的摆渡人黎明前在雾港收到一封来自未来自己的信，必须决定交出船钟还是带它穿过封港线。",
            genre="悬疑",
            visual_style="克制的东方水墨电影感",
        ),
    ),
    AlphaStory(
        alias="story-02",
        version="v1",
        brief=_brief(
            title="最后一盏灯",
            synopsis="山城停电前，值班电工发现每一次恢复街区照明都会抹去一户人家的记忆，必须决定把最后电量交给医院还是旧剧院。",
            genre="科幻伦理",
            visual_style="潮湿夜色中的钠灯橙光与深蓝阴影",
        ),
    ),
    AlphaStory(
        alias="story-03",
        version="v1",
        brief=_brief(
            title="雪线来信",
            synopsis="高原邮差在暴雪封路前收到三封互相矛盾的遗书，必须决定先送出哪一封，并承担另外两条命运被改写的后果。",
            genre="人性剧情",
            visual_style="高反差雪原、红色邮包与低饱和人物特写",
        ),
    ),
)


@dataclass(frozen=True)
class AlphaAcceptanceResult:
    """Public result; review files contain no receipt or provider metadata."""

    receipts: tuple[dict[str, Any], ...]
    review_paths: tuple[Path, ...]
    qualification_issues: tuple[str, ...]


def alpha_contract_hash() -> str:
    """Fingerprint production prompt/planning contracts without exposing them."""

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
    return sha256_text(canonical_json({
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
    }))


def _public_token_usage(trace: Any) -> dict[str, int]:
    input_tokens = output_tokens = 0
    for artifact in trace.artifacts:
        if artifact.kind != ArtifactKind.RESPONSE or not isinstance(artifact.content, dict):
            continue
        usage = artifact.content.get("usage")
        if not isinstance(usage, dict):
            continue
        input_value = usage.get("inputTokens")
        output_value = usage.get("outputTokens")
        if isinstance(input_value, int) and not isinstance(input_value, bool) and input_value >= 0:
            input_tokens += input_value
        if isinstance(output_value, int) and not isinstance(output_value, bool) and output_value >= 0:
            output_tokens += output_value
    return {"inputTokens": input_tokens, "outputTokens": output_tokens, "totalTokens": input_tokens + output_tokens}


def _stable_issue_codes(trace: Any) -> set[str]:
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
    for attempt in trace.attempts:
        code = attempt.outcome_code
        if (
            attempt.status != AttemptStatus.SUCCEEDED
            and isinstance(code, str)
            and (code.startswith("provider.") or code.startswith("contract."))
            and _SAFE_ISSUE_CODE.fullmatch(code)
        ):
            codes.add(code)
    return codes


def _first_pass_stats(repository: SQLiteRepository, run_id: str, trace: Any) -> dict[str, int]:
    execution = repository.get_run_execution_trace(run_id)
    accepted = rejected = outcome_unknown = cancelled = not_run = 0
    for stage in STAGE_ORDER:
        unit_ids = {unit.id for unit in execution.work_units if unit.stage == stage}
        attempts = [attempt for attempt in trace.attempts if attempt.work_unit_id in unit_ids]
        primary_by_unit = {
            attempt.work_unit_id: attempt
            for attempt in attempts
            if attempt.attempt_kind == GenerationAttemptKind.PRIMARY
        }
        if unit_ids and set(primary_by_unit) == unit_ids and all(
            attempt.status == AttemptStatus.SUCCEEDED for attempt in primary_by_unit.values()
        ):
            accepted += 1
        elif any(attempt.outcome_unknown for attempt in attempts):
            outcome_unknown += 1
        elif any(attempt.status == AttemptStatus.FAILED and not attempt.outcome_unknown for attempt in primary_by_unit.values()):
            rejected += 1
        elif any(attempt.status == AttemptStatus.CANCELLED for attempt in attempts):
            cancelled += 1
        else:
            not_run += 1
    return {
        "total": len(STAGE_ORDER), "accepted": accepted, "rejected": rejected,
        "outcomeUnknown": outcome_unknown, "cancelled": cancelled, "notRun": not_run,
    }


def _maximum_attempts_per_work_unit(trace: Any) -> int:
    counts: dict[str, int] = {}
    for attempt in trace.attempts:
        if attempt.work_unit_id is not None:
            counts[attempt.work_unit_id] = counts.get(attempt.work_unit_id, 0) + 1
    return max(counts.values(), default=0)


def _invariant_codes(repository: SQLiteRepository, *, run_id: str, trace: Any) -> set[str]:
    run = repository.get_run(run_id)
    envelopes = repository.list_stage_envelopes(run.project_id)
    installed = [
        envelope for envelope in envelopes
        if envelope.head.status == StageStatus.READY and envelope.payload is not None
    ]
    codes: set[str] = set()
    if run.status.value == "succeeded":
        if len(installed) != len(STAGE_ORDER) or len(run.result_revision_ids) != len(STAGE_ORDER):
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
    profile_alias: str,
    story: AlphaStory,
    repeat_ordinal: int,
    duration_milliseconds: int,
    commit_sha: str,
) -> dict[str, Any]:
    completed = repository.get_run(run_id)
    trace = repository.get_run_trace(run_id)
    codes = _stable_issue_codes(trace)
    if isinstance(completed.failure_code, str) and _SAFE_ISSUE_CODE.fullmatch(completed.failure_code):
        codes.add(completed.failure_code)
    codes.update(_invariant_codes(repository, run_id=run_id, trace=trace))
    # This exact field set is a security boundary: receipt consumers never see
    # real profile names, endpoints, models, prompts, raw responses, run IDs,
    # provider configuration, or workload/story fingerprints.
    return {
        "commit": commit_sha,
        "contractHash": alpha_contract_hash(),
        "profileId": profile_alias,
        "storyId": story.alias,
        "sampleId": f"{story.alias}-repeat-{repeat_ordinal:02d}",
        "status": completed.status.value,
        "issueCodes": sorted(codes),
        "durationMilliseconds": duration_milliseconds,
        "tokens": _public_token_usage(trace),
        "scores": {
            "firstPass": _first_pass_stats(repository, run_id, trace),
            "maxAttemptsPerWorkUnit": _maximum_attempts_per_work_unit(trace),
        },
    }


def _content_only_review_payload(repository: SQLiteRepository, project_id: str) -> dict[str, Any]:
    """Return only canonical V2 authoring content, never head/run/provenance data."""

    envelopes = repository.list_stage_envelopes(project_id)
    by_stage = {envelope.head.stage: envelope.payload for envelope in envelopes}
    if any(by_stage.get(stage) is None for stage in STAGE_ORDER):
        raise ValueError("cannot export a review sample without all canonical stages")
    names = {
        StageName.STORY_BIBLE: "storyBible",
        StageName.STORY_GRAPH: "storyGraph",
        StageName.SCENE_BEATS: "sceneBeats",
        StageName.STORYBOARD: "storyboard",
    }
    return {
        names[stage]: by_stage[stage].model_dump(mode="json", by_alias=True)
        for stage in STAGE_ORDER
    }


def _source_checkout_root() -> Path:
    """Resolve the checkout root without making Git state changes."""

    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip()).resolve()


def _prepare_review_directory(review_directory: Path, *, checkout_root: Path) -> Path:
    if not review_directory.is_absolute():
        raise ValueError("review_directory must be an absolute path")
    resolved_directory = review_directory.resolve()
    if resolved_directory.is_relative_to(checkout_root):
        raise ValueError("review_directory must be outside the source checkout")
    if resolved_directory.exists() and (not resolved_directory.is_dir() or resolved_directory.is_symlink()):
        raise ValueError("review_directory must be an ordinary directory path")
    if resolved_directory.exists() and any(resolved_directory.iterdir()):
        raise ValueError("review_directory must be empty; Alpha never overwrites a review pack")
    return resolved_directory


def _publish_review_directory(staging_directory: Path, review_directory: Path) -> tuple[Path, ...]:
    """Atomically expose a complete staged review pack, never individual files."""

    if review_directory.exists():
        if not review_directory.is_dir() or review_directory.is_symlink() or any(review_directory.iterdir()):
            raise ValueError("review_directory changed while Alpha was running")
        review_directory.rmdir()
    staging_directory.replace(review_directory)
    return tuple(review_directory / f"review-{ordinal:02d}.json" for ordinal in range(1, 7))


def _write_review_sample(review_directory: Path, ordinal: int, payload: Mapping[str, Any]) -> Path:
    # Opaque sequential names prevent the review artifact from disclosing its
    # provider/profile/run provenance. Ordering is deterministic by anonymous
    # profile alias then fixed story alias; no local mapping file is needed.
    path = review_directory / f"review-{ordinal:02d}.json"
    path.write_text(canonical_json(dict(payload)) + "\n", encoding="utf-8")
    return path


def _source_sqlite_path(source_database_url: str) -> Path:
    """Return a real SQLite source path without normalizing or opening it for write."""

    url = make_url(source_database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("Alpha source profiles require an existing file-backed SQLite database")
    path = Path(url.database).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Alpha source profile database does not exist")
    return path


@contextmanager
def _stable_source_sqlite_files(source_path: Path) -> Iterable[bool]:
    """Hold non-mutating SQLite locks while copying a source database and WAL."""

    try:
        import fcntl
    except ImportError as error:  # pragma: no cover - Alpha's SQLite source is POSIX-only today.
        raise RuntimeError("Alpha needs POSIX SQLite file locks for a non-mutating source snapshot") from error

    handles: list[int] = []

    def lock_shared(path: Path, offset: int, length: int) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        handles.append(descriptor)
        deadline = time.monotonic() + 10
        while True:
            try:
                fcntl.lockf(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB, length, offset, os.SEEK_SET)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("timed out waiting for a stable source SQLite snapshot")
                time.sleep(0.01)

    try:
        # A rollback-journal writer may already own RESERVED and need PENDING
        # to commit. Taking RESERVED first waits for that writer before we
        # hold PENDING, avoiding a RESERVED/PENDING lock-order inversion.
        lock_shared(source_path, _SQLITE_PENDING_BYTE + 1, 1)
        lock_shared(source_path, _SQLITE_PENDING_BYTE, 1)
        lock_shared(source_path, _SQLITE_PENDING_BYTE + 2, 510)
        source_shm_path = source_path.with_name(f"{source_path.name}-shm")
        wal_locks_held = source_shm_path.exists()
        if wal_locks_held:
            # WAL_WRITE_LOCK, WAL_CKPT_LOCK, and WAL_RECOVER_LOCK. POSIX file
            # locks do not write the SHM bytes they protect.
            try:
                lock_shared(source_shm_path, _SQLITE_WAL_LOCK_OFFSET, 3)
            except FileNotFoundError as error:
                raise RuntimeError("source SQLite WAL-index changed before it could be locked; retry") from error
        yield wal_locks_held
    finally:
        for descriptor in reversed(handles):
            try:
                fcntl.lockf(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def _sqlite_file_state(path: Path) -> tuple[bool, int, int, int, int, int]:
    if not path.exists():
        return False, 0, 0, 0, 0, 0
    stat = path.stat()
    return True, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _copy_stable_source_sqlite_pair(source_path: Path, copied_path: Path) -> None:
    """Copy a source main/WAL pair, retrying rather than accepting SHM races."""

    source_wal_path = source_path.with_name(f"{source_path.name}-wal")
    source_shm_path = source_path.with_name(f"{source_path.name}-shm")
    copied_wal_path = copied_path.with_name(f"{copied_path.name}-wal")
    for _attempt in range(3):
        with _stable_source_sqlite_files(source_path):
            before = tuple(_sqlite_file_state(path) for path in (source_path, source_wal_path, source_shm_path))
            shutil.copyfile(source_path, copied_path)
            if before[1][0]:
                shutil.copyfile(source_wal_path, copied_wal_path)
            elif copied_wal_path.exists():
                copied_wal_path.unlink()
            after = tuple(_sqlite_file_state(path) for path in (source_path, source_wal_path, source_shm_path))
        # Even a held SHM lock is tied to an inode that another process can
        # unlink and recreate. Always compare complete file identity and
        # metadata, not merely lock ownership, before accepting a copied pair.
        if before == after:
            return
        if copied_path.exists():
            copied_path.unlink()
        if copied_wal_path.exists():
            copied_wal_path.unlink()
    raise RuntimeError("source SQLite WAL state changed during snapshot; retry after writer activity settles")


def _load_named_profiles(source_database_url: str, profile_ids: Iterable[str]) -> list[TextProviderProfileSnapshot]:
    """Read profiles through a read-only snapshot, never a repository/migrator.

    ``immutable=1`` is deliberately not used: it would hide committed data that
    is still in a live WAL file. Opening even a ``mode=ro`` connection against
    the source can update its ``-shm`` sidecar. We instead lock source WAL and
    checkpoint writers without changing bytes, copy a stable main/WAL pair,
    then use a read-only connection to back that pair up into a disposable DB.
    """

    source_path = _source_sqlite_path(source_database_url)
    with tempfile.TemporaryDirectory(prefix="plotloom-alpha-profile-snapshot-") as snapshot_root:
        root = Path(snapshot_root)
        copied_path = root / source_path.name
        _copy_stable_source_sqlite_pair(source_path, copied_path)
        copied_source = sqlite3.connect(f"{copied_path.as_uri()}?mode=ro", uri=True)
        snapshot_path = root / "profiles.sqlite3"
        destination = sqlite3.connect(snapshot_path)
        try:
            # The read-only copied source may create only temporary sidecars.
            # Backup materializes one coherent database for profile queries.
            copied_source.backup(destination)
        finally:
            copied_source.close()
            destination.close()

        source = sqlite3.connect(f"{snapshot_path.as_uri()}?mode=ro", uri=True)
        try:
            source.execute("PRAGMA query_only=ON")
            profiles: list[TextProviderProfileSnapshot] = []
            for profile_id in profile_ids:
                row = source.execute(
                    "SELECT settings FROM v2_text_provider_profiles WHERE id = ?",
                    (profile_id,),
                ).fetchone()
                if row is None:
                    raise ValueError(f"saved text provider profile not found: {profile_id}")
                settings = row[0]
                if not isinstance(settings, str):
                    raise ValueError("saved text provider profile has invalid settings")
                profiles.append(TextProviderProfileSnapshot.model_validate(json.loads(settings)))
            return profiles
        finally:
            source.close()


def _validate_commit_sha(value: str) -> str:
    if not _COMMIT_SHA.fullmatch(value):
        raise ValueError("commit must be a 40-character hexadecimal Git commit SHA")
    return value.lower()


def _parse_commit_sha(value: str) -> str:
    try:
        return _validate_commit_sha(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _resolve_commit_sha(explicit_commit: str | None) -> str:
    if explicit_commit is not None:
        return _validate_commit_sha(explicit_commit)
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return _validate_commit_sha(completed.stdout.strip())


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _receipt_score_value(sample: Mapping[str, Any], key: str) -> int:
    scores = sample.get("scores")
    if not isinstance(scores, Mapping):
        return 0
    if key == "maxAttemptsPerWorkUnit":
        value = scores.get(key)
    else:
        first_pass = scores.get("firstPass")
        value = first_pass.get(key) if isinstance(first_pass, Mapping) else None
    return value if _is_nonnegative_int(value) else 0


def _receipt_has_whitelisted_shape(sample: Any) -> bool:
    if not isinstance(sample, Mapping) or set(sample) != _RECEIPT_FIELDS:
        return False
    if not isinstance(sample.get("commit"), str) or not _COMMIT_SHA.fullmatch(sample["commit"]):
        return False
    if not isinstance(sample.get("contractHash"), str) or not re.fullmatch(r"[0-9a-f]{64}", sample["contractHash"]):
        return False
    if not all(isinstance(sample.get(key), str) for key in ("profileId", "storyId", "sampleId", "status")):
        return False
    issue_codes = sample.get("issueCodes")
    if not isinstance(issue_codes, list) or not all(isinstance(code, str) and _SAFE_ISSUE_CODE.fullmatch(code) for code in issue_codes):
        return False
    if not _is_nonnegative_int(sample.get("durationMilliseconds")):
        return False
    tokens = sample.get("tokens")
    if not isinstance(tokens, Mapping) or set(tokens) != _TOKEN_FIELDS or not all(_is_nonnegative_int(value) for value in tokens.values()):
        return False
    if tokens["totalTokens"] != tokens["inputTokens"] + tokens["outputTokens"]:
        return False
    scores = sample.get("scores")
    if not isinstance(scores, Mapping) or set(scores) != _SCORE_FIELDS:
        return False
    first_pass = scores.get("firstPass")
    return (
        isinstance(first_pass, Mapping)
        and set(first_pass) == _FIRST_PASS_FIELDS
        and all(_is_nonnegative_int(value) for value in first_pass.values())
        and _is_nonnegative_int(scores.get("maxAttemptsPerWorkUnit"))
    )


def alpha_qualification_issue_codes(receipts: Iterable[Mapping[str, Any]]) -> list[str]:
    """Evaluate Alpha's full 18-run release matrix from secret-free receipts."""

    samples = [sample if isinstance(sample, Mapping) else {} for sample in receipts]
    issues: list[str] = []
    if any(not _receipt_has_whitelisted_shape(sample) for sample in samples):
        issues.append("alpha.receipt.schema")
    expected_profile_ids = {f"profile-{index:02d}" for index in range(1, ALPHA_PROFILE_COUNT + 1)}
    expected_story_ids = {story.alias for story in ALPHA_STORIES}
    if len(samples) != ALPHA_EXPECTED_RUN_COUNT:
        issues.append("alpha.matrix.run_count")
    if {sample.get("profileId") for sample in samples} != expected_profile_ids:
        issues.append("alpha.matrix.profile_identity")
    expected_cells = {
        (profile_id, story_id, f"{story_id}-repeat-{repeat:02d}")
        for profile_id in expected_profile_ids
        for story_id in expected_story_ids
        for repeat in range(1, ALPHA_REPEATS_PER_STORY + 1)
    }
    actual_cells = {
        (sample.get("profileId"), sample.get("storyId"), sample.get("sampleId"))
        for sample in samples
    }
    if actual_cells != expected_cells:
        issues.append("alpha.matrix.sample_identity")
    if {sample.get("contractHash") for sample in samples} != {alpha_contract_hash()}:
        issues.append("alpha.matrix.contract_identity")
    if len({sample.get("commit") for sample in samples if isinstance(sample, Mapping)}) != 1:
        issues.append("alpha.matrix.commit_identity")
    if {sample.get("storyId") for sample in samples} - expected_story_ids:
        issues.append("alpha.matrix.story_identity")
    if any(sample.get("status") != "succeeded" for sample in samples):
        issues.append("alpha.matrix.run_completion")
    if any(
        isinstance(sample.get("issueCodes"), list) and any(
            isinstance(code, str) and (code == "provider.outcome_unknown" or code.startswith("conformance."))
            for code in sample["issueCodes"]
        )
        for sample in samples
    ):
        issues.append("alpha.matrix.invariant")
    if any(
        _receipt_score_value(sample, "maxAttemptsPerWorkUnit") > 3
        for sample in samples
    ):
        issues.append("alpha.matrix.attempt_limit")
    for profile_id in sorted(expected_profile_ids):
        profile_samples = [sample for sample in samples if sample.get("profileId") == profile_id]
        accepted = sum(_receipt_score_value(sample, "accepted") for sample in profile_samples)
        total = sum(_receipt_score_value(sample, "total") for sample in profile_samples)
        if total != ALPHA_TOTAL_STAGES_PER_PROFILE:
            issues.append(f"alpha.{profile_id}.stage_count")
        elif accepted < ALPHA_REQUIRED_FIRST_PASS_STAGES_PER_PROFILE:
            issues.append(f"alpha.{profile_id}.first_pass")
    return sorted(set(issues))


def run_alpha_acceptance(
    *,
    source_database_url: str,
    profile_ids: Iterable[str],
    review_directory: Path,
    provider_resolver: TextProviderResolver | None = None,
    server_key_resolver: Callable[[str], str | None] | None = None,
    commit_sha: str | None = None,
) -> AlphaAcceptanceResult:
    """Execute Alpha's 2 × 3 × 3 matrix through the production pipeline.

    ``provider_resolver`` is test-only dependency injection.  The normal CLI
    leaves it unset and uses the saved profile's real configured provider.
    """

    selected_ids = list(profile_ids)
    if len(selected_ids) != ALPHA_PROFILE_COUNT or len(set(selected_ids)) != ALPHA_PROFILE_COUNT:
        raise ValueError("Alpha requires exactly two distinct saved profile IDs")
    resolved_commit_sha = _resolve_commit_sha(commit_sha)
    review_destination = _prepare_review_directory(review_directory, checkout_root=_source_checkout_root())
    profiles = _load_named_profiles(source_database_url, selected_ids)
    resolver = provider_resolver or SnapshotTextProviderResolver()
    if server_key_resolver is None:
        settings = PlotloomSettings.from_env()

        def key_resolver(profile_id: str) -> str | None:
            key = settings.text_api_key_for_profile(profile_id)
            return key.get_secret_value() if key is not None else None
    else:
        key_resolver = server_key_resolver

    receipts: list[dict[str, Any]] = []
    staged_review_paths: list[Path] = []
    review_destination.parent.mkdir(parents=True, exist_ok=True)
    staging_directory = Path(tempfile.mkdtemp(
        prefix=f".{review_destination.name}.plotloom-stage-",
        dir=review_destination.parent,
    ))
    # The temporary root owns every database, journal, artifact, prompt, and
    # response. The staged directory is atomically renamed only on success.
    try:
        with tempfile.TemporaryDirectory(prefix="plotloom-alpha-acceptance-") as temporary_root:
            root = Path(temporary_root)
            for profile_index, profile in enumerate(profiles, start=1):
                profile_alias = f"profile-{profile_index:02d}"
                for story_index, story in enumerate(ALPHA_STORIES, start=1):
                    for repeat_ordinal in range(1, ALPHA_REPEATS_PER_STORY + 1):
                        database_path = root / f"{profile_alias}-{story.alias}-{repeat_ordinal}.sqlite3"
                        artifact_root = root / f"{profile_alias}-{story.alias}-{repeat_ordinal}-artifacts"
                        repository = SQLiteRepository(f"sqlite:///{database_path}")
                        secrets = RunSecretBroker(server_key_resolver=key_resolver)
                        runner: LifecycleJobRunner | None = None
                        try:
                            project = repository.create_project(story.brief.model_copy(deep=True))
                            run = repository.create_run(
                                project.id,
                                RunKind.PIPELINE,
                                STAGE_ORDER,
                                provider_snapshot=profile.model_dump(mode="json", by_alias=True),
                            )
                            runner = LifecycleJobRunner(
                                repository,
                                PipelineEngine(repository, resolver, secrets),
                                RunContext(providers=ProviderPorts(), artifacts=LocalArtifactStore(artifact_root)),
                                max_workers=1,
                                secret_registrar=secrets,
                            )
                            started = time.perf_counter()
                            runner.submit(run.id).result()
                            elapsed_ms = int((time.perf_counter() - started) * 1000)
                            receipts.append(_receipt_for(
                                repository,
                                run_id=run.id,
                                profile_alias=profile_alias,
                                story=story,
                                repeat_ordinal=repeat_ordinal,
                                duration_milliseconds=elapsed_ms,
                                commit_sha=resolved_commit_sha,
                            ))
                            if repeat_ordinal == 1 and repository.get_run(run.id).status.value == "succeeded":
                                review_ordinal = (profile_index - 1) * ALPHA_STORY_COUNT + story_index
                                staged_review_paths.append(_write_review_sample(
                                    staging_directory,
                                    review_ordinal,
                                    _content_only_review_payload(repository, project.id),
                                ))
                        finally:
                            if runner is not None:
                                runner.close()
                            secrets.close()
                            repository.close()
        qualification = list(alpha_qualification_issue_codes(receipts))
        if len(staged_review_paths) != ALPHA_PROFILE_COUNT * ALPHA_STORY_COUNT:
            qualification.append("alpha.review_pack.count")
        if qualification:
            return AlphaAcceptanceResult(tuple(receipts), (), tuple(sorted(set(qualification))))
        review_paths = _publish_review_directory(staging_directory, review_destination)
        return AlphaAcceptanceResult(tuple(receipts), review_paths, ())
    finally:
        if staging_directory.exists():
            shutil.rmtree(staging_directory)


def _parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the blinded three-story Plotloom Alpha acceptance matrix.")
    parser.add_argument("--profile", action="append", dest="profile_ids", required=True, help="saved text-provider profile ID; pass exactly twice")
    parser.add_argument("--review-directory", required=True, type=Path, help="empty local directory for six anonymized content-only review JSON files")
    parser.add_argument("--source-database-url", help="existing Plotloom database URL; defaults to configured database")
    parser.add_argument("--commit", type=_parse_commit_sha, help="40-character checkpoint commit SHA; defaults to the current HEAD commit")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    """CLI entry point: JSONL receipts only on stdout, generic errors on stderr."""

    options = _parse_arguments(arguments)
    if len(options.profile_ids) != ALPHA_PROFILE_COUNT or len(set(options.profile_ids)) != ALPHA_PROFILE_COUNT:
        print("Alpha requires exactly two distinct saved profiles.", file=sys.stderr)
        return 2
    settings = PlotloomSettings.from_env()
    try:
        result = run_alpha_acceptance(
            source_database_url=options.source_database_url or settings.database_url,
            profile_ids=options.profile_ids,
            review_directory=options.review_directory,
            commit_sha=options.commit,
            server_key_resolver=lambda profile_id: (
                key.get_secret_value()
                if (key := settings.text_api_key_for_profile(profile_id)) is not None
                else None
            ),
        )
    except Exception:
        print("Alpha setup failed; inspect local configuration. Temporary evidence was removed.", file=sys.stderr)
        return 2
    for receipt in result.receipts:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    if result.qualification_issues:
        print("Alpha qualification failed: " + ", ".join(result.qualification_issues), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
