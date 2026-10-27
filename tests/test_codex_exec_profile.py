import subprocess
from hashlib import sha256
from pathlib import Path

import pytest

from plotloom.codex_exec_profile import (
    DISABLED_CLI_FEATURES,
    VALIDATOR_FILES,
    cli_feature_flags,
)
from tests.codex_exec_runtime_fixtures import (
    codex_exec_test_source as _codex_exec_test_source,  # noqa: F401
)


@pytest.fixture
def observed_cli(tmp_path, monkeypatch, codex_exec_test_source):
    from plotloom import codex_exec_profile

    executable = tmp_path / "codex"
    executable.write_bytes(b"test-owned executable identity")
    executable.chmod(0o700)
    original_run = subprocess.run
    observation = {"stdout": b"codex-cli 0.163.0-alpha.10.2\n", "stderr": b"", "returncode": 0}

    def run(command, **options):
        if command != [str(executable), "--version"]:
            return original_run(command, **options)
        if "error" in observation:
            raise observation["error"]
        return subprocess.CompletedProcess(command, **observation)

    monkeypatch.setattr(subprocess, "run", run)
    return codex_exec_profile, executable, codex_exec_test_source, observation


@pytest.mark.parametrize("version", ["0.162.0-alpha.17.2", "0.163.0-alpha.10.2", "9.99.0"])
def test_profile_records_observed_versions_without_an_allowlist(observed_cli, version):
    module, executable, source, observation = observed_cli
    observation["stdout"] = f"codex-cli {version}\n".encode()
    profile = module.build_codex_exec_profile(executable, source_root=source)
    assert profile.cli_version == f"codex-cli {version}"
    assert profile.executable_sha256 == sha256(executable.read_bytes()).hexdigest()


@pytest.mark.parametrize("unusable", [
    {"returncode": 2}, {"stdout": b""}, {"stdout": b"\xff"},
    {"stdout": b"codex-cli " + b"1" * 400}, {"stdout": b"codex-cli 1\nextra line"},
    {"stdout": b"not version metadata"},
    {"error": OSError("private error must not enter profile")},
    {"error": subprocess.TimeoutExpired("codex", 5)},
])
def test_unavailable_version_metadata_does_not_block_profile(observed_cli, unusable):
    module, executable, source, observation = observed_cli
    observation.update(unusable)
    profile = module.build_codex_exec_profile(executable, source_root=source)
    assert profile.cli_version is None
    assert profile.executable_sha256 == sha256(executable.read_bytes()).hexdigest()
    assert "private error must not enter profile" not in profile.model_dump_json()


def test_version_warning_is_not_an_execution_failure_or_profile_output(observed_cli):
    module, executable, source, observation = observed_cli
    observation["stderr"] = b"private warning must not enter profile"
    profile = module.build_codex_exec_profile(executable, source_root=source)
    assert profile.cli_version == "codex-cli 0.163.0-alpha.10.2"
    assert "private warning must not enter profile" not in profile.model_dump_json()


@pytest.mark.parametrize("defect", ["missing", "symlink"])
def test_fixture_configuration_keeps_the_production_regular_file_guard(observed_cli, monkeypatch, tmp_path, defect):
    module, executable, source, _observation = observed_cli
    config = tmp_path / "unavailable-openssl.cnf"
    if defect == "symlink":
        config.symlink_to(module.NODE_OPENSSL_CONFIG)
    monkeypatch.setattr(module, "NODE_OPENSSL_CONFIG", config)
    with pytest.raises(RuntimeError, match="pinned Node validator OpenSSL configuration"):
        module.build_codex_exec_profile(executable, source_root=source)


@pytest.mark.parametrize("boundary", ["source", "toolchain"])
def test_absent_version_metadata_does_not_bypass_identity_checks(observed_cli, monkeypatch, boundary):
    module, executable, source, observation = observed_cli
    observation["returncode"] = 2

    def refuse(*_args, **_kwargs):
        raise RuntimeError("required identity unavailable")

    monkeypatch.setattr(module, "_source_hash" if boundary == "source" else "validator_toolchain_hash", refuse)
    with pytest.raises(RuntimeError, match="required identity unavailable"):
        module.build_codex_exec_profile(executable, source_root=source)


def test_frozen_profile_still_binds_observed_metadata_and_executable(observed_cli):
    module, executable, source, observation = observed_cli
    first = module.build_codex_exec_profile(executable, source_root=source)
    assert module.build_codex_exec_profile(executable, source_root=source).profile_hash == first.profile_hash
    observation["stdout"] = b"codex-cli 9.99.0\n"
    changed_version = module.build_codex_exec_profile(executable, source_root=source)
    assert changed_version.profile_hash != first.profile_hash
    executable.write_bytes(b"different test-owned executable")
    changed_binary = module.build_codex_exec_profile(executable, source_root=source)
    assert changed_binary.executable_sha256 != first.executable_sha256
    assert changed_binary.profile_hash != changed_version.profile_hash


def test_codex_exec_validator_pin_covers_runtime_authority_and_current_sources() -> None:
    required = {
        "scripts/storyboard-content-validation.mjs",
        "src/plotloom/project_storage/operational_state.py",
        "src/plotloom/persistence/project/production_rebuild_quiescence.py",
        "src/plotloom/outline_report_metadata.py",
        "src/plotloom/outline_preparation.py",
        "src/plotloom/persistence/project/source_outline_mutations.py",
        "src/plotloom/codex_exec_contracts.py",
        "src/plotloom/codex_exec_gc_contracts.py",
        "src/plotloom/codex_exec_receipt_contracts.py",
        "src/plotloom/codex_exec_constants.py",
        "src/plotloom/codex_exec_attempt_contracts.py",
        "src/plotloom/codex_exec_auth.py",
        "src/plotloom/codex_exec_delivery.py",
        "src/plotloom/codex_exec_files.py",
        "src/plotloom/codex_exec_profile.py",
        "src/plotloom/codex_exec_resources.py",
        "src/plotloom/codex_exec_python_environment.py",
        "src/plotloom/codex_exec_runtime_tree.py",
        "scripts/provision_codex_exec_python.py",
        "src/plotloom/codex_exec_prompts.py",
        "src/plotloom/codex_exec_runtime.py",
        "src/plotloom/codex_exec_catalog.py",
        "src/plotloom/codex_exec_telemetry.py",
        "src/plotloom/codex_exec_tool_source.py",
        "src/plotloom/autopilot_exec.py",
        "src/plotloom/autopilot_image_controller.py",
        "src/plotloom/autopilot_text_controller.py",
        "src/plotloom/creative_handoff_package_exchange.py",
        "src/plotloom/persistence/project/autopilot.py",
        "src/plotloom/persistence/project/autopilot_bindings.py",
        "src/plotloom/persistence/project/image_source_lineage.py",
        "src/plotloom/project_storage/autopilot_validation.py",
        "src/plotloom/project_storage/creative_evidence_inventory.py",
        "services/creator_workbench/codex_exec_supervisor.py",
        "services/creator_workbench/codex_exec_supervisor_gc.py",
        "services/creator_workbench/codex_exec_supervisor_errors.py",
        "services/creator_workbench/codex_exec_supervisor_job.py",
        "services/creator_workbench/codex_exec_supervisor_ledger.py",
        "services/creator_workbench/codex_exec_supervisor_process.py",
        "services/creator_workbench/codex_exec_supervisor_environment.py",
        "services/creator_workbench/codex_exec_supervisor_validation.py",
        "services/creator_workbench/codex_exec_supervisor_validation_process.py",
        "services/creator_workbench/codex_exec_supervisor_image.py",
        "services/creator_workbench/codex_exec_supervisor_terminal.py",
        "services/creator_workbench/codex_exec_supervisor_worker.py",
        "services/creator_workbench/host_bridge.py",
        "services/creator_workbench/codex_client.py",
        "services/creator_workbench/isolated.py",
        "services/creator_workbench/manage.py",
        "scripts/branch_suggestion.py",
        "scripts/cast-style.mjs",
        "scripts/art-style.mjs",
        "scripts/native_bridge_intent.py",
        "scripts/native_bridge_presentation.py",
        "pyproject.toml",
        "uv.lock",
    }
    source_root = Path(__file__).resolve().parents[1]

    required.update({
        "src/plotloom/image_exchange_files.py",
        "src/plotloom/image_exchange_references.py",
        "src/plotloom/image_delivery_reader.py",
        "src/plotloom/image_delivery_manifest.py",
        "src/plotloom/creative_handoff_identity.py",
        "src/plotloom/creative_exchange_files.py",
        "src/plotloom/creative_execution_pin.py",
        "src/plotloom/creative_package_projection.py",
        "src/plotloom/codex_exec_host_client.py",
        "services/creator_workbench/codex_exec_terminal_inspection.py",
        "services/creator_workbench/codex_exec_terminal_receipt.py",
    })
    assert required <= set(VALIDATOR_FILES)
    assert all((source_root / relative).is_file() for relative in VALIDATOR_FILES)
    from plotloom.codex_exec_profile import INSTRUCTION_FILES

    assert "src/plotloom/outline_preparation.py" in INSTRUCTION_FILES
    assert {
        "apps",
        "browser_annotation_api",
        "browser_use",
        "browser_use_external",
        "browser_use_full_cdp_access",
        "in_app_browser",
        "multi_agent",
        "multi_agent_v2",
        "tool_call_mcp_elicitation",
    } <= set(DISABLED_CLI_FEATURES)
    assert "view_image" not in DISABLED_CLI_FEATURES
    assert not {"web_search_cached", "web_search_request"} & set(DISABLED_CLI_FEATURES)


def test_cli_image_capabilities_are_enabled_only_for_image_attempts() -> None:
    text_flags = cli_feature_flags("text")
    image_flags = cli_feature_flags("image")

    assert text_flags == ("--disable", "image_generation", "--disable", "view_image")
    assert image_flags == ("--enable", "image_generation", "--enable", "view_image")
    with pytest.raises(ValueError, match="supported delivery domain"):
        cli_feature_flags("other")


def test_v8_requires_the_current_checked_python_permission_and_capacity_contracts():
    from pydantic import ValidationError

    from plotloom.codex_exec_contracts import CodexExecProfile
    from tests.codex_exec_fixtures import PROFILE

    value = PROFILE.model_dump(mode="json", by_alias=True)
    current = CodexExecProfile.model_validate(value)
    assert current.contract_version == "plotloom.codex-exec.v8"
    for drift in (
        {"permissionProfile": "plotloom_autopilot_delivery_v4"},
        {"textValidatorRuntimeProfile": "node_openssl_private_zsh_tmp_and_validator_aliases_v2"},
        {"textValidatorRuntimeProfile": None},
    ):
        with pytest.raises(ValidationError, match="isolated checked-lock runtime"):
            CodexExecProfile.model_validate(value | drift)
    retained_v6 = CodexExecProfile.model_validate(value | {
        "contractVersion": "plotloom.codex-exec.v6",
        "maxProcesses": 1, "maxTextProcesses": None, "maxImageProcesses": None, "maxQueuedJobs": None,
        "permissionProfile": "plotloom_autopilot_delivery_v4",
        "textValidatorRuntimeProfile": "node_openssl_private_zsh_tmp_and_validator_aliases_v2",
    })
    assert retained_v6.profile_hash != current.profile_hash


def test_empty_catalog_decoder_is_bound_into_the_validator_profile(observed_cli):
    module, executable, source, _observation = observed_cli
    first = module.build_codex_exec_profile(executable, source_root=source)
    leaf = source / 'src/plotloom/codex_exec_catalog.py'
    assert leaf.is_file() and 'src/plotloom/codex_exec_catalog.py' in module.VALIDATOR_FILES
    leaf.write_text(leaf.read_text() + '\n# Test-owned changed decoder identity.\n')
    changed = module.build_codex_exec_profile(executable, source_root=source)
    assert changed.validator_hash != first.validator_hash
    assert changed.profile_hash != first.profile_hash
