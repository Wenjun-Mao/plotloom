"""Ledger-free project-folder video lifecycle composition."""

from __future__ import annotations

from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence
from .media_admission import KeyframeAdmission
from .media_character_references import CharacterReferencePersistence
from .media_image_currentness import ImageJobCurrentness
from .media_same_person_reviews import SamePersonReviewPersistence
from .media_video import VideoJobPersistence
from .media_video_currentness import VideoJobCurrentness
from .media_video_source import VideoSourceTiming
from .media_video_segments import VideoSegmentPersistence


class DirectVideoJobPersistence(VideoJobPersistence):
    """Project-folder lifecycle with no retained Wan ledger dependency.

    Shared media state mechanics remain reusable, but a direct H3 owner has
    no same-transaction pilot-accounting object. A snapshot that tries to use
    the old paid policy therefore fails before it can read or create any Wan
    ledger row.
    """

    def __init__(
        self,
        access: ProjectPersistenceAccess,
        canonical: ProjectCanonicalPersistence,
        admission: KeyframeAdmission,
        references: CharacterReferencePersistence,
        image_currentness: ImageJobCurrentness,
        same_person: SamePersonReviewPersistence,
        currentness: VideoJobCurrentness,
        source_timing: VideoSourceTiming,
        segments: VideoSegmentPersistence,
    ) -> None:
        super().__init__(
            access,
            canonical,
            admission,
            references,
            image_currentness,
            same_person,
            currentness,
            accounting=None,
            source_timing=source_timing,
            segments=segments,
        )
