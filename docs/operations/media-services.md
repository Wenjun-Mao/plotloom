# Using and maintaining media services

Gateway, dashboard and Voice Lab source is maintained in private [Wenjun-Mao/media-services](https://github.com/Wenjun-Mao/media-services). Plotloom keeps its application, creator-workbench, H3 HTTP adapter/catalog and consumer checks. Service users need no repository access; current service URLs/authentication are unchanged.

- [H3 video colleague guide](minimax-h3-gateway-client-guide.md), including 1–9 ordered references and optional 0–3 character voices.
- [Qwen image colleague guide](qwen-image-gateway-client-guide.md).
- [Voice Lab workflow](voice-lab-client-guide.md) and [published voices/takes API](voice-takes-client-guide.md).
- Owner/developer: [canonical service release and rollback instructions](https://github.com/Wenjun-Mao/media-services/blob/main/docs/operations/media-services.md).

Plotloom consumes the authenticated HTTP contract; do not import backend source or add a sibling-checkout runtime dependency. Backend tests/builds live with their services. Plotloom retains adapter, application and creator-workbench consumer checks; changed contracts need an actual Plotloom-transport-to-installed-gateway journey, with inference faked where appropriate.

Extraction preserves current deployment artifacts/data/model locations and the retained Application Support workbench checkout. It does not activate the separately pending client-IP change, restart workbench or enable Tailnet. CI stays off unless Wenjun explicitly requests a run.
