"""One bounded reconciliation step; durable checkpoints own all continuation."""
from sqlalchemy import select

from .autopilot_contracts import CheckpointEvidence, CommandAuthority, OperationScope, POLICY_VERSION
from .autopilot_launch import assert_frozen_execution, assert_frozen_pins, require_job_capacity
from .autopilot_exec import cancel_codex_exec, reconcile_codex_exec
from .autopilot_text_stages import TEXT_STAGES, adopt_brief_source, prepare_text, native_checkpoint_evidence, adopt_text
from .creative_commands import CREATIVE_METHODS, read_creative_delivery, send_creative_candidate, current_creative_candidate
from .exceptions import InvalidTransitionError
from .image_job_contracts import ImageJobError
from .domain import StageName
from .native_bridge_intent_service import NativeBridgeIntentService
from .native_bridge_presentation_service import NativeBridgePresentationService
from .persistence.schema import ProductionBridgeRevisionRow, AutopilotCheckpointRow
from .production_bridge_contracts import ProductionBridgeAcceptRequest


class AutopilotTextController:
    def __init__(self, storage, registry):
        self.storage, self.registry = storage, registry
        self.bridge_services = {"bridge-intent": NativeBridgeIntentService(storage, registry),
            "bridge-presentation": NativeBridgePresentationService(storage, registry)}

    @staticmethod
    def checkpoint(view, key):
        return next((item for item in view.checkpoints if item["operationKey"] == key), None)

    @staticmethod
    def command(store, view, claim, scope):
        return store.repository.autopilot_command(CommandAuthority(view.id, claim, scope))

    def advance(self, store, view, claim):
        """Returns True only when text/installation are completely adopted."""
        if view.state not in {"running", "waiting"}:
            self.reconcile_inactive(store, view, claim)
            return False
        assert_frozen_execution(store, self.registry, view.policy)
        self.settle_delivered(view)
        if self.checkpoint(view, "source") is None:
            with self.command(store, view, claim, OperationScope.SOURCE):
                adopt_brief_source(store)
                store.repository.autopilot.progress("outline")
            return False
        for stage in TEXT_STAGES:
            checkpoint = self.checkpoint(view, stage)
            if checkpoint is None:
                require_job_capacity(view)
                with self.command(store, view, claim, OperationScope.TEXT):
                    request = prepare_text(store, stage, view.policy)
                    evidence = native_checkpoint_evidence(store, request)
                    if evidence.execution_pin != view.policy.execution_pins[stage]:
                        raise InvalidTransitionError("prepared native pin differs from launch")
                    store.repository.autopilot.checkpoint(stage, state="prepared", evidence=evidence)
                    store.repository.autopilot.progress(stage)
                # Export is idempotent by original identity, outside SQLite.
                self.publish_prepared_package(store, view, request, evidence.execution_pin)
                return False
            if checkpoint["state"] != "adopted":
                self.native_step(store, view, claim, stage, checkpoint)
                return False
        if self.checkpoint(view, "bridge.prepare") is None:
            with self.command(store, view, claim, OperationScope.INSTALL):
                state = store.production_bridge_state()
                if state.preparation.status != "available":
                    raise InvalidTransitionError(state.preparation.reason)
                proposal = store.prepare_production_bridge(state.preparation.request).proposal
                with store.repository._read() as session:
                    row = session.scalar(select(ProductionBridgeRevisionRow).where(
                        ProductionBridgeRevisionRow.project_id == view.project_id, ProductionBridgeRevisionRow.revision == proposal.revision))
                    store.repository.autopilot.checkpoint("bridge.prepare", state="adopted",
                        evidence=CheckpointEvidence(owner="bridge-proposal", subject_id=row.id, result={"contentHash": row.content_hash}))
                store.repository.autopilot.progress("bridge-intent")
            return False
        for stage, service in self.bridge_services.items():
            checkpoint = self.checkpoint(view, stage)
            if checkpoint is None:
                require_job_capacity(view)
                with self.command(store, view, claim, OperationScope.INSTALL):
                    proposal = store.production_bridge_state().proposal
                    job = service.prepare_in_store(store, expected_revision=proposal.revision, expected_hash=proposal.content_hash)
                    request, _data = service._request(store, view.project_id, job)
                    evidence = native_checkpoint_evidence(store, request)
                    if evidence.execution_pin != view.policy.execution_pins[stage]:
                        raise InvalidTransitionError("bridge native pin differs from launch")
                    store.repository.autopilot.checkpoint(stage, state="prepared", evidence=evidence)
                    store.repository.autopilot.progress(stage)
                self.publish_prepared_package(store, view, request, evidence.execution_pin)
                return False
            if checkpoint["state"] != "adopted":
                self.native_step(store, view, claim, stage, checkpoint)
                return False
        if self.checkpoint(view, "installation") is None:
            with self.command(store, view, claim, OperationScope.INSTALL):
                proposal = store.production_bridge_state().proposal
                installed = store.accept_production_bridge(ProductionBridgeAcceptRequest(
                    expected_proposal_revision=proposal.revision, expected_content_hash=proposal.content_hash))
                if installed.installation is None or installed.installation.status != "current":
                    raise InvalidTransitionError("installed canonical bundle is not current")
                head = store.authoring.get_stage_head(view.project_id, StageName.STORYBOARD)
                checkpoint = store.repository.autopilot.checkpoint("installation", state="adopted",
                    evidence=CheckpointEvidence(owner="installation", subject_id=head.entity_revision_id,
                        result={"revision": head.revision, "contentHash": head.content_hash, "admissionId": installed.installation.admission_id}))
                store.repository.autopilot.decide(checkpoint, subject={"revision": head.revision, "contentHash": head.content_hash},
                    rationale="完整来源、分支、AI 戏剧意图与呈现建议通过当前规范门槛后安装；没有人类审阅声明。")
                store.repository.autopilot.progress("references")
            return False
        return True

    def native_step(self, store, view, claim, stage, checkpoint):
        evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
        bridge = stage in self.bridge_services
        service = self.bridge_services.get(stage)
        if view.policy.version == POLICY_VERSION:
            self.codex_exec_step(store, view, claim, stage, checkpoint, evidence, bridge=bridge, service=service)
            return
        if checkpoint["state"] == "delivered":
            self.adopt_delivered(store, view, claim, stage, checkpoint, evidence)
            return
        # Always inspect the original job before considering a never-sent call.
        with self.command(store, view, claim, OperationScope.EVIDENCE):
            request = (service._request(store, view.project_id, evidence.job_id)[0] if bridge else
                store.repository.creative_terminal.run_request(view.project_id, stage, evidence.job_id))
        transport = self.registry.status(evidence.job_id)
        if checkpoint["state"] == "prepared" and transport["state"] == "prepared":
            # Exact durable preparation and absent native attempt permit only
            # the original request's atomic initial publication.
            store.creative_handoff_exchange().write_package(request, evidence.execution_pin)
        delivery = self.validated_delivery(store, view, stage, request)
        if delivery is not None:
            self.registry.assert_creative_task_identity(evidence.job_id, project_id=view.project_id, stage=stage)
            with self.command(store, view, claim, OperationScope.INSTALL if bridge else OperationScope.EVIDENCE):
                if bridge:
                    service._admit(store, request, delivery)
                else:
                    getattr(store, CREATIVE_METHODS[stage][2])(delivery)
                store.repository.autopilot.checkpoint(stage, state="delivered", expected_revision=checkpoint["revision"],
                    evidence=evidence.model_copy(update={"delivery_hash": delivery.manifest_hash}))
            if view.policy.version != POLICY_VERSION:
                self.registry.complete_creative_task(evidence.job_id, project_id=view.project_id, stage=stage)
            return
        if checkpoint["state"] == "prepared" and transport["state"] == "prepared":
            def before_send():
                with self.command(store, view, claim, OperationScope.INSTALL if bridge else OperationScope.TEXT):
                    assert_frozen_pins(store, view.policy)
                    if not bridge and current_creative_candidate(store, stage, evidence.job_id, require_fresh=True).status != "prepared":
                        raise InvalidTransitionError("native candidate changed before dispatch admission")
                    if bridge and not store.repository.production_bridge_intent.mark_dispatched(view.project_id, evidence.job_id):
                        raise InvalidTransitionError("bridge proposal changed before dispatch")
                    store.repository.autopilot.checkpoint(stage, state="sent", expected_revision=checkpoint["revision"],
                        evidence=evidence.model_copy(update={"result": evidence.result | {"dispatchAttempted": True}}))
            if bridge:
                service.send_in_store(store, evidence.job_id, before_send=before_send, expected_task_id=view.policy.specialist_bindings["text"], expected_bindings=view.policy.specialist_bindings)
            else:
                send_creative_candidate(store, self.registry, stage, evidence.job_id, before_send=before_send, expected_task_id=view.policy.specialist_bindings["text"], expected_bindings=view.policy.specialist_bindings)
            return
        if transport["state"] == "prepared":
            # A sent checkpoint with no retained receipt is uncertainty, never
            # proof of non-submission. It cannot re-enter the send path.
            target = "outcome_unknown"
        else:
            target = "outcome_unknown" if transport["state"] == "outcome_unknown" else "sent"
        if checkpoint["state"] == "outcome_unknown":
            target = "outcome_unknown"
        if checkpoint["state"] != target:
            with self.command(store, view, claim, OperationScope.EVIDENCE):
                facts = evidence.result | {"dispatchAttempted": True}
                if target == "outcome_unknown":
                    facts["dispatchOutcomeUnknown"] = True
                store.repository.autopilot.checkpoint(stage, state=target, expected_revision=checkpoint["revision"], evidence=evidence.model_copy(update={"result": facts}))

    @staticmethod
    def publish_prepared_package(store, view, request, execution_pin):
        """Publish the package format selected by the frozen executor contract."""
        exchange = store.creative_handoff_exchange()
        if view.policy.version == POLICY_VERSION:
            return exchange.write_package(request, execution_pin, executor_backend="codex_exec")
        return exchange.write_package(request, execution_pin)

    def codex_exec_step(self, store, view, claim, stage, checkpoint, evidence, *, bridge, service):
        if checkpoint["state"] == "delivered":
            self.adopt_delivered(store, view, claim, stage, checkpoint, evidence)
            return
        with self.command(store, view, claim, OperationScope.EVIDENCE):
            request = (service._request(store, view.project_id, evidence.job_id)[0] if bridge else
                store.repository.creative_terminal.run_request(view.project_id, stage, evidence.job_id))
        paths = store.creative_handoff_exchange().write_package(
            request, evidence.execution_pin, executor_backend="codex_exec"
        )
        def before_spawn():
            # The earlier controller gate can be separated from host admission
            # by package hashing and durable reservation. Recheck the exact
            # policy and stage owner immediately before committing spawn intent.
            assert_frozen_execution(store, self.registry, view.policy)
            if not bridge:
                candidate = current_creative_candidate(
                    store, stage, evidence.job_id, require_fresh=True
                )
                if candidate.status != "prepared":
                    raise InvalidTransitionError("creative candidate changed before Codex Exec admission")
            if bridge and not store.repository.production_bridge_intent.mark_dispatched(
                view.project_id, evidence.job_id
            ):
                raise InvalidTransitionError("bridge proposal changed before Codex Exec admission")

        attempt, _receipt, _profile = reconcile_codex_exec(
            store, self.registry, view, claim, checkpoint,
            domain="text", package_path=paths["packagePath"], command_factory=self.command,
            before_spawn=before_spawn,
            operation_scope=OperationScope.INSTALL if bridge else OperationScope.TEXT,
        )
        if attempt.state in {"failed", "settled"} and attempt.terminal_result in {"failure", "not_started"}:
            raise InvalidTransitionError("Codex Exec text attempt reached a terminal failure; preserve this attempt for review.")
        if attempt.state == "outcome_unknown":
            raise ImageJobError("codex_exec_outcome_unknown", "Codex Exec outcome is being reconciled; do not send another attempt.")
        if attempt.state == "cancel_requested":
            return
        current = store.repository.autopilot.current(view.project_id)
        current_checkpoint = self.checkpoint(current, stage)
        current_evidence = CheckpointEvidence.model_validate(current_checkpoint["evidence"])
        delivery = self.validated_delivery(store, view, stage, request)
        if delivery is None:
            return
        with self.command(store, view, claim, OperationScope.INSTALL if bridge else OperationScope.EVIDENCE):
            if bridge:
                service._admit(store, request, delivery)
            else:
                getattr(store, CREATIVE_METHODS[stage][2])(delivery)
            store.repository.autopilot.checkpoint(stage, state="delivered",
                expected_revision=current_checkpoint["revision"],
                evidence=current_evidence.model_copy(update={"delivery_hash": delivery.manifest_hash}))

    def adopt_delivered(self, store, view, claim, stage, checkpoint, evidence):
        bridge = stage in self.bridge_services
        with self.command(store, view, claim, OperationScope.EVIDENCE):
            request = (self.bridge_services[stage]._request(store, view.project_id, evidence.job_id)[0] if bridge else
                store.repository.creative_terminal.run_request(view.project_id, stage, evidence.job_id))
        delivery = self.validated_delivery(store, view, stage, request, expected_hash=evidence.delivery_hash)
        if delivery is None:
            raise InvalidTransitionError("retained native delivery is unavailable")
        with self.command(store, view, claim, OperationScope.INSTALL if bridge else OperationScope.TEXT):
            if bridge:
                service = self.bridge_services[stage]
                request, data = service._request(store, view.project_id, evidence.job_id)
                if data["status"] != "ready":
                    service._admit(store, request, delivery)
                proposal = store.production_bridge_state().proposal
                with store.repository._read() as session:
                    row = session.get(AutopilotCheckpointRow, checkpoint["id"])
                decision = store.repository.autopilot.decide(row,
                    subject={"proposalRevision": proposal.revision, "proposalHash": proposal.content_hash},
                    rationale="采用同一冻结原生建议的完整第一稿；人类意图/呈现审阅仍待最终素材包确认。")
                command = (store.repository.production_bridge.adopt_machine_intent if stage == "bridge-intent"
                    else store.repository.production_bridge.adopt_machine_presentation)
                result = command(view.project_id, decision_id=decision, expected_revision=proposal.revision, expected_hash=proposal.content_hash).proposal
                result_facts = {"revision": result.revision, "contentHash": result.content_hash}
            else:
                candidate = getattr(store, CREATIVE_METHODS[stage][0])().candidate
                if candidate is None or candidate.job_id != evidence.job_id:
                    raise InvalidTransitionError("retained native candidate is no longer current")
                if candidate.status == "prepared":
                    getattr(store, CREATIVE_METHODS[stage][2])(delivery)
                result_facts = adopt_text(store, stage, evidence.job_id)
            recorded = store.repository.autopilot.checkpoint(stage, state="adopted", expected_revision=checkpoint["revision"],
                evidence=evidence.model_copy(update={"result": evidence.result | result_facts}))
            if not bridge:
                store.repository.autopilot.decide(recorded, subject=result_facts, rationale="通过当前来源/完整性门槛后采用冻结原生第一稿；待最终人类素材审阅。")
            store.repository.autopilot.progress(stage)

    def settle_delivered(self, view):
        if view.policy.version == POLICY_VERSION:
            return
        for checkpoint in view.checkpoints:
            evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
            if evidence.job_id and evidence.owner in {*TEXT_STAGES, *self.bridge_services} and checkpoint["state"] in {"delivered", "adopted"}:
                if self.registry.status(evidence.job_id)["state"] != "completed":
                    self.registry.complete_creative_task(evidence.job_id, project_id=view.project_id, stage=evidence.owner)

    def cancel_pending(self, store, view):
        methods = {"outline": store.cancel_outline_candidate, "branches": store.cancel_branch_candidate,
            "characters": store.cancel_cast_candidate, "art": store.cancel_art_candidate,
            "script": store.cancel_script_candidate, "storyboard": store.cancel_storyboard_review_candidate}
        for checkpoint in view.checkpoints:
            evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
            if not evidence.job_id or checkpoint["state"] == "adopted":
                continue
            if evidence.executor_attempt_id is not None:
                cancel_codex_exec(store, self.registry, view.id, checkpoint)
                if evidence.owner in self.bridge_services:
                    store.repository.production_bridge_intent.cancel(view.project_id, evidence.job_id)
                elif evidence.owner in methods:
                    methods[evidence.owner](evidence.job_id)
                continue
            if evidence.owner in self.bridge_services:
                store.repository.production_bridge_intent.cancel(view.project_id, evidence.job_id)
            elif evidence.owner in methods:
                methods[evidence.owner](evidence.job_id)

    def reconcile_inactive(self, store, view, claim):
        self.settle_delivered(view)
        if view.policy.version == POLICY_VERSION:
            self.reconcile_codex_inactive(store, view, claim)
            return
        for checkpoint in view.checkpoints:
            evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
            if not evidence.job_id or evidence.owner not in {*TEXT_STAGES, *self.bridge_services} or checkpoint["state"] in {"delivered", "adopted"}:
                continue
            if self.registry.status(evidence.job_id)["state"] == "prepared":
                continue
            with self.command(store, view, claim, OperationScope.EVIDENCE):
                service = self.bridge_services.get(evidence.owner)
                request = (service._request(store, view.project_id, evidence.job_id)[0] if service else
                    store.repository.creative_terminal.run_request(view.project_id, evidence.owner, evidence.job_id))
                delivery = self.validated_delivery(store, view, evidence.owner, request)
                if delivery is None:
                    continue
                self.registry.assert_creative_task_identity(evidence.job_id, project_id=view.project_id, stage=evidence.owner)
                if service:
                    owner = store.repository.production_bridge_intent
                    if view.state in {"paused", "blocked"}:
                        owner.record_response(view.project_id, evidence.job_id,
                            response_evidence={"manifest": delivery.manifest.model_dump(mode="json", by_alias=True), "manifestHash": delivery.manifest_hash},
                            response_hash=delivery.manifest.candidate.sha256, provider_request_id=None, usage=None)
                    else:
                        # Stopped/taken-over work retains terminal bytes without
                        # allowing the original proposal to advance.
                        owner.cancel(view.project_id, evidence.job_id)
                        service._admit(store, request, delivery)
                else:
                    store.repository.creative_terminal.retain_run_receipt(view.project_id, delivery)
                store.repository.autopilot.checkpoint(checkpoint["operationKey"], state="delivered", expected_revision=checkpoint["revision"],
                    evidence=evidence.model_copy(update={"delivery_hash": delivery.manifest_hash}))
            if view.policy.version != POLICY_VERSION:
                self.registry.complete_creative_task(evidence.job_id, project_id=view.project_id, stage=evidence.owner)

    def reconcile_codex_inactive(self, store, view, claim):
        for checkpoint in view.checkpoints:
            evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
            if (not evidence.job_id or evidence.owner not in {*TEXT_STAGES, *self.bridge_services}
                    or checkpoint["state"] in {"delivered", "adopted"}
                    or evidence.executor_attempt_id is None):
                continue
            bridge = evidence.owner in self.bridge_services
            service = self.bridge_services.get(evidence.owner)
            with self.command(store, view, claim, OperationScope.EVIDENCE):
                request = (service._request(store, view.project_id, evidence.job_id)[0] if bridge else
                    store.repository.creative_terminal.run_request(view.project_id, evidence.owner, evidence.job_id))
            paths = store.creative_handoff_exchange().write_package(
                request, evidence.execution_pin, executor_backend="codex_exec"
            )
            attempt, _receipt, _profile = reconcile_codex_exec(
                store, self.registry, view, claim, checkpoint,
                domain="text", package_path=paths["packagePath"], command_factory=self.command,
                allow_admission=False,
            )
            if attempt is None or attempt.state not in {"completed", "settled"}:
                continue
            delivery = self.validated_delivery(store, view, evidence.owner, request)
            if delivery is None:
                continue
            current = store.repository.autopilot.current(view.project_id)
            current_checkpoint = self.checkpoint(current, evidence.owner)
            current_evidence = CheckpointEvidence.model_validate(current_checkpoint["evidence"])
            with self.command(store, view, claim, OperationScope.EVIDENCE):
                if service:
                    owner = store.repository.production_bridge_intent
                    if view.state in {"paused", "blocked"}:
                        owner.record_response(view.project_id, evidence.job_id,
                            response_evidence={"manifest": delivery.manifest.model_dump(mode="json", by_alias=True),
                                "manifestHash": delivery.manifest_hash},
                            response_hash=delivery.manifest.candidate.sha256, provider_request_id=None, usage=None)
                    else:
                        owner.cancel(view.project_id, evidence.job_id)
                        service._admit(store, request, delivery)
                else:
                    store.repository.creative_terminal.retain_run_receipt(view.project_id, delivery)
                store.repository.autopilot.checkpoint(evidence.owner, state="delivered",
                    expected_revision=current_checkpoint["revision"],
                    evidence=current_evidence.model_copy(update={"delivery_hash": delivery.manifest_hash}))

    def validated_delivery(self, store, view, stage, request, *, expected_hash=None):
        """All receipt/adoption states share the launch execution boundary."""
        service = self.bridge_services.get(stage)
        if view.policy.version == POLICY_VERSION:
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(view.id, stage)
            if attempt is None or attempt.state not in {"completed", "settled"} or receipt is None:
                return None
            profile = self.registry.codex_exec_profile()
            delivery = store.creative_handoff_exchange().read_delivery(
                request, view.policy.execution_pins[stage], executor_backend="codex_exec",
                executor_attempt=attempt, executor_profile=profile, executor_receipt=receipt,
            )
        else:
            delivery = service._delivery(store, request) if service else read_creative_delivery(store, request)
        if delivery is not None:
            if delivery.manifest.executor_provenance.code_revision != view.policy.code_revision:
                raise InvalidTransitionError("native delivery code revision differs from launch")
            if expected_hash is not None and delivery.manifest_hash != expected_hash:
                raise InvalidTransitionError("retained native receipt differs from checkpoint evidence")
        return delivery
