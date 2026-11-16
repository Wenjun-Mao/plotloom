"""Caller speaker labels and immutable per-job audio reference identities."""
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from .contracts import SourceUrlAssetRequest
from .voice_reference import MAX_VOICE_BYTES, MIN_VOICE_DURATION_MS, MAX_VOICE_DURATION_MS, VOICE_SAMPLE_RATE

REFERENCE_MAX_AUDIOS = 3
REFERENCE_AUDIO_CONTRACT_VERSION = 1
REFERENCE_AUDIO_FORMAT = {"container": "wav", "codec": "pcm_s16le", "channels": 1,
    "sampleRate": VOICE_SAMPLE_RATE, "minDurationMs": MIN_VOICE_DURATION_MS,
    "maxDurationMs": MAX_VOICE_DURATION_MS, "maxBytes": MAX_VOICE_BYTES}


class ReferenceAudioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speaker: str = Field(min_length=1, max_length=128)

    @field_validator("speaker")
    @classmethod
    def validate_speaker(cls, value: str) -> str:
        if value != value.strip() or not value or any(ord(char) < 32 for char in value):
            raise ValueError("speaker must be a nonempty label without surrounding whitespace")
        return value


class ReferenceAudioSource(ReferenceAudioRequest, SourceUrlAssetRequest):
    """Source URLs are transient admission inputs, never frozen metadata."""


class ReferenceAudio(ReferenceAudioRequest):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: StrictInt = Field(ge=1, le=REFERENCE_MAX_AUDIOS)
    audioName: str = Field(min_length=1)
    sourceSha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    preparedSha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sourceSizeBytes: StrictInt = Field(ge=1, le=MAX_VOICE_BYTES)
    durationMs: StrictInt = Field(ge=1000, le=10_000)

    def public(self) -> dict:
        return self.model_dump(exclude={"audioName"})
