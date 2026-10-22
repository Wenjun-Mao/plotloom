# ADR 0091: Minimum character design at confirmation

Status: accepted, 2026-09-26

The author rejected the all-optional character form: permissive persistence is
not a useful product definition. Each character needs at least one nonblank
personality trait and a nonblank appearance before acceptance or reopened save.
Temperament, voice direction and review-note content remain optional at this stage.

The specialist proposes these fields; the author may edit them. Trusted code
checks structure and substantive text presence, not creative quality. A trailing
legacy inference marker alone does not count as text. Do not strip stored values.
Reject non-string personality entries; allow blank spare trait rows when at least
one trait is nonblank. No invented fallback from motivation or automatic content.

Both confirmation endpoints enforce the same rule. The editor marks the trait
group and appearance with `*`, displays adjacent errors and blocks submission.
New frozen character-writing instructions include this minimum. Admission may
still expose an incomplete candidate for author repair; existing accepted
revisions remain readable and unchanged, but any new save must meet the rule.

This supersedes the all-optional UI note, not the source-note separation of ADR
0090. Tests cover blanks, missing/malformed values, marker-only text, repair,
multi-character validation and both confirmation paths. No media dispatch,
creative acceptance, historical data rewrite or new voice requirement.
