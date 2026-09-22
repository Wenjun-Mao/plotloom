"""Asynchronous bridge-intent inference over the existing trusted text adapter."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import closing
from hashlib import sha256
from threading import RLock
from typing import Any, Mapping

from pydantic import ValidationError

from .creative_handoff_exchange import canonical_json
from .domain import ProviderAuthMode
from .exceptions import InvalidTransitionError
from .generation.contracts import GenerationRequest, PromptMessage
from .generation.exceptions import (
    ProviderCapabilityError, ProviderOutcomeUnknownError,
    ProviderRequestNotSentError, ProviderResponseError, ResponseExtractionError,
    SecretLeaseError,
)
from .generation.prompts import PromptRenderer
from .generation.responses import extract_json_response, redact_provider_boundary_evidence
from .pipeline import RunSecretBroker, TextProviderResolver
from .production_bridge_intent_contract import (
    MAX_INTENT_CONTEXT_CHARACTERS, bind_intent_suggestions, intent_response_schema,
)
from .provider_profiles import TextProviderProfileSnapshotV3
from .project_storage.composition import ProjectFolderStorage


PROMPT_ID = "production_bridge_intent"


class ProductionBridgeIntentService:
    """One job executor; durable state and admission remain project-owned."""

    def __init__(
        self, storage: ProjectFolderStorage, *, resolver: TextProviderResolver,
        secrets: RunSecretBroker, max_workers: int = 1,
    ) -> None:
        self.storage, self.resolver, self.secrets = storage, resolver, secrets
        self.renderer = PromptRenderer()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="plotloom-bridge-intent")
        self._lock = RLock()
        self._active: dict[str, Future[None]] = {}

    def create(
        self, project_id: str, *, expected_revision: int, expected_hash: str,
        profile_snapshot: Mapping[str, Any], session_api_key: str | None = None,
    ) -> str:
        snapshot = TextProviderProfileSnapshotV3.model_validate(profile_snapshot)
        with closing(self.storage.projects.open(project_id)) as store:
            context, targets = store.repository.production_bridge_intent.source_context(
                project_id, expected_revision=expected_revision, expected_hash=expected_hash,
            )
            if len(canonical_json({"context": context, "targets": targets})) > MAX_INTENT_CONTEXT_CHARACTERS:
                raise InvalidTransitionError("bridge intent context exceeds the bounded one-package inference limit")
            schema = intent_response_schema([item["id"] for item in targets])
            rendered = self.renderer.render(PROMPT_ID, {
                "source_context": context, "targets": targets, "json_schema": schema,
            })
            job_id = store.repository.production_bridge_intent.enqueue(
                project_id, expected_revision=expected_revision, expected_hash=expected_hash,
                profile_snapshot=snapshot.model_dump(mode="json", by_alias=True),
                prompt_trace=rendered.trace.model_dump(mode="json", by_alias=True),
                prompt_messages=[message.model_dump(mode="json") for message in rendered.messages],
                response_schema=schema,
            )
        self.submit(project_id, job_id, session_api_key=session_api_key)
        return job_id

    def submit(self, project_id: str, job_id: str, *, session_api_key: str | None = None) -> None:
        with self._lock:
            if job_id in self._active:
                return
            with closing(self.storage.projects.open(project_id)) as store:
                data = store.repository.production_bridge_intent.load_job(project_id, job_id)
                if data["status"] != "queued":
                    raise InvalidTransitionError("only a queued bridge inference job may be submitted")
                profile = TextProviderProfileSnapshotV3.model_validate(data["profile"])
            if session_api_key:
                self.secrets.register_run_override(job_id, session_api_key, profile_id=profile.profile_id)
            try:
                future = self._executor.submit(self._execute, project_id, job_id)
            except BaseException:
                self.secrets.release_run(job_id)
                raise
            self._active[job_id] = future
            future.add_done_callback(lambda _done, jid=job_id: self._completed(jid))

    def _completed(self, job_id: str) -> None:
        with self._lock:
            self._active.pop(job_id, None)

    def _execute(self, project_id: str, job_id: str) -> None:
        lease = None
        dispatched = False
        try:
            with closing(self.storage.projects.open(project_id)) as store:
                owner = store.repository.production_bridge_intent
                data = owner.load_job(project_id, job_id)
                if data["status"] != "queued":
                    return
                profile = TextProviderProfileSnapshotV3.model_validate(data["profile"])
                adapter, model = self.resolver.resolve(data["profile"])
                auth_mode = ProviderAuthMode(profile.text_auth_mode)
                lease = self.secrets.lease_for_run(job_id, auth_mode=auth_mode, profile_id=profile.profile_id)
                request_extension, reasoning_mode, extraction_policy = profile.request_contract()
                request = GenerationRequest(
                    messages=tuple(PromptMessage.model_validate(item) for item in data["messages"]),
                    model=model, temperature=profile.text_temperature,
                    max_output_tokens=min(profile.text_max_output_tokens, max(512, len(data["expectedIds"]) * 160)),
                    response_schema=data["schema"] if adapter.capabilities.json_schema else None,
                    response_schema_name="production_bridge_intent_v1" if adapter.capabilities.json_schema else None,
                    metadata={"job_id": job_id, "prompt_hash": data["promptHash"]},
                    request_extension=request_extension, reasoning_mode=reasoning_mode,
                )
                if not owner.mark_dispatched(project_id, job_id):
                    return
                dispatched = True
                response = adapter.generate(request, lease)
                redacted = redact_provider_boundary_evidence(response.raw, secret_lease=lease)
                if not isinstance(redacted, dict):
                    raise ResponseExtractionError("provider evidence is not an object")
                response_hash = sha256(canonical_json(redacted)).hexdigest()
                usage = response.usage.model_dump(mode="json") if response.usage is not None else None
                owner.record_response(
                    project_id, job_id, response_evidence=redacted, response_hash=response_hash,
                    provider_request_id=response.request_id, usage=usage,
                )
                extracted = extract_json_response(response.model_copy(update={"raw": redacted}), policy=extraction_policy)
                suggestions = bind_intent_suggestions(extracted.value, data["expectedIds"])
                excerpts = {entry["id"]: entry["sourceExcerpt"].strip() for entry in owner.expected_entries(project_id, job_id)}
                if any(text.strip() == excerpts[target] for target, text in suggestions.items()):
                    raise ValueError("inferred intent merely repeated a source excerpt")
                owner.finish_success(
                    project_id, job_id, suggestions=suggestions,
                    response_evidence=redacted, response_hash=response_hash,
                    provider_request_id=response.request_id, usage=usage,
                )
        except ProviderOutcomeUnknownError as error:
            self._record_failure(project_id, job_id, "outcome_unknown", error.code, str(error), lease)
        except ProviderRequestNotSentError as error:
            self._record_failure(project_id, job_id, "failed", error.code, str(error), lease)
        except ProviderResponseError as error:
            self._record_failure(project_id, job_id, "failed", error.code, str(error), lease)
        except ProviderCapabilityError as error:
            self._record_failure(project_id, job_id, "failed", "provider.capability", str(error), lease)
        except (ResponseExtractionError, ValidationError, ValueError):
            self._record_failure(project_id, job_id, "failed", "intent.invalid_response", "模型回答未满足完整戏剧意图合同。", lease)
        except SecretLeaseError:
            self._record_failure(project_id, job_id, "failed", "provider.credential_unavailable", "文本配置凭据不可用。", lease)
        except BaseException:
            # Once dispatch intent is committed, an unclassified transport or
            # process error cannot prove that an external call did not happen.
            self._record_failure(
                project_id, job_id,
                "outcome_unknown" if dispatched else "failed",
                "provider.outcome_unknown" if dispatched else "bridge.preflight_failed",
                "模型调用结果不确定；不会自动重试。" if dispatched else "推断准备失败；未发起模型调用。",
                lease,
            )
        finally:
            if lease is not None:
                lease.revoke()
            self.secrets.release_run(job_id)

    def _record_failure(self, project_id: str, job_id: str, status: str, code: str, message: str, lease: Any) -> None:
        safe = redact_provider_boundary_evidence(message, secret_lease=lease)
        with closing(self.storage.projects.open(project_id)) as store:
            store.repository.production_bridge_intent.finish_failure(
                project_id, job_id, status=status, code=code, message=str(safe),
            )

    def inspect(self, project_id: str) -> None:
        """Reconcile a prior-process dispatch, but never disturb this process's worker."""

        with closing(self.storage.projects.open(project_id)) as store:
            latest = store.production_bridge_state().intent_job
            if latest is not None and latest.status == "dispatched":
                with self._lock:
                    active = latest.id in self._active
                if not active:
                    store.repository.production_bridge_intent.reconcile_dispatched(project_id)

    def cancel(self, project_id: str, job_id: str) -> None:
        with closing(self.storage.projects.open(project_id)) as store:
            store.repository.production_bridge_intent.cancel(project_id, job_id)

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)
