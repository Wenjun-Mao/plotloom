# Spark generation operations

Spark runs two private generation backends behind one typed gateway. The
backends have separate runtime, API, and qualification contracts; the durable
gateway FIFO is the only intentionally shared runtime boundary.

For package ownership, independent builds, affected tests and safe selective
deployment, start with [Media-service maintenance](media-services.md). It also
documents Voice Lab's participation in the shared lane and the dashboard's private
read-only SQLite contract, without combining their distinct storage lifetimes.

## Choose the correct document set

| Need | MiniMax-H3 video | Qwen-Image-2.1 image |
| --- | --- | --- |
| Chinese colleague API guide | [H3 client guide](minimax-h3-gateway-client-guide.md) | [Qwen client guide](qwen-image-gateway-client-guide.md) |
| Deploy, operate, or troubleshoot | [H3 operator manual](minimax-h3-gateway-manual.md) | [Qwen operator manual](qwen-image-gateway-manual.md) |
| Reproduce the engine installation | [H3 reproducible setup](../../services/minimax_h3_gateway/docs/h3-reproducible-setup.md) | [Qwen reproducible setup](../../services/minimax_h3_gateway/docs/qwen-image-spark-setup.md) |
| Understand sampling or evaluation choices | [H3 rationale and operations](../../services/minimax_h3_gateway/docs/h3-rationale-and-operations.md) | [ADR 0072](../adr/0072-shared-qwen-image-and-h3-generation-lane.md) and [ADR 0073](../adr/0073-qwen-image-reviewed-canvas-contract.md) |
| Draft and review single-image provider prompts | [Living H3 prompt-writing playbook](h3-prompt-writing-playbook.md) and [offline complete-prompt example](../verification/2026-09-24-h3-reviewed-directions-offline.md) | Not applicable |

## Shared boundary

The Tailnet gateway is at `http://100.64.35.71:8090`. `/health` is an
unauthenticated readiness endpoint; job creation, status, cancellation, and
downloads require the team bearer value. Keep the direct ComfyUI and SGLang
services loopback-only.

One durable SQLite FIFO serializes managed inference: at most one H3 ComfyUI,
Qwen SGLang or Voice Lab generation runs at a time. It is intentionally an unlimited queue;
source download, input decoding, and managed-output transfer do not hold the
GPU lane. See [ADR 0072](../adr/0072-shared-qwen-image-and-h3-generation-lane.md)
and its Voice Lab extension in [ADR 0097](../adr/0212-published-voice-performance-takes-and-shared-admission.md).

Both backends retain their gateway-managed delivery for 72 hours, and retain
the job record plus transient gateway input for at most 30 days. Import a
selected result into Plotloom or another durable asset store before expiry.

Do not treat this index as an API reference. Start with the backend-specific
guide above so a Qwen image setting is never confused with an H3 video setting.

## Creator workbench access

The separate [private Tailscale workbench guide](../../services/creator_workbench/README.md#private-colleague-access-over-tailscale)
covers the colleague HTTPS URL, shared-admin trust boundary, required running
services, verification limits and endpoint-scoped disable command. It is not
the Spark gateway and does not expose its bearer credential or directly publish
the Mac bridge's listener/token. Workbench co-admins can still invoke the
configured native queues through the workbench.
