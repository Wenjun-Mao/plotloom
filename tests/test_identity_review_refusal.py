"""Both API compositions expose the same actionable identity-review refusal."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.errors import register_api_error_handlers
from plotloom.api.project_folder import create_project_folder_authoring_app
from plotloom.exceptions import SamePersonReviewRequiredError
from tests.test_project_storage_source_outline import _storage


@pytest.mark.parametrize("composition", ["service", "project_folder"])
def test_identity_review_refusal_has_identical_public_contract(tmp_path, composition):
    if composition == "project_folder":
        app = create_project_folder_authoring_app(_storage(tmp_path))
    else:
        app = FastAPI()
        register_api_error_handlers(app)

    @app.get("/identity-refusal")
    def refuse():
        raise SamePersonReviewRequiredError(shot_id="shot-1", binding_id="binding-1")

    response = TestClient(app).get("/identity-refusal")
    assert response.status_code == 409
    assert response.json() == {
        "code": "same_person_review_required",
        "shotId": "shot-1",
        "bindingId": "binding-1",
        "technicalMessage": "identity-aware keyframe requires a current passing same-person review",
        "message": str(SamePersonReviewRequiredError(shot_id="shot-1", binding_id="binding-1")),
    }
