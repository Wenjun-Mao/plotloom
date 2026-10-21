# H3 dashboard generation console

Status: delivered at `30c3df75`; deployed on Spark and private HTTPS verified
2026-10-21 after owner activation. Baseline `deebca11`.

Evidence: [verification receipt](../verification/2026-10-21-h3-dashboard-generation.md).
Later [owner-requested manual walkthrough](../verification/2026-10-21-h3-console-manual-walkthrough.md)
completed one live canary and core UI journeys, and identified two client-side
defects: repeated pagination while loading and poll-erased playback errors.
Both were separately authorized, [corrected and deployed](../verification/2026-10-21-h3-console-ui-state-fixes.md)
at `ef8417ba`, with unit and real-browser regression evidence; neither was waived.

## Approved deliverable

Extend the specialist dashboard with single H3 image-to-video submission: uploaded
or downloadable-URL start image, optional same-mode end image, prompt, quality
1/2/3/8, six exact resolutions, 5–15-second duration, optional seed and aspect policy.
Open the accepted job in the existing queue/detail/preview/download interface.
Allow copying settings into the form; images must be supplied again.

The existing gateway remains the sole admission/queue/dispatch owner. Add only a
fixed-target server-side submission boundary using a separately mounted gateway
key. Preserve read-only database/media mounts, tailnet-only access, and unknown
dispatch safety. No browser credential, new database, GPU/model load, automatic
retry, cancellation/deletion, batch, T2V, voice or Qwen generation control.

## Execution and verification

1. Record the newly approved write boundary in ADR 0100, leaving ADR 0099 as history.
2. Implement bounded, validated JSON/multipart forwarding to exactly the existing
   H3 image admission route. Require same-origin browser POST; never replay a
   submission with unknown outcome. Keep upstream credentials/errors private.
3. Implement Chinese form, single-flight submission, explicit error/unknown state,
   selected-job polling and deliberate settings reuse without resubmission.
4. Test via mocked upstream plus isolated real FastAPI/file-SQLite browser journey.
   Run the full locked gateway suite and targeted UI/lint checks. No new live model
   generation is needed for this slice; browser fixtures are not model acceptance.
5. Review a stable candidate independently. At an observed idle checkpoint, rebuild
   and replace only the dashboard container. Mount a dedicated mode-0600 secret
   file, not the gateway environment file. Verify healthy reads, protected POST and
   unchanged generation containers. Preserve pending native Tailscale-admin gate;
   do not bypass it or expose an alternative public listener.
6. Update Chinese guide/receipt and commit locally. Broader specialist integration,
   director contact, merge and push remain held. Stop after deployed-loopback
   verification if administrator HTTPS activation remains unavailable.

Rollback: restore the preceding dashboard image/config only; leave generation,
SQLite, outputs, shared lane and unrelated Serve handlers intact.
