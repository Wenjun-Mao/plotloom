# Original native image ingestion follow-up

Scope: owner's bounded follow-up after manual specialist restart; no new generation,
reference selection/approval/rejection, media changes, lease clearing or service restart.
Project `4ede8a69-bd36-4e3e-9e6f-5678181a29fa`, isolated8851, S01 environment;
original job `ij_69ef9153276d482584017a9ac68ddc48`, request hash
`e81b3ff3e37d56f7d3d672f8935711ae009ca6bbd2b135b24283d0c94a67de6d`.
This supplements the [overnight receipt](2026-10-06-full-creator-e2e.md), not a rewrite
of its then-current queued/no-delivery evidence. Executable state remains unchanged.

## Pre-test inventory

| Controls | Functional check / visible state / evidence |
|---|---|
| E09/C34 | Inspect original task; ordinary existing-art-proposal Check admits genuine delivery or retains precise failure. Exact S01 candidate provenance, unselected state; before/after readback hashes. |
| P03 | Reload and repeated existing-job check retain exact job/candidate/assets, no duplicate and no send. |
| P04/C54 | Gallery entry, image zoom, Close/Escape/focus restoration; thumbnail behavior if present. Compare only if multiple viewable candidates exist. |
| E09/P04 | Switch S01→P01→S01, retain exact subject and candidate; no reference decision mutation. |
| E22 | Separate actual1700×900/1280×768 viewport pixel inspection and bounds; >=30s ordinary-input exploration. No mobile/1024 or creative-quality claims. |

Off-happy-path checks: repeated completion refresh cannot duplicate admission;
subject switch and Escape cannot select a candidate or change its ownership.
Normal8841, protected owner projects and pristine planning seed remain out of scope.

## Results

At13:19:04 UTC, ordinary **检查图像交付** called only the original F3B
`art-reference-proposals/ij_69ef9153276d482584017a9ac68ddc48/refresh`.
Before: exported/current, zero deliveries, gallery “等待图片/尚无可显示的候选图片”.
After: delivered/current, same request hash, “图片已返回”, one visible unselected
candidate and explicit “用作此环境的参考图” button. Delivery acceptance is not
reference selection or owner creative approval.

| Identity | Observed value |
|---|---|
| Delivery | `c48e55a2-e6ee-437b-88ba-cd72a5387223`, accepted, manifest SHA `77ed9d4f6d566ba662a954d5ac144b4ebbcab12127692399521c50b8ce10a2f0` |
| Candidate | `a6e48087-1a8c-4a73-880f-943f1b9bf968` |
| Managed asset | `684e1485-a8e5-4344-ac6a-74ab31856c54` |
| Original | `exec-0f5ebbdb-fea5-4046-8584-f4d2f881bc64.png`, PNG1672×941,2164411bytes |
| SHA256 | `e7d08453082acb51715e89a66824f21b28c587521758f50bb83d09b679d255ca` |
| Display SHA | `45b2bd7d3c7f3869923ab42d5212d814fbd7fa6e687ed55b4478537494dcdddc` |
| Stored provenance | origin `art_reference_proposal`, scene:S01, original proposal/delivery/output, rights `unknown`; tool codex_imagegen/task `01a0c506-84d5-7161-8ae0-2ae914e5d81a`; executor revision902a23d/skillv3; explicit exploratory-QA/not-owner-approval limitations |

Served-original GET200 bytes/hash match both the actual delivery PNG and candidate.
Root independently corroborated delivery/identity/provenance and served-original hash.

| Subcase | Action → visible outcome / classification |
|---|---|
| E09/C34 ingestion | Original Check → returned image/current exactS01; LIVE_UI_ISOLATED PASS, supporting READBACK; genuine native delivery, not independent P0 lineage. |
| P03 idempotence | Two more ordinary existing-job Checks, with a reload between, retain byte-identical proposal/asset projections: one delivery/one candidate/assets3→4 once. All three observed POSTs are the same refresh; zero send/prepare/select/reject/cancel POSTs. PASS. |
| P04/C54 thumbnail | Single visible thumbnail click retains exact viewed asset; no current-reference badge/decision. PASS for single-candidate browsing, not multi-thumbnail switching. |
| P04/C54 zoom | Ordinary image click → full bounded zoom; Close and Escape each return to exact image-trigger focus, no selection. PASS. |
| E09/P04 subject | S01→P01 shows prop workspace/no candidates; returnS01 shows original asset and returned status. PASS; no subject reassignment. |
| Comparison | Exactly one viewable candidate; comparison controls absent by current>1 contract. Pair comparison NOT_EXERCISED; no extra image generated. |
| E22 pixels | Separately inspected1700×900 and1280×768 gallery/zoom/details. Natural page scrolling, readable subject/status/details, bounded image/Close; document clientWidth=scrollWidth at both widths. No unintended horizontal overflow, occlusion or distorted image observed. |
| Exploratory | >32seconds paced ordinary scrolling, focus/Tab, thumbnail, zoom/Escape; exact unselected state retained. No mutation commands activated. |

## Observed candidate-projection defect (not repaired)

Technical details show **来源信息不可用 / 权利信息不可用**, while managed-assets
readback retains origin and unknown rights. This is not lost provenance. Root cause:
`media_art_reference_proposals.py:_candidate_dict` uses bare
`ManagedAssetPersistence.managed_asset_dict`, which omits provenance; the separate
managed-assets list joins/project-declares it. `ArtReferenceGallery.tsx:CandidateDetails`
expects `candidate.asset.provenance.origin/rights`. Thus the candidate projection and
frontend contract disagree. Root independently source-confirmed this diagnosis.
Visible source/rights display is FAIL; technical subject/proposal/delivery/asset/hash
are correct. No source patch, sandbox/HTML rewrite or broad workaround authorized here.

## Preservation and boundaries

Before/after SHA256 of JSON-stringified GET projections are identical:

| Projection | SHA256 |
|---|---|
| source-outline | `887931a7103c4ffd179231fb424ef92435765bfc696afcdb3802d610a93778e0` |
| cast | `5ca5a287a9a6122c407566a3c53e15ec28806dc62014f643ce4f242af01bdad3` |
| art | `dc2347401a84de179a639f25f2b2dd0110203a0c94486ea3638e5b22d25df89c` |
| script | `1143ae8b2951b8cb3d5a10b0d56cd37129f1c23e7427c9b13e73cef11a799d2d` |
| graph-workbench | `24a97f8aab962b9cf3880f105b3200c78a3ad0f8829b4904838958972996e387` |
| art-reference-decisions | `7448644781ef722d7f88e30b2d27659cc58310cc968fbe11f23b2f8c3a67f6a6` |

Reference states/decisions remain empty. All three previous managed-image projections
are identical. Retained H3 current selections match overnight identities/revisions:
opening4abc…r2, guidance23640870…r1, silent90f0e4cf…r4, all current/selected;
this is post-check READBACK against prior receipt, not a new playback claim.
Exact dispatch receipt now completed; thread's inflight.json absent after legitimate
admission, with no manual lease deletion. Pristine seed draft1/9nodes9edges/buffers{}
and binding88613527… unchanged. Normal8841/services/source untouched.
Root's before-check independent protected aggregate `df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`
matches overnightfinal/all84 owner files; root's final independent comparison is
identical, including protected configurations. This is separate READBACK support,
not a claim that an unvisited owner UI operation was exercised.

Historical queue/start blockage remains accurate for the overnight checkpoint. Owner
manual restart and actual specialist completion precede this follow-up; the cause or
durability of that wake recovery is not proven by successful ingestion. No new job,
reference acceptance, media/creative-quality approval, source change or full gate rerun.

Evidence: [viewport images](assets/native-image-ingestion-2026-10-07/)
01 pre-check,02 returned gallery1700,03 zoom1700,04 gallery1280,05 zoom1280,
06 unselected/details1280,07 unselected/details1700. All directly inspected;
root separately inspected02–06. Final browser remains S01,1700×900/no modal.
Nonprinting exact-credential scan of13 scoped docs/screenshots/delivery/receipt files
found zero matches; no credential values printed or tool-history redaction claimed.
Main reviewed the complete receipt, independently inspected02–06 pixels and verified
original served PNG identity/protected comparison. This scoped documentation/evidence
publication includes no source/runtime repair; the projection defect remains NOT REPAIRED.
