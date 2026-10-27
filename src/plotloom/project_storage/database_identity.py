"""File-attached local identity, independent of guest filesystem inode numbers."""

import ctypes
import errno
import os
import stat
import sys
from pathlib import Path
from uuid import UUID, uuid4

from ..exceptions import InvalidTransitionError

ATTRIBUTE = b"user.plotloom.runtime-incarnation"
_MISSING = {errno.ENODATA, getattr(errno, "ENOATTR", errno.ENODATA)}


def _darwin_attribute(descriptor, value=None):
    library = ctypes.CDLL(None, use_errno=True)
    if value is None:
        operation = library.fgetxattr
        operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p,
                              ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
        operation.restype = ctypes.c_ssize_t
        buffer = ctypes.create_string_buffer(64)
        result = operation(descriptor, ATTRIBUTE, buffer, len(buffer), 0, 0)
        if result >= 0:
            return buffer.raw[:result]
    else:
        operation = library.fsetxattr
        operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p,
                              ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
        operation.restype = ctypes.c_int
        # Darwin XATTR_CREATE differs from Linux's constant.
        result = operation(descriptor, ATTRIBUTE, value, len(value), 0, 0x0002)
        if result == 0:
            return None
    code = ctypes.get_errno()
    raise OSError(code, os.strerror(code))


def _read(descriptor):
    if sys.platform == "darwin":
        return _darwin_attribute(descriptor)
    return os.getxattr(descriptor, ATTRIBUTE)


def _create(descriptor, value):
    if sys.platform == "darwin":
        _darwin_attribute(descriptor, value)
    else:
        os.setxattr(descriptor, ATTRIBUTE, value, flags=os.XATTR_CREATE)


def database_identity(path: Path, *, create=False):
    """Read identity without side effects; only trusted authorization may create.

    This is an identifier, not a credential. Supported byte-only restore creates
    a different file without this attribute; deliberate metadata cloning is outside
    the authority boundary of a writable local installation.
    """
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise InvalidTransitionError("runtime identity requires one regular database file")
        try:
            value = _read(descriptor)
        except OSError as error:
            if error.errno not in _MISSING or not create:
                raise
            try:
                _create(descriptor, uuid4().hex.encode("ascii"))
                os.fsync(descriptor)
            except OSError as collision:
                if collision.errno != errno.EEXIST:
                    raise
            value = _read(descriptor)
        identity = value.decode("ascii")
        if len(identity) != 32 or UUID(hex=identity).hex != identity:
            raise ValueError("noncanonical runtime identity")
        # A replacement between open and read must not authorize the new path.
        current = path.stat(follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != (current.st_dev, current.st_ino):
            raise InvalidTransitionError("database changed during runtime identity lookup")
        return identity
    except (OSError, ValueError, AttributeError) as error:
        raise InvalidTransitionError("database has no verified local runtime identity") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
