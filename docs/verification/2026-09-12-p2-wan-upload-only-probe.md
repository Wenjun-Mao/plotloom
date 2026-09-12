# P2 Wan upload-only probe receipt

Captured 2026-09-12. This is an isolated operational diagnostic, not a video
submission, billing, or audiovisual-acceptance record.

## Boundaries and preconditions

- Process-only opt-in: `PLOTLOOM_ENABLE_WAN_P2=true` was set only on the probe
  process before `PlotloomSettings` resolved. `.env` retained SHA-256
  `3a9b4d4c09088217021480052bd99d7bffd5addcd8a452ee1fb2288521be3aa7`.
- The trusted local configuration supplied the video credential and configured
  upload base; neither a credential, a response body, nor a URL was logged or
  persisted.
- The exact PNG was read from the isolated pilot artifact root and its SHA-256
  was verified as
  `c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd`
  before transmission.
- A marker outside the checkout was written before the request, with replay
  forbidden. The one-shot session locally refused any request except one
  multipart `POST` to the documented Atlas upload endpoint; HTTP retry counts
  were explicitly zero.
- Current official Atlas API documentation was checked: it documents the
  multipart upload endpoint separately from video generation. The probe invoked
  the upload method directly and has no code path to `generateVideo`, polling,
  retrieval, or a Plotloom application submit API.

## Read-only pilot state

Before and after the request, historical job
`vj_22de3a4aac36446aa33597240963524a` remained `outcome_unknown` with
`dispatch_outcome_unknown`, no prediction ID, no output URI/hash, and its
original dispatch timestamp. The sole P2 ledger remained `5 / 100` requested
seconds reserved (four immutable events: reserve, pre-dispatch release, reserve,
historical dispatch claim). No pilot database row or artifact changed.

## One upload result

Exactly one allowlisted multipart upload `POST` was made. It completed in
**2343 ms**. The real transport response followed its 2xx path, but the upload
payload did not contain a documented HTTPS URL at an accepted top-level or
`data.url` location:

| Field | Observed safe evidence |
| --- | --- |
| phase | `upload` |
| safe code | `invalid_upload_url` |
| HTTP status | not retained as an integer; the transport's 2xx control path was observed |
| allowlisted POST count | `1` |
| response URL/body | not retained |
| ledger unchanged | yes |

No generation request, retry, poll, retrieval, video submission, budget release
or reset occurred. The returned payload is intentionally not captured, so this
does not diagnose the provider envelope beyond the strict documented URL forms.
A future change, if separately authorized, would need a reviewed transport
contract update with secret-free, allowlisted evidence; this receipt does not
justify a replay or a parser workaround.
