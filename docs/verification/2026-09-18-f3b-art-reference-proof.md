# F3B art-reference proof receipt

Date: 2026-09-18. Implementation candidate: `7c581d8f12358697579b012d5e14974396981a86` plus the final F3A-to-F3B folder-schema transition and verification commit.

## Scope and ownership

This proof exercised the F3B boundary in a disposable format-9 project under
`.local/relay/e214ed2e-fbe6-4f7d-b0a2-f2e6c777985c/f3b-live-proof/`. It used
the current project-folder owners for accepted source/outline/map/graph/cast
and accepted art. A retained upstream-valid art candidate supplied stable
`S01` and `P01`; its only local projection was the F3A code-owned
`sectionUsage` mapping. The specialist did not alter canon.

The author-side overlay explicitly requested cinematic realism while retaining
the upstream semi-realistic painterly art direction as provenance. Trusted code
froze accepted-art revision/hash and the individual stable subject hash;
ImageGen produced untrusted candidate bytes; the existing manual package,
preflight, managed-asset and currentness owners admitted them.

## Attended ImageGen evidence

Two built-in ImageGen calls were made; no refinements or other providers were
used.

| Subject | Frozen proposal | Built-in task | Result and honest limitation |
| --- | --- | --- | --- |
| `scene:S01` — storm weather-station room | `ij_2b137bd4fe644be48271a776436e4d64` | `b9806aa6-cfd8-4bf3-b50f-8111dcb43879` | Empty cinematic storm room visibly contains a rain-streaked observation window, blue instrument light and disconnected cable ends. It adds a chair and richer instrument/set detail not requested; it is not a continuity-approved shot. |
| `prop:P01` — spare power cable | `ij_a431ce02a632458da1567f60f7392985` | `6ccf323e-41a8-4433-b456-e8437ee5d2f3` | White-ground, no-hands cable study visibly shows one wet coiled cable and two connectors. It reads modern/industrial and does not establish period/manufacturing provenance or future shot scale. |

Each package was pinned immediately before its call with the image-specialist
skill at `7c581d8…`. Completion manifests record the exact prompt, task ID and
output SHA-256. The existing cleanup helper first correctly refused a
non-private tool staging directory; after the exact task directory was
restricted to mode `0700`, it copied each hash-matching output into project
delivery and removed only that staged source. No generated output remains in
the task staging directory.

## Runtime/currentness evidence

- Both delivery refreshes returned `accepted`, each creating exactly one
  managed asset with `art_reference_proposal` provenance.
- A fresh process reopened the same file-SQLite project and listed both
  proposals as `current: true`.
- Reopening/saving accepted art with only an S01 summary change made both
  stored studies `current: false`; historical bytes remain managed evidence.
- The production FastAPI/browser regression covers prepare/re-copy, delivery
  refresh/import, current/missing/stale display, backend restart, explicit
  cancellation releasing close, and a late cancelled delivery returning
  `inapplicable` with no candidate.
- The F3A-to-F3B transition test removes only the three proposal tables from
  an otherwise current folder, verifies that read-only inspection refuses the
  mutation, and proves writable admission restores the exact schema with no
  proposal rows. An independent read-only follow-up found no P0-P2 issue in
  the transition's normal/closed admission and recovery boundaries.

## Exclusions and acceptance

This is technical visual proof only. No human creative approval, reference
selection, Shot, Approval, F4 script, F5 cross-shot plan, H3/video, voice, or
production continuity claim was made.
