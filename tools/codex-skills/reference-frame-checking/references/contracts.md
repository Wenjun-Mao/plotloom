# Case and report contract v1

Paths are absolute, originals are retained and never modified. All image entries use `{ "path": "/absolute/file", "sha256": "..." }`. A normalized case contains `schemaVersion: 1`, `caseId`, `sourceContext` object, nonempty `originals` array of pinned source files, `frames` array and `references` array (possibly empty). Each frame has unique `id`, `image`, nonempty `expected`; include `sourceCut` and `atMs` when known. Each reference has unique `id` and `image`. IDs identify roles, not pixel content: equal hashes across distinct IDs are valid. Supply relevant references explicitly; an empty array is not proof of identity matching. The production adapter verifies the pinned manifest storyboard and ordered images, assigns each image to its corresponding source cut and checks timing; when a manifest omits the segment ID, its pinned storyboard must contain exactly one segment. It does not rewrite originals.

Preparation verifies all pins and records case hash, current skill/tool hashes, evidence IDs and canonical fingerprint. It performs no image decoding or extraction. Validation recomputes bindings from the current original files; changed, missing, or foreign inputs invalidate the report. A content hash cannot prove an image was viewed or establish its creative quality. Keep old reports and cases separate when inputs or rules change.

Example report:

```json
{
  "schemaVersion": 1, "caseId": "E02-10", "bundleFingerprint": "fingerprint",
  "skillVersion": "0.1.0", "reviewer": {"model": "gpt-6.1-terra", "reasoning": "high"},
  "decision": "fail", "summary": "A visible material contradiction.",
  "findings": [{"category": "action-start", "severity": "material", "claim": "Describe visible source conflict.", "evidenceIds": ["frame:1"]}],
  "evidenceViewed": ["frame:1"], "limitations": ["Other frames not yet inspected."]
}
```

Decision is `pass`, `fail` or `needs_review`. Findings have `category`, `severity` (`material`, `minor`, `uncertain`), nonempty `claim`, and nonempty `evidenceIds` contained in `evidenceViewed`. Pass requires all supplied IDs and no material/uncertain finding. Fail needs at least one material finding. Needs-review cannot coexist with an observed material finding: use fail and state additional uncertainty. Mechanical validation checks declarations, not truth or viewing. Record the actual viewing tool trace and audit separately. Missing source context or inaccessible image blocks a pass, not a reason to invent evidence.

Batch sampler input is a JSON array of `{ "report": "...", "bundle": "..." }`, paths relative to the batch file. It validates current reports, samples pass/fail with a recorded seed, and lists needs-review separately. It performs no audit; coordinator opens original images independently and records actual agreement and coverage.
