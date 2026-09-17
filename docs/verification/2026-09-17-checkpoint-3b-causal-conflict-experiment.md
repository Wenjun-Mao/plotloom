# Checkpoint 3B causal-conflict diagnostic receipt

This is a smallest, disposable feasibility experiment for the unresolved
author-owned causal inconsistency recorded in the typed-entry requalification
receipt. It is not a production gate, an implementation change, a detector
accuracy claim, Storyboard Approval, human creative approval, or checkpoint 3B
acceptance.

## Diagnosis before dispatch

The retained Scene Beats prompt artifact
`c749d5ca-b5d0-4551-a7fa-0a378202336c` in trace
`.local/relay/4a28dfe9-1dff-46f7-9239-45fa0d7cfcba/trace-final.json` supplies
the keep-ending node with a summary that says the siblings jointly repair the
watch. Its sole incoming edge and the compiled typed entry both declare
`prop_pocket_watch=已修复` before that node begins. The pre-dispatch hypothesis
was that the node summary denotes action inside that node, and therefore asks
for an event already declared complete at entry. This is a content/causal
question, not a typed-entry compiler failure: the direct edge itself is
internally consistent.

The sell-path/join predecessor-state omission remains a separate deferred
problem and is intentionally excluded. No retained project, canonical stage,
profile, configuration, source, or generated media is modified.

## Frozen A/B design

The ignored local record contains two neutral case IDs, an unchanged extracted
source case, a control differing only in `targetNode.summary`, one common
conflict-report instruction, pre-dispatch hashes and expectations, and raw
sanitized responses. The control changes the summary's repair action to a
post-repair handoff; its remaining supplied fields were inspected and do not
express the same temporal conflict. Exactly two independent requests will be
made using the current default profile's existing public settings, with no
pipeline integration, retry, schema framework, prompt tuning, or chain history.

The success condition is narrow: report the specific A conflict with the
relevant summary and typed-entry references, and do not report that same
relationship as a conflict in B. A format failure, unsupported assertion, or
unknown request outcome is a failed experiment. The result can establish only
one A/B feasibility observation, never detector precision or general
reliability.

## Dispatch record and result

The two independent requests used the saved default profile version 11 / hash
`6f0e6d29521b4d19b2bf1e8dd7410de72355390e20d916289b8d8ad6e9567473`,
the existing `qwen3527b` OpenAI-compatible transport, disabled reasoning, its
existing 10-second connection and 600-second attempt limits, and the existing
Scene Beats maximum of 8,192 output tokens. The server credential was held in
an ephemeral one-use lease and is absent from all retained evidence.

| Case | Input SHA-256 | Request / usage | Returned status | Assessment |
| --- | --- | --- | --- | --- |
| A | `59737682343fd674b794750620e2c479bbaf9b960a70d1714a69c9411e4cfa1c` | `chatcmpl-7jvfi3yobH2dJ4ZGcak5QGRdnaVEpzJC`; 750 input / 78 output tokens | `no_conflict` | Failure: it cited only `incidentEdges[0].entityStateEffects` and `typedEntry.requiredEntityStates`, which agree, while omitting `targetNode.summary` and the stated temporal conflict. |
| B | `9a0b2fc6ec20d909b78b715376861e5872225a6b62560d1c866613d288a8b26c` | `chatcmpl-E0FEXk7sQgYOLhJwWo90utTIv86fACaP`; 757 input / 78 output tokens | `no_conflict` | Not a same-relationship false positive, but it made the same unsupported narrow comparison and omitted the changed summary. |

Both outputs were valid JSON objects with the requested keys and a permitted
status, but neither actually reviewed the supplied target-node field that
distinguishes the cases. Therefore the predeclared success criterion is **not
met**. This is a failed feasibility observation: the reduced material does not
itself state that the summary's repair occurs after the supplied entry state, so
the experiment did not contain a hard temporal contradiction under its own
generic rule.

The neutral case IDs differ only for request identification. After excluding
that key, the exact semantic diff is one path: `targetNode.summary`, changing
`姐弟俩共同修好了怀表` to `姐弟俩带着已修复的怀表，准备交给等候多年的顾客`.
The original extracted case is retained unchanged. Raw sanitized request and
response evidence, pre-dispatch expectations, hashes, and the profile-free
transport record remain only in ignored
`.local/relay/11f6d741-7a58-4646-ac12-4f137f6cf0e5/`.

## Independent Terra review and disposition

An attended, read-only Terra review examined the exact diff and both completed
envelopes. It confirmed that, other than neutral `caseId`, only
`targetNode.summary` changes; both stop-finished requests return valid allowed
objects; and their cited edge effects and typed-entry states agree. It further
found that case A says the siblings repaired the watch but does not expressly
locate that repair after entry. The control is plainly compatible. Thus the
responses' `no_conflict` conclusion is defensible for the reduced material even
though neither cited the summary, and the predeclared A expectation relied on
an unstated sequencing assumption. This is engineering review only—neither
human creative approval nor general detector reliability is claimed.

Tracker state: **experiment complete; checkpoint 3B remains not accepted**.
Recommendation: **refine with one later, separately authorized experiment**.
Its frozen A input must state the temporal relation explicitly (for example,
the entry state says the watch is already repaired and the node summary says
that during this node the siblings repair the previously unrepaired watch); B
would remove only that stated incompatibility. Retain the same narrow,
non-generative boundary. This experiment should be discarded as support for a
temporal-conflict detector claim. The deferred sell/join causal defect remains
out of scope.
