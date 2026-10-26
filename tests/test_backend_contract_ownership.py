"""B1 leaves retain wire identity and import independently of orchestration."""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys

import pytest

# Reviewed pre-extraction schemas: class names, aliases, defaults and validators.
SCHEMAS = {
    "project_contracts:Project": "64166a788f2fa56c6058a4128f81e7eb48fe0ff5e11614727993aa5f8ef8fca9",
    "project_contracts:ProjectCreation": "81171a55ac6e950c18b325da4f82c23d6fbd9e79334b21fcdaa0936e1f1e1728",
    "stage_contracts:StageEnvelope": "4a9679dec80748e9a8a9303d3b7beac1a0ec8888c23fa855ffb649e779c62170",
    "run_contracts:GenerationRun": "c1c24bd43dcfb622eaf13c43c02d8ac038080196c58127a63e7956ac4a5f7c41",
    "run_contracts:RepairSource": "28ea0f29833f911b712387a694bccd9e00b94a7ab144837d00d2fa2768499031",
    "repair_contracts:WorkUnitRepairScope": "9420d67211255ad574e2ca1c6e0e2e1a6b28b9114a43fc4921e03f27fe26d7e7",
    "gate_contracts:GateEvaluation": "72198770f09c6183bf2b5837e3bf735448d201a6c43148720dbe75e1678ad8a3",
    "media_task_contracts:MediaTask": "a2c879f35bb16a83d39f34b24583529d5371dbae7bb66e412ae3114113f99654",
    "provider_contracts:ProviderSnapshot": "5fdeb96dae9677a780f88fee09dfb4755c57b4bcec612ba5c95a84374273a6ac",
    "provider_contracts:ProviderSettings": "22408accff009f06100d1ca7e0357e6368bef76eb669d8ae7c636b1449dfd989",
}


@pytest.mark.parametrize(
    "module,name,digest", [(*key.split(":"), value) for key, value in SCHEMAS.items()]
)
def test_contract_schema_identity(module, name, digest):
    model = getattr(importlib.import_module("plotloom." + module), name)
    payload = json.dumps(
        model.model_json_schema(),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert hashlib.sha256(payload.encode()).hexdigest() == digest


@pytest.mark.parametrize(
    "first",
    ["provider_profiles", "provider_snapshot", "run_contracts", "project_contracts"],
)
def test_contracts_cold_import_without_http_runtime_or_domain_barrel(first):
    code = f"""
import importlib, sys
importlib.import_module('plotloom.{first}')
for name in ('provider_profiles', 'provider_snapshot', 'run_contracts', 'project_contracts', 'repair_contracts'):
    importlib.import_module('plotloom.' + name)
assert 'plotloom.domain' not in sys.modules
assert 'plotloom.runtime' not in sys.modules
assert 'plotloom.api' not in sys.modules
from plotloom.provider_profiles import validate_public_api_root
from plotloom.public_values import validate_public_api_root as leaf
assert validate_public_api_root is leaf
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
