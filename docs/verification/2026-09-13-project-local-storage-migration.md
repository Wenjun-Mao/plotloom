# Project-local P2 storage migration receipt

Captured 2026-09-13. This receipt moves the active retained P2 working set into
ignored project-local storage without rewriting immutable database, package,
manifest, ledger, selection, or prior verification records. No provider call,
generation, polling, or live video review occurred.

## Active entrypoint

The existing ignored `data/plotloom.sqlite3` belonged to separate local work and
was left untouched. The retained P2 set therefore lives at:

```text
data/retained-pilots/p2-wan-pilot-FrZTHA/
├── plotloom.sqlite3
├── artifacts/
├── review-packs/p2-adjoining-profile-2026-09-13/
└── image-exchange/
```

Run this retained pilot with its explicit, narrow compatibility mapping:

```sh
PLOTLOOM_DATA_DIR=data/retained-pilots/p2-wan-pilot-FrZTHA \
PLOTLOOM_IMAGE_EXCHANGE_ROOT=data/retained-pilots/p2-wan-pilot-FrZTHA/image-exchange \
PLOTLOOM_LEGACY_ARTIFACT_ROOTS=/Users/wjmao/projects/HU/plotloom-p2-wan-pilot-FrZTHA/artifacts \
PLOTLOOM_ENABLE_WAN_P2=false \
uv run plotloom
```

The legacy root is a read-only URI relocation allowlist, not an external data
root: stored immutable `file://` artifact URIs map only to their matching
relative path beneath the project-local `artifacts/` directory. The original
pilot and exchange roots remain as recoverable source snapshots for now because
historical receipts name them; no old absolute record was modified.

Local review aid: [adjoining native MP4](../../data/retained-pilots/p2-wan-pilot-FrZTHA/review-packs/p2-adjoining-profile-2026-09-13/adjoining-profile-native.mp4).

## Copy and preservation evidence

- Copied and SHA-256-compared all 22 regular files from the original P2 root
  and its declared adjoining image exchange into the active project-local root.
- Both source and destination SQLite databases returned `PRAGMA integrity_check
  = ok` before the destination was opened.
- The selected original `vj_053f8298b8f9449ca68478c8a97e72b1` remains selected
  with output `b8f27b9e689020ba0186f044a2428f56ff73e97e8fb3e58d014b56fa416d65ae`.
  The adjoining `vj_a05b1888a93546f3b6840a0aa9508683` remains unselected, and
  historical `vj_22de3a4aac36446aa33597240963524a` remains `outcome_unknown`
  with no output hash.
- The copied v2 package `ij_0c684f98a5f0417ba7a06ba0241048f4` validates with its
  frozen v2 executor pin and yields
  `adjoining-profile-original.png` SHA-256
  `0d007e461b0524cb8682ebfb3dd52f7e8073964c1b1a53dca60c9ad24d8e8c84`.

## Reopen and media evidence

The runtime was rebuilt against the explicit project-local data, exchange, and
legacy mapping with WAN disabled. It served the workbench, listed the retained
project and all preserved jobs, and served a range request for the selected MP4:

```text
GET selected video media, Range: bytes=0-127
206 Partial Content
Content-Range: bytes 0-127/7890164
Accept-Ranges: bytes
```

This proves path resolution and local byte-range playback plumbing only; it is
not a new temporal or audio review.

## Narrow historical staging disposition

One exact Codex ImageGen staging file was eligible for recoverable cleanup. Its
bytes, filename, and P1.5 delivery identity matched the project-local exchange
delivery and managed artifact; Plotloom runtime has no path dependency on the
Codex staging tree.

| Source | SHA-256 | Bytes | Disposition |
| --- | --- | ---: | --- |
| `/Users/wjmao/.codex/generated_images/01a0984d-ceb0-7aa2-a9ba-51072c117cf4/exec-eb97885b-f647-463c-9951-79061dac4511.png` | `0d007e…e8c84` | 2,000,319 | Moved to `/Users/wjmao/.Trash/plotloom-adjoining-profile-original-20260913.png`; matching project delivery/artifact rehashed after move. |

No staging parent, wildcard, user input, unrelated Codex output, ambiguous file,
or old pilot root was deleted. Future successful specialist deliveries use the
repository helper to copy, validate, and remove only exact task-owned staged
files; refusal leaves files intact and reports why.

## Checks and limits

- Focused storage/skill tests: `35 passed` across artifact relocation,
  configuration, image-job, and staging-cleanup coverage.
- Python compilation completed for the changed modules/scripts.
- The configured `ruff` executable is not installed in this environment, so
  lint was not run; this is the only known local verification gap at capture.
