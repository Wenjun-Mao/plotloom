# Plotloom development contract

- Fix root causes and contracts rather than symptoms; preserve regression coverage for current supported behavior.
- Breaking changes and targeted development-data resets are the preferred default. Do not add or retain backward-compatibility layers, historical replay support, or automatic backups unless explicitly required. Remove obsolete code and tests with retired contracts; prefer the smallest current-contract implementation.
- Keep resets and deletions scoped to identified disposable data. Preserve current user-valued assets and work unless their removal is explicitly authorized; retain credential protection, transaction integrity, and unknown-dispatch safety. This policy does not authorize broad deletion or removal of current product features such as snapshot/restore.
- Keep credentials out of project state, persistence, logs, traces, and public settings.
- Development/test generation through Codex ImageGen and the owner's H3 gateway is pre-authorized; no per-call user approval is needed. Use bounded experiments and preserve dispatch safety. Other providers or paid fallbacks require explicit approval; generation authority does not imply creative acceptance or deletion authority.
- Preserve the extraction boundary: production code must not import or read Narrative Forge V1 runtime paths or data.
- Record durable changes to public APIs, prompt/schema contracts, persistence, runtime behavior, or workflow semantics as concise ADRs.
- Keep generated frontend assets in `src/plotloom/static/` fresh whenever `frontend/` changes.
- Use `uv` and checked lockfiles. Run focused checks during edits and broader required gates on stable candidates, proportional to risk; repeat only when changes or evidence justify it.

## Bounded delivery

- Before a generation-contract fix, identify which fields the author, model, and trusted code own. Check primary prompt, response schema, binder, and validator agreement before adding correction machinery. Amend the relevant ADR before changing ownership; do not rewrite retained evidence to imply it satisfied a newer contract. Old contracts need not remain executable.
- Keep approved scope, phase-specific instructions and progress in the roadmap, not this file. Start at `docs/roadmap/README.md`; each assignment must identify its approved step, deliverable, evidence, exclusions and stopping condition.
- Use one source owner by default and GPT-5.6 Terra for delegated work unless a concrete exception is justified. Keep briefs bounded with minimal history. Use an independent review on a stable candidate; reopen only for concrete findings or material changes. Do not leave delegated work without a supported completion-reporting path.
- Fix demonstrated blockers within scope; defer optional improvements. A review finding is not authorization to expand scope. Material changes to the approved outcome, acceptance, risk or authority require user agreement before implementation.
- After two unsuccessful attempts at the same acceptance criterion, preserve the evidence and reassess the cause and method before dispatching again. Explain the adjustment; do not repeat the same broad assignment or build more tracking machinery instead of delivering the outcome.
- At the end of a completed, verified implementation, merge the scoped changes back to `main` and push to `origin` by default, unless the user explicitly requests otherwise. Check remote divergence and preserve unrelated work; never force-push or bypass failed gates. Report the pushed revision and any pending CI separately from local verification.
- Long-running jobs should report completion/failure through the existing task/job mechanism. Avoid frequent model-driven polling, repeated inventory calls, and unchanged status narration. Keep searches and output targeted; exclude generated assets unless they are the subject of the task.
- Report implementation, executed verification and product acceptance separately, with revision/worktree state, remaining gaps and next action. Test counts and worker reports alone do not establish acceptance. Include usage/cost deltas only when available from existing records; do not invent measurements.
