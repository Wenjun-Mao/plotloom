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


@dataclass(frozen=True)
class QaReference:
    owner: str
    subject_id: str
    decision_id: str
    assets: tuple[tuple[str, str], ...]


@dataclass(frozen=True, kw_only=True)
class NativeMaterialQaScope(DelegatedQaScope):
    """One native review bundle, never an extension of a manual-image grant."""
    run_id: str
    bundle_hash: str
    material_closure: str
    references: tuple[QaReference, ...]


def require_native_bundle(scope, bundle, bundle_hash):
    from .persistence.codec import stable_hash
    if not isinstance(scope, NativeMaterialQaScope):
        raise InvalidTransitionError("QA material handoff requires an exact native-bundle grant")
    references = tuple(QaReference(item["owner"], item["subjectId"], item["decisionId"],
        tuple((asset["assetId"], asset["originalHash"]) for asset in item["assets"])) for item in bundle["references"])
    frames = tuple(QaMaterial(item["shotId"], item["assetId"], item["originalHash"]) for item in bundle["frames"])
    if (bundle_hash != scope.bundle_hash or stable_hash(bundle) != scope.bundle_hash
            or bundle["runId"] != scope.run_id or bundle["materialClosure"] != scope.material_closure
            or bundle["inventory"]["storyboardHash"] != scope.storyboard_hash
            or references != scope.references or frames != scope.materials):
        raise InvalidTransitionError("QA authority does not cover this exact native material bundle")
    return scope


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
), NativeMaterialQaScope(
    id="creator-completion-native-20261022", project_id="6e70451f-e9fd-4460-a475-bce50fde6503",
    storyboard_hash="017604f92aa0d0da9584c4016a7fa525c8841652767e4899d9cf135613594c3b",
    materials=(
        QaMaterial("node-1d6a9231-4f81-56ad-b1ff-3ac5fd6a1506-s1-c1", "c236a80b-2761-4c6c-93f6-cea6198b5672", "81ae4a781e8cd641854116a9ef3467b48f859e0452dbf4ff2a8a7940a027c6b4"),
        QaMaterial("node-fa93ce6c-bdef-53d2-b195-481f304258db-s1-c1", "2f27377a-eb96-418c-869c-6150e57a1204", "42eadbc693e96460aeee4d921fd87673c23747bb743097487f1e07b0ab9653da"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2",
    run_id="faa941da-f566-4b8c-8b79-758664a8d060",
    bundle_hash="8d3859e258c5c98d0240138d2f0fa0b042547a402ba222ec15606f16f088ad0d",
    material_closure="cb0f5586bd2c3697b163c781992074622adb3e19762fea88d4942640f471286d",
    references=(
        QaReference("character-reference", "C01", "1a7aa52e-c957-481e-9f99-01357d994478", (
            ("989d49b3-ed96-4fcd-9c61-5aa20480588e", "331be0786aba2c32288597c41e717dfb4b4756beaa0d8cec20ea8a88315ad91c"),)),
        QaReference("art-reference", "S01", "8322f9b9-bb19-486c-b42c-8b61c983f067", (
            ("7fe5590f-974f-4dcf-bbc1-dd12d3e9fb62", "20d7e2e20e280c070334bb5a6afcfb209cddfa7c2fba110075564fdae6c9d218"),)),
        QaReference("art-reference", "S02", "50bf5362-134a-44fd-9070-e3ae6e664607", (
            ("53777940-da8f-4f6b-ac4d-083346cfed6a", "11c853f92e09715c30c8e5de6fcdef3845d44ff25d3cce83a99fb79f14bc3a6e"),)),
    ),
), DelegatedQaScope(
    id="playable-example-watercolor-20261022", project_id="7304da14-c3aa-40aa-9b5b-236d6979ac25",
    storyboard_hash="db1e06c758cd35b6fc5b31c64e247e2e8dcd81e3410e28607bf3e721f1098858",
    materials=(
        QaMaterial("SH01", "e6768a75-cbc3-468b-b9cc-a9af541004ff", "bf597b2edc2014e1f1abf4f2d66e9babba36921c2dc9ed978f19f0fced9064be"),
        QaMaterial("SH02", "90ab0914-27ac-461e-9e50-ad5dbf9685fc", "f67b2c4f02397415c7bca38f145bf2d55be45d671f8c7686c8526f1a3c9f4081"),
        QaMaterial("SH03", "1ba4e87a-9a55-479a-9769-9978b3d2ac7e", "ba5af56db0b1c639414109bd02cd91e52c4029f916dae74014e084825cb4e315"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2", max_submissions=None, max_requested_seconds=None,
), DelegatedQaScope(
    id="playable-example-cinematic-20261022", project_id="7690e55d-3f08-4056-8f7b-8455814c4928",
    storyboard_hash="d7f332d31144e20fa3623794360ab76187c418997ca866ab96776552ea419536",
    materials=(
        QaMaterial("SH01", "bc7a9965-db5b-4fc9-ab9c-5903f41fcc27", "17edc858aa790890becd87f2eaec55efbd1985e50de758b0ffe9ec47982a022e"),
        QaMaterial("SH02", "9482a310-e1c6-4de7-9717-2f78948e0985", "7ebfb532b5c2b82090b0f6042198c534454d270a1c59654288f83a1008a670e8"),
        QaMaterial("SH03", "d651393d-3a0e-444e-abcb-b5805569ddf7", "1ff62ad7f5889057509963c6dbd8c33a702667f9b79d9ef04648870792c27a06"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2", max_submissions=None, max_requested_seconds=None,
), DelegatedQaScope(
    id="playable-example-stylized3d-20261022", project_id="02a9c60d-9b37-46fd-9446-806cb0aa8a1f",
    storyboard_hash="1a44ab0d29d1aec108dd1899e774e75f28a099e59d01a3ba7fb9a5d99be8c848",
    materials=(
        QaMaterial("SH01", "f1a8a840-3886-41f7-a7e6-a32977d7a0da", "ce9cfcbf6686b565aeeb0a58f525181065fab76c15befa1cb37fc3abd10c1afa"),
        QaMaterial("SH02", "8a3a5750-77b5-4af3-8a60-028e94bc5782", "d31e5dbf98631e9b9c8eef830d83c598f67dbf30ee5646782112141be456a2c4"),
        QaMaterial("SH03", "525a22ea-8baf-4283-9f1c-f66b45d7484c", "06b4c30185600b3cd29bca17c812113400067f8272e6c7cd423885890ba2e9fb"),
    ), profile_id="minimax_h3_quality8_portrait_576x1024_v2", max_submissions=None, max_requested_seconds=None,
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
    if isinstance(scope, NativeMaterialQaScope) and session.info.get("native_qa_handoff_bundle") != scope.bundle_hash:
        from .persistence.project.autopilot_closure import material_closure
        from .persistence.schema import AutopilotRunRow, AutopilotHandoffRow
        from .persistence.codec import stable_hash
        run = session.get(AutopilotRunRow, scope.run_id)
        pointer = run.handoff if run is not None else None
        receipt = session.get(AutopilotHandoffRow, pointer["receiptId"]) if isinstance(pointer, dict) else None
        if (run is None or run.project_id != project_id or run.state != "handed_off" or receipt is None
                or receipt.run_id != scope.run_id or receipt.receipt.get("bundleHash") != scope.bundle_hash
                or receipt.receipt_hash != stable_hash(receipt.receipt) or receipt.receipt_hash != pointer.get("receiptHash")
                or receipt.receipt.get("materialClosure") != material_closure(session, project_id)):
            raise InvalidTransitionError("QA authority requires its exact current native material handoff")
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
