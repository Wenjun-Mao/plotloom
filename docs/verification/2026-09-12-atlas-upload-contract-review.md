# Atlas upload contract review

Captured 2026-09-12. This is a documentation and fixture review only: no Atlas
request, generation, poll, download, pilot database, ledger, secret, or
historical job was touched.

## Sources and findings

`chub search 'AtlasCloud API' --json` returned no Atlas documentation record on
2026-09-12, so this review used Atlas's public sources directly.

1. [Atlas Upload Files](https://www.atlascloud.ai/docs/upload-files) documents
   `POST https://api.atlascloud.ai/api/v1/model/uploadMedia`, a multipart
   `file` request field, and code examples that read the temporary upload URL
   from top-level `url`.
2. [Atlas Calling your first model](https://www.atlascloud.ai/docs/models/get-start)
   independently shows the same upload endpoint, multipart `file` request, and
   `response.json().get("url")` response access. It separately documents video
   generation IDs at `data.id`; that is not an upload-envelope contract.
3. The AtlasCloudAI organization’s
   [upload skills reference](https://github.com/AtlasCloudAI/atlas-cloud-skills/blob/main/atlas-cloud/references/upload.md)
   conflicts with the hosted docs: its examples read `data.download_url`.
   It does not support Plotloom's former `data.url` branch.

## Diagnosis and disposition

Plotloom already sends the documented endpoint and multipart field. Its response
adapter, however, accepted an undocumented `data.url` success shape in addition
to the hosted contract's top-level `url`. That was a strict-boundary defect: a
2xx error-like object could be treated as a successful upload if it happened to
contain that nested member. The transport now accepts only a top-level HTTPS
`url`, with fixtures covering the documented request/success pair and rejection
of `data.url`, `data.download_url`, error objects, and non-object JSON.

This is a code-contract repair, not live qualification. The prior one-shot probe
retained neither its body nor URL and therefore does not establish its provider
envelope or the cause of its `invalid_upload_url` result. The conflict between
Atlas's hosted docs and organization-maintained skills reference remains an open
provider-contract question. Any future expansion of the response allowlist needs
separate authorization, source reconciliation, and safe shape evidence; it must
not retry or reinterpret the historical unknown dispatch.
