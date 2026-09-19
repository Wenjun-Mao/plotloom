# ADR 0067: Read-only story-and-branch prototype

Status: Accepted, 2026-09-18.

## Context

The F1B section map compiles to the canonical `StoryGraph`; F4 accepts one
script revision whose `sectionBindings` map those same stable section IDs to
episodes. The workbench presents each owner separately, so a creator cannot
comfortably read a route without navigating dense editors or raw JSON.

## Decision

Add an opt-in, full-width `?view=story-prototype&project=<id>` reader. It reads
the existing `story_graph` stage plus the existing accepted F4 script endpoint.
`deriveRoutes` remains the route derivation owner. The reader applies
`sectionBindings` only to locate the script episode for each graph node; it
does not persist a graph, route, script, selection, or draft and exposes no
save/accept/generation action.

The page labels its Chinese interface separately from English source content.
It displays accepted script revision/hash as technical detail and identifies
the original upstream report as distinct from the current accepted revision.
It does not embed or transform the report, preserving its sandbox boundary.

## Consequences and deferred work

- A route reader can show only graph nodes with accepted script bindings; a
  project missing either owner receives a clear read-only error, not a demo
  substitution.
- The currently selected route limits screenplay reading to its nodes, so a
  mutually exclusive sibling ending does not appear in the reader.
- This is a U2 presentation prototype, not the U1–U4 redesign, localization
  framework, F5 production-media connection, or Play replacement.
- Pinned `novel-script` and `novel-storyboard` renderers support Chinese and
  English report chrome, but preserve authored data. Storyboard prompt language
  is independent and defaults to English. A whole-workflow language decision
  therefore remains deferred; this prototype does not translate existing
  English source or change prompt ownership.
