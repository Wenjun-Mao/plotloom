"""Runtime capability is API presentation, never persisted proposal evidence."""
from typing import Annotated, Literal

from pydantic import Field

from ..domain import CamelModel
from ..production_bridge_contracts import ProductionBridgeState

# The domain state declares its job later in that module; resolve its completed
# namespace before deriving the API-only response contract.
ProductionBridgeState.model_rebuild()


class BridgeIntentAvailable(CamelModel):
    status: Literal["available"] = "available"


class BridgeIntentUnavailable(CamelModel):
    status: Literal["unavailable"] = "unavailable"
    reason: Literal["not_configured"] = "not_configured"


class ProductionBridgeRuntimeState(ProductionBridgeState):
    intent_generation: Annotated[BridgeIntentAvailable | BridgeIntentUnavailable, Field(discriminator="status")]


class BridgeIntentUnavailableError(Exception):
    """Only the absent runtime wiring, not provider readiness or transport errors."""
