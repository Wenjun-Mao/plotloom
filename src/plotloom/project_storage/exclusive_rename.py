"""Native implementations of one atomic, no-overwrite publication contract."""

import ctypes
import errno
import os
import sys


def rename_exclusive(source_fd: int, source: str, target_fd: int, target: str) -> None:
    """Never substitute rename/replace or a hard-link publication window."""
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        name, flag = "renameatx_np", 0x00000004  # SDK sys/stdio.h: RENAME_EXCL.
    elif sys.platform == "linux":
        name, flag = "renameat2", 1  # Linux RENAME_NOREPLACE.
    else:
        raise OSError(
            errno.ENOTSUP, "artifact publication requires native exclusive rename"
        )
    function = getattr(library, name, None)
    if function is None:
        raise OSError(
            errno.ENOTSUP, "artifact publication requires native exclusive rename"
        )
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    if function(source_fd, os.fsencode(source), target_fd, os.fsencode(target), flag):
        code = ctypes.get_errno()
        raise OSError(
            code, "artifact exclusive publication failed: " + os.strerror(code)
        )
