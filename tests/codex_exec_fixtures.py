"""Synthetic source-bound profile for isolated orchestration tests only."""

from plotloom.codex_exec_contracts import CodexExecProfile, CodexExecReadiness


PROFILE = CodexExecProfile(
    contractVersion="plotloom.codex-exec.v7",
    executableSha256="a" * 64,
    cliVersion="codex-cli test-fixture",
    model="gpt-6.1-sol",
    reasoningEffort="medium",
    capabilities=(
        "exec_json_events_v1",
        "session_rollout_v1",
        "image_gen_event_v1",
        "image_reference_view_v1",
        "delivery_directory_write_v1",
    ),
    instructionHash="b" * 64,
    validatorHash="c" * 64,
    authenticationStore="file",
    permissionProfile="plotloom_autopilot_delivery_v5",
    toolProfile="plotloom_autopilot_tools_v4",
    textValidatorRuntimeProfile="node_openssl_private_zsh_tmp_and_checked_python_v3",
    maxRuntimeSeconds=1800,
    maxEventBytes=50_000_000,
    maxOutputBytes=500_000_000,
    maxImageOutputs=4,
)


def install_profile(registry):
    """Inject a deterministic profile without contacting a host or provider."""
    registry.codex_exec_profile = lambda: PROFILE
    registry.codex_exec_readiness = lambda: CodexExecReadiness(state="ready")
    return registry
