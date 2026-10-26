"""Freeze one disposable native matrix before project admission; no model calls."""
import fcntl
import json
import os
import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import model_validator

from .alpha_provenance import native_contract_hash, require_preflight, source_snapshot
from .alpha_workloads import ALPHA_ACCEPTANCE_VERSION, ALPHA_STORIES, SAMPLE_KEYS
from .brief_contracts import ProjectBrief
from .codex_exec_pool_contracts import CodexExecPoolLimits
from .domain_base import CamelModel
from .generation.prompts import canonical_json

# Match the observed production installation's persisted limits, with a distinct
# private supervisor. This does not copy its namespace or qualification grants.
NATIVE_POOL_LIMITS = CodexExecPoolLimits(max_processes=4, max_text_processes=2,
    max_image_processes=2, max_queued_jobs=4)


class NativeSample(CamelModel):
    sample_id: str
    project_id: UUID
    brief: ProjectBrief


class NativeCampaign(CamelModel):
    version: Literal["alpha_native_codex_three_story.v1"] = ALPHA_ACCEPTANCE_VERSION
    samples: tuple[NativeSample, ...]
    source: dict
    contract_hash: str
    preflight_hash: str
    pool_limits: CodexExecPoolLimits
    data_root: str
    token_file: str
    private_root: str

    @model_validator(mode="after")
    def exact_frozen_matrix(self):
        if tuple(item.sample_id for item in self.samples) != SAMPLE_KEYS or len({s.project_id for s in self.samples}) != 9:
            raise ValueError("campaign must freeze the exact nine distinct native samples")
        for sample, story in zip(self.samples, (s for s in ALPHA_STORIES for _ in range(3)), strict=True):
            if sample.brief != story.brief:
                raise ValueError("native Alpha Brief bytes differ from the fixed workload")
        if self.pool_limits != NATIVE_POOL_LIMITS or self.contract_hash != native_contract_hash(self.source):
            raise ValueError("native Alpha policy or execution contract differs")
        return self


def write_private_json(path, value, *, replace=False):
    """Publish one owner-only JSON file; never overwrite by default."""
    path = Path(path)
    data = (canonical_json(value) + "\n").encode()
    if not replace:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        return
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        write_private_json(temporary, value)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_campaign(work_root, executable, preflight_path):
    work_root = Path(work_root)
    if not work_root.is_absolute() or work_root.exists() or work_root.is_symlink():
        raise ValueError("native campaign requires a fresh absolute disposable directory")
    snapshot = source_snapshot(executable, NATIVE_POOL_LIMITS)
    if work_root.resolve().is_relative_to(Path(snapshot["sourceRoot"])):
        raise ValueError("native campaign installation must stay outside the source checkout")
    proof_hash = require_preflight(preflight_path, snapshot)
    work_root.mkdir(mode=0o700)
    for child in ("data/outputs", "data/application", "private", "evidence"):
        (work_root / child).mkdir(parents=True, mode=0o700)
    token = work_root / "private/token"
    descriptor = os.open(token, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(secrets.token_urlsafe(48))
    campaign = NativeCampaign(samples=tuple(NativeSample(sample_id=key, project_id=uuid4(), brief=story.brief)
        for key, story in zip(SAMPLE_KEYS, (s for s in ALPHA_STORIES for _ in range(3)), strict=True)),
        source=snapshot, contract_hash=native_contract_hash(snapshot), preflight_hash=proof_hash,
        pool_limits=NATIVE_POOL_LIMITS, data_root=str(work_root / "data"),
        token_file=str(token), private_root=str(work_root / "private/codex-exec"))
    # The immutable complete matrix exists before any create/launch admission.
    write_private_json(work_root / "campaign.json", campaign.model_dump(mode="json", by_alias=True))
    write_private_json(work_root / "preflight.json", json.loads(Path(preflight_path).read_text()))
    return campaign


def load_campaign(work_root, *, check_source=False):
    root = Path(work_root)
    if not root.is_absolute() or root.is_symlink() or root.resolve(strict=True) != root:
        raise ValueError("native campaign root must be an absolute physical directory")
    if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError("native campaign root requires owner-only permissions")
    path = root / "campaign.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("native campaign manifest must be a regular file")
    campaign = NativeCampaign.model_validate_json(path.read_bytes())
    if (campaign.data_root != str(root / "data") or campaign.token_file != str(root / "private/token")
            or campaign.private_root != str(root / "private/codex-exec")):
        raise ValueError("native campaign runtime paths escape its disposable installation")
    if any(p.is_symlink() for p in (root / "data", root / "private", root / "evidence")):
        raise ValueError("native campaign directories cannot be aliases")
    if require_preflight(root / "preflight.json", campaign.source) != campaign.preflight_hash:
        raise ValueError("native campaign preflight proof changed")
    if check_source and source_snapshot(campaign.source["cliPath"], campaign.pool_limits) != campaign.source:
        raise ValueError("frozen native campaign source/CLI/profile/runtime drifted")
    return campaign


@contextmanager
def campaign_lease(root):
    """Serialize preparation of native samples across qualification invocations."""
    descriptor = os.open(Path(root) / ".campaign.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def publish_sample_outcome(evidence, *, receipt, bindings, content=None, cancellation=False):
    """Atomically publish a complete terminal set; interruption cannot wedge reuse.

    Staging has no outcome authority. A retry over an installed paused project
    may recapture it without new native work. Published bytes never change.
    """
    from tempfile import TemporaryDirectory
    evidence = Path(evidence)
    if evidence.is_symlink() or evidence.resolve(strict=True) != evidence:
        raise ValueError("sample evidence must be a physical directory")
    target = evidence / ("cancellation" if cancellation else "outcome")
    values = {"bindings.private.json": bindings, "receipt.json": receipt}
    if content is not None:
        values = {"content.json": content} | values
    if target.exists():
        if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(values):
            raise ValueError("published sample outcome inventory differs")
        for name, value in values.items():
            path = target / name
            expected = (canonical_json(value) + "\n").encode()
            if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
                raise ValueError("published sample outcome bytes differ")
        return target
    with TemporaryDirectory(prefix=".outcome-staging-", dir=evidence) as temporary:
        staging = Path(temporary) / "complete"
        staging.mkdir(mode=0o700)
        for name, value in values.items():
            write_private_json(staging / name, value)
        staging.rename(target)
    return target
