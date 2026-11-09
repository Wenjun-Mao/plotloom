# Normalized report contract

Run `python3 scripts/progress.py MANIFEST`. Paths are absolute or relative to the
manifest directory. The input contains `source: {file, sha256, episodes}` where
episodes are ordered `{id, segments: [segmentId, ...]}`. The caller extracts this
order from the actual owning source and binds its hash. `technical` is an array of
`{segmentId, receipt: {file, sha256}, media: {file, sha256}, status}`; only `PASS`
with current content-bound receipt and media is reported as retained technical
proof, not a claim that generic code interprets provider-specific receipt semantics.
`selections` contains `{segmentId, media, evidence}` with two file/hash bindings;
these must come from an explicit decision, not enumeration. Both sets can have
multiple technical attempts, but duplicate selections are rejected. The adapter is
responsible for establishing provider-specific semantics before normalizing.

Optional `exports` entries contain `episodeId`, `sourceSha256`, `selectionSha256`,
`selection: {file, sha256}`, `receipt: {file, sha256}`, `media: {file, sha256}`,
`segments`, and `proofs: [{file, sha256}, ...]`. These are frozen bindings, not
independent proof of the assertions inside those files. Source, explicit selection,
segment order, all bindings and proof files must match current input for reuse.
The selection file must be JSON `{ "selections": [...] }` containing exactly the
current normalized selection rows for the exported episode, in source order,
including their media and evidence bindings; changing a take invalidates reuse.
The caller must validate receipt semantics and any underlying proof dependencies; a
matching hash alone cannot certify frames, PCM or clocks. Report the qualification
scope and historical evidence separately. Malformed manifests, duplicate IDs,
unknown IDs, or out-of-order selections fail closed. The tool emits JSON to stdout
and never modifies inputs.

## Plotloom adapter

From the project root, using the checked environment:

```sh
uv run --locked --no-sync python tools/codex-skills/assembly-progress-checking/scripts/plotloom_adapter.py --selection docs/roadmap/别叫我的名字-shuohao-production/exports/episode1-preview-v1/episode1-selection.json
uv run --locked --no-sync python tools/codex-skills/assembly-progress-checking/scripts/plotloom_preview.py
```

The adapter validates each explicit `selected` review with the actual `selected_clip`
manager function, without generating or decoding all media anew. Multiple valid
selected reviews for a segment are an unresolved conflict. It separately reports
all observed review decisions and technical receipt bindings; unselected technical
attempts do not establish eligibility for final assembly. When `--selection` is supplied, only its ordered, source-current rows with exact
packet, review and native bindings can count; an empty or partial file stays empty
or partial. Without the flag, uniquely valid per-take decisions count; conflicts
remain gaps. The full decision inventory is informational in both modes.
The preview command validates retained hash bindings and reports historical claims;
it is not a fresh verification of frames, PCM, timestamps or listening.


## Troubleshooting

If the Plotloom checker reports a missing exact grant binding, treat it as an
artifact handoff gap, not a media failure or provider permission. The owning
lookup matches `evidence/post-intent.json` → `admissionSha256` against
`.local/ref2va/manager/admissions/*.json`. The authorized coordinator may register
a verified byte-exact, already approved and admitted grant in that registry,
preserving existing files and avoiding duplicate digest matches. Do not synthesize a grant, weaken the check, broaden lookup or
automatically copy or authorize anything. The checker remains read-only and
reports the gap until the owning workflow resolves it. This is conditional
troubleshooting, not an additional routine production preflight.
