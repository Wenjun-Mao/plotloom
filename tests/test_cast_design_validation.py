from copy import deepcopy

import pytest

from plotloom.cast_design_validation import validate_cast_design


def design(persona):
    return {"characters": [{"id": "C01", "persona": persona}]}


@pytest.mark.parametrize("traits", [None, "Careful", [], ["", "  "], ["（推断）"], [None], ["Careful", 4]])
def test_requires_nonblank_string_trait(traits):
    with pytest.raises(ValueError, match="性格特点"):
        validate_cast_design(design({"personality": traits, "appearance": "Blue coat"}))


@pytest.mark.parametrize("appearance", [None, "", " \n", "（推断）", " (推断) ", 4])
def test_requires_appearance(appearance):
    with pytest.raises(ValueError, match="外观"):
        validate_cast_design(design({"personality": ["Careful"], "appearance": appearance}))


def test_preserves_valid_annotated_values_and_checks_every_character():
    cast = design({"personality": ["", "审慎（推断）"], "appearance": "深蓝外套（推断）"})
    original = deepcopy(cast)
    validate_cast_design(cast)
    assert cast == original
    cast["characters"].append({"id": "C02"})
    with pytest.raises(ValueError, match="C02"):
        validate_cast_design(cast)
