# 0115 Workspace Home navigation

Status: Accepted, 2026-10-04.

## Problem

The upper-left brand is display-only, so the creator has no direct return to
the start screen. A plain link would bypass the workspace's draft gate. An
empty project ID alone cannot express Home: blank and teaching workspaces also
use an empty ID while navigating between their own pages.

## Decision

Make the brand a native **首页** button with the accessible name **返回首页**,
visible destination cue, keyboard focus and hover feedback. Submit explicit
Home intent through the existing draft-gated workspace navigation. Once
admitted, clear only the mounted canonical snapshot through the session owner
and display existing onboarding. Clean blank/sample sessions also reach Home;
ordinary local page changes continue to retain their snapshot.

Home does not close, archive, delete, cancel, approve or generate anything.
Existing durable draft saves and unsaved local Save/Discard/Cancel decisions
remain authoritative. Refused saves keep the current workspace and input.
Saved project routes remain reachable through history and the project directory.
Disable the control during hydration, canonical saves, Close/Delete or snapshot
transitions so it cannot detach the workspace from admitted operations.

## Guardrails

Cover blank/sample Home, local Cancel and Save, durable draft recovery, retained
project lifecycle and browser Back/Forward. Keep public APIs and persistence
unchanged; test mutations use disposable fixtures. The Chinese manual remains
deferred until the owner's same-day walkthrough changes settle.
