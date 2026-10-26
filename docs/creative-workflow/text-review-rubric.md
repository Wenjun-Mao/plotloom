# Text quality review

Read each opaque content sample independently. Score the six dimensions below
with integers from 1 to 5. Use 1 for a fundamental failure, 2 for substantial
repair, 3 for usable content needing revision, 4 for coherent and effective work,
and 5 for unusually strong work with only minor refinements. Judge the supplied
content; do not infer who or what produced it.

| Score-sheet field | What to assess |
|---|---|
| `narrativeClarity` | Clear stakes, goals, dramatic progression and understandable outcomes. |
| `branchCausality` | Choices cause distinct consequences; joins and endings preserve their conditions. |
| `continuity` | Character knowledge, motivations, objects and world facts remain consistent across each route. |
| `performanceReadability` | Dialogue and actions give performers concrete, intelligible intentions. |
| `shotLanguage` | Shots communicate action and emotion with clear staging, framing and transitions. |
| `pacingAndEditCost` | Timing supports the drama and branching structure without avoidable repetition or impractical edits. |

Set `fatalContradiction` when a contradiction makes the story or a complete route
incoherent without fundamental rewriting. Replace every draft zero and PENDING
value. Preserve the prefilled identity/hash fields; submit only the closed score
sheet, without adding comments or metadata.

The quality gate requires no fatal contradiction, each score at least 3, each
sample's mean at least 3.5, and each dimension's median across the complete reading
set at least 4. These scores are independent content assessment, not a claim of
human product approval.
