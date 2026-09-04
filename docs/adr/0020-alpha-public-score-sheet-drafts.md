# ADR 0020: Alpha public score-sheet drafts

## Status

Accepted.

## Context

Alpha's six blinded content files need a reviewer to return score sheets bound
to the exact commit, contract, opaque review ID, and content hash. Previously
that binding was only available in `review-mapping.private.json`, which also
contains profile, story, and sample associations that must not be disclosed to
the reviewer.

## Decision

Publish one closed `review-<opaque>.score-sheet.json` draft beside each blinded
content sample in the same staging directory and atomically expose both sets of
files. A draft includes only the fields of the final `CodexExternalReview`
shape. Its identity fields are prefilled from public pack data. The seven
reviewer decisions use draft-only sentinels: all scores are `0` and
`fatalContradiction` is `"PENDING"`.

Drafts validate through a dedicated closed draft model, but are intentionally
not final review schema values. The receipt builder detects and rejects an
unfilled draft before it can build a tracked result. Reviewers replace the
sentinels with the ordinary final schema's six 1--5 scores and boolean fatal
decision. The private map remains owner-only and is never used to construct a
public draft.

## Rejected alternatives

- **Share the private map with reviewers.** It exposes the anonymous
  profile/story/sample associations that blinding is meant to protect.
- **Use a valid low score as a pending marker.** A real failed review could
  equal that value, so the receipt builder could not reliably distinguish an
  unfinished draft from an intentional evaluation.
- **Publish templates after the content pack.** It creates a partial public
  release surface and breaks the pack's atomicity contract.

## Consequences and guardrails

- Public drafts must remain closed and contain no profile, story, sample,
  provider, run, prompt, or response fields.
- The final review schema remains 1--5 scores and a boolean fatal decision.
- Tests prove every qualified pack publishes paired drafts atomically and that
  the receipt builder rejects an unfilled draft.
