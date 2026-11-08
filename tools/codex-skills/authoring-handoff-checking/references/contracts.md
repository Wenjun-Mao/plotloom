# Case and report contract v1

Case paths are absolute pinned current files; evidence entries provide an ID, source key and JSON Pointer to the precise review region. All files are input data. Examine only listed regions and needed adjacent evidence, not metadata, quality labels or historical decisions. For per-segment work, read the matching episode outline/script/staging and neighboring segments. Pointers and IDs address real source; no extracted paraphrase is authoritative. The adapter checks the selected overrides against their pins, reconstructs and compares the combined current storyboard, and binds the manifest, source files and overrides. It does not authorize any production action. If sources change, prepare a new case; old reports remain historical.

For this project only, from the repository root, use a new output directory:

```sh
python3 tools/codex-skills/authoring-handoff-checking/scripts/prepare_project.py --project "$PWD" --output /absolute/new-output-directory
```

It emits E01.json, E02.json and E03.json. Each case contains current episode outline, script, matching staging scenes and current segment cuts, blocking, soundscapes and prompts, plus pins for owning sources and override files. The adapter fails closed for stale manifest, source or override and differing reconstruction. It does not make semantic decisions, inspect actual provider requests or outputs, or compare source dialogue mechanically.

Run the existing, unchanged Shuohao validators on current inputs for mechanical contracts; inspect their actual outputs and record failures/limits separately. For this production the storyboard validation command is:

```sh
node /Users/wjmao/.codex/skills/novel-storyboard/scripts/novel-storyboard.mjs validate 'docs/roadmap/别叫我的名字-shuohao-production/storyboard.json' --script 'docs/roadmap/别叫我的名字-script.json' --outline 'docs/roadmap/别叫我的名字-outline.json' --art 'docs/roadmap/别叫我的名字-art/别叫我的名字-art.json' --cast 'docs/roadmap/别叫我的名字-cast.json' --no-log
```

Consult the installed novel-outline, novel-script and novel-staging validator `--help` for their actual input requirements; retain stdout, exit status and hashes in the review location. Validators cover their declared deterministic rules only; specifically confirm exact speaker ownership and actual opening semantically, and report any missing validator or untested identity as uncertainty. Do not adapt validators or rewrite a failing source.

A report is JSON:

```json
{
  "schemaVersion": 1, "skillVersion": "0.1.0", "caseId": "E01", "caseSha256": "<sha256 of case file>",
  "reviewer": {"model": "gpt-6.1-terra", "reasoning": "high"},
  "decision": "pass", "summary": "Conclusion with scope.",
  "checks": [
    {"aspect": "hook", "status": "pass", "notes": "What was compared.", "evidence": [{"id": "outline", "pointer": "/hook"}, {"id": "script", "pointer": "/scenes/0/flow/0"}]},
    {"aspect": "dialogue", "status": "pass", "notes": "Comparison and mechanical validator limits.", "evidence": [{"id": "script", "pointer": ""}, {"id": "E01-01:h3Prompt", "pointer": ""}]},
    {"aspect": "visibility_state", "status": "pass", "notes": "Evidence considered.", "evidence": [{"id": "E01-01:cuts", "pointer": ""}]},
    {"aspect": "action_ownership", "status": "pass", "notes": "Evidence considered.", "evidence": [{"id": "E01-01:cuts", "pointer": ""}]},
    {"aspect": "sound", "status": "pass", "notes": "Evidence considered.", "evidence": [{"id": "E01-01:soundscape", "pointer": ""}]}
  ],
  "findings": [], "limitations": ["No transport or generated media reviewed."]
}
```

Each check is required exactly once; statuses are `pass`, `fail`, `needs_review`. A finding has `aspect`, `severity` (`material`, `minor`, `uncertain`), `origin` (`source`, `transport`, `generation`, `unknown`), `claim` and `evidence`, each reference `{id, pointer}` with a JSON Pointer relative to its case evidence region. Material contradictions require at least two distinct evidence IDs, showing both sides. Only make transport or generation findings when corresponding actual evidence is supplied and bound in the case. A pass has no material or uncertain findings and all checks pass. Fail needs a material finding and failed check, with failed checks and material findings matching by aspect. Needs_review requires a genuinely unresolved check or uncertain finding and cannot contain a material finding or failed check. Include coverage, validator outcomes, missing context and perceptual/transport limits in notes or limitations. Validator output itself is not evidence of model observation.

```sh
python3 tools/codex-skills/authoring-handoff-checking/scripts/review_results.py /absolute/E01.json /absolute/review.json
```

The helper checks pins, pointers and report consistency, not actual semantic correctness, complete inspection, validator execution, speaker attribution, or whether the cited evidence supports the claim. A matching file hash does not itself prove source authority: the adapter's manifest/override reconstruction is a separate prerequisite.
