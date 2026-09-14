# Three-story Alpha acceptance

> **Policy update (2026-09-07):** [ADR 0024](adr/0024-pluggable-text-backends-and-independent-qualification.md)
> approves independently qualifying each supported backend: nine runs, at least
> 30/36 first-pass stages, and three blinded reviews with the existing quality
> thresholds. Implementation is pending. This page's commands and 18-run/six-review
> requirements describe the existing two-profile `alpha_chinese_three_story.v1`
> mode; they remain exact and must not be used to label a nine-run result as a
> legacy Alpha pass. The current llama canary is not qualification evidence.

This is the repeatable Alpha acceptance runner. It is an operator run against
two already-saved text-provider profiles and **does contact those configured
providers**, so it can incur cost. Automated tests inject a fixture provider
through the same production pipeline and never contact a provider.

Run it from its source checkout after the two intended profiles have been saved
in the configured application-data directory. The review directory must be an
empty, local **absolute** directory outside that checkout. The runner rejects
any path inside the checkout even if it is ignored by Git:

Before starting the 18-run matrix, probe both profiles and verify that each
provider reports an effective per-request (or per-slot) context at least as
large as the profile's declared context. A multi-slot service may divide a
process-wide context pool. Correct that service/profile mismatch first; a run
truncated at the smaller physical limit is not Alpha evidence.

```sh
uv run python scripts/alpha_acceptance.py \
  --profile local_profile_a \
  --profile local_profile_b \
  --review-directory /absolute/path/to/untracked-alpha-review \
  --commit "$(git rev-parse --verify HEAD^{commit})"
```

`--commit` is optional, but when supplied it must be an exact 40-character
hexadecimal commit identifier **equal to the source checkout's current
`HEAD`**. The Alpha publication runner resolves the checkout that owns the
running source module and refuses to run if it contains any tracked or
untracked non-ignored change; passing an older or prepared SHA does not bypass
this check. If omitted, the runner resolves that same `HEAD` itself. This
applies to every caller of the publication runner, not only the CLI. The
external review directory is outside the checkout and is not part of this Git
check. Neither choice records working-tree content in the receipt. The
publication boundary repeats the same clean-tree and HEAD check after all
model runs and before returning receipts or publishing a review pack, so a
checkout changed during the long matrix cannot be labelled as the starting
commit.

The runner executes exactly 18 disposable runs: three fixed, versioned Chinese
briefs × three repeats × two saved profiles. Each run goes through the normal
four-stage production pipeline, including planning, work-unit execution,
validation, sealing, and atomic canonical installation. Alpha reads the current
application profile records through one read-only SQLite transaction; it never
initializes schema or writes to that installation store. Every temporary project
folder, separate application store, artifact, prompt, and response is removed
after execution.

Standard output is JSONL receipt data. Every receipt has only the validated
run-code `commit`, the production `contractHash`, anonymous `profileId`,
`storyId`, and `sampleId`, status, stable issue codes, token totals, duration,
and a `scores` object containing first-pass stage counts and maximum attempts
per work unit. This is a strict whitelist. It deliberately excludes real
profile IDs, endpoints, models, IP addresses, credentials, prompts, responses,
run IDs, provider configuration, and story/workload hashes.

Qualification requires all 18 runs to succeed, every work unit to remain at or
below three attempts, zero `provider.outcome_unknown` and `conformance.*`
invariants (including partial canonical installation), and at least 30 of 36
first-pass stages for each anonymous profile.

Only after all 18 runs and qualification succeed, the runner atomically
publishes six deterministically selected samples: repeat one for every
anonymous profile/story pair. Before publication it applies a cryptographically
secure random permutation and assigns opaque random IDs, so neither filename
nor file order exposes profile or story order. Each `review-<opaque>.json`
file contains only the four canonical authoring payloads (`storyBible`,
`storyGraph`, `sceneBeats`, `storyboard`), with no run, profile, provider,
trace, prompt, response, or receipt metadata.

The same atomic pack includes a paired
`review-<opaque>.score-sheet.json` for every content file. These public
templates prefill only the commit, contract hash, opaque review ID, content
hash, fixed rubric/reviewer identities, six rubric fields, and
`fatalContradiction`; they contain no profile, story, sample, provider, run,
prompt, or response data. They let reviewers bind their score sheets without
ever receiving the private map. A template deliberately uses score `0` and
`fatalContradiction: "PENDING"` as visible draft sentinels. Before submission,
replace all six zeroes with integer scores from 1 through 5 and replace
`"PENDING"` with `true` or `false`. The final receipt builder rejects an
unfilled template; a draft can never be counted as a passing review.

The same external directory also contains `review-mapping.private.json`. It is
the sole unblinding map, is created with owner-only `0600` permissions, and
maps an opaque review ID to the anonymous profile/story/sample aliases and the
content hash. The map also freezes the exact run-code commit and production
contract hash for the whole six-sample pack. It stays outside the checkout, is
never included in stdout or a tracked receipt, and must not be shared with a
reviewer. Share only the six content files; retain the private mapping locally
for the release owner to bind returned scores back to both the reviewed content
and the code/contract that produced it. Share the six content files and their
six paired score-sheet templates only; never share the private mapping.

## Independent Codex review gate

After a qualified six-file pack exists, an independent Codex reviewer may
submit one closed JSON score sheet per opaque review ID. This is an engineering
quality gate named `codex_external_review`, not a human product Approval. A
score sheet accepts exactly: commit, contract hash, opaque review ID, content
hash, rubric version, fixed reviewer value, six integer scores from 1 to 5,
and boolean `fatalContradiction`. It cannot carry comments, story text, prompt
text, profile/story/run/model/provider identity, or any other field. The
published `0`/`"PENDING"` files are drafts, not score sheets accepted by this
final schema.

The release owner loads the frozen pack provenance from the private map,
validates each sheet against it, and uses the closed receipt builder to record
only the validated blinded score sheets, the commit/contract hash derived from
that pack, secret-free aggregate gate result, and stable issue codes in a
tracked receipt. There is no caller-supplied commit or contract override, so an
old scored pack cannot be relabelled as a newer build. Malformed raw sheets are
never echoed into that receipt. The gate passes only when all six samples are
present and identity bound, none has a fatal contradiction, every individual
score is at least 3, every sample average is at least 3.5, and every rubric
dimension has a median of at least 4. This gate has not yet been executed merely
because the runner or these rules exist; no documentation or receipt should
claim completion until the six blinded reviews have been validated.
