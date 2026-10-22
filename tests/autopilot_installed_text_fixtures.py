"""Closed default eight-text/install prefix; all image work stays destination-local."""
from contextlib import closing

import pytest

from tests.autopilot_controller_fixtures import (
    default_brief,
    environment,
    run_text,
    runtime,
)
from tests.autopilot_installed_text_core import (
    InstalledTextCopy,
    InstalledTextPrefix,
    claim_installed_text_copy,
    focused_installation_policy,
    installed_text_history,
    installed_text_view,
)
from tests.autopilot_seed_fixtures import (
    copy_closed_autopilot_seed,
    freeze_closed_autopilot_seed,
    run_facts,
)


def assert_installed_text_boundary(store, registry):
    """Ordinary open validates authority first; the default contract remains strict."""
    view = installed_text_view(store)
    if store.project().brief != default_brief():
        raise ValueError("installed-text prefix requires the unchanged default Brief")
    if view.policy != focused_installation_policy(store, registry):
        raise ValueError("installed-text prefix requires the unchanged default policy")
    return installed_text_history(store, view)


def build_installed_text_prefix(root):
    with pytest.MonkeyPatch.context() as patch:
        storage, registry, service, view, calls = environment(root, patch)
        try:
            run_text(service, view)  # Unchanged real default preparation/installation.
            host = registry._codex_exec_test_host
            with closing(storage.projects.open(view.project_id)) as store:
                view, policy_text, records = assert_installed_text_boundary(store, registry)
                home_name = store.home.name
            if (len(calls) != 8 or host.image_calls or host.pending or registry.view()["busy"]
                    or len(host.statuses) != 8
                    or any(status.state not in {"completed", "settled"} for status in host.statuses.values())):
                raise ValueError("installed-text prefix still has pending fake host work")
        finally:
            service.close()
        assert service._thread is None and service._descriptor is None
    project = freeze_closed_autopilot_seed(root, view.project_id, home_name)
    return InstalledTextPrefix(project, str(view.id), policy_text, records)


def copy_installed_text_prefix(seed, destination, monkeypatch) -> InstalledTextCopy:
    storage, before = copy_closed_autopilot_seed(seed.project, destination)
    registry, service, host = runtime(storage, monkeypatch)
    try:
        with closing(storage.projects.open(seed.project.project_id)) as store:
            checked, policy_text, records = assert_installed_text_boundary(store, registry)
            if (str(checked.id), policy_text, records) != (seed.run_id, seed.policy_text, seed.text_records):
                raise ValueError("installed-text prefix immutable history changed")
            assert run_facts(checked) == run_facts(before)
        return claim_installed_text_copy(storage, registry, service, host, before)
    except BaseException:
        service.close()
        raise


def installed_text_image_environment(tmp_path, monkeypatch, installed_text_prefix, *, auto_deliver=True, geometry=None):
    copied = copy_installed_text_prefix(installed_text_prefix, tmp_path / "installed-text-copy", monkeypatch)
    host = copied.registry._codex_exec_test_host
    # Image-only knobs apply after the real text cut and fresh claim/current read.
    host.auto_deliver, host.image_geometry = auto_deliver, geometry
    return copied.storage, copied.registry, copied.service, copied.view, copied.image_calls, copied.text_calls
