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
publishes the explicit review directory with exactly six deterministic files,
`review-01.json` through `review-06.json`: repeat one for every anonymous
profile/story pair. Each file contains only the four canonical authoring
payloads (`storyBible`, `storyGraph`, `sceneBeats`, `storyboard`), with no run,
profile, provider, trace, prompt, response, or receipt metadata. File ordering
is deterministic by requested profile order then the fixed story order, so no
mapping file is necessary. Do not check in the review directory or create a
mapping file; reviewers should receive only those blinded content files.
