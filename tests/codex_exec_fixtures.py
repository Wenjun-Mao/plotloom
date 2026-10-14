"""Synthetic source-bound profile for isolated orchestration tests only."""

from plotloom.codex_exec_contracts import CodexExecProfile


PROFILE = CodexExecProfile(
    executableSha256="a" * 64,
    cliVersion="codex-cli test-fixture",
    model="gpt-6.1-sol",
    reasoningEffort="medium",
    capabilities=(
        "exec_json_events_v1",
        "session_rollout_v1",
        "image_gen_event_v1",
        "delivery_directory_write_v1",
    ),
    instructionHash="b" * 64,
    validatorHash="c" * 64,
    sandboxProfile="read_only_with_delivery_write",
    maxRuntimeSeconds=1800,
    maxEventBytes=50_000_000,
    maxOutputBytes=500_000_000,
    maxImageOutputs=4,
)


def install_profile(registry):
    """Inject a deterministic profile without contacting a host or provider."""
    registry.codex_exec_profile = lambda: PROFILE
    return registry
