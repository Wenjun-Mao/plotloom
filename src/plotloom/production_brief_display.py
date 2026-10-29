"""Explicit current-DTO display projection; unknown requirements fail visibly."""
from .production_brief_labels import ENUMS, LABELS, SOUND_ROLES

DISPLAY_VERSION = "plotloom.production-brief-display.v1"
ENTITY = "id name description visualAnchors soundAnchors allowedStates continuityRules"
SHAPES = {
    "shot": "id sceneId order title shotSize durationUnits cameraAngle cameraMovement composition visualIntent motionIntent action visibleTexts transition cueIds audioPlan characterIds locationId propIds requiredEntityStates entryState exitState",
    "context": "scene beats dialogueCues characters locations props requiredEntityStates productionPresentation",
    "scene": "id storyNodeId order title objective locationId characterIds beatIds durationBudgetUnits entryState exitState",
    "beat": "id sceneId order visibleEvent entryState exitState",
    "cue": "id beatId order speakerId voiceOver text language delivery performanceNotes estimatedDurationUnits",
    "entity": ENTITY, "character": ENTITY + " role goal traits voiceAnchors",
    "continuity": "facts entityStates screenDirection lighting sound notes",
    "state": "entityType entityId state", "visible": "text",
    "audio": "events", "event": "id kind description startOffsetUnits durationUnits",
    "presentation": "review effectiveShot", "review": "physical literalSources messagePresentation reason",
    "physical": "action composition visualIntent motionIntent cameraMovement", "literal": "shotId index",
    "presented": "messagePresentation reason", "references": "keyframe endFrame identityLineage",
    "frame": "assetId width height intent aspectPolicy", "intent": "role identityIntent compositionIntent styleIntent sourceRefs targetUse",
    "targetUse": "kind targetShotId source", "frameSource": "assetId sourceShotId originShotId",
    "identity": "characterId assets", "asset": "assetId",
    "timing": "sourceTiming playbackIntent", "sourceTiming": "kind durationUnits cut",
    "cut": "sectionId episode sceneIndex cutIndex shotId seconds beats",
    "settings": "provider request", "provider": "provider model",
    "request": "durationSeconds resolution audio aspectPolicy seed profileId width height fps frameCount allowLetterbox allowCenterCrop quality automaticRetryLimit",
}
CHILDREN = {
    "shot": {"audioPlan": "audio", "visibleTexts": "visible", "requiredEntityStates": "state", "entryState": "continuity", "exitState": "continuity"},
    "context": {"scene": "scene", "beats": "beat", "dialogueCues": "cue", "characters": "character", "locations": "entity", "props": "entity", "requiredEntityStates": "state", "productionPresentation": "presented"},
    "scene": {"entryState": "continuity", "exitState": "continuity"},
    "beat": {"entryState": "continuity", "exitState": "continuity"},
    "continuity": {"entityStates": "state"}, "audio": {"events": "event"},
    "presentation": {"review": "review", "effectiveShot": "shot"},
    "review": {"physical": "physical", "literalSources": "literal"},
    "references": {"keyframe": "frame", "endFrame": "frame", "identityLineage": "identity"},
    "frame": {"intent": "intent"}, "intent": {"targetUse": "targetUse"},
    "targetUse": {"source": "frameSource"}, "identity": {"assets": "asset"},
    "timing": {"sourceTiming": "sourceTiming"}, "sourceTiming": {"cut": "cut"},
    "settings": {"provider": "provider", "request": "request"},
}
# Exact provenance and retired source versions are preserved in technical detail.
# These are explicit current DTO fields, not an unknown-key or hash-name bypass.
TECHNICAL = {
    "visible": "sourceCoordinates sourceContentHash",
    "presentation": "id revision sourceHash source bindingRevisionFloor",
    "review": "expectedRevision sourceHash approvalId storyboardRevision reviewed",
    "references": "samePersonReviewId",
    "frame": "revision bindingId selectionRevision originalHash mimeType visualIntentId visualIntentRevision provenance approvalId storyboardRevision sourceTiming",
    "intent": "attribution sourceEndorsement sourceBindingId retainedVisualIntentId",
    "targetUse": "targetContext", "frameSource": "bindingId bindingHash visualIntentId visualIntentRevision intentHash originalHash originJobId originCandidateId originRequestHash originDeliveryHash",
    "identity": "referenceDecisionId referenceRevision characterContextHash", "asset": "originalHash",
    "sourceTiming": "admissionId proposalRevision proposalContentHash cutHash installedStageRevisions shotId storyboardRevision",
    "cut": "source frame h3Prompt", "provider": "adapterId adapterVersion capabilityVersion costPolicy backendBinding",
    "request": "profileVersion",
}
ROOT_FIELDS = {'resolvedContext', 'shotPresentation', 'storyboardRevision', 'languageContract', 'shot', 'endFrame', 'request', 'approvalId', 'storyboardEntityRevisionId', 'canonicalInputRevisions', 'keyframe', 'playbackIntent', 'approvalGateSetVersion', 'samePersonReviewId', 'provider', 'sourceTiming', 'compilerVersion', 'identityLineage', 'snapshotVersion', 'executionRetry'}
OWNERS = {"shot": ("分镜与声音计划", "Storyboard and sound plan"), "resolvedContext": ("场景、人物与对白", "Scene, character and dialogue sources"),
    "shotPresentation": ("镜头呈现", "Shot presentation"), "keyframe": ("首帧使用决定", "Opening-frame decision"),
    "endFrame": ("尾帧使用决定", "Ending-frame decision"), "identityLineage": ("人物参考决定", "Character-reference decision"),
    "sourceTiming": ("作者时长来源", "Authored timing source"), "request": ("生成设置", "Generation settings"), "provider": ("提供方适配器", "Provider adapter")}


def source_owner(path, english):
    return OWNERS.get(path.split(".")[0], ("来源合同", "Source contract"))[int(english)]


def readable_sections(snapshot, sections):
    english = snapshot["languageContract"]["contentLocale"] == "en-US"
    conflicts = []
    def conflict(path):
        owner = source_owner(path, english)
        conflicts.append({"path": path, "owner": owner, "message": (
            f"This requirement has no readable production representation. Review its owning source: {owner}."
            if english else f"此要求尚无可审阅的制作表达；请回到所属来源处理：{owner}。")})

    def value_text(value, key, shape, path):
        if key == "provider" and value == "minimax_h3_gateway":
            return "MiniMax H3"
        if key in {"profileId", "model"} and isinstance(value, str) and value.startswith("minimax_h3_"):
            request = snapshot["request"]
            quality = "quality" if english else "质量档位"
            return f"MiniMax H3 · {request['width']} × {request['height']} · {quality} {request['quality']}"
        if key in {"speakerId", "voiceOver", "characterIds", "characterId", "locationId", "propIds"}:
            names = {item["id"]: item.get("name") for group in ("characters", "locations", "props")
                for item in snapshot["resolvedContext"].get(group, [])}
            if isinstance(value, str) and names.get(value):
                return f"{names[value]} ({value})"
        table = ENUMS.get(key)
        if key == "kind":
            table = SOUND_ROLES if shape == "event" else ({"canonical": ("已审阅分镜", "Reviewed storyboard"), "f5_bridge": ("已安装分镜切段", "Installed storyboard cut")} if shape == "sourceTiming" else {"cross_shot_initial_keyframe": ("沿用已审阅的跨镜头首帧", "Reuse the reviewed cross-shot opening frame")})
        if key == "role" and shape == "intent":
            table = {"shot_keyframe": ("镜头首帧", "Shot opening frame"), "protagonist_reference": ("人物参考", "Character reference"), "location_reference": ("场景参考", "Location reference")}
        if table and value not in (None, ""):
            if not isinstance(value, str) or value not in table:
                conflict(path)
                return "Unsupported source value" if english else "来源值尚不受支持"
            return table[value][int(english)]
        if value is None or value == "":
            return "Not specified" if english else "未指定"
        if isinstance(value, bool):
            return ("Yes" if value else "No") if english else ("是" if value else "否")
        if key.endswith("Units") and isinstance(value, (int, float)):
            return f"{value / 1000:g} " + ("seconds" if english else "秒")
        if key in {"durationSeconds", "seconds"}:
            return f"{value:g} " + ("seconds" if english else "秒")
        if key in {"width", "height"}:
            return f"{value} px"
        if key == "fps":
            return f"{value} fps"
        if isinstance(value, (dict, list)):
            conflict(path)
            return "Review source" if english else "请处理来源"
        return str(value)

    def fact_items(value, path, label, items):
        if isinstance(value, (dict, list)) and not value:
            items.append({"path": path, "label": label, "value": "None" if english else "无"})
        elif isinstance(value, dict):
            for index, (name, fact) in enumerate(sorted(value.items()), 1):
                fact_label = f"{label} {index}"
                items.append({"path": f"{path}.{name}", "label": fact_label + (" · Name" if english else " · 名称"), "value": str(name)})
                fact_items(fact, f"{path}.{name}", fact_label + (" · Value" if english else " · 要求值"), items)
        elif isinstance(value, list):
            for index, fact in enumerate(value):
                fact_items(fact, f"{path}.{index}", f"{label} {index + 1}", items)
        else:
            items.append({"path": path, "label": label, "value": value_text(value, "", "continuity", path)})

    def walk(data, shape, path, prefix, items):
        if data is None:
            items.append({"path": path, "label": prefix, "value": "Not specified" if english else "未指定"})
            return
        if not isinstance(data, dict):
            conflict(path)
            return
        fields = SHAPES[shape].split()
        technical = TECHNICAL.get(shape, "").split()
        for key in sorted(set(data) - set(fields) - set(technical)):
            conflict(f"{path}.{key}" if path else key)
        for key in fields:
            if key not in data:
                continue
            value = data[key]
            source_path = f"{path}.{key}" if path else key
            label = LABELS[key][int(english)]
            label = f"{prefix} · {label}" if prefix else label
            nested = CHILDREN.get(shape, {}).get(key)
            values = value if isinstance(value, list) else [value]
            if not values:
                items.append({"path": source_path, "label": label, "value": "None" if english else "无"})
            for index, item in enumerate(values):
                item_path = f"{source_path}.{index}" if isinstance(value, list) else source_path
                item_label = f"{label} {index + 1}" if isinstance(value, list) else label
                if nested:
                    walk(item, nested, item_path, item_label, items)
                elif key == "facts" and isinstance(item, dict):
                    # This current DTO explicitly owns authored fact-map keys.
                    fact_items(item, item_path, item_label, items)
                else:
                    items.append({"path": item_path, "label": item_label,
                        "value": value_text(item, key, shape, item_path),
                        "kind": "exact_text" if key == "text" else "text"})

    result = []
    paths = {"shot": "shot", "context": "resolvedContext", "presentation": "shotPresentation"}
    for section in sections:
        items = []
        shape = section["id"]
        walk(section["content"], shape, paths.get(shape, ""), section["label"] if section["content"] is None else "", items)
        if shape == "context":
            for index, cue in enumerate(snapshot["resolvedContext"].get("dialogueCues", [])):
                identity = cue.get("speakerId") or cue.get("voiceOver")
                visible = identity in snapshot["shot"].get("characterIds", [])
                if cue.get("voiceOver"):
                    text = (("Off-screen voiceover; the visible character keeps their lips completely closed." if visible else "Off-screen voiceover.")
                        if english else ("画外音；画面中的此人物双唇完全闭合。" if visible else "画外音。"))
                else:
                    text = (("On-screen speaker." if visible else "Off-screen speaker.") if english else ("画面内人物说话。" if visible else "画外人物说话。"))
                text += " Speak the exact authored line once." if english else "作者原文只说一次。"
                items.append({"path": f"resolvedContext.dialogueCues.{index}",
                    "label": f"Dialogue {index + 1} · Speech and lips" if english else f"对白 {index + 1} · 发声与口型", "value": text})
        result.append(section | {"items": items})
    for key in sorted(set(snapshot) - ROOT_FIELDS):
        conflict(key)
    return result, conflicts
