"""A change tripwire for reviewed immutable/value-only construction (ADR 0184)."""
import ast
import json
import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from plotloom import codex_exec_contracts, public_values
from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.codex_exec_pool_contracts import CodexExecPoolLimits
from plotloom.domain_base import CamelModel

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = {
    "src/plotloom/codex_exec_contracts.py": ["CodexExecProfile"],
    "src/plotloom/codex_exec_pool_contracts.py": ["CodexExecPoolLimits"],
    "src/plotloom/domain_base.py": ["CamelModel", "to_camel"],
    "src/plotloom/public_values.py": ["SECRET_SETTING_NAMES", "is_secret_setting_name",
                              "contains_secret_setting", "contains_secret_value"],
}


def test_profile_construction_value_only_contract_requires_explicit_review():
    """Changing reviewed validators/defaults/dependencies must reopen reuse safety.

    This deliberately fails on semantic AST changes; it is a review tripwire,
    not a claim that arbitrary Python can be mechanically proved pure.
    """
    payload = {}
    for name, expected in REVIEWED.items():
        nodes = []
        for node in ast.parse((ROOT / name).read_text()).body:
            selected = getattr(node, "name", None) in expected or (
                isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id in expected for target in node.targets))
            if selected:
                nodes.append(node)
        assert len(nodes) == len(expected)
        payload[name] = ast.dump(ast.Module(body=nodes, type_ignores=[]), include_attributes=False)
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert digest == "c8159d2b5d7f447bf8aa71ac5ccfb6ccd33c4e0bab47fa3dbaa7696fbe4701f9", (
        "Profile construction dependencies changed: disable reuse or review ADR 0184 before updating this pin.")
    assert codex_exec_contracts.CamelModel is CamelModel
    assert codex_exec_contracts.contains_secret_setting is public_values.contains_secret_setting
    assert codex_exec_contracts.contains_secret_value is public_values.contains_secret_value
    assert public_values.re is re and public_values.urlparse is urlparse and public_values.parse_qsl is parse_qsl
    assert type(public_values.SECRET_SETTING_NAMES) is frozenset
    assert all(type(value) is str for value in public_values.SECRET_SETTING_NAMES)
    for model, expected in (
        (CodexExecProfile, {"supported_capability_set"}),
        (CodexExecPoolLimits, {"domains_fit_global_capacity"}),
    ):
        decorators = model.__pydantic_decorators__
        assert set(decorators.model_validators) == expected
        for name in ("validators", "field_validators", "root_validators",
                     "field_serializers", "model_serializers", "computed_fields"):
            assert not getattr(decorators, name)
        assert all(field.default_factory is None for field in model.model_fields.values())
