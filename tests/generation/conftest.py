from __future__ import annotations

from collections import deque

from plotloom.generation.contracts import (
    GenerationRequest,
    ProviderCapabilities,
    ProviderResponse,
)
from plotloom.generation.secrets import InMemorySecretVault, SecretLease


class QueueProvider:
    name = "queue-provider"

    def __init__(self, responses: list[str], *, json_schema: bool) -> None:
        self.capabilities = ProviderCapabilities(json_schema=json_schema)
        self._responses = deque(responses)
        self.requests: list[GenerationRequest] = []
        self.observed_secrets: list[str] = []

    def generate(
        self,
        request: GenerationRequest,
        secret: SecretLease,
    ) -> ProviderResponse:
        self.requests.append(request)
        with secret.reveal() as api_key:
            self.observed_secrets.append(api_key)
        content = self._responses.popleft()
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            raw={
                "id": f"response-{len(self.requests)}",
                "model": request.model,
                "choices": [
                    {
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            },
        )


def secret_lease(*, max_uses: int = 1) -> tuple[InMemorySecretVault, SecretLease]:
    vault = InMemorySecretVault()
    vault.put("text-provider", "test-provider-secret")
    return vault, vault.lease("text-provider", max_uses=max_uses)
