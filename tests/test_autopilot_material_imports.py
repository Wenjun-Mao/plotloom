"""Material schemas import cold; complete inventory alone owns persistence."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from plotloom.autopilot_early_references import EarlyReferenceDiscovery
from plotloom.autopilot_handoff_contracts import CurrentReviewBundle
from plotloom.autopilot_materials import (
    MaterialInventory,
    MaterialSubject,
    inventory_hash,
)
from plotloom.contract_hash import stable_hash
from plotloom.persistence.codec import stable_hash as persisted_hash

ROOT = Path(__file__).resolve().parents[1]
COLD_CHECK = """
import importlib
import inspect
import json
from pathlib import Path
import sys

entry, attribute, owner, source_root, prefix, pure = sys.argv[1:]
module = importlib.import_module(entry)
assert Path(sys.prefix).resolve() == Path(prefix).resolve()
relative = Path(*entry.split("."))
expected = Path(source_root) / "src" / relative
expected = expected / "__init__.py" if entry == "plotloom.persistence" else expected.with_suffix(".py")
assert Path(module.__file__).resolve() == expected.resolve()
persistence = sorted(name for name in sys.modules
    if name == "plotloom.persistence" or name.startswith("plotloom.persistence."))
if pure == "yes":
    assert not persistence, persistence
else:
    assert persistence
model = getattr(module, attribute)
assert model.__module__ + "." + model.__qualname__ == owner
owner_module, owner_name = owner.rsplit(".", 1)
assert model is getattr(sys.modules[owner_module], owner_name)
owner_path = Path(source_root) / "src" / Path(*owner_module.split(".")).with_suffix(".py")
assert Path(inspect.getfile(model)).resolve() == owner_path.resolve()
print(json.dumps({"entry": entry, "prefix": sys.prefix, "executable": sys.executable,
    "entrySource": module.__file__, "modelIdentity": owner,
    "modelSource": inspect.getfile(model), "persistenceModules": persistence}, sort_keys=True))
"""


@pytest.mark.parametrize("entry,attribute,owner,pure", [
    ("plotloom.autopilot_materials", "MaterialInventory", "plotloom.autopilot_materials.MaterialInventory", True),
    ("plotloom.autopilot_early_references", "EarlyReferenceDiscovery", "plotloom.autopilot_early_references.EarlyReferenceDiscovery", True),
    ("plotloom.autopilot_handoff_contracts", "MaterialInventory", "plotloom.autopilot_materials.MaterialInventory", True),
    ("plotloom.persistence", "ProjectSQLiteRepository", "plotloom.persistence.project.repository.ProjectSQLiteRepository", False),
    ("plotloom.persistence.project.first_install_references", "EarlyReferenceDiscovery", "plotloom.autopilot_early_references.EarlyReferenceDiscovery", False),
    ("plotloom.persistence.project.autopilot_inventory_validation", "MaterialInventory", "plotloom.autopilot_materials.MaterialInventory", False),
    ("plotloom.project_storage.material_bundle_validation", "AutomaticMaterialBundle", "plotloom.autopilot_materials.AutomaticMaterialBundle", False),
], ids=["material", "discovery", "handoff", "repository", "first-install", "inventory-validator", "bundle-validator"])
def test_cold_material_entry_uses_project_runtime_and_canonical_models(
    tmp_path, entry, attribute, owner, pure
):
    assert Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", COLD_CHECK, entry, attribute, owner,
            str(ROOT), sys.prefix, "yes" if pure else "no"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    binding = json.loads(result.stdout)
    assert binding["entry"] == entry and binding["modelIdentity"] == owner
    (tmp_path / "cold-binding.json").write_text(json.dumps(binding, indent=2) + "\n")


def inventory_payload():
    return {
        "version": "pre-video.inventory.v2", "entityRevisionId": "entity-1",
        "storyboardRevision": 1, "storyboardHash": "1" * 64, "productionHash": "2" * 64,
        "castRevision": 1, "artRevision": 1,
        "subjects": [
            {"owner": "character-reference", "id": "cast_keeper", "subjectType": None,
                "sceneId": None, "characterIds": [], "consumerCharacterId": "keeper"},
            {"owner": "art-reference", "id": "S01", "subjectType": "scene",
                "sceneId": None, "characterIds": []},
            {"owner": "image", "id": "shot-1", "subjectType": None,
                "sceneId": "S01", "characterIds": ["keeper"]},
        ],
        "routeCount": 2,
    }


def test_current_inventory_json_hash_and_shared_schema_identity():
    raw = inventory_payload()
    inventory = MaterialInventory.model_validate(raw)
    assert inventory.model_dump(mode="json", by_alias=True) == raw
    assert inventory.subjects[0].operation_key == "character-reference:cast_keeper"
    assert inventory.subjects[0].consumer_character_id == "keeper"
    assert persisted_hash is stable_hash
    assert inventory_hash(inventory) == stable_hash(raw) == "7ebf73c92de58aa80054498ec16b992307d251ce6685ee4a93e966aba27feaac"
    assert CurrentReviewBundle.model_fields["inventory"].annotation is MaterialInventory
    assert EarlyReferenceDiscovery.model_fields["subjects"].annotation == list[MaterialSubject]
    schema = MaterialInventory.model_json_schema(by_alias=True)
    assert schema["title"] == "MaterialInventory"
    assert schema["properties"]["version"]["enum"] == ["pre-video.inventory.v1", "pre-video.inventory.v2"]
    assert schema["properties"]["version"]["default"] == "pre-video.inventory.v2"
    assert schema["properties"]["subjects"]["items"] == {"$ref": "#/$defs/MaterialSubject"}
    assert "consumerCharacterId" in schema["$defs"]["MaterialSubject"]["properties"]


def test_discovery_keeps_exact_current_payload_and_material_subject():
    raw = {"version": "pre-video.early-references.v1", "castRevision": 1,
        "castHash": "9" * 64, "artRevision": 1, "artHash": "a" * 64,
        "subjects": inventory_payload()["subjects"][:2]}
    discovery = EarlyReferenceDiscovery.model_validate(raw)
    assert discovery.model_dump(mode="json", by_alias=True) == raw
    assert type(discovery.subjects[0]) is MaterialSubject
    schema = EarlyReferenceDiscovery.model_json_schema(by_alias=True)
    assert schema["properties"]["version"]["const"] == raw["version"]
    assert schema["properties"]["subjects"]["items"] == {"$ref": "#/$defs/MaterialSubject"}


def test_current_inventory_still_requires_explicit_cast_consumer_identity():
    raw = inventory_payload()
    raw["subjects"][0].pop("consumerCharacterId")
    with pytest.raises(ValidationError, match="explicit consumer identity"):
        MaterialInventory.model_validate(raw)


def test_inventory_still_refuses_duplicate_operation_identity():
    raw = inventory_payload()
    raw["subjects"].append(dict(raw["subjects"][0]))
    with pytest.raises(ValidationError, match="identities must be unique"):
        MaterialInventory.model_validate(raw)
