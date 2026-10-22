"""HTTP freshness for the workbench's stable-name static build (ADR 0104)."""

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class RevalidatingStaticFiles(StaticFiles):
    """Allow cached bytes only after validating them against the deployed build."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        # HTML, JS and CSS share stable URLs across deployments. Apply this
        # after StaticFiles chooses 200/304 so either response retains policy.
        response.headers["Cache-Control"] = "no-cache"
        return response
