"""Closed owner-granted QA scopes; project labels and API strings cannot enroll."""
from dataclasses import dataclass

from .delegated_qa_contracts import AgentQaAttribution
from .exceptions import InvalidTransitionError

REVIEWER_PREFIX = "@plotloom:agent-qa:"


@dataclass(frozen=True)
class QaMaterial:
    shot_id: str
    asset_id: str
    original_hash: str


@dataclass(frozen=True)
class DelegatedQaScope:
    id: str
    project_id: str
    storyboard_hash: str
    materials: tuple[QaMaterial, ...]
    profile_id: str
    max_submissions: int | None = None
    max_requested_seconds: int | None = None

    def __post_init__(self):
        for name, minimum in (("max_submissions", 1), ("max_requested_seconds", 5)):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < minimum):
                raise ValueError(f"{name} must be null or an integer >= {minimum}")


# This immutable fixture grant is intentionally narrow. Extending it requires a
# new owner-authorized source decision, not a public enrollment endpoint.
SCOPES = (DelegatedQaScope(
    id="disposable-qa-20261019", project_id="326a5137-1851-4b5c-8ab2-b600ec7bda23",
    storyboard_hash="b4da9c96f5bfa09548446249960605e7a87671936d75e8fbec62ecef73043295",
    materials=(
        QaMaterial("SH01", "4c3cc979-1c8b-4ec0-8f4b-51b5b7162d1e", "663563c08200c9446c64a840a4d8bb3d0229da5c92ebb4bc799db2131209de7d"),
        QaMaterial("SH02", "3cd3e765-367d-4af5-926c-ca9b57425352", "95b940909d5de508d86216a190b0247efe08d6bf606f0ba6c51a0c4a58f26360"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2", max_submissions=2, max_requested_seconds=10,
), DelegatedQaScope(
    id="finished-example-watercolor-20261022", project_id="ad20c897-e263-402d-9333-82de890a6038",
    storyboard_hash="47a58c603db8397dd865243b94e7484dbf5c4a229ba81db310396d68a9090a21",
    materials=(
        QaMaterial("SH01", "945722fd-3a76-4a37-85b5-fdc2fc055d2a", "bf597b2edc2014e1f1abf4f2d66e9babba36921c2dc9ed978f19f0fced9064be"),
        QaMaterial("SH02", "311e94d7-9827-490e-be78-8c4bdec3aa89", "f67b2c4f02397415c7bca38f145bf2d55be45d671f8c7686c8526f1a3c9f4081"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2",
), DelegatedQaScope(
    id="finished-example-cinematic-20261022", project_id="d7deb82f-4801-4c9f-bfa8-9195c3b36489",
    storyboard_hash="1a044bd7d5ddd75ee7ceef384bed8df7d08e08db680daf5aab520d1eaf07d14e",
    materials=(
        QaMaterial("SH01", "50b9db6e-7cf2-460a-91f9-45b4a2d91539", "17edc858aa790890becd87f2eaec55efbd1985e50de758b0ffe9ec47982a022e"),
        QaMaterial("SH02", "1c3953aa-a242-49ba-8c2c-ac1c1e42733b", "7ebfb532b5c2b82090b0f6042198c534454d270a1c59654288f83a1008a670e8"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2",
), DelegatedQaScope(
    id="finished-example-stylized3d-20261022", project_id="21dd0cbd-3ba9-4cfa-927a-88a877b047ea",
    storyboard_hash="daa67ee1d86e5807dc5f0685e5f7e3ed49506ef3904cc8be1c02fb1878df3fa5",
    materials=(
        QaMaterial("SH01", "7944c2e3-3c84-4e05-ab73-3bff66271927", "ce9cfcbf6686b565aeeb0a58f525181065fab76c15befa1cb37fc3abd10c1afa"),
        QaMaterial("SH02", "67013757-6c21-4fd9-96e7-5368948ca8b9", "d31e5dbf98631e9b9c8eef830d83c598f67dbf30ee5646782112141be456a2c4"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2",
),)


def project_scope(project_id):
    return next((scope for scope in SCOPES if scope.project_id == project_id), None)


def require_scope(project_id, attribution):
    parsed = AgentQaAttribution.model_validate(attribution)
    scope = project_scope(project_id)
    if scope is None or parsed.scope_id != scope.id:
        raise InvalidTransitionError("agent QA requires the exact owner-granted disposable project scope")
    return scope


def attribution_for_reviewer(project_id, reviewer):
    if not reviewer.startswith(REVIEWER_PREFIX):
        return None
    value = AgentQaAttribution(scope_id=reviewer.removeprefix(REVIEWER_PREFIX)).model_dump(mode="json", by_alias=True)
    require_scope(project_id, value)
    return value


def reject_reserved_reviewer(reviewer):
    if reviewer.strip().startswith(REVIEWER_PREFIX):
        raise InvalidTransitionError("reserved QA attribution requires a typed owner-granted decision")


def reviewer_for(attribution):
    return REVIEWER_PREFIX + attribution.scope_id


def _observed_qa_attribution(container):
    if not isinstance(container, dict) or "attribution" not in container:
        return None
    actor = container["attribution"]
    if AgentQaAttribution.model_validate(actor).model_dump(mode="json", by_alias=True) != actor:
        raise ValueError("retained QA attribution must be canonical")
    return actor


def direction_attribution(snapshot):
    """Observe QA markers; ordinary invalid shapes stay with the video reader."""
    package = snapshot.get("reviewedDirections") if isinstance(snapshot, dict) else None
    basis = package.get("reviewBasis") if isinstance(package, dict) else None
    return _observed_qa_attribution(basis)


def keyframe_attribution(snapshot):
    frame = snapshot.get("keyframe") if isinstance(snapshot, dict) else None
    intent = frame.get("intent") if isinstance(frame, dict) else None
    return _observed_qa_attribution(intent)


def raw_connection(session):
    return session.connection().connection.driver_connection


def require_qa_write(session, project_id, attribution, *, board_hash=None, asset_id=None, shot_id=None):
    from .domain import StageName
    from .persistence.schema import EntityRevisionRow, ManagedAssetRow, StageHeadRow
    scope = require_scope(project_id, attribution)
    from .project_storage.delegated_qa_grants import require_command_context
    require_command_context(raw_connection(session), scope)
    head = session.query(StageHeadRow).filter_by(project_id=project_id, stage=StageName.STORYBOARD.value).one()
    revision = session.get(EntityRevisionRow, head.entity_revision_id)
    if revision.content_hash != scope.storyboard_hash or board_hash not in {None, scope.storyboard_hash}:
        raise InvalidTransitionError("QA authority does not cover a changed storyboard")
    if asset_id is not None:
        material = next((item for item in scope.materials if item.asset_id == asset_id and item.shot_id == shot_id), None)
        asset = session.get(ManagedAssetRow, asset_id)
        if material is None or asset is None or asset.project_id != project_id or asset.original_hash != material.original_hash:
            raise InvalidTransitionError("QA authority does not cover this material or shot")
    return scope


def binding_attribution(project_id, approval, intent, *, asset_id, shot_id):
    """Portable attribution validation; currentness remains the normal owner's job."""
    actor = attribution_for_reviewer(project_id, approval.reviewer)
    if actor != intent.get("attribution"):
        raise InvalidTransitionError("material decision and storyboard review attribution differ")
    if actor:
        scope = require_scope(project_id, actor)
        if approval.content_hash != scope.storyboard_hash or not any(
                item.asset_id == asset_id and item.shot_id == shot_id for item in scope.materials):
            raise InvalidTransitionError("QA binding exceeds its exact board and material scope")
    return actor
