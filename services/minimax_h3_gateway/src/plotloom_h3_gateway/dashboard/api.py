"""Read-only browser surface, reachable externally only through Tailscale Serve."""
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .health import HealthProbe
from .media import media_response
from .reader import DashboardReader, ReadError

STATIC = Path(__file__).parent / "static"


def create_dashboard(data_root: Path, *, health=None, hosts=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    reader = DashboardReader(data_root)
    probe = health or HealthProbe()
    app.state.reader = reader
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts or [
        "gx10-1523.tail6040ad.ts.net", "127.0.0.1", "localhost",
    ])

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        if request.headers.get("sec-fetch-site") == "cross-site":
            response = JSONResponse({"error": "cross_site_request_refused"}, status_code=403)
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'none'"
        )
        return response

    @app.exception_handler(ReadError)
    async def read_error(request, error):
        return JSONResponse({"error": error.code}, status_code=error.status)

    @app.get("/dashboard")
    def redirect():
        return RedirectResponse("/dashboard/", status_code=307)

    @app.get("/dashboard/")
    def page():
        return FileResponse(STATIC / "index.html", media_type="text/html")

    @app.get("/dashboard/assets/{name}")
    def asset(name: str):
        types = {"dashboard.js": "text/javascript", "dashboard.css": "text/css", "favicon.svg": "image/svg+xml"}
        if name not in types:
            raise ReadError("not_found", 404)
        return FileResponse(STATIC / name, media_type=types[name])

    @app.get("/dashboard/api/overview")
    def overview():
        try:
            value = reader.overview()
        except ReadError as error:
            value = {"database": "unavailable", "error": error.code, "queue": [],
                     "queued": None, "active": None}
        return {**value, "gateway": probe.get()}

    @app.get("/dashboard/api/jobs")
    def jobs(search: str = "", backend: str = "", status: str = "", cursor: str = "",
             limit: int = Query(default=50, ge=1, le=100)):
        return reader.jobs(search=search, backend=backend, status=status, cursor=cursor, limit=limit)

    @app.get("/dashboard/api/jobs/{job_id}")
    def job(job_id: str):
        return reader.detail(job_id)

    @app.get("/dashboard/api/jobs/{job_id}/prompt")
    def prompt(job_id: str):
        return {"prompt": reader.job(job_id)["prompt"]}

    @app.api_route("/dashboard/media/{job_id}", methods=["GET", "HEAD"])
    def media(job_id: str, request: Request, download: bool = False):
        return media_response(reader, job_id, request, download=download)

    return app
