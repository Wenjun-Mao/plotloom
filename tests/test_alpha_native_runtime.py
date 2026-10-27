"""Refuse qualification path aliases before any runtime initialization/admission."""
import importlib.util
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


@pytest.mark.parametrize("alias", ["sample", "nonprivate-sample", "outcome", "cancellation", "pauses", "resumptions", "runtime.json", "campaign-runtime"])
def test_actual_native_owner_refuses_alias_before_compose_or_launch(tmp_path, monkeypatch, alias):
    service = Path(__file__).resolve().parents[1] / "services/creator_workbench"
    monkeypatch.syspath_prepend(str(service))
    spec = importlib.util.spec_from_file_location("alpha_native_path_test_owner", service / "alpha_native_runtime.py")
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    root = tmp_path / "fixture-not-native-campaign"
    root.mkdir(mode=0o700)
    for name in ("evidence", "private"): (root / name).mkdir(mode=0o700)
    sample_id = "story-01-repeat-01"
    sample = root / "evidence" / sample_id
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    if alias == "sample":
        sample.symlink_to(foreign, target_is_directory=True)
    elif alias == "nonprivate-sample":
        sample.mkdir(mode=0o755)
    else:
        sample.mkdir(mode=0o700)
        path = root / "private/runtime.json" if alias == "campaign-runtime" else sample / alias
        path.symlink_to(foreign / "missing")
        assert not path.exists() and path.is_symlink()
    # Only frozen-manifest/lease fixtures are substituted. The real owner must
    # refuse its selected path before reaching any runtime or native operation.
    monkeypatch.setattr(owner, "campaign_lease", lambda *_: nullcontext())
    monkeypatch.setattr(owner, "load_campaign", lambda *_a, **_k:
        SimpleNamespace(samples=[SimpleNamespace(sample_id=sample_id, project_id=uuid4())]))
    def forbidden(*_a, **_k): pytest.fail("path alias reached runtime initialization/native launch")
    monkeypatch.setattr(owner, "compose", forbidden)
    monkeypatch.setattr(owner.AutopilotTextPrefix, "launch", forbidden)
    with pytest.raises(ValueError, match="alias|private"):
        owner.run_sample(root, sample_id)
    assert not list(foreign.iterdir())
    assert not (root / "private/codex-exec").exists()
    assert not (root / "data").exists()
