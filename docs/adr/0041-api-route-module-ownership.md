# ADR 0041: API route module ownership

## Status

Accepted for the API modularization checkpoint.

## Context

The original API module combined public factory imports, application
composition, wire contracts, errors, route families, and a separate
project-folder authoring composition. Its size made route ownership and
dependency boundaries difficult to review without changing product behavior.

## Decision

Keep the `plotloom.api` package and its `__init__` module as the public factory façade. Normal runtime composition
delegates each existing route family through named registrar functions with
explicit repository, scheduler, and callback dependencies. Error mapping and
wire contracts live outside the façade. The project-folder authoring factory
remains a separate direct-storage composition: it does not share normal route
implementations or claim a browser-selectable persistence mode.

The approved project-folder storage destination remains decided; only a future
production cutover's timing is deferred.

## Consequences

Existing imports and HTTP contracts remain stable while ownership is visible at
the registration boundary. New contract fields must split DTO, serializer, or
protocol families instead of extending a catch-all model module beyond the
size guardrail. Any future merging of normal and project-folder routes requires
separate evidence that their storage and lifecycle contracts are equivalent.

## Implementation amendment

The normal factory now composes a typed `TextAdmissionService` with the exact
repository, scheduler, defaults, availability, resolver, and secret-source
dependencies it needs. That service owns profile projection, trusted-adapter
validation, request-scoped credential admission, process-lifetime readiness
observations, and the scheduler completion observer. It does not persist a
browser credential or introduce a generic dependency container.

The direct-storage media registrar owns managed asset import and serving,
visual intent, reviewed-keyframe choice, previews, and workbench presentation.
The image-job registrar owns only character-reference and image-job package
preparation, delivery refresh, and cancellation. Their distinct project-handle
and exchange lifetimes remain explicit; no normal-storage route or provider
runtime behavior moved into that composition.

Before the move, both factory contracts were characterized from an isolated
source export of original monolith `5ec8ef83fc3fa6efdd9b3b41f5e76a7a8c2e1daf`.
The retained regression test compares the complete canonical contract using a
provenance-bound SHA-256, preserving route, OpenAPI, signature, state, static,
lifespan, and callback evidence without generating an expectation from the
candidate.
