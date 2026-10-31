"""Explicit standalone ZIP export; private build receipts stay project-local."""
from fastapi.responses import JSONResponse, Response

from ..player_export import current_export_presentation, export_player
from ..player_export_contracts import PlayerExportRequest, PlayerExportSafetyError


def register_player_export_routes(app, opened_project):
    @app.exception_handler(PlayerExportSafetyError)
    async def unsafe_presentation(_request, error):
        return JSONResponse(status_code=422, content={"code": "player_export_private_material", "message": str(error)})

    @app.get("/api/v2/projects/{project_id}/player-export-presentation", response_model=PlayerExportRequest)
    def presentation(project_id: str):
        with opened_project(project_id) as store:
            return current_export_presentation(store)

    @app.post("/api/v2/projects/{project_id}/player-exports")
    def export(project_id: str, body: PlayerExportRequest):
        with opened_project(project_id) as store:
            content, receipt_uri = export_player(store, body)
        return Response(content, media_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="{body.game_id}.zip"',
            "X-Plotloom-Build-Receipt": receipt_uri,
            "Cache-Control": "no-store",
        })
