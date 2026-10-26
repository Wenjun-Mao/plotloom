"""Confined atomic blind publication, separate from private native execution state."""
import json, os, secrets, tempfile
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Mapping
from typing import Any, Protocol
from .alpha_review_contracts import ReviewPackManifest, ReviewSampleManifest
from .alpha_review_templates import OPAQUE_REVIEW_ID_PATTERN, CONTENT_HASH_PATTERN, write_codex_external_review_templates
from .alpha_provenance import validate_commit_sha
from .alpha_workloads import ALPHA_EXPECTED_REVIEW_COUNT, REVIEW_SAMPLE_KEYS
from .generation.prompts import canonical_json, sha256_text
from .project_storage import ProjectStore
from .stage_contracts import StageName, STAGE_ORDER
_REVIEW_MAPPING_FILENAME = "review-mapping.private.json"

class _ReviewRandomSource(Protocol):
    """Small injectable surface; production uses ``secrets.SystemRandom``."""

    def sample(self, population: list[int], k: int) -> list[int]: ...

    def getrandbits(self, k: int) -> int: ...

@dataclass(frozen=True)
class _ReviewCandidate:
    """Private pre-publication association; never serialize into a receipt."""

    story_id: str
    sample_id: str
    payload: dict[str, Any]
    content_hash: str

def content_only_review_payload(store: ProjectStore) -> dict[str, Any]:
    """Return only canonical V2 authoring content, never head/run/provenance data."""

    envelopes = store.authoring.list_stage_envelopes(store.manifest.project_id)
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

def _prepare_review_directory(review_directory: Path, *, checkout_root: Path) -> Path:
    if not review_directory.is_absolute():
        raise ValueError("review_directory must be an absolute path")
    if review_directory.is_symlink():
        raise ValueError("review_directory cannot be a symlink")
    resolved_directory = review_directory.resolve()
    if resolved_directory.is_relative_to(checkout_root):
        raise ValueError("review_directory must be outside the source checkout")
    if resolved_directory.exists() and (not resolved_directory.is_dir() or resolved_directory.is_symlink()):
        raise ValueError("review_directory must be an ordinary directory path")
    if resolved_directory.exists() and any(resolved_directory.iterdir()):
        raise ValueError("review_directory must be empty; Alpha never overwrites a review pack")
    return resolved_directory

def _publish_review_directory(
    staging_directory: Path,
    review_directory: Path,
    review_ids: Iterable[str],
) -> tuple[Path, ...]:
    """Atomically expose a complete staged review pack, never individual files."""

    if review_directory.exists():
        if not review_directory.is_dir() or review_directory.is_symlink() or any(review_directory.iterdir()):
            raise ValueError("review_directory changed while Alpha was running")
        review_directory.rmdir()
    staging_directory.replace(review_directory)
    return tuple(review_directory / f"{review_id}.json" for review_id in review_ids)

def _write_review_sample(
    review_directory: Path,
    review_id: str,
    payload: Mapping[str, Any],
) -> Path:
    """Write a content-only blinded sample whose filename is an opaque ID."""

    if not OPAQUE_REVIEW_ID_PATTERN.fullmatch(review_id):
        raise ValueError("review sample needs an opaque review ID")
    path = review_directory / f"{review_id}.json"
    path.write_text(canonical_json(dict(payload)) + "\n", encoding="utf-8")
    return path

def _randomized_review_candidates(
    candidates: Iterable[_ReviewCandidate],
    *,
    random_source: _ReviewRandomSource | None = None,
) -> tuple[tuple[str, _ReviewCandidate], ...]:
    """Assign opaque IDs after secure random permutation of fixed samples.

    Selection remains deterministic (repeat one for each story),
    but neither file order nor IDs reveal the selected story ordering.
    Tests inject a minimal deterministic source; production always obtains its
    randomness from the operating system through :class:`secrets.SystemRandom`.
    """

    source = random_source or secrets.SystemRandom()
    items = tuple(candidates)
    indexes = source.sample(list(range(len(items))), len(items))
    if sorted(indexes) != list(range(len(items))):
        raise ValueError("review random source returned an invalid permutation")
    assigned: list[tuple[str, _ReviewCandidate]] = []
    used_ids: set[str] = set()
    for index in indexes:
        review_id = f"review-{source.getrandbits(128):032x}"
        if review_id in used_ids:
            raise ValueError("review random source produced a duplicate opaque ID")
        used_ids.add(review_id)
        assigned.append((review_id, items[index]))
    return tuple(assigned)

def _write_private_review_mapping(
    review_directory: Path,
    assignments: Iterable[tuple[str, _ReviewCandidate]],
    *,
    commit_sha: str,
    contract_hash: str,
) -> Path:
    """Write the sole private unblinding map with owner-only permissions.

    This file is intentionally placed in private campaign state, separate from the review pack,
    and is never returned as a public receipt or published review sample.
    """

    entries = [
        {
            "reviewId": review_id,
            "storyId": candidate.story_id,
            "sampleId": candidate.sample_id,
            "contentHash": candidate.content_hash,
        }
        for review_id, candidate in assignments
    ]
    path = review_directory / _REVIEW_MAPPING_FILENAME
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as mapping_file:
            mapping_file.write(
                canonical_json(
                    {
                        "version": "alpha_native_review_mapping.v1",
                        "commit": commit_sha,
                        "contractHash": contract_hash,
                        "reviewCount": ALPHA_EXPECTED_REVIEW_COUNT,
                        "entries": entries,
                    }
                )
                + "\n"
            )
    finally:
        # ``fdopen`` owns and closes the descriptor on the normal and error
        # paths. If it failed before ownership transferred, close defensively.
        try:
            os.close(descriptor)
        except OSError:
            pass
    os.chmod(path, 0o600)
    return path

def load_private_review_manifest(mapping_path: Path, *, campaign_root: Path | None = None) -> ReviewPackManifest:
    """Read only the safe review ID/hash bindings from the private map.

    The mapping file itself remains an operator-only unblinding artifact. This
    parser intentionally does not return its story/repeat fields, so callers
    cannot accidentally put them into an external-review receipt.
    """

    if mapping_path.is_symlink() or not mapping_path.is_file() or mapping_path.stat().st_mode & 0o077:
        raise ValueError("private review mapping requires an owner-only regular file")
    try:
        payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("private review mapping is unreadable") from error
    if not isinstance(payload, Mapping) or set(payload) != {
        "version",
        "commit",
        "contractHash",
        "reviewCount",
        "entries",
    }:
        raise ValueError("private review mapping has invalid shape")
    if (
        payload.get("version") != "alpha_native_review_mapping.v1"
        or payload.get("reviewCount") != ALPHA_EXPECTED_REVIEW_COUNT
        or not isinstance(payload.get("entries"), list)
    ):
        raise ValueError("private review mapping has invalid version")
    try:
        commit = validate_commit_sha(payload.get("commit"))
    except (TypeError, ValueError) as error:
        raise ValueError("private review mapping has invalid commit") from error
    contract_hash = payload.get("contractHash")
    if not isinstance(contract_hash, str) or not CONTENT_HASH_PATTERN.fullmatch(contract_hash):
        raise ValueError("private review mapping has invalid contract hash")
    manifests: list[ReviewSampleManifest] = []
    associations = []
    for entry in payload["entries"]:
        if not isinstance(entry, Mapping) or set(entry) != {"reviewId", "storyId", "sampleId", "contentHash"}:
            raise ValueError("private review mapping has invalid entry")
        sample_id = entry.get("sampleId")
        if sample_id not in REVIEW_SAMPLE_KEYS or entry.get("storyId") != sample_id.rsplit("-repeat-", 1)[0]:
            raise ValueError("private review mapping has invalid preselected sample association")
        associations.append(sample_id)
        review_id = entry.get("reviewId")
        content_hash = entry.get("contentHash")
        if not isinstance(review_id, str) or not OPAQUE_REVIEW_ID_PATTERN.fullmatch(review_id):
            raise ValueError("private review mapping has invalid review ID")
        if not isinstance(content_hash, str) or not CONTENT_HASH_PATTERN.fullmatch(content_hash):
            raise ValueError("private review mapping has invalid content hash")
        manifests.append(ReviewSampleManifest(review_id=review_id, content_hash=content_hash))
    if len({item.review_id for item in manifests}) != len(manifests):
        raise ValueError("private review mapping has duplicate review IDs")
    if len(manifests) != ALPHA_EXPECTED_REVIEW_COUNT:
        raise ValueError("private review mapping must contain all three native Alpha samples")
    if len(set(associations)) != len(associations) or set(associations) != set(REVIEW_SAMPLE_KEYS):
        raise ValueError("private review mapping must cover each preselected sample exactly once")
    if campaign_root is not None:
        from .alpha_campaign import load_campaign
        campaign = load_campaign(campaign_root)
        if commit != campaign.source["commit"] or contract_hash != campaign.contract_hash:
            raise ValueError("private review mapping differs from its frozen campaign")
        for entry in payload["entries"]:
            _selected_content(campaign_root, campaign, entry["sampleId"], expected_hash=entry["contentHash"])
    return ReviewPackManifest(
        commit=commit,
        contract_hash=contract_hash,
        samples=tuple(manifests),
    )


def publish_native_review_pack(work_root, review_directory):
    """Publish only the three preselected repeat-one canonical text exports."""
    from .alpha_campaign import campaign_lease, load_campaign
    root = Path(work_root)
    with campaign_lease(root):
        campaign = load_campaign(root)
        checkout = Path(campaign.source["sourceRoot"])
        destination = _prepare_review_directory(Path(review_directory), checkout_root=checkout)
        if destination.is_relative_to(root) or root.is_relative_to(destination):
            raise ValueError("blind review pack must stay separate from private campaign state")
        candidates = []
        for sample_id in REVIEW_SAMPLE_KEYS:
            payload, content_hash = _selected_content(root, campaign, sample_id)
            candidates.append(_ReviewCandidate(story_id=sample_id.rsplit("-repeat-", 1)[0], sample_id=sample_id,
                payload=payload, content_hash=content_hash))
        assignments = _randomized_review_candidates(candidates)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".alpha-review-", dir=destination.parent) as temporary:
            staging = Path(temporary) / "pack"
            staging.mkdir(mode=0o700)
            for review_id, candidate in assignments:
                _write_review_sample(staging, review_id, candidate.payload)
            write_codex_external_review_templates(staging, ((i, c.content_hash) for i, c in assignments),
                commit=campaign.source["commit"], contract_hash=campaign.contract_hash)
            mapping = _write_private_review_mapping(root / "private", assignments,
                commit_sha=campaign.source["commit"], contract_hash=campaign.contract_hash)
            try:
                return _publish_review_directory(staging, destination, (i for i, _ in assignments)), mapping
            except BaseException:
                mapping.unlink()
                raise


def _selected_content(root, campaign, sample_id, *, expected_hash=None):
    """Bind one preselected export to its exact retained sample receipt."""
    from .alpha_receipts import NativeSampleReceipt
    from hashlib import sha256
    outcome = Path(root) / "evidence" / sample_id / "outcome"
    if outcome.is_symlink() or outcome.resolve(strict=True) != outcome:
        raise ValueError("selected native outcome must be a physical directory")
    for name in ("receipt.json", "content.json"):
        if (outcome / name).is_symlink() or not (outcome / name).is_file():
            raise ValueError("selected native content must use regular retained files")
    receipt = NativeSampleReceipt.model_validate_json((outcome / "receipt.json").read_bytes())
    raw = (outcome / "content.json").read_bytes()
    payload = json.loads(raw)
    content_hash = sha256(raw).hexdigest()
    if (receipt.status != "installed" or receipt.sample_id != sample_id
            or receipt.commit != campaign.source["commit"] or receipt.contract_hash != campaign.contract_hash
            or receipt.profile_hash != campaign.source["profileHash"] or content_hash != receipt.content_hash
            or (expected_hash is not None and expected_hash != content_hash)
            or not isinstance(payload, Mapping) or set(payload) != {"storyBible", "storyGraph", "sceneBeats", "storyboard"}
            or raw != (canonical_json(payload) + "\n").encode()):
        raise ValueError("selected native review content/receipt identity differs")
    return payload, content_hash
