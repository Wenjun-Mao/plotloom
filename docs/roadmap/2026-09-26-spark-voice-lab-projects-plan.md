# Spark Voice Lab: projects, selective generation and published Voice IDs

**Status:** Implemented and live-verified in the specialist Voice Lab on
2026-09-27; independent review and Plotloom integration remain on hold.
Follow-on to the deployed
[Voice Lab MVP](2026-09-26-spark-voice-lab-plan.md), governed by
[ADR 0207](../adr/0207-voice-lab-projects-and-published-voice-identity.md).
This is specialist-side work on the retained checkout. The hold on Plotloom
director contact, Plotloom code changes, merge and push remains in force.

## Outcome and boundary

Opening the Lab root shows a project chooser, not the retained verification
round. A user can create an empty named project, rename/switch/delete it, edit
its author text, and add or regenerate one candidate without disturbing the
others. A chosen generation can be published as an immutable Voice ID that
survives project deletion and is retrievable for later Plotloom integration.

The current implementation has global `rounds`, `candidates`, `selections`
and `clone_trials` in one SQLite store, one serial worker, and a UI that opens
the latest round automatically. The existing real pilot audio is user-valued:
preserve its IDs, WAVs and hashes during the cutover. Project independence is
content isolation, not authentication or per-user privacy.

## Contract to implement

- **Project:** opaque `projectId`, editable name/brief/audition line, content
  revision, candidate list and project-scoped lab selection. `/` always shows
  the chooser; a project URL selects a project explicitly. A new project has
  no generated content. Editable text is a draft until saved; concurrent stale
  saves receive a revision conflict instead of overwriting another tab.
- **Candidate slot:** globally unique stable `candidateId`, editable design
  direction and current-generation pointer. Project candidate count is not
  constrained to 2/4/6/8; the UI can still offer batch creation as a shortcut.
  Add, remove or regenerate one slot independently. Generation freezes the
  exact project text, direction, seed, model and preparation version in a new
  immutable `generationId`; editing a draft never mutates a prior WAV.
- **Replacement:** generate to a new managed path and validate both the
  original WAV and optional H3 derivative before changing the current pointer.
  On failure, retain the prior usable generation. On success, clear a lab-only
  selection of the replaced generation and remove its old *unpublished* WAV
  after the database switch. If file cleanup fails, record/retry a scoped
  cleanup debt; never report the old WAV as current. Keep an immutable
  generation tombstone with hash/provenance rather than a dangling playable
  path. A queued/running clone
  trial must pin its source generation until it finishes, so replacement cannot
  remove a file still needed for that trial.
- **Published voice:** explicit Publish of the selected validated generation
  into independently managed immutable voice storage and returns `voiceId`.
  Store source candidate/generation provenance, transcript, model details and
  SHA-256. Repeating Publish on that same generation returns its existing
  Voice ID. Read-only metadata/audio endpoints resolve the exact frozen bytes.
  A later candidate regeneration or project deletion cannot change them. Do
  not expose a voice-retirement action until Plotloom dependency checks exist.
- **Deletion:** confirm exact project name; reject while its generation or
  clone jobs are nonterminal. Delete only that project's records and managed
  unpublished media, never arbitrary paths or independently published voice
  files. Candidate removal follows the same reference and busy-job rules.

The new project/candidate/generation/voice API replaces global round creation
and selection after the cutover; do not keep a parallel legacy authoring API.
Stable error codes should distinguish stale revision, busy project, invalid
generation, missing asset and failed cleanup. Public responses remain
path-free and secret-free. The read-only published-voice contract is the
specialist handoff surface; Plotloom import/binding is a separate later slice.

## Ordered delivery

1. **Storage and migration.** With the Lab worker idle, take a scoped verified
   copy of the current SQLite/media state. Introduce project, candidate-slot,
   generation and published-voice tables/relations transactionally. Migrate
   the retained verification round, selection and clone history into a named
   pilot project without regenerating or changing audio hashes. Reject an
   inconsistent migration before changing the live service; retain the source
   evidence until the migrated browser journey is verified.
2. **One-candidate lifecycle.** Refactor the store and serial worker around
   frozen generation jobs, pointer-swap on success, failed-replacement safety,
   dependent clone pinning and scoped old-WAV cleanup. Add project CRUD,
   revision checks, candidate add/edit/remove/regenerate, and current/history
   queries. Preserve unknown-dispatch behavior on restart; do not silently
   replay a job.
3. **Voice publication and UI.** Add immutable Publish and hash-checked
   read-only Voice ID retrieval. Replace automatic latest-round loading with
   the chooser and explicit project URL. Provide editable project/candidate
   fields, per-candidate Generate/Regenerate, Add candidate, switch, rename,
   delete confirmation, visible current/stale/failed states, and Voice ID copy.
   Keep blind listening, two-item comparison and new-line clone testing scoped
   to the selected project.
4. **Verification and deployment.** Run focused fake-engine migration,
   concurrency, cleanup and API tests first. Exercise the real FastAPI browser
   journey against a file SQLite database, then deploy the wheel to Spark and
   test one bounded real project: generate A, add/generate B, regenerate A,
   publish A, edit/switch projects, delete the source project, and resolve the
   identical Voice ID WAV afterward. Verify B's hash stayed unchanged and the
   old unpublished A WAV was removed. Retain a secret-free receipt and browser
   capture; use one independent review on the stable candidate.

## Acceptance and exclusions

- `/` is empty of any selected project/audio, while the old pilot appears only
  when its named project is opened; refresh and direct project URLs work.
- Project rename, switching, text edits, deletion and stale-revision rejection
  work. A failed single-candidate regeneration leaves its prior WAV intact;
  successful replacement changes only that candidate and removes its old
  unpublished WAV. Adding one candidate does not regenerate siblings.
- Candidate IDs remain stable and unique; generation and Voice IDs are new,
  immutable identities. Published audio/hash survive regeneration, project
  deletion, service restart and browser refresh. Active jobs block deletion;
  interrupted jobs never replay without an explicit user action.
- Run module tests, repository tests affected by the service-root contract,
  JavaScript syntax/build checks, real browser tests, wheel install smoke, and
  `git diff --check`. Report exact outcomes and any untested case.

No Plotloom UI/API integration, gateway Voice ID lookup, H3 video generation,
emotion-control claim, access-control system, automatic retention policy or
published-voice retirement is included. Do not contact the Plotloom director
or merge/push this specialist branch while the owner's hold remains.
