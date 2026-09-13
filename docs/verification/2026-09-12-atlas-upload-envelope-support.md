# Atlas upload-envelope support verification

Captured 2026-09-12 for the explicit parser-contract repair. This is not a live
provider qualification, upload, video submission, or audiovisual acceptance.

## Root cause and decision

The isolated upload receipt recorded an HTTP-200 object with a nonempty HTTPS
`data.download_url`, while the transport accepted only top-level `url`.
Atlas's hosted upload documentation shows the top-level form; the
AtlasCloudAI-maintained skills reference shows the nested form. ADR 0031 now
allows exactly those two forms, not a general nested-URL search.

## Verified contract

- The multipart request remains one `POST` with field `file`; no retry policy
  or runtime opt-in changed.
- Top-level `url`, nested `data.download_url`, and an exactly matching dual
  form are accepted. A signed query string returns unchanged in memory.
- Missing candidates, `data.url`, deeper fields, malformed/non-object `data`,
  null/non-string/empty/insecure/hostless/userinfo/control-character/malformed
  port candidates, non-null `error`, and conflicting candidates are rejected
  with the existing allowlisted `invalid_upload_url` diagnostic only.
- Existing service tests retain the post-claim unknown-outcome and 5-second
  budget behavior; this parser change does not create a replay or release path.

## Evidence boundary

The checks use mocked HTTP responses and make no authenticated or provider
request. No response URL, provider body, credential, or signed query string is
persisted by the parser or included in its diagnostics. This validates a narrow
source contract only; the 2026-09-12 shape-probe receipt remains the sole live
observation and no fresh provider result is claimed here.
