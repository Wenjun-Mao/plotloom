# ADR 0035: Backend-owned video modules and service packages

## Context

MiniMax-H3 began as a bounded gateway and then acquired a Plotloom adapter,
transport, capability record, gateway workflow, browser presentation, and
acceptance fixtures. Although its runtime contract was narrow, those files
were scattered across generic Plotloom modules and a core-package gateway.
That made the H3 deployment difficult to inspect or hand off, and left the
generic video lifecycle coupled to one adapter class through `isinstance`
branches.

## Decision

Keep the generic immutable video-job lifecycle and adapter protocols in
`plotloom.video_provider` and `plotloom.video_jobs`. Put each provider's
implementation below `plotloom.video_backends/<backend>/`.

The first relocated package is
`plotloom.video_backends.minimax_h3`, which owns the H3 capability record,
adapter, strict gateway transport, and H3-only frontend/E2E support. The
generic lifecycle asks an adapter for its public capability projection and an
optional versioned production contract; it does not branch on the H3 class.

The Spark gateway is a separately packaged service under
`services/minimax_h3_gateway/src/plotloom_h3_gateway`. Its Dockerfile copies
only that package. The service owns the ComfyUI workflow/profile and durable
gateway state; the Plotloom client adapter never imports its ComfyUI graph.

## Consequences

- A future backend gets a sibling package and a separate service only when it
  has an independently deployed runtime. It must not add model-name special
  cases to another backend.
- Historical snapshot schemas, adapter IDs, HTTP envelopes, and job recovery
  semantics remain unchanged by this directory refactor.
- Gateway tests add their service-owned source directory only for isolated
  tests, mirroring the Docker package boundary rather than making the gateway
  an accidental dependency of the main Plotloom wheel.
- The [H3 operator manual](../operations/minimax-h3-gateway-manual.md) is the
  human handoff entry point; source profile, tests, and this ADR remain its
  versioned implementation evidence.

## Alternatives rejected

- Keeping H3 classes in `video_provider.py`: simple in the short term, but
  provider-specific growth would make the generic contract a catch-all.
- Moving the entire video lifecycle into the H3 package: it would falsely make
  approvals, snapshots, selection, and persistence H3-specific.
- Leaving the gateway under `src/plotloom`: that implies the main Plotloom
  wheel owns a remote service dependency, whereas Docker is the actual service
  packaging boundary.
