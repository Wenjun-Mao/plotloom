"""Own one loopback workbench, bridge and outbound shim for a test installation."""

import argparse
import json
import os
import shlex
import signal
import socket
import stat
import sys
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

import uvicorn
from host_bridge import QueueBridge, handler_for

from plotloom.api import create_project_folder_authoring_app
from plotloom.project_storage.composition import ProjectFolderStorage


@dataclass(frozen=True)
class RuntimeConfig:
    data_root: Path
    static_dir: Path
    native_executable: Path
    token_file: Path
    port: int
    bridge_port: int
    enable_h3: bool = False

    def validated(self):
        if type(self.enable_h3) is not bool:
            raise ValueError("isolated H3 opt-in must be a boolean")
        if any(not 0 <= p <= 65535 for p in (self.port, self.bridge_port)):
            raise ValueError("ports must be between 0 and 65535")
        if self.port and self.port == self.bridge_port:
            raise ValueError("workbench and bridge require distinct ports")
        if self.data_root.is_symlink():
            raise ValueError("isolated installation root must not be a symlink")
        data = self.data_root.resolve(strict=True)
        for name in ("outputs", "application"):
            child = data / name
            if not child.is_dir() or child.is_symlink():
                raise ValueError(f"isolated installation requires a real {name} directory")
        # Registry roots are durable dispatch authority. Refuse foreign paths;
        # never relocate them or release a lease to make startup succeed.
        application = data / "application"
        if any(p.is_symlink() for p in application.rglob("*")):
            raise ValueError("isolated application state must not contain symlinks")
        settings = application / "specialists" / "settings.json"
        if settings.exists():
            for root in json.loads(settings.read_text())["roots"].values():
                if not Path(root).resolve().is_relative_to(application):
                    raise ValueError("specialist dispatch root belongs to another installation")
        token_path = self.token_file.absolute()
        if token_path.is_symlink() or token_path.parent.is_symlink():
            raise ValueError("bridge credential must not be a symlink")
        token_path = token_path.resolve(strict=True)
        if token_path.is_relative_to(data):
            raise ValueError("bridge credential must stay outside installation state")
        for path, mode in ((token_path, 0o600), (token_path.parent, 0o700)):
            metadata = path.stat()
            if stat.S_IMODE(metadata.st_mode) != mode or metadata.st_uid != os.getuid():
                raise ValueError("bridge credential requires owner-only file and directory permissions")
        if not token_path.is_file():
            raise ValueError("bridge credential must be a regular file")
        token = token_path.read_text().strip()
        if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("bridge token must contain at least 32 non-whitespace ASCII characters")
        executable = self.native_executable.resolve(strict=True)
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError("native queue executable must be an executable regular file")
        static = self.static_dir.resolve(strict=True)
        if not static.is_dir():
            raise ValueError("static assets must be an existing directory")
        return RuntimeConfig(data, static, executable, token_path, self.port, self.bridge_port, self.enable_h3)


@dataclass
class IsolatedRuntime:
    app: object
    bridge: QueueBridge
    socket: socket.socket
    bridge_server: ThreadingHTTPServer
    bridge_thread: Thread
    shim: Path

    @property
    def url(self):
        return f"http://127.0.0.1:{self.socket.getsockname()[1]}"

    @property
    def bridge_url(self):
        return f"http://127.0.0.1:{self.bridge_server.server_port}"


def load_h3_configuration(trusted_checkout_root: Path):
    """Load only trusted provider settings; RuntimeConfig owns every path."""
    from plotloom.config import VideoProviderSettings
    return VideoProviderSettings.from_env(repo_root=trusted_checkout_root)


@contextmanager
def compose(config: RuntimeConfig):
    """Bind both ports before serving; release only resources owned here."""
    config = config.validated()
    with ExitStack() as resources:
        workbench_socket = resources.enter_context(socket.socket())
        workbench_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        workbench_socket.bind(("127.0.0.1", config.port))
        workbench_socket.listen(2048)
        server = ThreadingHTTPServer(("127.0.0.1", config.bridge_port), BaseHTTPRequestHandler)
        resources.callback(server.server_close)
        shim_root = Path(resources.enter_context(TemporaryDirectory(prefix="plotloom-isolated-")))
        shim = shim_root / "codex"
        client = Path(__file__).with_name("codex_client.py").resolve(strict=True)
        shim.write_text(
            f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(client))} \"$@\"\n"
        )
        shim.chmod(0o700)
        environment = os.environ | {
            "PLOTLOOM_CODEX_BRIDGE_URL": f"http://127.0.0.1:{server.server_port}",
            "PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE": str(config.token_file),
            "NO_PROXY": "127.0.0.1",
            "no_proxy": "127.0.0.1",
        }
        storage = ProjectFolderStorage(
            outputs_root=config.data_root / "outputs",
            application_data_root=config.data_root / "application",
        )
        from plotloom.video_backends.minimax_h3.runtime import build_h3_backend
        # Load only provider configuration; RuntimeConfig remains storage authority.
        settings = load_h3_configuration(Path(__file__).resolve().parents[2]) if config.enable_h3 else None
        provider, adapter = build_h3_backend(settings, enabled=config.enable_h3)
        app = create_project_folder_authoring_app(
            storage, video_provider=provider, video_adapter=adapter, static_dir=config.static_dir,
            specialist_executable=str(shim), specialist_environment=environment,
        )
        bridge = QueueBridge(config.native_executable, app.state.specialists.path, config.token_file.read_text().strip())
        server.RequestHandlerClass = handler_for(bridge)

        @app.get("/healthz")
        def health():
            return {"status": "ok"}

        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield IsolatedRuntime(app, bridge, workbench_socket, server, thread, shim)
        finally:
            server.shutdown()
            thread.join(timeout=3)


def port(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--static-dir", type=Path, required=True)
    parser.add_argument("--codex", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=port, required=True)
    parser.add_argument("--bridge-port", type=port, required=True)
    parser.add_argument("--enable-h3", action="store_true", help="Explicitly enable the trusted H3 backend for this isolated installation")
    args = parser.parse_args()
    config = RuntimeConfig(args.data_root, args.static_dir, args.codex, args.token_file, args.port, args.bridge_port, args.enable_h3)
    def exit_process(_signal, _frame):
        # Uvicorn replays SIGTERM after its own shutdown. A Python exit lets
        # the outer composition close the bridge and shim before termination.
        raise SystemExit(0)

    previous = signal.signal(signal.SIGTERM, exit_process)
    try:
        with compose(config) as runtime:
            server = uvicorn.Server(uvicorn.Config(runtime.app, host="127.0.0.1", port=args.port))
            server.run(sockets=[runtime.socket])
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    main()
