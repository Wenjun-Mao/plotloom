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
