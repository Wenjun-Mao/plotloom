"""Provider-neutral dispatch diagnostics reject untrusted evidence."""

import pytest
from plotloom.video_provider import WanDispatchDiagnostic


@pytest.mark.parametrize(
    ("phase", "code", "status"),
    [
        ("https://signed.example/?token=secret", "http_rejected", 401),
        ("upload", "provider detail: secret", 401),
        ("upload", "http_rejected", True),
        ("upload", "http_rejected", 99),
    ],
)
def test_diagnostic_allowlist_rejects_untrusted_runtime_values(
    phase, code, status
) -> None:
    with pytest.raises(ValueError):
        WanDispatchDiagnostic(phase, code, status)  # type: ignore[arg-type]


def test_video_job_service_requires_explicit_adapter() -> None:
    from plotloom.video_jobs import VideoJobService

    with pytest.raises(TypeError, match="adapter"):
        VideoJobService(None, None, None)  # type: ignore[call-arg, arg-type]


@pytest.mark.parametrize("owner", ["service", "persistence"])
def test_missing_production_contract_cannot_prepare_a_new_wan_request(
    owner: str,
) -> None:
    from types import SimpleNamespace
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.persistence.project.media_video_preparation import VideoJobPreparation
    from plotloom.video_jobs import VideoJobService
    from plotloom.video_provider import VideoProviderError

    class Repository:
        def assert_video_authority(self, _project_id):
            pass

        def prepare_video_job(self, *_args, **_kwargs):
            pytest.fail("missing current contract reached persistence")

    values = dict(
        approval_id="approval",
        shot_id="shot",
        storyboard_revision=1,
        expected_selection_revision=0,
        idempotency_key="retired-wan",
    )
    if owner == "service":
        adapter = SimpleNamespace(production_contract=lambda **_kwargs: None)
        service = VideoJobService(Repository(), None, None, adapter=adapter)
        with pytest.raises(VideoProviderError, match="explicit production contract"):
            service.prepare(
                "project",
                **values,
                requested_seconds=None,
                resolution=None,
                audio=None,
                aspect_policy=None,
                allow_letterbox=False,
                allow_center_crop=False,
                seed=None,
                profile_id=None,
            )
    else:
        with pytest.raises(
            InvalidTransitionError, match="explicit production contract"
        ):
            VideoJobPreparation.prepare_video_job(
                Repository(), "project", **values, production_contract=None
            )
