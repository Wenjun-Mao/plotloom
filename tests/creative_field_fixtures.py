"""Small frozen request owners; no native dispatch or semantic model evidence."""
from plotloom.autopilot_brief_style import freeze_brief_style
from plotloom.cast_style import freeze_cast_style
from plotloom.creative_field_ownership import freeze_field_ownership
from tests.content_language_fixtures import original_request


def cast_case(*, saved=True, locale="zh-CN"):
    request = original_request("characters", locale=locale)
    request.content_validation_contract = "plotloom.typed-content-result.v1"
    contract = freeze_brief_style("暖色留白，保留人物矛盾。") if saved else freeze_cast_style("realistic", None)
    request.input_artifacts |= {"cast-style-contract.json": contract, "section-map.json": {"sections": [
        {"sectionId": "opening", "footageMode": "footage"}, {"sectionId": "choice", "footageMode": "route_only"}]},
        "outline.json": {"characters": [{"id": "C01", "name": "Mara"}]}}
    freeze_field_ownership(request)
    from plotloom.provider_literals import freeze_provider_context
    freeze_provider_context(request)
    marker = "Saved Brief direction" if saved else contract["preset"]["label"]
    value = {"lang": "zh" if locale == "zh-CN" else "en", "characters": [{"id": "C01", "image": {"style": marker},
        "sectionPresence": [{"sectionId": "opening", "footageMode": "footage", "present": True, "context": "灯下的抉择。"},
                            {"sectionId": "choice", "footageMode": "route_only", "present": False, "context": "选择节点。"}]}],
        "notes": "C01 在灯下作出选择。"}
    if saved:
        value["styleAuthority"] = {key: contract[key] for key in ("authority", "direction", "stageInstructionContract", "contentHash")}
    return request, value
