"""Preserve reviewed target-use authority through an explicit human handoff."""
from ...exceptions import InvalidTransitionError
from ...source_endorsed_intent import parse_saved_intent
from ..schema import ReviewedShotBindingRow, VisualIntentRow


def authored_intent(payload):
    return parse_saved_intent({key: value for key, value in payload.items() if key != "targetUse"}).model_dump(mode="json", by_alias=True)


def prepare_handoff_intents(session, repository, project_id, observations, frames):
    """Read/validate every source before any handoff authority is written."""
    plans, changed_ids = {}, set()
    for observation, frame in zip(observations, frames, strict=True):
        if getattr(observation.intent, "source_binding_id", None) is not None or getattr(observation.intent, "retained_visual_intent_id", None) is not None:
            raise InvalidTransitionError("handoff author fields cannot select new cross-shot source authority")
        payload = observation.intent.model_dump(mode="json", by_alias=True)
        if "sourceEndorsement" in payload:
            from .handoff_intent_context import assert_source_intent
            try:
                assert_source_intent(session.connection().connection.driver_connection, project_id, payload)
            except (ValueError, TypeError, KeyError) as error:
                raise InvalidTransitionError("source-endorsed intent differs from its exact saved source") from error
            if payload != frame.get("intentContext", {}).get("intent"):
                raise InvalidTransitionError("source-endorsed intent must preserve exact displayed saved context; edits are authored input")
        binding = session.get(ReviewedShotBindingRow, frame["sourceId"]) if frame["origin"] == "human_binding" else None
        intent = session.get(VisualIntentRow, binding.visual_intent_id) if binding else None
        target_use = frame.get("targetUse")
        if binding is not None and not repository._media.admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding):
            raise InvalidTransitionError("displayed reviewed image use is no longer current")
        if target_use is not None and (intent is None or intent.intent.get("targetUse") != target_use):
            raise InvalidTransitionError("displayed cross-shot target use changed")
        unchanged = intent is not None and authored_intent(intent.intent) == payload
        if intent is not None and not unchanged:
            changed_ids.add(intent.id)
        # Ordinary shared imported material retains its existing common stream;
        # explicitly typed uses always have independent target-shot streams.
        key = (frame["assetId"], frame["shotId"] if target_use else None)
        previous = plans.get(key)
        if previous is not None and previous["payload"] != payload:
            raise InvalidTransitionError("ordinary shared material requires one visual intent; explicitly review cross-shot use first")
        plans[key] = {"payload": payload, "existing": intent if unchanged else None,
            "binding": binding, "targetUse": target_use}
    for plan in plans.values():
        use = plan["targetUse"]
        while use is not None:
            source = use["source"]
            if source["visualIntentId"] in changed_ids:
                raise InvalidTransitionError("handoff changes required source intent for a cross-shot frame; review source and target use afresh in the workbench")
            use = session.get(VisualIntentRow, source["visualIntentId"]).intent.get("targetUse")
    return plans


def persist_handoff_intent(repository, project_id, frame, plan):
    existing = plan["existing"]
    if existing is not None:
        return {"id": existing.id, "revision": existing.revision}
    return repository._media.intents.create_visual_intent(project_id, frame["assetId"], plan["payload"],
        target_shot_id=frame["shotId"],
        retained_target_binding_id=plan["binding"].id if plan["targetUse"] else None)
