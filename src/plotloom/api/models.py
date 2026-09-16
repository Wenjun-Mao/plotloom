from __future__ import annotations

import base64
import binascii
from datetime import datetime
import json
from typing import Any, Mapping, Protocol

from fastapi import HTTPException, Request, status

from ..domain import (
    PUBLIC_PROVIDER_SETTING_FIELDS,
    GenerationRun,
    MediaKind,
    MediaPromptContext,
    ProviderAuthMode,
    ProviderSettings,
    ProviderSnapshot,
    validate_public_provider_snapshot,
)
from ..persistence import ApprovalClosure, ApprovalDecision
from ..provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PresetId,
    StageMaxOutputTokens,
    TextProviderCapabilities,
    TextProviderProfileSnapshot,
    V2ExtractionPolicy,
    execution_preset,
)
from ..generation.providers import ProviderAdapter
from ..generation.secrets import SecretLease
from .contracts import (
    ApprovalClosureView as ApprovalClosureView,
    ApprovalDecisionView as ApprovalDecisionView,
    AuthoringDraftDiscardRequest as AuthoringDraftDiscardRequest,
    AuthoringDraftUpsertRequest as AuthoringDraftUpsertRequest,
    CanonicalDraftConsumption as CanonicalDraftConsumption,
    ExactWorkUnitRepairRequest as ExactWorkUnitRepairRequest,
    ImageJobCancellationRequest as ImageJobCancellationRequest,
    LifecycleRequest as LifecycleRequest,
    MediaTaskRequest as MediaTaskRequest,
    PipelineRunRequest as PipelineRunRequest,
    ProjectCreateRequest as ProjectCreateRequest,
    ProjectDuplicateRequest as ProjectDuplicateRequest,
    ProjectFolderImageJobCreateRequest as ProjectFolderImageJobCreateRequest,
    ProjectFolderVisualIntentRequest as ProjectFolderVisualIntentRequest,
    ProjectListResponse as ProjectListResponse,
    ProjectOperationalState as ProjectOperationalState,
    ProjectMediaTasksResponse as ProjectMediaTasksResponse,
    ProjectPatchRequest as ProjectPatchRequest,
    ProjectPermanentDeleteRequest as ProjectPermanentDeleteRequest,
    ProjectRunsResponse as ProjectRunsResponse,
    ProviderSettingsUpdate as ProviderSettingsUpdate,
    RebuildRequest as RebuildRequest,
    StageEnvelopesResponse as StageEnvelopesResponse,
    StagePatchRequest as StagePatchRequest,
    StoryboardApprovalRequest as StoryboardApprovalRequest,
    StoryboardReviewResponse as StoryboardReviewResponse,
    TextBackendReadiness as TextBackendReadiness,
    TextProviderProbeResponse as TextProviderProbeResponse,
    TextProviderProfileActivate as TextProviderProfileActivate,
    TextProviderProfileAvailabilityUpdate as TextProviderProfileAvailabilityUpdate,
    TextProviderProfileCreate as TextProviderProfileCreate,
    TextProviderProfileUpdate as TextProviderProfileUpdate,
    TextProviderProfileView as TextProviderProfileView,
    TextProviderProfilesResponse as TextProviderProfilesResponse,
)


class RunScheduler(Protocol):
    def submit(self, run_id: str, *, session_api_key: str | None = None) -> Any: ...

    def request_cancel(self, run_id: str) -> GenerationRun: ...


class MediaScheduler(Protocol):
    def submit(self, task_id: str, *, session_api_key: str | None = None) -> Any: ...


class MediaPromptCompiler(Protocol):
    def compile(
        self, context: MediaPromptContext, kind: MediaKind
    ) -> tuple[str, dict[str, Any]]: ...


class TextProviderResolver(Protocol):
    def resolve(
        self, provider_snapshot: Mapping[str, Any]
    ) -> tuple[ProviderAdapter, str]: ...


class TextProfileSecretSource(Protocol):
    def server_key_available(self, profile_id: str = "default") -> bool: ...

    def lease_for_profile(
        self,
        profile_id: str,
        *,
        auth_mode: ProviderAuthMode,
    ) -> SecretLease | None: ...


def _session_api_key(request: Request) -> str | None:
    value = (request.headers.get("X-Plotloom-Session-API-Key") or "").strip()
    if len(value) > 4096:
        raise HTTPException(status_code=400, detail="session API key is too long")
    return value or None


def _normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Idempotency-Key must not be blank")
    if len(normalized) > 255:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key must be at most 255 characters"
        )
    return normalized


def _encode_project_cursor(cursor: tuple[datetime, str] | None) -> str | None:
    if cursor is None:
        return None
    created_at, project_id = cursor
    payload = json.dumps(
        {"createdAt": created_at.isoformat(), "id": project_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_project_cursor(value: str | None) -> tuple[datetime, str] | None:
    if value is None:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if set(payload) != {"createdAt", "id"} or not isinstance(payload["id"], str):
            raise ValueError("wrong cursor shape")
        created_at = datetime.fromisoformat(payload["createdAt"])
        if created_at.tzinfo is not None:
            raise ValueError(
                "cursor timestamp must use the database's local UTC representation"
            )
        if not payload["id"]:
            raise ValueError("blank project ID")
        return created_at, payload["id"]
    except (
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid project cursor",
        ) from error


def _submit_with_optional_session_key(
    scheduler: Any, resource_id: str, request: Request
) -> Any:
    session_key = _session_api_key(request)
    if session_key is None:
        return scheduler.submit(resource_id)
    return scheduler.submit(resource_id, session_api_key=session_key)


def _merge_provider_settings(
    persisted: ProviderSettings,
    defaults: ProviderSettings,
    key_availability: Mapping[str, bool],
) -> ProviderSettings:
    if persisted.revision == 0:
        # No row means environment-owned defaults still define the profile.
        values = {
            field: getattr(defaults, field) for field in PUBLIC_PROVIDER_SETTING_FIELDS
        }
    else:
        values = {
            field: getattr(persisted, field)
            if getattr(persisted, field) is not None
            else getattr(defaults, field)
            for field in PUBLIC_PROVIDER_SETTING_FIELDS
        }
    values.update(
        profile_version=persisted.revision,
        revision=persisted.revision,
        updated_at=persisted.updated_at,
        text_key_available=bool(key_availability.get("text_key_available", False)),
        image_key_available=bool(key_availability.get("image_key_available", False)),
        video_key_available=bool(key_availability.get("video_key_available", False)),
    )
    return ProviderSettings.model_validate(values)


def _public_provider_snapshot(settings: ProviderSettings) -> dict[str, Any]:
    snapshot = ProviderSnapshot.model_validate(
        settings.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields),
        )
    )
    return validate_public_provider_snapshot(
        snapshot.model_dump(mode="json", by_alias=True)
    )


def _default_text_profile_snapshot(
    defaults: ProviderSettings,
) -> TextProviderProfileSnapshot:
    """Translate the old runtime defaults into the first V2 named profile."""

    preset = execution_preset(PresetId.COMPATIBLE_V1)
    values: dict[str, Any] = {
        "profile_schema_version": 2,
        "profile_id": DEFAULT_PROVIDER_PROFILE_ID,
        "profile_version": 0,
        "text_provider": defaults.text_provider or "openai-compatible",
        "text_base_url": defaults.text_base_url or "https://api.atlascloud.ai/v1",
        "text_model": defaults.text_model or "deepseek-v3",
        "text_auth_mode": defaults.text_auth_mode.value,
        "text_capabilities": TextProviderCapabilities(
            chat_completions=defaults.text_capabilities.chat_completions,
            json_object=defaults.text_capabilities.json_object,
            json_schema=defaults.text_capabilities.json_schema,
            chat_template_kwargs=False,
        ),
        "text_context_window_tokens": defaults.text_context_window_tokens,
        "text_max_output_tokens": defaults.text_max_output_tokens,
        "text_temperature": defaults.text_temperature,
        "text_max_concurrency": defaults.text_max_concurrency,
        "text_connect_timeout_seconds": defaults.text_connect_timeout_seconds,
        "text_attempt_timeout_seconds": defaults.text_attempt_timeout_seconds,
        "redirect_policy": "no_follow",
        "request_extension": preset.request_extension,
        "reasoning_mode": preset.reasoning_mode,
        "extraction_policy": V2ExtractionPolicy(),
        "stage_max_output_tokens": StageMaxOutputTokens(
            story_bible=min(8192, defaults.text_max_output_tokens),
            story_graph=min(8192, defaults.text_max_output_tokens),
            scene_beats=min(4096, defaults.text_max_output_tokens),
            storyboard=min(4096, defaults.text_max_output_tokens),
        ),
        "max_semantic_corrections": 2,
        "preset_id": PresetId.COMPATIBLE_V1,
        "preset_version": preset.preset_version,
    }
    try:
        return TextProviderProfileSnapshot.model_validate(values)
    except ValueError:
        values["preset_id"] = PresetId.CUSTOM
        return TextProviderProfileSnapshot.model_validate(values)


def _approval_decision_view(decision: ApprovalDecision) -> ApprovalDecisionView:
    return ApprovalDecisionView(
        id=decision.id,
        project_id=decision.project_id,
        entity_revision_id=decision.entity_revision_id,
        subject_type=decision.subject_type,
        subject_id=decision.subject_id,
        subject_revision=decision.subject_revision,
        content_hash=decision.content_hash,
        canonical_input_revisions=dict(decision.canonical_input_revisions),
        gate_set_version=decision.gate_set_version,
        decision=decision.decision,
        reviewer=decision.reviewer,
        note=decision.note,
        created_at=decision.created_at,
    )


def _approval_closure_view(closure: ApprovalClosure) -> ApprovalClosureView:
    return ApprovalClosureView(
        decision=_approval_decision_view(closure.decision),
        active=closure.active,
        stale_reasons=list(closure.stale_reasons),
    )
