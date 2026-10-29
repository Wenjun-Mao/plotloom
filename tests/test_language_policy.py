"""Prospective project/report identity, source preservation and manual defaults."""
from copy import deepcopy
from contextlib import closing

import pytest

from plotloom.creative_handoff_contracts import CreativeHandoffError
from plotloom.creative_handoff_identity import request_hash
from plotloom.language_policy import (
    LANGUAGE_CONTRACT_FILENAME, assert_candidate_report_language,
    assert_language_current, language_contract, supported_content_locale,
)
from plotloom.outline_preparation import outline_request
from plotloom.story_workloads import FIXED_CHINESE_BRIEF
from plotloom.working_inputs import BriefWorkingInput
from tests.source_outline_fixtures import _material, _storage


@pytest.mark.parametrize("locale,report", [("zh-CN", "zh"), ("en-US", "en")])
def test_project_language_freezes_report_identity_and_preserves_source(tmp_path, locale, report):
    storage = _storage(tmp_path)
    brief = FIXED_CHINESE_BRIEF.model_copy(update={"language": locale})
    with closing(storage.projects.create(brief)) as store:
        source = _material()
        store.save_source_material(expected_source_revision=0, material=source)
        request = outline_request(store)
        frozen = request.input_artifacts[LANGUAGE_CONTRACT_FILENAME]
        assert frozen == language_contract(locale)
        assert frozen["reportLocale"] == report
        assert "applicationLocale" not in frozen
        assert request.source == source.model_dump(mode="json", by_alias=True)
        candidate = {"lang": report, "quotation": "原文 / Original quote", "episodes": []}
        before = deepcopy(candidate)
        assert_candidate_report_language(candidate, request.input_artifacts)
        assert candidate == before
        changed = request.model_copy(update={"input_artifacts": request.input_artifacts | {
            LANGUAGE_CONTRACT_FILENAME: language_contract("en-US" if locale == "zh-CN" else "zh-CN")}})
        assert request_hash(changed) != request_hash(request)
        with pytest.raises(CreativeHandoffError, match="项目语言"):
            assert_language_current(request.input_artifacts, "en-US" if locale == "zh-CN" else "zh-CN")
        for invalid in (None, "en" if report == "zh" else "zh", locale):
            with pytest.raises(CreativeHandoffError) as error:
                assert_candidate_report_language(candidate | {"lang": invalid}, request.input_artifacts)
            assert error.value.code == "candidate_language_mismatch"


@pytest.mark.parametrize("locale,title", [("zh-CN", "未命名故事"), ("en-US", "Untitled story")])
def test_blank_manual_title_follows_creative_locale(locale, title):
    value = BriefWorkingInput(title=" ", synopsis="An original synopsis.", language=locale)
    restored = BriefWorkingInput.model_validate_json(value.model_dump_json(by_alias=True))
    assert restored.confirmed().title == title
    assert restored.confirmed().language == locale


@pytest.mark.parametrize("locale", ["en", "zh", "fr-FR", "", " EN-US "])
def test_new_work_rejects_unsupported_language_with_actionable_chinese(tmp_path, locale):
    with pytest.raises(ValueError, match="请选择简体中文"):
        supported_content_locale(locale)
    with pytest.raises(ValueError, match="请选择简体中文"):
        BriefWorkingInput(title="Existing title", synopsis="Story", language=locale).confirmed()
    storage = _storage(tmp_path)
    with pytest.raises(ValueError, match="请选择简体中文"):
        storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"language": locale}))
    assert not list(storage.projects.outputs_root.glob("*/plotloom-project.json"))


def test_retained_request_carries_no_manufactured_language_assertion():
    candidate = {"lang": "en", "source": "unchanged"}
    before = deepcopy(candidate)
    assert_candidate_report_language(candidate, {})
    assert candidate == before
