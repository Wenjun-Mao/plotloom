# ADR 0065: F5A source-bound storyboard review revisions

Status: Accepted, 2026-09-18.

## Context

F4 now owns an accepted upstream `script.json` with an exact stable
section-to-episode mapping and a complete transitive currentness binding.
The pinned `novel-storyboard` skill consumes that script and produces raw
storyboard JSON plus a derived HTML report. Plotloom's legacy storyboard,
shot, playback, approval, and media paths are independent product owners; using
them as a receiving shape would reconstruct the retired V2 Bible/SceneBeats
path and create a competing shot or production authority.

## Decision

F5A owns one source-bound review lifecycle. It freezes the current accepted F4
script revision/content hash, its complete inherited input binding, and the
ordered section/episode mapping in a manual F0 handoff. It persists the raw,
validated upstream `storyboard.json` and its original derived report as an
accepted *review revision*. A new candidate or an explicit cancellation is the
only way to change that review state; acceptance does not install canonical
shots or authorise media work.

The pinned `novel-storyboard` validator is run against the frozen script and
execution-only upstream outline/cast inputs. The receiving check also requires
the candidate's episode set and order to exactly match F4's frozen mapping.
Any change to the accepted script or an inherited source, outline, map, graph,
cast, art, target, timing allocation, or mapping makes candidate admission and
review state stale.

## Consequences

The HTML report stays an inspectable, sandboxed derived artifact, never an
editable or canonical authority. F5A introduces no V2 Bible/SceneBeats
projection, shot/media compiler, player change, selected reference, dispatch
control, or H3-duration behaviour. A later product integration must make its
own source-to-product ownership decision and cannot treat a review revision as
an approved production payload.
