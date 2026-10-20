"""Pin an exact managed file before streaming bounded original-byte ranges."""
from __future__ import annotations

import os
import re
import stat

from fastapi.responses import Response, StreamingResponse

from .reader import DashboardReader, ReadError


class PinnedResponse(StreamingResponse):
    def __init__(self, handle, *, offset, length, status, headers, mime):
        self.handle = handle

        def chunks():
            handle.seek(offset)
            remaining = length
            while remaining:
                chunk = handle.read(min(65536, remaining))
                if not chunk:
                    raise OSError("managed output changed during transfer")
                remaining -= len(chunk)
                yield chunk

        super().__init__(chunks(), status_code=status, headers=headers, media_type=mime)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            self.handle.close()


def media_response(reader: DashboardReader, job_id: str, request, *, download=False):
    row = reader.job(job_id)
    state = reader.availability(row)
    if state != "available":
        raise ReadError("output_" + state, 409 if state == "not_ready" else 410)
    name = reader.output_name(row)
    directory = None
    handle = None
    try:
        # The pinned fd closes the validate/open race, including directory replacement.
        directory = os.open(reader.outputs, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        handle = os.fdopen(fd, "rb")
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size <= 0 or info.st_size != row["output_size_bytes"]:
            raise ReadError("output_unavailable", 410)
        size = info.st_size
        mime = "video/mp4" if row["backend"] == "h3_video" else "image/png"
        headers = {"Accept-Ranges": "bytes", "Cache-Control": "no-store",
                   "Content-Disposition": f'{"attachment" if download else "inline"}; filename="{name}"'}
        digest = row.get("output_sha256")
        if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest):
            headers["ETag"] = '"' + digest + '"'
        start, end, status_code = 0, size - 1, 200
        value = request.headers.get("range")
        if_range = request.headers.get("if-range")
        if value and (not if_range or if_range == headers.get("ETag")):
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", value.strip())
            if not match or not any(match.groups()):
                raise ValueError()
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            else:
                suffix = int(last)
                if suffix <= 0:
                    raise ValueError()
                start = max(0, size - suffix)
            if start >= size or end < start:
                raise ValueError()
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
            status_code = 206
        length = end - start + 1
        headers["Content-Length"] = str(length)
        if request.method == "HEAD":
            handle.close()
            return Response(status_code=status_code, headers=headers, media_type=mime)
        response = PinnedResponse(handle, offset=start, length=length, status=status_code,
                                  headers=headers, mime=mime)
        handle = None
        return response
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}", "Cache-Control": "no-store"})
    except OSError as error:
        raise ReadError("output_unavailable", 410) from error
    finally:
        if handle is not None:
            handle.close()
        if directory is not None:
            os.close(directory)
