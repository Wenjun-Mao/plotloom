# 0092 — Distinguish selection state from actions

Status: Accepted

## Context

The appearance workspace used filled primary buttons to display its selected
generation mode. The creator mistook that state for an action still to perform.
The same treatment appeared in comparison membership and retained candidates.

## Decision

Use native radio controls for mutually exclusive form modes, with a labelled
group and visible checked state. Preserve prerequisite and read-only guards.
Selection does not create, send, save or accept anything. Keep those as separate
action buttons. Multi-selection toggles expose `aria-pressed` and a visible check,
not a filled primary background. Tabs use an active underline; gallery subject
and thumbnail navigation identify the current item in text.

Do not convert action buttons to radios or disable a selected mode merely to
make it look selected. Do not rely on color alone to convey selection.

## Consequences and guardrails

No generation, persistence or acceptance semantics change. Native radios provide
keyboard selection and mutual exclusion. Component and browser tests cover mode
changes and disabled refinement; existing comparison tests retain capacity and
clear behavior. Future selection controls should follow this distinction.
