# ADR 0139: Profile owned text credentials

Status: adopted under the owner's current-only configuration requirement,
2026-10-08. Supersedes the default-profile environment fallback in the M1.5
configuration contract; frozen jobs and session-key ownership are unchanged.

## Problem and decision

Configuration review found an explicit pre-M1.5 compatibility branch:
`default` could borrow `TEXT_MODEL_API_KEY` or `ATLASCLOUD_API_KEY`, while all
other profiles used their exact namespaced credential. This hid missing default
configuration and could attach an unrelated provider credential to its endpoint.

Every text profile, including `default`, now resolves only
`PLOTLOOM_PROFILE_<UPPERCASE_PROFILE_ID>_TEXT_API_KEY`. An absent or empty variable
means no server key; the existing session-key and authentication-mode contracts
still determine submission eligibility. Keys remain ephemeral, server-only and
excluded from saved public profiles, projects and frozen packages.

No alias reader, fallback, automatic credential copying or settings rewrite is
provided. Image/video keys and native specialist transport are unchanged.
Deployment must explicitly configure the intended profile before API inference;
this change does not enable a provider or authorize a paid call.

## Alternatives and guardrails

Retaining a default-only alias would preserve the hidden configuration split;
automatically copying an old key would assume its intended provider ownership.
Both are rejected. Tests require named-default resolution, empty/missing refusal
despite old globals, other-profile isolation and non-overriding trusted dotenv
loading. Existing profile-scoped session leases remain independently tested.
