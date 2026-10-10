"""Browser-fixture socket ownership; never probe, release and rebind."""
from contextlib import contextmanager
from collections.abc import Iterator
import socket


@contextmanager
def owned_loopback_listener(port: int = 0) -> Iterator[socket.socket]:
    if not 0 <= port <= 65535:
        raise ValueError("fixture listener port must be between 0 and 65535")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
        listener.listen(128)
        yield listener
