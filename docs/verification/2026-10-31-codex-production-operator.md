# Codex production-operator contract qualification

ADR 0230 closes a demonstrated normal-project blocker: explicit Codex generation
authorization could otherwise be stored as an unnamed creator. The caller now
supplies an optional Codex operator; trusted code records and binds it through
Start replay, preparation, dispatch, manual readback and portable recovery.
QA attribution remains separate, including its original scope/budget/grant fences.
No source, prompt, model, provider, media-quality or retry permission changes.

Independent review approved the stable source delta. The new cohesive operator
module keeps actor validation out of the batch controller and recovery reader.
The oversized frontend API owner has only one type-field addition; extracting
unrelated API responsibilities is unwarranted. No production file exceeds 500
lines as a result of this new responsibility.

Executed in the existing locked macOS arm64 / Python 3.12.13 / Node 24.18.0
envelope, without live providers:

- Focused: 126 Python cases across the new operator tests and the existing
  delegated-QA, batch, adoption, recovery, replacement, selection and fidelity
  owners passed; 19 frontend authorization cases passed.
- The decoded synthetic-media journey passed Codex Start → fake-provider
  ingestion → exact native playback-window selection → snapshot/restore and
  selected-media readback. It created no inspection or quality-pass facts.
- Missing/changed/malformed operator, exact lost-ack replay, QA bypass,
  tampered persisted actors/snapshots and nonportable dispatch-grant regressions
  passed. Existing creator/QA authorization serialization is unchanged.
- Quick: 184 frontend files, 1,704 cases and both type checks passed.
- Scoped Ruff F checks and the 21-file native validation resource check passed.
- Two deterministic frontend builds produced identical nine-file workbench/
  player SHA-256 trees, with generated assets refreshed.

Logs and hash trees are retained under `.local/last-projection-resume/` as
`codex-operator-affected-contracts.log`, `codex-operator-quick.log`,
`codex-operator-validation-resources.log`, `codex-operator-build-{1,2}.log`
and `codex-operator-asset-determinism.json`. The first focused run's two
test-harness failures are retained; they were corrected without weakening
product safeguards. Tests use synthetic task UUIDs.

This stable authorization change requires a new final full local gate and exact
installed-package proof. The earlier `06992e24` 366-case browser pass and wheel
smoke remain evidence for that earlier checkpoint, not a pass for this delta.
The original ready first-shot directions/fidelity evidence stays unchanged;
the operator field is trusted authorization provenance, never model-owned prose.
No H3 submission occurred before this repair. Resume the original ready batch
only after focused qualification, exact-package checking and safe runtime
restart/readback. Final activation still requires the complete release gate.
Hosted CI and push were not requested or run.
