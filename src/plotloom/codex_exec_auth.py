"""Host-side authentication readiness for the source-owned Codex Exec boundary."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .codex_exec_contracts import CodexExecReadiness

AUTHENTICATION_STORE = "file"


def credential_free_environment(environment: dict[str, str] | None = None) -> dict[str, str]:
    """Keep credential-like inherited variables out of supervisor children."""
    result = dict(os.environ if environment is None else environment)
    secret_markers = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    for name in tuple(result):
        if any(marker in name.upper() for marker in secret_markers):
            result.pop(name, None)
    return result


def resolve_codex_home(
    environment: dict[str, str] | None = None,
    *,
    forbidden_roots: tuple[Path, ...] = (),
) -> Path:
    """Resolve the existing host auth home without creating or relocating it."""
    selected = environment if environment is not None else os.environ
    raw = selected.get("CODEX_HOME")
    home = Path(raw).expanduser() if raw else Path.home() / ".codex"
    if home.is_symlink() or not home.is_dir():
        raise ValueError("Codex authentication home must already be a regular directory")
    resolved = home.resolve(strict=True)
    metadata = resolved.stat()
    if not resolved.is_dir() or metadata.st_uid != os.getuid():
        raise ValueError("Codex authentication home must belong to the current user")
    for root in forbidden_roots:
        candidate = root.expanduser().resolve(strict=False)
        if resolved.is_relative_to(candidate):
            raise ValueError("Codex authentication home cannot be inside project or supervisor state")
    return resolved


def check_codex_exec_readiness(
    executable: Path,
    *,
    environment: dict[str, str] | None = None,
    forbidden_roots: tuple[Path, ...] = (),
    source_root: Path | None = None,
    timeout_seconds: float = 8.0,
) -> CodexExecReadiness:
    """Check the local login marker using the exact store/home used by exec."""
    try:
        if source_root is not None:
            from .codex_exec_resources import validator_toolchain_hash
            from .codex_exec_runtime_tree import python_source_identity

            validator_toolchain_hash(source_root)
            python_source_identity(source_root)
        auth_home = resolve_codex_home(environment, forbidden_roots=forbidden_roots)
        child_environment = credential_free_environment(environment)
        child_environment["CODEX_HOME"] = str(auth_home)
        result = subprocess.run(
            [
                str(executable),
                "--config",
                f'cli_auth_credentials_store="{AUTHENTICATION_STORE}"',
                "login",
                "status",
            ],
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            env=child_environment,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return CodexExecReadiness(state="unavailable")
    return CodexExecReadiness(
        state="ready" if result.returncode == 0 else "not_authenticated"
    )
