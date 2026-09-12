# Atlas upload response-shape probe receipt

Captured 2026-09-12. This is an isolated, one-upload qualification record. It
is not a video submission, a parser-contract change, or audiovisual acceptance.

## Boundaries and preconditions

- The probe ran its malicious-payload projection fixtures before networking. The
  fixtures proved that the persisted projection contains only fixed field names,
  presence/type labels, and booleans; it does not retain fixture values.
- It set `PLOTLOOM_ENABLE_WAN_P2=true` only inside the probe process before
  `PlotloomSettings` resolved. The API credential remained in process memory.
  No credential, request body/key, header, response body, error text, or URL
  value was printed or persisted.
- The approved PNG's SHA-256 was verified before transmission:
  `c002678f891281cc6424f7ae833f21d091949a94b28b75ab78bfe67742ecb4bd`.
  `.env` retained SHA-256
  `3a9b4d4c09088217021480052bd99d7bffd5addcd8a452ee1fb2288521be3aa7`.
- An external exclusive pre-send marker was checked and created before the
  request. The instrumented session allowed one multipart `POST` only, disabled
  redirects, and configured every retry count as zero. The raw response existed
  only in memory; a separate external safe-result file retains the projection
  below so a terminal loss cannot justify a replay.
- The probe invoked the existing `AtlasCloudWanTransport.upload` method. It has
  no path to `generateVideo`, application submission, polling, retrieval, or
  pilot persistence.

## Observed result

Exactly one allowlisted upload POST completed in **2193 ms**. The response HTTP
status was observed before JSON parsing as **200**. The strict current transport
then rejected the response because it has no top-level HTTPS `url`; no production
parser was changed.

| Safe field | Observed finite evidence |
| --- | --- |
| allowlisted POST count | `1` |
| HTTP status | `200` |
| status observed before JSON | `true` |
| JSON parser invoked | `true` |
| overall JSON type | `object` |
| top-level `url` | absent; not a nonempty HTTPS string |
| `data` | present; `object` |
| `data.url` | absent; not a nonempty HTTPS string |
| `data.download_url` | present; `string`; nonempty HTTPS string with host |
| `error` | absent |
| `code` | present; `integer` |
| response `status` | absent |
| conflicting nonempty URL candidates | `false` |
| transport outcome | not accepted; safe exception enum `transport_rejected` |

No response scalar values, signed URL, URL, unknown member name, error text, or
headers are retained in this receipt.

## Unchanged pilot state

The isolated pilot SQLite database was opened read-only before and after the
request. Historical job `vj_22de3a4aac36446aa33597240963524a` remains
`outcome_unknown` with `dispatch_outcome_unknown`; it has no prediction, output
URI, or output hash. The shared ledger remains **5 / 100** requested seconds
reserved with **4** immutable events. The before/after safe snapshots matched.

## Inference and next decision

This live HTTP-200 response establishes that the provider currently returns a
`data.download_url`-shaped upload envelope for this request, rather than the
adopted hosted-doc top-level-`url` envelope. It explains the prior
`invalid_upload_url` outcome and confirms the strict parser's rejection is
working as specified; it does not establish that the nested candidate is a safe
or durable success contract.

Any expansion of the upload-response allowlist needs a separate explicit
contract decision reconciling this observed envelope with the conflicting
published sources, plus regression tests. This receipt authorizes neither a
replay nor video generation.
