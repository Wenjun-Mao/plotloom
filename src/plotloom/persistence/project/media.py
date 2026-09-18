"""Typed composition root for focused project-media persistence owners."""

from __future__ import annotations

from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .cast import ProjectCastPersistence
from .drafts import ProjectDraftPersistence
from .media_admission import KeyframeAdmission
from .media_assets import ManagedAssetPersistence
from .media_character_references import CharacterReferencePersistence
from .media_image_currentness import ImageJobCurrentness
from .media_image_delivery import ImageJobDeliveryPersistence
from .media_image_preparation import ImageJobPreparationPersistence
from .media_keyframes import ReviewedKeyframePersistence
from .media_reference_proposals import CharacterReferenceProposalPersistence
from .media_art_reference_proposals import ArtReferenceProposalPersistence
from .media_same_person_reviews import SamePersonReviewPersistence
from .media_tasks import GenericMediaTaskPersistence
from .media_direct_video import DirectVideoJobPersistence
from .media_video import VideoJobPersistence, VideoPilotAccountingPort
from .media_video_currentness import VideoJobCurrentness
from .media_visual_intents import VisualIntentPersistence


class ProjectMediaPersistence:
    """Create the fixed, typed media owners consumed by the legacy facade."""

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        drafts: ProjectDraftPersistence,
        cast: ProjectCastPersistence,
        accounting: VideoPilotAccountingPort | None,
    ) -> None:
        admission = KeyframeAdmission(access)
        references = CharacterReferencePersistence(access, canonical, cast)
        image_currentness = ImageJobCurrentness(access, canonical, admission, references)
        same_person = SamePersonReviewPersistence(access, canonical, admission, references)
        video_currentness = VideoJobCurrentness(
            access, canonical, admission, references, same_person
        )
        self.assets: ManagedAssetPersistence = ManagedAssetPersistence(access, admission)
        self.intents: VisualIntentPersistence = VisualIntentPersistence(access, drafts)
        self.admission: KeyframeAdmission = admission
        self.keyframes: ReviewedKeyframePersistence = ReviewedKeyframePersistence(
            access, canonical, admission, image_currentness, same_person
        )
        self.video: VideoJobPersistence = VideoJobPersistence(
            access,
            canonical,
            admission,
            references,
            image_currentness,
            same_person,
            video_currentness,
            accounting,
        )
        self.direct_video: DirectVideoJobPersistence = DirectVideoJobPersistence(
            access,
            canonical,
            admission,
            references,
            image_currentness,
            same_person,
            video_currentness,
        )
        self.references: CharacterReferencePersistence = references
        self.proposals: CharacterReferenceProposalPersistence = (
            CharacterReferenceProposalPersistence(access, canonical, references)
        )
        self.art_references: ArtReferenceProposalPersistence = ArtReferenceProposalPersistence(access)
        self.same_person: SamePersonReviewPersistence = same_person
        self.video_currentness: VideoJobCurrentness = video_currentness
        self.image_currentness: ImageJobCurrentness = image_currentness
        self.image_preparation: ImageJobPreparationPersistence = (
            ImageJobPreparationPersistence(
                access, canonical, drafts, admission, references, image_currentness
            )
        )
        self.image_delivery: ImageJobDeliveryPersistence = ImageJobDeliveryPersistence(
            access, image_currentness
        )
        self.tasks: GenericMediaTaskPersistence = GenericMediaTaskPersistence(access, canonical)
