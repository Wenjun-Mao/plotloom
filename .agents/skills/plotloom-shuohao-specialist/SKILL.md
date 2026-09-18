---
name: plotloom-shuohao-specialist
description: Deliver one frozen Plotloom Shuohao-derived creative-stage candidate and HTML report from an explicit project-local package, without changing project canon, approvals, selections, media, or application code.
---

# Plotloom Shuohao Specialist

Use this skill only for one exact package path supplied by the coordinator. The
package's `request.json` is the authority. It is a manual candidate handoff,
not a backend job, a review decision, or permission to edit canon.

## Scope and ownership

- Read `request.json`, `COPY_ASSIGNMENT.txt`, every `inputs/*.json`, and
  `completion-manifest.example.json` before starting.
- Read the pinned stage skill named by `upstreamSkillPath`, plus the references
  it routes to for this request. Run its deterministic `validate` and `render`
  commands from `third_party/shuohao-skills`; this is a repository-checkout
  seam, not a capability supplied by an installed Plotloom wheel. Do not use an
  unpinned checkout, a global installation, an API key, or a provider fallback.
- The author owns source text, rights/attribution declarations, desired
  adaptation, and acceptance. The specialist owns a proposed stage-shaped JSON
  candidate and a derived report. F0 trusted Plotloom code owns frozen identity,
  request hashes, candidate admission, and currentness. A later selected owner
  must own review and canonical installation.
- Preserve upstream JSON shapes directly: write only the requested stage's
  `candidateFilename` (`outline.json`, `cast.json`, `art.json`, `script.json`,
  or `storyboard.json`). The HTML report is derived from that JSON; it is never
  an editable authority.
- For a `characters` candidate, preserve every established `characters[].id`.
  Each ID must be nonblank and unique. This is Plotloom's narrow receiving
  extension to the upstream shape: do not invent a replacement identity store
  or alter upstream fields to satisfy it.
- For an `art` candidate, honor the request's explicit Plotloom `sectionUsage`
  extension. It is code-owned linkage, not upstream art semantics: emit exactly
  the supplied section IDs once, and use only the candidate's stable scene/prop
  IDs. Do not invent an episode, hook, or parallel graph to populate it.

## Delivery

1. Follow the upstream skill's stage boundaries and validators. Seed-derived
   facts in supplied inputs are trusted context, not fields to reinvent.
2. From the package directory, write exactly the sibling
   `../delivery/<candidateFilename>` and derive `../delivery/report.html`.
   Never create `package/delivery`. Do not produce media in this F0 path.
3. Copy the completion template to `delivery/completion.json` and fill it
   truthfully: actual byte hashes, checked-out code revision, this skill's hash,
   model/reasoning when known (including a coordinator-specified execution
   model), and concrete limitations. Publish the
   completion file last, once; do not edit it or either declared output later.
4. Re-read the manifest and compare job ID, request hash, stage, filenames, and
   hashes with the frozen request. Report only the package and candidate paths.

## Prohibitions

- Do not modify package files, source/project records, accepted revisions,
  approvals, selections, managed assets, or any application/test code.
- Do not claim source clearance, creative approval, currentness, or canonical
  installation. A stale request must be returned as a candidate and rejected by
  the owning currentness check.
- Do not start a second coordinator, queue, plan-expansion system, or a custom
  replacement for upstream stage validators/reports.
