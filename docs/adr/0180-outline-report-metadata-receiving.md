# ADR 0180: Outline report metadata receiving

Status: Implemented candidate, 2026-10-16; independent/Root source review pending.

Related: [0058](0058-f1a-source-outline-review-contract.md) preserves upstream
candidate ownership and explicit acceptance;
[0112](0112-original-source-direction-and-outline-settings.md) owns saved content
settings and frozen currentness.

## Context

Consumed allocation 946f7858 passed upstream full Outline validation, then
failed rendering: top-level `lang="zh-CN"` is not an upstream report UI key.
The upstream validator omits this domain check. Saved content locale `zh-CN`
remains valid and independent. This differs from the earlier 1b891486 exact
warning-enum failure. Both allocations stay spent and strictly unresolved;
neither retained candidate nor evidence is rewritten.

## Decision

`outline_report_metadata` owns a strict typed projection of the original
Outline dictionary. Other creative fields are explicitly allowed. Omitted/null
`lang` preserves upstream default Chinese; otherwise only exact `zh`/`en` is
accepted. The temporary model is discarded. No candidate serialization,
normalization, default insertion or `params.language` requirement is added.

The same type generates `outline-report-metadata-schema.json` in new frozen
Outline inputs. The primary instruction explains UI/content separation.
Expected-schema identity is checked independently of saved-settings guards at
publication/recovery, native plan construction, manual intake and project
preparation/admission/acceptance. Input/profile identities bind the new contract.
Old contracts need not remain executable; historical evidence remains unchanged.

Error ordering is intentional:

- Native plan construction, including `_projection`, checks expected schema
  early: existing request/path/backend/revision/execution-pin guards precede it;
  frozen-package/manifest/output checks follow it. Host reconstruction errors
  retain `validation_plan_invalid`. No unchecked builder or skip flag exists.
- For a valid native plan, existing package/profile/resource/input/inventory/size
  guards run first. Descriptor-confined reads compare raw SHA/size to inventory
  before JSON parsing or metadata assertion. Invalid metadata fails before
  validation workspace/report creation or subprocess spawn. All later immutable
  candidate/package, runtime, cancellation and receipt checks remain.
- Manual intake keeps package/manifest/provenance/hash/object/HTML priority,
  then checks schema currentness and metadata on its existing parsed object.
- Direct admission keeps identity/stale/cancellation/settings/status priority.
  Ready retries check manifest conflict first, then current schema and the
  stored Outline actually returned. Prepared admission checks incoming content.
  Acceptance checks stored content after authority/CAS/stale/settings guards
  and before hashing or revision writes. All checks use the same assertion.
- New preparation retains the active-publication guard and existing pin freeze
  before schema currentness. Schema rejection rolls the enclosing transaction
  back, including the pending pin; no second pin validator or durable partial
  publication is introduced.

The upstream gitlink, validator/renderer and two Node argv remain unchanged.
No extra process, dependency, deadline or budget policy is introduced.
Installed library receiving imports no checkout validator. This applies only
to Outline; Cast's language/custom UI semantics remain separate.

## Alternatives and guardrails

Reject locale stripping or forced render language, prompt-only or host-only
patches, a competing full Outline model, vendored fixes and a global language
registry. Each either hides invalid metadata, leaves a bypass or expands scope.

Regression coverage includes exact/default values and permissive schema parity,
content-locale preservation, schema/input/profile drift, genuine Node render,
no-spawn failures, confined/digest reads, manual/direct/ready/acceptance bypasses,
and six double-fault neighborhoods matching the ordering above. Installed-wheel
smoke extends the outside-checkout probe. Focused checks precede the reviewed
story-authoring/shared-provider-dispatch contract union. Full qualification,
commit, new native generation, CI and product acceptance require separate release.
