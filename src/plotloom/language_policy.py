"""Project language is creative authority; application presentation is independent."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from .domain_base import CamelModel

ContentLocale = Literal["zh-CN", "en-US"]
ReportLocale = Literal["zh", "en"]
LANGUAGE_CONTRACT_FILENAME = "language-contract.json"
LANGUAGE_POLICY_VERSION = "plotloom.project-language.v1"
TIMING_POLICY_VERSION = "dialogue.bilingual.v2"
APPLICATION_LOCALE: Literal["zh-CN"] = "zh-CN"


def supported_content_locale(language: str) -> ContentLocale:
    if language not in ("zh-CN", "en-US"):
        raise ValueError("项目内容语言不受支持：请选择简体中文（zh-CN）或英语（en-US），然后重新应用简报。")
    return language


class ProjectLanguageContract(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    version: Literal["plotloom.project-language.v1"] = LANGUAGE_POLICY_VERSION
    content_locale: ContentLocale
    report_locale: ReportLocale
    timing_policy_version: str = Field(min_length=1)


def language_contract(language: str) -> dict:
    locale = supported_content_locale(language)
    return ProjectLanguageContract(content_locale=locale,
        report_locale="zh" if locale == "zh-CN" else "en",
        timing_policy_version=TIMING_POLICY_VERSION).model_dump(mode="json", by_alias=True)


def language_instructions(language: str) -> str:
    frozen = language_contract(language)
    return (
        f" Read inputs/{LANGUAGE_CONTRACT_FILENAME}: content locale {frozen['contentLocale']}, "
        f"report locale {frozen['reportLocale']}, policy {frozen['version']}. "
        "Set candidate top-level lang to the frozen report locale. Every newly authored readable "
        "description, action, note, choice and explanation follows the content locale. Report headings "
        "and readable diagnostics follow the report locale. Exact source excerpts, proper names, "
        "explicit intentional foreign speech and literal visible words keep their original bytes. "
        "Stable keys, IDs and enums keep their identities. English provider prompts are derived technical "
        "instructions, never the primary readable creative description. Do not silently translate "
        "source facts, change spans, invent exceptions or claim creative acceptance."
    )


def freeze_request_language(request, language: str) -> None:
    """Preparation only: existing immutable request/currentness hashing owns bytes."""
    request.input_artifacts[LANGUAGE_CONTRACT_FILENAME] = language_contract(language)
    request.creative_brief += "\n\n" + language_instructions(language)
    from .creative_field_ownership import freeze_field_ownership
    if request.stage != "video-directions":
        freeze_field_ownership(request)
    from .provider_literals import LITERAL_STAGES, freeze_provider_context, provider_literal_instructions
    if request.stage in LITERAL_STAGES:
        freeze_provider_context(request)
        request.creative_brief += provider_literal_instructions()


def language_response_schema(schema: dict, language: str) -> dict:
    """Freeze report metadata in a stage-owned schema without touching prose."""
    from copy import deepcopy
    schema = deepcopy(schema)
    schema["properties"]["lang"] = {"type": "string", "const": language_contract(language)["reportLocale"]}
    schema["required"] = list(dict.fromkeys([*schema.get("required", []), "lang"]))
    return schema


def report_locale(artifacts: dict) -> ReportLocale:
    value = artifacts.get(LANGUAGE_CONTRACT_FILENAME)
    return ProjectLanguageContract.model_validate(value).report_locale if value is not None else "zh"


def assert_language_current(artifacts: dict, language: str) -> None:
    from .creative_handoff_contracts import CreativeHandoffError

    if artifacts.get(LANGUAGE_CONTRACT_FILENAME) != language_contract(language):
        raise CreativeHandoffError("project_language_stale", "项目语言或语言规则已变化，请取消旧任务并重新准备；原结果仍保留。")


def assert_candidate_report_language(candidate: dict, artifacts: dict) -> None:
    """Check frozen new-work identity without modifying candidate or historical bytes."""
    from .creative_handoff_contracts import CreativeHandoffError

    value = artifacts.get(LANGUAGE_CONTRACT_FILENAME)
    if value is None:
        return  # Historical frozen requests have no prospective language assertion.
    frozen = ProjectLanguageContract.model_validate(value)
    if value != language_contract(frozen.content_locale):
        raise CreativeHandoffError("project_language_stale", "任务语言规则已变化，请重新准备。")
    if candidate.get("lang") != frozen.report_locale:
        raise CreativeHandoffError("candidate_language_mismatch", "候选内容的报告语言与项目语言不一致，请按冻结的语言规则修正候选内容。")


def assert_new_request_language(request) -> None:
    """Only new publication needs current authority; retained reads never add it."""
    from .creative_handoff_contracts import CreativeHandoffError

    value = request.input_artifacts.get(LANGUAGE_CONTRACT_FILENAME)
    if value is None:
        raise CreativeHandoffError("project_language_missing", "新生成任务必须冻结项目内容语言；请重新准备，不能以旧格式跳过语言检查。")
    frozen = ProjectLanguageContract.model_validate(value)
    if value != language_contract(frozen.content_locale):
        raise CreativeHandoffError("project_language_stale", "新生成任务的语言规则已过期，请重新准备。")
    from .content_language_contract import is_language_check
    from .provider_literals import LITERAL_STAGES, validate_context
    if request.stage in LITERAL_STAGES and not is_language_check(request):
        validate_context(request)


def assert_bound_report_language(candidate: dict, binding) -> None:
    if binding.language_contract is not None:
        assert_candidate_report_language(candidate, {
            LANGUAGE_CONTRACT_FILENAME: binding.language_contract.model_dump(mode="json", by_alias=True)})


def default_creative_title(language: str) -> str:
    return "Untitled story" if supported_content_locale(language) == "en-US" else "未命名故事"
