# ADR 0238 — Manually invoked video checking

Accepted November 8, 2026 for the owner-authorized checker pilot.

## Decision

Keep a self-contained personal Codex skill in
`tools/codex-skills/video-checking/`, with personal discovery linked to that
versioned source. Disable implicit invocation. This is optional agent review,
not a Plotloom runtime dependency or a new mandatory production gate; ADR 0226
continues to apply. Checking grants no generation, retry, source-edit or
production-selection authority and preserves an existing generation pause.

The author supplies actions, world state, references and dialogue. Local tools
own hashing, current-source binding, decode-evidence reuse, frame extraction,
report validation and reproducible audit selection. GPT-6.1 Terra/high workers
own bounded primary observations and recommendations. The coordinator audits
samples from both passes and rejections against independently chosen actual
frames, handles uncertainty and decides narrow skill improvements.

Review results pin their skill version and complete evidence-bundle fingerprint.
The mechanical cache excludes review prose, so instruction updates do not
require extracting unchanged frames again. Current validation rechecks pinned
originals; a retained snapshot alone does not prove the source is still current.
Fingerprints detect ordinary changes/corruption, not deliberate forgery. JSON
declarations of viewed evidence require actual tool trace or audit support.

Missing required recognition blocks a pass, but an independent observed material
picture defect can already support rejection. ASR is not perceptual listening,
voice/acting acceptance, literal spoken-word certification or lip-sync review.
Correctly caught output defects are not checker defects. Improve demonstrated
misses, false rejections and wasted work with narrow changes and regression
examples; retain old reports with their actual version and inspection limits.

## Consequences

The first pilot uses retained media only. Actual elapsed time can be recorded;
cost and speed savings require comparable measurements and are not assumed.
No provider, service, production-state, CI or publishing changes are included.
The bounded plan and evidence are recorded in
`docs/roadmap/2026-11-08-video-checking-skill.md`.

## Generated contact coverage correction

Version0.1.2 fixes a production-discovered evidence bug: literal multiplication
expressions in xstack offsets overlapped the declared uniform frames. Generate
numeric coordinates and check PNG dimensions against the declared tile grid
before recording coverage. Current review/detail validation also requires exact
current preparation-code pins, so a stale malformed bundle cannot be relabeled
with a newer review version. Old reports/caches remain immutable historical
evidence, not valid current primary bundles.

Real FFmpeg colored-tile regressions prove geometry and every input position for
full, partial and single-frame pages; a rebound malformed legacy bundle is
rejected by current review/detail validation. Four already selected clips receive
source-bound coverage-only supplements while their original anchor/recognition
judgments stay attributed. This is repair of inspection evidence, not a reason
to regenerate media or repeat unaffected full reviews.

## Future checking guidance

Version 0.1.3 aligns the result validator and fixture with the skill version and
adds narrow guidance on source-fidelity materiality and face-covering integrity.
An unmet crop remains a deviation; a coordinator's explicit quality exception
does not erase observed findings or establish literal compliance. The framing
example is calibrated from retained evidence, not a held-out accuracy result.
New production reviews remained on 0.1.2; retained older reviews keep their
original versions and attribution. The new guidance applies to future invocations.
Retain original findings and reviews under their actual version, including when
a coordinator selects media under a quality waiver.
