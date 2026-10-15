"""Frozen child environments and narrow filesystem permissions."""
from __future__ import annotations

import json
import os
from hashlib import sha256

from codex_exec_supervisor_errors import CodexExecSupervisorError

from plotloom.codex_exec_auth import credential_free_environment


def _text_openssl_config(profile):
    from plotloom.codex_exec_profile import (
        NODE_OPENSSL_CONFIG,
        TEXT_VALIDATOR_RUNTIME_PROFILE,
    )

    if (profile.contract_version != "plotloom.codex-exec.v8"
            or profile.text_validator_runtime_profile != TEXT_VALIDATOR_RUNTIME_PROFILE):
        raise CodexExecSupervisorError("Codex Exec text validator runtime profile is unsupported")
    if NODE_OPENSSL_CONFIG.is_symlink() or not NODE_OPENSSL_CONFIG.is_file():
        raise CodexExecSupervisorError("Codex Exec Node validator OpenSSL configuration is unavailable")
    return NODE_OPENSSL_CONFIG


class CodexExecSupervisorEnvironmentMixin:
    @staticmethod
    def _disabled_python_cache(private_dir):
        from plotloom.codex_exec_runtime_tree import stable_file_hash

        marker = private_dir / "python-cache-disabled"
        try:
            descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
        if stable_file_hash(marker) != sha256(b"").hexdigest():
            raise CodexExecSupervisorError("Python cache fence must be the empty host-owned marker")
        return marker

    def _cli_environment(self, private_dir, *, source_root, domain, source_resources=None, profile=None):
        environment = credential_free_environment()
        for name in tuple(environment):
            if name.startswith(("PYTHON", "UV_", "NODE_", "DYLD_", "LD_", "CONDA_")) or name in {
                "VIRTUAL_ENV", "OPENSSL_CONF", "PLOTLOOM_SOURCE_ROOT", "PLOTLOOM_UV",
                "PLOTLOOM_NODE", "PLOTLOOM_PYTHON", "__PYVENV_LAUNCHER__", "UV",
            }:
                environment.pop(name, None)
        (private_dir / "tmp").mkdir(mode=0o700, exist_ok=True)
        (private_dir / "uv-cache").mkdir(mode=0o700, exist_ok=True)
        environment["TMPDIR"] = str(private_dir / "tmp")
        environment["TMPPREFIX"] = str(private_dir / "tmp" / "zsh")
        environment["CODEX_HOME"] = str(self.codex_home)
        environment["UV_CACHE_DIR"] = str(private_dir / "uv-cache")
        if domain == "text":
            environment["OPENSSL_CONF"] = str(_text_openssl_config(profile))
            environment["PLOTLOOM_SOURCE_ROOT"] = str(source_root)
            tool_paths = dict(source_resources.tools) if source_resources is not None else {}
            if "node" in tool_paths:
                environment["PLOTLOOM_NODE"] = str(tool_paths["node"])
            if "python" in tool_paths:
                from plotloom.codex_exec_python_environment import (
                    inspect_checked_python_environment,
                )
                from plotloom.codex_exec_runtime_tree import python_source_identity

                current = inspect_checked_python_environment(source_root)
                source_parent, source_hash = python_source_identity(source_root)
                if (source_resources.python_environment != current.root
                        or source_resources.python_environment_hash != current.identity_hash
                        or source_resources.python_source_hash != source_hash
                        or tool_paths["python"] != current.interpreter):
                    raise CodexExecSupervisorError("Codex Exec Python resources changed before child launch")
                environment["PYTHONPATH"] = str(source_parent)
                environment["PYTHONNOUSERSITE"] = "1"
                environment["PYTHONDONTWRITEBYTECODE"] = "1"
                environment["PYTHONPYCACHEPREFIX"] = str(self._disabled_python_cache(private_dir))
                environment["UV_PROJECT_ENVIRONMENT"] = str(current.root)
                environment["UV_NO_CONFIG"] = "1"
                environment["UV_OFFLINE"] = "1"
                environment["UV_PYTHON_DOWNLOADS"] = "never"
                environment["UV_PYTHON"] = str(current.base_interpreter)
                environment["PLOTLOOM_UV"] = str(tool_paths["uv"])
                environment["PLOTLOOM_PYTHON"] = str(current.interpreter)
        return environment

    @staticmethod
    def _permission_filesystem_config(
        profile, job_root, delivery, private_dir, codex_home, source_read_paths=(), *, domain,
        additional_write_paths=(),
    ):
        values = {
            ":root": "deny",
            ":minimal": "read",
            ":tmpdir": "write",
            ":slash_tmp": "deny",
            str(codex_home): "deny",
            str(job_root / "package"): "read",
            str(delivery): "write",
            str(private_dir / "tmp"): "write",
            str(private_dir / "uv-cache"): "write",
        }
        values.update({str(path): "read" for path in source_read_paths})
        values.update({str(path): "write" for path in additional_write_paths})
        if domain == "text":
            values[str(_text_openssl_config(profile))] = "read"
        encoded = ",".join(f'{json.dumps(key)}={json.dumps(value)}' for key, value in values.items())
        return f"permissions.{profile.permission_profile}.filesystem={{{encoded}}}"
