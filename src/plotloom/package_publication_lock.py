"""Atomic cooperating lock-file creation before immutable package publication."""
import os


def open_publication_lock(path, *, dir_fd=None):
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        return os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dir_fd)
    except FileExistsError:
        # The owner never unlinks this empty lock. A concurrent creator's
        # existing entry must be reopened without repeating creation.
        return os.open(path, flags, dir_fd=dir_fd)
