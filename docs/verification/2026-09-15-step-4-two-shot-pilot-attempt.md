# Step 4 bounded two-shot pilot attempt — text-generation blocker

Captured 2026-09-15 at `abd3f2d`. This is a secret-free operational receipt.
It records one real, bounded production-profile attempt and its stopping
condition; it is not a creative, audiovisual, human, Alpha, or release claim.

## Scope and fresh project

- Fresh labelled project: `失物站台` (`ae4595cf-2bcc-480a-839b-af3a8901240c`),
  retained under the ignored project output root as
  `20260915T184701745587Z__ae4595cf-2bcc-480a-839b-af3a8901240c`.
- Canonical brief: Chinese, 9:16, cinematic realism; one protagonist finds an
  old lost watch at a quiet night station, checks the photograph inside, and
  safely puts it away to return to station staff.
- The saved active text profile's ordinary, non-generating readiness probe
  reported `available` / `readiness.models_verified`. No profile fields,
  provider routing, credentials, gateway deployment, source, configuration, or
  prior project were changed.
- The configured H3 V4 backend reported enabled with the approved portrait
  profile `minimax_h3_fp8_turbo4_portrait_576x1024_v1`, `reject_mismatch`, and
  native audio. It was admitted only as a future path: no H3 job was prepared
  or submitted.

## Actual four-stage run and blocker

Run `2326517e-9e51-4771-aa15-eeeecb3382bd` started through the ordinary
workbench with all four canonical stages selected. Project-owned provenance
retains the prompts, sanitized responses, validation events, and correction
links; this receipt intentionally does not copy provider material.

| Stage / unit | Observed result |
| --- | --- |
| Story Bible #1 | Accepted and sealed on attempt 1. |
| Story Graph #1 | Accepted and sealed on attempt 2 after its normal correction path. |
| Scene Beats #1–#6 | Individually accepted on attempt 1 but not installed because the stage aggregate did not seal. |
| Scene Beats #7 | Quarantined on attempt 3 with `semantic.invalid_continuity_entity_state`. |
| Scene Beats #8; Storyboard | Never dispatched; the run stopped when #7 quarantined. |

The causal failure is model output that referenced a continuity entity state
outside the frozen Story Bible's allowed-state contract. The semantic validator
correctly prevented installation. This is not evidence that the validator, H3,
or media admission should be weakened.

After the third bounded unit attempt, the normal isolated-repair action was
tried once. It did **not** submit another model request: pre-dispatch rejected
the repair with `repair.parent_evidence_invalid: source reusable unit requires
one immutable candidate`. Read-only inspection later established that this was
not an attribution to the quarantined target: the old repair projection tried
to freeze every non-target sibling, including never-dispatched Scene Beats #8,
which correctly has no candidate. The target remains bound to its rejected
attempt/response/validation lineage; successful siblings have one candidate
each. No full-stage rebuild, manual rewrite, new project, or source/configuration
change was attempted.

## Retained evidence and non-actions

The project remains in the ignored output root. Its evidence hashes at capture:

| Retained item | SHA-256 |
| --- | --- |
| `project.json` | `eeaa80fa1e81a7fdbfa65fc3ee05a68146232cc94b8af25f1a289b9d45bb865b` |
| `project.sqlite3` | `9daf40733bddf727c8b6cee6063f7d48d75f171ef15c8733d1261df357f74b7c` |
| retained run artifact | `03e8673a2a1f6592c4059be2fa12e3032c1f390317acc58f6fa90153fb699454` |

No character-reference proposal or decision, image package, ImageGen call,
staging cleanup, keyframe, H3 preparation/copy/refresh/select sequence,
five-second clip, provider video dispatch, media selection, playback,
snapshot, close/reopen, or isolated restore was performed. Accordingly the
ImageGen count is **0** and the H3 I2V job count is **0**.

## Acceptance disposition

| Dimension | Disposition |
| --- | --- |
| Engineering | Partial only: production text/H3 readiness and the quarantined validation boundary were observed; the required two-shot lineage is absent. |
| Creative | Not assessed: no storyboard or visual candidate was installed. |
| Human / audiovisual | Pending: no clips exist to inspect or listen to. Audio presence is not treated as an audiovisual judgment. |

The owned local Plotloom server was stopped after this receipt was captured.
The next action is contract-level diagnosis of the precise repair-parent
evidence rejection, preserving this project and run rather than resubmitting
unknown or already-bounded work.
