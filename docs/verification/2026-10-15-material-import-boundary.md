# Material model import boundary — 2026-10-15

> Local QA artifact references below are historical; the [2026-10-25 cleanup](../roadmap/2026-10-25-top-five-cleanup.md)
> retires their storage, replay/launch/cutback instructions and preservation holds.
> Recorded outcomes and limits remain; current ADR/API contracts still apply.

## Failure and owning repair

The first ignored campaign wiring attempt on clean
`ce6aaeca4e59bc6fa1ee76edcb58241be85e94d3` exited 2 during collection:
one import error, **zero test bodies**, no actual-pytest runtime binding.
Its ordinary helper import entered `autopilot_materials`, whose eager codec and
closure imports initialized persistence/repository. First-install quiescence then
imported discovery models back through the partially initialized material module.
Prior persistence-first entry-point passes did not cover this cold entry.

The production repair changes only `autopilot_materials.py`: import canonical
hashing from its existing `contract_hash` owner, and load `production_closure`
inside the complete-inventory operation for every caller. Shared model imports
no longer initialize repository composition. No caller/test/runner warm-up,
path injection, conditional exception or new model layer is added. ADR 0162's
existing leaf-hash paragraph now names this universal operation boundary.

All class bodies and calculation ASTs match the original, excluding only the
new operation-owned import. Actual before/after comparison of five model schemas,
qualified class identities and sample inventory/discovery/bundle payloads is
identical. Canonical inventory hash is unchanged; the codec still reexports the
same hash function. Versions, aliases, consumer mapping, validators, budgets,
route coverage, closure calculation and exception behavior are unchanged.

## Executed scoped verification

- New `test_autopilot_material_imports.py` first through `verify.py focused`:
  **11 passed**, 3.671 runner seconds; original handle 52855, exit 0.
- Exact nine-file focused union: **73 passed**, 400.40 pytest / 417.779 runner
  seconds; original handle 29166, exit 0. It includes the new file, early
  references, early-reference limits, images, image safety, review readiness,
  handoff, Codex Exec profile and resources. One existing Starlette/httpx warning.
- Seven fresh `-I -B` children per focused run use the actual project interpreter
  and source paths, with bounded timeouts and no preloads/path injection. Three
  model entry points load no persistence modules; four legitimate persistence/
  storage entry points import successfully with canonical class identity.
  Exact JSON/schema, hash identity and invalid inventory refusals also pass.
- Native ownership **discovery only** passed: 2,378 pytest cases / 225 files,
  1,381 Vitest / 159 files, 319 browser / 93 files; no test bodies executed.
  The 11 new cases belong to `story-authoring`. Handle 15954, exit 0.
- Scoped Ruff I/F and `git diff --check` passed. One new-test import was sorted
  before any test execution; no test failure or assertion weakening occurred.

Focused runs use explicitly owned external temp/cache paths; pytest options
contain only basetemp/cache configuration, with no ambient selection or plugin overrides.
Original process groups 5998, 6433 and 10671 were absent before the exact owned
external root was removed. Both sets of seven actual child bindings are retained.

## Evidence and limits

Ignored evidence is under
`.local/native-proof/material-import-repair-ce6aaeca-20261015/`: before/after
schema/dump captures, `contract-preservation.json`, first/affected focused logs,
both cold-binding packets, ownership/lint logs, preservation and terminal audits.
The affected log SHA-256 is
`b1f290b74d48accfe402dec1516daaf07fd0b7f9bdaca570d7833be1e87fa49f`.

The 95 F5 input paths are unchanged; only `autopilot_materials.py` changes bytes
to SHA-256 `2c9836a6d8cfa62ad85d41ad14d6ce80223669b34392e6af14ccccff7d74c986`.
The strict Python source-tree identity therefore changes. New source-bound
profiles/validator hashes and package qualification are required; none were
evaluated here. Existing source/profile/evidence descriptors were not repinned.

First wiring log/XML/launch/audit, its retained failed external root, 27 prior
control snapshots and 2,981 historical hash entries remain unchanged. Earlier
2367 Python, 1381 Vitest, repaired 319 browser, F5, wheel and smoke outcomes retain
their original source pins. They are not fresh qualification of this source.
The failed wiring attempt was not retried; no campaign preparation/seal/preflight,
current native/CLI profile evaluation, generation, provisioning, full gate, CI,
push or merge ran.
Independent stable code/wording review found no required corrections, completed
turn `01a13def-7a5e-70d2-9f83-2c39f9fd7b40` (read-only static review). The manager's
independent source, AST, snapshot, cold-binding and log audit found no issues.
The manager owns subsequent qualification and any fresh-identity campaign-check
allocation.
