"""Read-only terminal evidence inspection after the complete child group exits."""
from __future__ import annotations
from plotloom.codex_exec_runtime import assert_file_changes_confined, locate_exact_session, package_tree_hash, read_exec_events, CodexExecRuntimeError
from plotloom.codex_exec_telemetry import read_cli_session


def inspect_terminal(attempt, profile, job_root, stdout_path, codex_home):
    if package_tree_hash(job_root, max_total_bytes=profile.max_output_bytes) != attempt.package_hash:
        raise CodexExecRuntimeError("Codex Exec frozen package changed during the process")
    stream = read_exec_events(stdout_path, max_event_bytes=profile.max_event_bytes, max_total_bytes=profile.max_output_bytes)
    assert_file_changes_confined(stream, job_root / "delivery")
    session_path = locate_exact_session(codex_home, stream.session_id)
    session = read_cli_session(
        session_path,
        stream.session_id,
        max_event_bytes=profile.max_event_bytes,
        max_total_bytes=profile.max_output_bytes,
    )
    return stream, session, session_path


def inspect_domain_evidence(attempt, stdout_path, session_path, stream, session,
                            job_root, source_root) -> bool:
    """Reject text/ImageGen contamination and require strict image no-dispatch proof."""
    if attempt.domain == "text" and (session.image_calls or session.image_events or session.reference_views):
        return False
    if attempt.domain == "image" and not session.image_calls and not session.image_events:
        from plotloom.codex_exec_recovery import prove_no_remote_dispatch
        prove_no_remote_dispatch(stdout_path, session_path, stream.session_id,
                                 job_root=job_root, source_root=source_root)
    return True
