"""Exact fresh-input identity and immutable construction, never cached authority."""
import json
from types import UnionType
from typing import Literal, Union, get_args, get_origin

import pytest
from pydantic import ValidationError

from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.persistence.project.autopilot_profile_construction import (
    _ProfileConstruction,
)
from tests.autopilot_profile_fixtures import observe_constructions
from tests.codex_exec_fixtures import PROFILE


def policy_text(**changes):
    return json.dumps({"executorBinding": PROFILE.model_dump(mode="json", by_alias=True)} | changes)


def resolve(slot, raw):
    return slot.resolve(raw, json.loads(raw))


@pytest.mark.parametrize("difference", ["outside-binding", "encoding", "alias", "default", "profile"])
def test_single_success_slot_uses_exact_full_text_and_replaces_instead_of_history(monkeypatch, difference):
    first = policy_text()
    value = json.loads(first)
    if difference == "outside-binding":
        value["codeRevision"] = "f" * 40
    elif difference == "alias":
        value["executorBinding"]["cli_version"] = value["executorBinding"].pop("cliVersion")
    elif difference == "default":
        value["executorBinding"].pop("apiFallback")
    elif difference == "profile":
        value["executorBinding"]["model"] = "different-model"
    second = json.dumps(value, indent=2) if difference == "encoding" else json.dumps(value)
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    one = resolve(slot, first)
    assert resolve(slot, first) is one
    two = resolve(slot, second)
    assert two is not one
    assert resolve(slot, second) is two
    assert resolve(slot, first) is not one
    assert len(calls) == 3


@pytest.mark.parametrize("raw_type", [bytes, bytearray])
def test_non_text_json_uses_original_constructor_and_clears_prior_success(monkeypatch, raw_type):
    raw = policy_text()
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    first = resolve(slot, raw)
    encoded = raw_type(raw.encode())
    assert resolve(slot, encoded) == first
    assert resolve(slot, encoded) == first
    assert resolve(slot, raw) is not first
    assert len(calls) == 4


@pytest.mark.parametrize("binding", [None, {}, {"model": "invalid"}, "invalid"])
def test_failed_replacement_never_recovers_a_prior_success(monkeypatch, binding):
    raw = policy_text()
    invalid = json.dumps({"executorBinding": binding})
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    first = resolve(slot, raw)
    for _ in range(2):
        with pytest.raises(ValidationError) as cached:
            resolve(slot, invalid)
        with pytest.raises(ValidationError) as fresh:
            CodexExecProfile.model_validate(binding)
        assert str(cached.value) == str(fresh.value)
    assert resolve(slot, raw) is not first
    assert len(calls) == 6  # Initial + two failed pairs + fresh after failure.


def test_missing_binding_and_extraction_failure_keep_original_errors_and_clear_slot(monkeypatch):
    raw = policy_text()
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    first = resolve(slot, raw)
    with pytest.raises(ValidationError):
        resolve(slot, "{}")
    with pytest.raises(AttributeError):
        resolve(slot, "null")
    assert resolve(slot, raw) is not first
    assert len(calls) == 3


def versioned_payload(version):
    value = PROFILE.model_dump(mode="json", by_alias=True)
    value.update(contractVersion=f"plotloom.codex-exec.v{version}", maxProcesses=1)
    for name in ("maxTextProcesses", "maxImageProcesses", "maxQueuedJobs", "textValidatorRuntimeProfile"):
        value.pop(name, None)
    if version == 1:
        for name in ("authenticationStore", "permissionProfile", "toolProfile"):
            value.pop(name)
        value["sandboxProfile"] = "read_only_with_delivery_write"
    else:
        permission = {2: 2, 3: 2, 4: 2, 5: 3, 6: 4, 7: 5, 8: 5}[version]
        value["permissionProfile"] = f"plotloom_autopilot_delivery_v{permission}"
        value["toolProfile"] = f"plotloom_autopilot_tools_v{version if version < 4 else 4}"
        if version >= 5:
            value["textValidatorRuntimeProfile"] = {
                5: "node_openssl_and_private_zsh_tmp_v1",
                6: "node_openssl_private_zsh_tmp_and_validator_aliases_v2",
                7: "node_openssl_private_zsh_tmp_and_checked_python_v3",
                8: "node_openssl_private_zsh_tmp_and_checked_python_v3",
            }[version]
    if version == 8:
        value.update(maxTextProcesses=1, maxImageProcesses=1, maxQueuedJobs=1)
    return value


@pytest.mark.parametrize("version", range(1, 9))
def test_retained_serial_and_current_pool_profiles_keep_native_validation(monkeypatch, version):
    value = versioned_payload(version)
    expected = CodexExecProfile.model_validate(value)
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    raw = json.dumps({"executorBinding": value})
    first = resolve(slot, raw)
    assert first == expected and first.profile_hash == expected.profile_hash
    assert resolve(slot, raw) is first
    assert len(calls) == 1
    invalid = value | ({"maxProcesses": 2} if version < 8 else {"maxTextProcesses": 2})
    with pytest.raises(ValidationError):
        resolve(slot, json.dumps({"executorBinding": invalid}))
    with pytest.raises(ValidationError, match="credentials"):
        resolve(slot, json.dumps({"executorBinding": value | {"model": "sk-proj-privatecredential"}}))
    assert resolve(slot, raw) is not first
    assert len(calls) == 4


def test_mutable_input_does_not_alias_profile_and_hash_is_still_computed(monkeypatch):
    raw = policy_text()
    policy = json.loads(raw)
    slot = _ProfileConstruction()
    profile = slot.resolve(raw, policy)
    policy["executorBinding"]["capabilities"].clear()
    assert profile.capabilities == PROFILE.capabilities
    assert resolve(slot, raw) is profile
    with pytest.raises(ValidationError):
        profile.model = "changed"
    hashes, original = [], CodexExecProfile.profile_hash.fget

    def hashing(model):
        hashes.append(True)
        return original(model)

    monkeypatch.setattr(CodexExecProfile, "profile_hash", property(hashing))
    assert profile.profile_hash == profile.profile_hash
    assert len(hashes) == 2


@pytest.mark.parametrize("explicit_null", [True, False])
def test_optional_version_metadata_keeps_exact_text_reuse_only(monkeypatch, explicit_null):
    binding = PROFILE.model_dump(mode="json", by_alias=True)
    binding.pop("cliVersion")
    if explicit_null:
        binding["cliVersion"] = None
    raw = json.dumps({"executorBinding": binding})
    expected = CodexExecProfile.model_validate(binding)
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    first = resolve(slot, raw)
    assert first == expected and first.cli_version is None
    assert resolve(slot, raw) is first
    with pytest.raises(ValidationError):
        first.cli_version = "codex-cli 9.99.0"
    other = binding.copy()
    other.pop("cliVersion", None) if explicit_null else other.update(cliVersion=None)
    replacement = resolve(slot, json.dumps({"executorBinding": other}))
    assert replacement == first and replacement is not first
    assert replacement.profile_hash == first.profile_hash
    assert len(calls) == 2


@pytest.mark.parametrize("value", [None, "omitted", 1])
def test_optional_correction_limit_keeps_exact_text_reuse_and_failed_replacement_clears_slot(monkeypatch, value):
    binding = PROFILE.model_dump(mode="json", by_alias=True)
    binding.pop("textCorrectionLimit", None)
    if value != "omitted":
        binding["textCorrectionLimit"] = value
    raw = json.dumps({"executorBinding": binding})
    expected = CodexExecProfile.model_validate(binding)
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    first = resolve(slot, raw)
    assert first == expected and first.profile_hash == expected.profile_hash
    assert resolve(slot, raw) is first
    other = binding | {"textCorrectionLimit": None if value == "omitted" else 1 if value is None else None}
    replacement = resolve(slot, json.dumps({"executorBinding": other}))
    assert replacement is not first
    assert (replacement.profile_hash == first.profile_hash) is (value == "omitted")
    assert resolve(slot, raw) is not first
    for invalid in (True, 0, 2):
        with pytest.raises(ValidationError):
            resolve(slot, json.dumps({"executorBinding": binding | {"textCorrectionLimit": invalid}}))
        fresh = resolve(slot, raw)
        assert fresh == expected and fresh is not first
        assert resolve(slot, raw) is fresh
    assert len(calls) == 9  # Three valid replacements, then three failed/fresh pairs.


def test_reuse_requires_frozen_extra_forbidden_structurally_immutable_profile():
    def immutable(annotation):
        origin, arguments = get_origin(annotation), get_args(annotation)
        if annotation in (str, int, bool, type(None)):
            return True
        if origin is Literal:
            return all(type(value) in (str, int, bool, type(None)) for value in arguments)
        if origin in (Union, UnionType):
            return all(immutable(value) for value in arguments)
        return origin is tuple and arguments[-1] is Ellipsis and immutable(arguments[0])

    assert CodexExecProfile.model_config["frozen"] is True
    assert CodexExecProfile.model_config["extra"] == "forbid"
    assert all(immutable(field.annotation) for field in CodexExecProfile.model_fields.values())


def test_text_subclass_constructs_fresh_and_clears_exact_text_success(monkeypatch):
    class TextSubclass(str):
        pass

    raw = policy_text()
    calls = observe_constructions(monkeypatch)
    slot = _ProfileConstruction()
    first = resolve(slot, raw)
    assert resolve(slot, TextSubclass(raw)) == first
    assert resolve(slot, raw) is not first
    assert len(calls) == 3
