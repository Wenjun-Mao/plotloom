# Three-story Alpha acceptance

This is the repeatable Alpha acceptance runner. It is an operator run against
two already-saved text-provider profiles and **does contact those configured
providers**, so it can incur cost. Automated tests inject a fixture provider
through the same production pipeline and never contact a provider.

Run it only from a POSIX source checkout (the non-mutating SQLite snapshot uses
POSIX file locks) after the two intended profiles have been saved. The review
directory must be an empty, local **absolute** directory outside that checkout.
The runner rejects any path inside the checkout even if it is ignored by Git:

```sh
uv run python scripts/alpha_acceptance.py \
  --profile local_profile_a \
  --profile local_profile_b \
  --review-directory /absolute/path/to/untracked-alpha-review \
  --commit "$(git rev-parse --verify HEAD^{commit})"
```

`--commit` is optional, but when supplied it must be an exact 40-character
hexadecimal commit identifier. When the working tree is dirty, the release
owner should resolve and pass the prepared checkpoint at run time, as above.
If omitted, the runner safely resolves the current `HEAD` commit; neither
choice records working-tree content in the receipt.

The runner executes exactly 18 disposable runs: three fixed, versioned Chinese
briefs × three repeats × two saved profiles. Each run goes through the normal
four-stage production pipeline, including planning, work-unit execution,
validation, sealing, and atomic canonical installation. The source database is
read only: Alpha locks and snapshots its files without opening the source in
SQLite, retries detected WAL state changes, and fails safely rather than using
an inconsistent source snapshot. Every temporary SQLite database, artifact
root, prompt, and response is removed after execution.

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

The same external directory also contains `review-mapping.private.json`. It is
the sole unblinding map, is created with owner-only `0600` permissions, and
maps an opaque review ID to the anonymous profile/story/sample aliases and the
content hash. The map also freezes the exact run-code commit and production
contract hash for the whole six-sample pack. It stays outside the checkout, is
never included in stdout or a tracked receipt, and must not be shared with a
reviewer. Share only the six content files; retain the private mapping locally
for the release owner to bind returned scores back to both the reviewed content
and the code/contract that produced it.

## Independent Codex review gate

After a qualified six-file pack exists, an independent Codex reviewer may
submit one closed JSON score sheet per opaque review ID. This is an engineering
quality gate named `codex_external_review`, not a human product Approval. A
score sheet accepts exactly: commit, contract hash, opaque review ID, content
hash, rubric version, fixed reviewer value, six integer scores from 1 to 5,
and `fatalContradiction`. It cannot carry comments, story text, prompt text,
profile/story/run/model/provider identity, or any other field.

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
