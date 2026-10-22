"""Server-owned H3 backend composition, independent of installation storage."""
from ...config import PlotloomSettings, VideoProviderSettings
from .adapter import H3_CATALOG_ID, H3_PROFILES_BY_ID, MiniMaxH3GatewayAdapter
from .transport import MiniMaxH3GatewayTransport


def build_h3_backend(settings: PlotloomSettings | VideoProviderSettings | None, *, enabled: bool):
    """The composition owner supplies opt-in; ambient settings cannot enable it."""
    if not enabled:
        return None, None
    if settings is None or settings.video_api_key is None:
        raise RuntimeError("H3 gateway requires VIDEO_MODEL_API_KEY")
    if settings.video_provider != "minimax_h3_gateway" or settings.video_model not in {H3_CATALOG_ID, *H3_PROFILES_BY_ID}:
        raise RuntimeError("H3 gateway runtime must use the trusted MiniMax H3 catalog")
    return (
        MiniMaxH3GatewayTransport(settings.video_api_key.get_secret_value(), base_url=settings.video_base_url),
        MiniMaxH3GatewayAdapter(),
    )
