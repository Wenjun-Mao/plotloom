"""Freeze one disposable native matrix before project admission; no model calls."""
import fcntl
import json
import os
import secrets
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import model_validator

from .alpha_provenance import native_contract_hash, require_preflight, source_snapshot, source_checkout_root
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
    version: Literal["alpha_native_codex_three_story.v4"] = ALPHA_ACCEPTANCE_VERSION
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


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def private_directory(path, *, create=False):
    path = Path(path)
    if path.resolve(strict=not create) != path or path.is_symlink():
        raise ValueError("qualification evidence directory cannot be aliased")
    if create:
        private_directory(path.parent)
        path.mkdir(mode=0o700, exist_ok=True)
        sync_directory(path.parent)
    info = path.stat()
    if not path.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("qualification evidence directory must remain private")
    return path


def write_private_json(path, value, *, replace=False):
    """Durably publish a complete owner-only JSON file; no partial intent."""
    path = Path(path)
    data = (canonical_json(value) + "\n").encode()
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            temporary.replace(path)
        else:
            os.link(temporary, path, follow_symlinks=False)
        sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
        sync_directory(path.parent)


def durable_campaign_root(root, *, source_root, creating=False):
    """Temporary storage and aliases cannot hold native qualification authority."""
    root = Path(root)
    resolved = root.resolve(strict=not creating)
    temporary = {Path(tempfile.gettempdir()).resolve(), Path('/tmp').resolve(), Path('/var/tmp').resolve()}
    if (not root.is_absolute() or root != resolved or root.is_symlink()
            or resolved.is_relative_to(Path(source_root).resolve())
            or any(resolved.is_relative_to(base) for base in temporary)):
        raise ValueError("native campaign requires physical durable storage outside source and OS temporary roots")
    owner = root.parent if creating else root
    if (not owner.is_dir() or owner.stat().st_uid != os.getuid() or owner.stat().st_mode & 0o077):
        raise ValueError("native campaign root requires owner-only permissions")
    return root


def prepare_campaign(work_root, executable, preflight_path):
    work_root = Path(work_root)
    if not work_root.is_absolute() or work_root.exists() or work_root.is_symlink():
        raise ValueError("native campaign requires a fresh absolute disposable directory")
    snapshot = source_snapshot(executable, NATIVE_POOL_LIMITS)
    durable_campaign_root(work_root, source_root=snapshot["sourceRoot"], creating=True)
    proof_hash = require_preflight(preflight_path, snapshot)
    work_root.mkdir(mode=0o700)
    for child in ("data", "data/outputs", "data/application", "private", "evidence"):
        (work_root / child).mkdir(parents=True, mode=0o700)
    token = work_root / "private/token"
    descriptor = os.open(token, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(secrets.token_urlsafe(48))
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(token.parent)
    campaign = NativeCampaign(samples=tuple(NativeSample(sample_id=key, project_id=uuid4(), brief=story.brief)
        for key, story in zip(SAMPLE_KEYS, (s for s in ALPHA_STORIES for _ in range(3)), strict=True)),
        source=snapshot, contract_hash=native_contract_hash(snapshot), preflight_hash=proof_hash,
        pool_limits=NATIVE_POOL_LIMITS, data_root=str(work_root / "data"),
        token_file=str(token), private_root=str(work_root / "private/codex-exec"))
    # The immutable complete matrix exists before any create/launch admission.
    write_private_json(work_root / "campaign.json", campaign.model_dump(mode="json", by_alias=True))
    write_private_json(work_root / "preflight.json", json.loads(Path(preflight_path).read_text()))
    sync_directory(work_root.parent)
    return campaign


def load_campaign(work_root, *, check_source=False):
    root = Path(work_root)
    durable_campaign_root(root, source_root=source_checkout_root())
    path = root / "campaign.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("native campaign manifest must be a regular file")
    campaign = NativeCampaign.model_validate_json(path.read_bytes())
    if (campaign.data_root != str(root / "data") or campaign.token_file != str(root / "private/token")
            or campaign.private_root != str(root / "private/codex-exec")):
        raise ValueError("native campaign runtime paths escape its disposable installation")
    durable_campaign_root(root, source_root=campaign.source["sourceRoot"])
    for path in (root / "data", root / "private", root / "evidence", root / "data/outputs", root / "data/application"):
        if (not path.is_dir() or path.resolve(strict=True) != path
                or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077):
            raise ValueError("native campaign directories must retain their original private physical state")
    if not (root / "private/token").is_file() or (root / "private/token").is_symlink():
        raise ValueError("native campaign token is missing or aliased")
    if require_preflight(root / "preflight.json", campaign.source) != campaign.preflight_hash:
        raise ValueError("native campaign preflight proof changed")
    if check_source and source_snapshot(campaign.source["cliPath"], campaign.pool_limits) != campaign.source:
        raise ValueError("frozen native campaign source/CLI/profile/runtime drifted")
    return campaign


@contextmanager
def campaign_lease(root):
    """Serialize preparation of native samples across qualification invocations."""
    durable_campaign_root(root, source_root=source_checkout_root())
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
    target = Path(evidence) / ("cancellation" if cancellation else "outcome")
    if not cancellation and receipt.get("status") == "incomplete" and bindings.get("run", {}).get("state") == "paused":
        raise ValueError("user pause requires a separate immutable pause snapshot")
    values = {"bindings.private.json": bindings, "receipt.json": receipt}
    if content is not None:
        values = {"content.json": content} | values
    return publish_sample_record(target, values)


def publish_sample_record(target, values):
    """Publish one immutable evidence set; the caller owns the campaign lease."""
    target = Path(target)
    evidence = private_directory(target.parent)
    if target.exists():
        if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(values):
            raise ValueError("published sample outcome inventory differs")
        for name, value in values.items():
            path = target / name
            expected = (canonical_json(value) + "\n").encode()
            if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
                raise ValueError("published sample outcome bytes differ")
        return target
    with tempfile.TemporaryDirectory(prefix=".outcome-staging-", dir=evidence) as temporary:
        staging = Path(temporary) / "complete"
        staging.mkdir(mode=0o700)
        for name, value in values.items():
            write_private_json(staging / name, value)
        sync_directory(staging)
        staging.rename(target)
        sync_directory(evidence)
    return target
