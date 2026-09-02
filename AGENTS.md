# Plotloom development contract

- Fix root causes and contracts rather than symptoms. Add regression evidence for durable fixes.
- Keep the canonical domain independent of browser, provider, environment, and concrete filesystem concerns.
- Keep API keys out of project state, persistence, logs, traces, and public provider settings.
- Preserve the extraction boundary: production code must not import or read Narrative Forge V1 runtime paths or data.
- Record durable changes to public APIs, prompt/schema contracts, persistence, runtime behavior, or workflow semantics as concise ADRs.
- Keep generated frontend assets in `src/plotloom/static/` fresh whenever `frontend/` changes.
- Use `uv` and the checked lockfiles. Run focused checks first, then the full Python, frontend, build, and browser gates appropriate to the change.
