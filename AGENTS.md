# Plotloom development contract

- Fix root causes and contracts rather than symptoms. Add regression evidence for durable fixes.
- Keep the canonical domain independent of browser, provider, environment, and concrete filesystem concerns.
- Keep API keys out of project state, persistence, logs, traces, and public provider settings.
- Preserve the extraction boundary: production code must not import or read Narrative Forge V1 runtime paths or data.
- Record durable changes to public APIs, prompt/schema contracts, persistence, runtime behavior, or workflow semantics as concise ADRs.
- Keep generated frontend assets in `src/plotloom/static/` fresh whenever `frontend/` changes.
- Use `uv` and the checked lockfiles. Run focused checks first, then the full Python, frontend, build, and browser gates appropriate to the change.

## Bounded delivery

- For development work, follow [ADR 0023](docs/adr/0023-bounded-delivery-and-evidence.md). The current M1-C execution order is in [the completion plan](docs/roadmap/m1c-completion-plan.md); the capability matrix remains the product progress record.
- Start each checkpoint with a short brief: verified HEAD/worktree, one observable outcome, owned scope, acceptance evidence, and a stopping condition. Read only the context needed for that outcome.
- Before a generation-contract fix, identify which fields the author, model, and trusted code own. Check primary prompt, response schema, binder, and validator agreement before adding correction machinery. Amend the relevant ADR before changing ownership; preserve raw evidence and historical contracts.
- Use one implementation owner by default. Delegate only separately owned work that replaces work the owner would otherwise do; use GPT-5.6 Terra for subagents unless a concrete exception is justified. Give a bounded brief with minimal history. Use one independent review after the candidate stabilizes; reopen it only for a specific unresolved finding, regression, or material change.
- Run focused checks during edits and the full required gate on the stable candidate. Repeat or broaden checks when a change or failure justifies them, recording why; do not trade correctness for an arbitrary test-run quota.
- At the end of a completed, verified implementation, merge the scoped changes back to `main` and push to `origin` by default, unless the user explicitly requests otherwise. Check remote divergence and preserve unrelated work; never force-push or bypass failed gates. Report the pushed revision and any pending CI separately from local verification.
- Long-running jobs should report completion/failure through the existing task/job mechanism. Avoid frequent model-driven polling, repeated inventory calls, and unchanged status narration. Keep searches and output targeted; exclude generated assets unless they are the subject of the task.
- After one supporting-tool-only checkpoint, attempt the product outcome next. If a targeted fix leaves the same failure class unresolved, checkpoint the evidence and reassess the ownership/contract instead of starting another open-ended review cycle.
- End each checkpoint with the outcome, commit/worktree state, checks and remaining gaps, next action, and available response/token/cost deltas from existing usage records. Distinguish cached input from fresh input and reasoning from total output; disclose missing measurements. No numerical spending limit is a hard cap without enforcement.
