# Saved-profile conformance runner

This runner executes the production four-stage text pipeline repeatedly for
named, already-saved text-provider profiles. It is an operator acceptance
probe, not an automated model test: it contacts the configured provider and
can incur provider cost.

Run it from the checkout after starting Plotloom once so the desired profiles
exist in the configured database:

For the release gate, pass exactly two profiles and request strict M1.5
qualification:

```sh
uv run python scripts/conformance.py \
  --qualify-m15 \
  --profile local_llama \
  --profile second_local_model \
  --runs 3
```

Without `--qualify-m15`, any number of profiles/runs is an explicitly labelled
diagnostic probe and cannot be cited as the M1.5 gate. `--runs` defaults to
three. By default, the source database is the configured
`PLOTLOOM_DATABASE_URL`; use `--source-database-url` to read profiles from a
different existing Plotloom database.

Every sample uses the same fixed Chinese brief, creates a new temporary SQLite
database and artifact root, and runs Story Bible, Story Graph, Scene Beats, and
Storyboard through the normal job runner, `PipelineEngine`, work-unit planning,
validation, sealing, and atomic install. It only reads the requested profiles
from the source database, so it does not create projects, runs, or artifacts in
that database. Temporary evidence, including prompt and response artifacts, is
removed automatically when the command exits, including after a failed sample.
Strict M1.5 mode runs its two profiles concurrently, while the three samples
and all work units remain serial within each profile. Receipt order remains the
requested profile order followed by sample ordinal, so wall time is reduced
without increasing one profile's frozen concurrency. Disposable repositories
are initialized and migrated serially before profile workers start because
Alembic migration contexts are process-global; every initialized repository is
closed on setup or execution failure before its temporary directory is removed.

The command writes one JSONL receipt per sample to standard output. A receipt
contains only `profileId`, its public `profileHash`, the fixed-contract
`workloadHash`, distinct one-based `sampleOrdinal`, `runHash`, `topologyHash`,
terminal `status`, stable `issueCodes`, elapsed milliseconds, aggregate token
counts, stage-level first-pass counts, and the maximum attempts observed for one
work unit. Scene Beats or Storyboard earns one first-pass stage only when every
one of its shards succeeds on its primary attempt. `workloadHash` fingerprints
the fixed brief together with the planning, topology, schema, prompt, and
work-unit contract versions; `sampleOrdinal` prevents repeated samples from
being mistaken for one result. It deliberately excludes the brief, prompts,
responses, provider endpoint, model name, IP address, and credentials. A
command setup failure writes one generic message to standard error after
temporary evidence is removed, rather than serializing configuration or
temporary evidence.

The strict command rejects any shape other than two distinct profiles with
three samples each, then exits non-zero unless every requested profile completes every
sample, keeps every work unit within three attempts, preserves atomic canonical
installation, and passes at least five-sixths of the stage results on their
primary attempts. With the default three samples, this is the M1.5 threshold of
at least 10 of 12 stages per profile. Corrected extraction/schema/semantic codes
remain visible in receipts and count against first-pass performance, but do not
fail the invariant gate a second time; `conformance.*` violations and
`provider.outcome_unknown` remain independently disqualifying.

The gate is deliberately keyed by saved `profileId`, not by provider, model,
alias, or endpoint strings: those fields must never select special runtime
logic and are omitted from receipts. The operator is responsible for choosing
the two intended saved profiles; for M1.5 they are the profiles representing
the two current local models. Their frozen public `profileHash` values prove
which configurations ran without exposing those fields in the receipt.

Before a live qualification, verify that each provider's effective context for
one request is at least its saved profile's declared context. In runtimes that
split a total context pool across parallel slots, inspect the reported per-slot
value rather than assuming the process-wide launch argument applies to every
request. Fix the service or profile and re-probe first; a truncation-shaped
failure is not a valid qualification sample.

`issueCodes` are only Plotloom-owned stable validation, lifecycle, or run
failure codes (including migration `0007`'s run-level classifications), never
arbitrary provider error text. Automated tests inject a local fixture provider
into the same runner; they never contact a model service. The normal CLI does
not have a fixture option.

Passing this command for fixture tests or one profile does not complete M1.5.
The initial gate was completed on 2026-09-03: two real saved profiles each
produced three successful samples of the exact workload, with 12/12 first-pass
stages per profile and no correction or unknown-outcome attempt. The
secret-free receipts are checked in as
[`2026-09-03-m15-conformance.jsonl`](verification/2026-09-03-m15-conformance.jsonl).
Future contract or workload changes produce a different `workloadHash` and
must be qualified again rather than inheriting this result.
