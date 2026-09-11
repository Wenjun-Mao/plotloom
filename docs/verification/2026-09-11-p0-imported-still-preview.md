# P0 imported still-preview correction receipt

## Candidate and scope

- Initial correction: `72eddc6f3f1603774ad2b14ae235049427c1ea71`
  (`feat: harden reviewed still preview contracts`); final code candidate:
  `d5737604881e3cc5c18f9f3176dd9161749b3258` (`fix: block stale still
  preview admission`). The original P0 commits remain intact: `4dabfc5` and
  `dce8614`.
- Scope is limited to managed JPEG/PNG imports, explicit reviewed still
  keyframes, and a non-generative still animatic. No image/video provider,
  media task, GenerationRun, ProductionSnapshot, P1 work, merge, or push was
  introduced.

## Evidence inputs and provenance

The four browser-uploaded inputs are direct development-session ImageGen
outputs made on 2026-09-11. They are **not** asserted to be real scenes,
approved production assets, or repository-owned source material. In the real
browser journey, each multipart upload records the explicit origin `Direct
development-session images generated with imagegen on 2026-09-11`, rights
`unknown`, and declared addition `reference only`.

| File | SHA-256 |
|---|---|
| `supporting/p0-generated/01-arrival.png` | `42ec6a9e52e84a7df0e5ffe11bbd18f478f2774db16d08d105f602108d4af8e5` |
| `supporting/p0-generated/02-keys.png` | `48df3486bee8162e0b7c43f7a13fd0539c9c723d08a0737a75f75f10ea8f4b2e` |
| `supporting/p0-generated/03-pressure.png` | `b6d54e7caaa5c28a3478b68c0610ec07d207b5417c2745524b8b0575d32f5f67` |
| `supporting/p0-generated/04-establishing.png` | `75def13319ba1758d5ec24ff7236bd91fd862afecd56e71c2df6fb3c407e7611` |

## Observable journey

`frontend/e2e/imported-still-preview.spec.ts` starts a fresh local FastAPI
application with file-backed SQLite and filesystem artifact storage. At a
1440×900 browser viewport it creates an ordinary canonical project with one
three-shot scene, approves the saved storyboard, imports the four files,
compares and explicitly keeps candidates, records versioned intent with source
references, and binds the retained still to all three shots. It creates a
three-shot animatic, plays and seeks its exact authored 2000 ms third frame,
reloads, and opens a new browser page to prove restart hydration. It replaces
the first binding so the former preview is `STALE` and a newly frozen one is
`CURRENT`; an authored board edit blocks reviewed selection until normal
reapproval; archive then causes permanent deletion to refuse with
`project_managed_assets_present`.

The supporting screenshot is a test-produced 1440×900 capture from that
journey, not a mockup. Its SHA-256 is
`7d8c2fae541092bba8b4832625fc29779706f17e65c2745120bcfe2276fe84eb`.

![1440×900 reviewed still animatic with current and stale history](supporting/p0-imported-still-preview-1440x900.png)

## Completed checks

| Check | Result |
|---|---|
| Focused managed-media/config/repository/extraction tests | 55 passed |
| Full Python suite | 531 passed, 9 skipped, 272 pre-existing/dependency warnings |
| Frontend unit tests | 115 passed |
| Frontend and E2E TypeScript checks | passed |
| Vite production build | passed; generated `src/plotloom/static/` is included in the candidate |
| Full FastAPI/file-SQLite Playwright suite | 24 passed, including the P0 journey |
| `uv build --wheel` and installed-wheel smoke | passed for `plotloom-0.1.0-py3-none-any.whl` |
| Whitespace/diff integrity | `git diff --check` passed before candidate commit |

## Review disposition

One independent review of `72eddc6` found P0: a refined intent could leave its
old reviewed binding visible for new-preview admission, allowing a receipt that
was immediately `stale`. `d573760` resolves it at the repository lifecycle
transaction: only the latest per-Shot binding, latest same-asset/role intent,
and current exact approval are admission-eligible. The workbench now omits
ineligible bindings, and the backend regression proves the attempted preview
returns `409 invalid_transition`; the browser regression proves board-edit
reapproval exposes missing keyframes and requires an explicit new selection.
The reviewer reported no other findings. The finding is resolved and was
reverified by the completed checks above.
