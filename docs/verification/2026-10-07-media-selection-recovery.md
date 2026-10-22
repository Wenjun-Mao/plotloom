# Media selection authority and save completion verification

The media workbench now preserves acknowledged selection authority across rapid
shot changes. Independent review, 601 frontend tests and focused browser repeats
pass. The final unfiltered browser gate passed all206 tests6.2m without local
retries on unchanged856 inputs. Root approved and published executable
`7f1041c8a27b036c2e27b0c9e7b3e6601f88b81c` on 2026-10-08 at01:23 UTC.
Full native lifecycle acceptance remains PARTIAL.

## Product failure and durable repair

The first failed full gate retained a real product race: shot02 selection returned
revision2, but a shot03 read started before that ACK later published revision1.
The next selection correctly received backend CAS409. Context and sequence
ownership alone did not represent the minimum acknowledged project revision.

The owning media-read hook now tracks that floor for each project visit. An ACK
raises the floor and starts a complete read for the active context, superseding
pre-ACK reads. A lower projection fails explicitly; it cannot enable mutation
controls or replace the token. Old project visits and unmounted owners cannot
refresh a new workspace. Callers no longer blend a fresh token with stale
bindings. The backend CAS contract and usable shot navigation are unchanged.

[ADR0130](../adr/0130-media-selection-read-after-write-authority.md) records the
contract and rejected downstream workarounds. Deferred hook regressions cover
the held old read, explicit failed-read recovery, A-B-A and unmount ownership.
The imported-still journey retains its original rapid successive shot selections.

## Separate automation completion failures

Ordinary save followed by reload, an external upstream edit or lifecycle cleanup
must establish the exact successful browser write ACK and independent current
readback. A returned click, enabled button or one persisted field is insufficient.
The permanent [playbook](../creative-workflow/graph-workbench-acceptance.md) and
[ADR0127](../adr/0127-reusable-creator-lifecycle-acceptance.md) retain that rule;
intentional delayed-ACK and interrupted-save recovery remain exceptions.

| Journey | Retained failure | Correction |
|---|---|---|
| Brief structure | API preparation began before the UI Source confirmation ACK, correctly refusing missing Source | Await the exact Source PUT ACK/r1 and visible r1 before candidate preparation |
| Creator Production | Restored route-only graph committed r4, but navigation aborted its browser ACK; the older local receipt correctly became stale | Await the owned graph PUT ACK and full independent payload before external board drift/reload |
| Professional graph prose | Reload could interrupt a committed save before its browser receipt advanced; the enabled-button/single-field read was weaker evidence | Register the exact prose PUT waiter before typing; compare acknowledged draft revision and full independent payload before reload |
| Imported still cleanup | Navigation began36.8ms after the final reapproved-selection POST; archive208ms later correctly refused an active local writer | Await that exact final selection ACK, UI readiness and independent binding/revision readback before normal cleanup |

The final cleanup correction does not add ACK waits to the earlier rapid-shot
sequence. No busy retries, lease clearing, timeout weakening, forced interactions
or backend locking changes were introduced. Independent Sol/Medium source review
of the product repair and these bounded harness changes found no blocking issue.

## Executed checks and retained failed gates

All paths below are under ignored local
`output/playwright/full-lifecycle-2026-10-07/`.

| Check | Actual result |
|---|---|
| Focused media unit checks | 10 PASS in two files |
| Full frontend unit suite | 601 PASS in81 files3.34s |
| App and E2E types | PASS; E2E types repeated after the last harness edits |
| Source confirmation repeats | 3 PASS22.8s |
| Imported-still product-repair repeats | 3 PASS43.0s; no test-only waits inserted between the initial shot selections |
| Production ACK repeats | 3 PASS43.1s |
| Final graph and still completion repeats | 6 PASS34.4s, three executions per journey |
| brief-confirm-ack-final-browser-gate | 205 PASS / 1 FAIL5.8m; retained the product selection-floor race |
| media-read-after-write-final-browser-gate | 205 PASS / 1 FAIL6.3m; exposed the distinct Production ACK interruption |
| media-production-ack-final-browser-gate | 205 PASS / 1 FAIL6.2m; exposed the final selection cleanup ordering |
| owned-completion-ack-final-browser-gate | 206 PASS6.2m; no local automatic retry; all856 input hashes unchanged |

The first focused imported-still1440×900 preview pixel was directly inspected:
current/stale history and the loaded preview were readable. This is fixture still
presentation, not native image/video quality or every-route playback acceptance.

The earlier published5aff37e CI37701584435 finished successfully at
2026-10-08 00:02:31 UTC, with205 first-pass browser results and one retry pass.
It is qualified as one flaky result, not a clean206 first-pass gate. The exact
Source confirmation race is corrected above. That old CI does not qualify this
new candidate. Fresh full unfiltered [CI37712695213](https://github.com/Wenjun-Mao/plotloom/actions/runs/37712695213)
was dispatched on published7f1041c at01:23:35 UTC and finished success at02:00 UTC:
Python1,245 PASS and browser shards104+102 first-pass PASS. This qualifies7f1041c,
not later gallery changes.

## Candidate identity and distribution checks

The final gate began and finished with the same856 tracked source, test, config,
service and checked static inputs. Its aggregate is
`ec0762038617641908c0fb096b8be492492e4f10abb30c2c7c0a35b770f8d541`.
The earlier gate manifest helper returned truncated output and failed JSON parsing
before dispatch; the corrected helper records the compact aggregate/count. That
helper failure did not start or qualify a browser gate.

Deterministic rebuilds retain JS
`b9e6654517186f3c08fe50e7ab6485534992558bf5e9e1497c3ead33f4214870`.
CSS remains `d430ea5d72528c509b27446c10eb5ae34cada9c5e8808e8ad72c616570ea10cb`
and `29912296af73c3c5d3cd1eb885ddd30a6741e0b5ea097d18d848c3ea09c5b1a5`.
Normal8841's unchanged e941780 Python serves these frontend bytes through its
checkout mount; post-publication read-only health and all three served-hash checks
pass. Main matched origin after push; all856 gate inputs independently recomputed
to the exact final aggregate. No busy8861 restart, reload, continuation or resend occurred.

Lock, scoped API F401 lint and diff checks pass. Wheel build and installed smoke
pass; wheel SHA256 is
`7521d5af95e62110b538459ffaaa534d58f355ce9f402fe23021b50081d45343`.
Python1,245 PASS381.25s is reused from e941780 because backend source/tests/config
are unchanged; it was not rerun for this frontend-only repair. Later harness and
documentation edits do not alter the built product payload.

## Recovery coverage and remaining authority

[C50 draft recovery](2026-10-07-c50-draft-recovery.md) qualifies exact endpoint
detachment, newer-prose Undo refusal, incomplete JSON retention, valid field
completion and full cleanup. Its blank option/effect baseline does not establish
nonempty metadata preservation. A further UI-origin nonempty metadata check
retained exact option/consequence text and fact/entity effects through detach,
edge-delete/Undo and reopen; its independent r52 payload equals r48, and r54
cleanup equals the complete r46 baseline. The C50 receipt retains the interrupted
combined-helper limitation rather than counting another clean replay.
[C52 project ownership](2026-10-07-c52-project-ownership.md) separately retains
distinct A/B prose and incomplete JSON through history, nodes, modes, Brief/Source
and close/reopen. Immediate navigation after new unsaved prose drained the owning
ACK; full A r60/B r8 cleanup payloads equal their original baselines.
Six-sibling desktop and real OS blur coverage
are already recorded in the main ledger; old roadmap wording is not a new gap.

Owner protection still matches aggregate
`df1716a80d93bdf9aeaf2565464ac030340ab035cf86198d5355befea075f2a5`:
two database row/schema sets, Wind17/Rain67 files and three protected
configuration hashes/modes/UIDs. No native provider call or owner-data mutation
was made by this repair.

Full lifecycle acceptance remains PARTIAL. The [native Character/gallery checkpoint](2026-10-08-native-character-gallery.md)
now qualifies the completed frozen Image delivery and explicit selection; the
earlier active-task wording is superseded. Already authorized routine continuations
must not require repeated approval; ADR0131 records the correction.
Native Scene/Prop/refinement/pair, keyframe/endframe,
H3/all-route playback, video-bearing lifecycle, configured inference and supported
post-install revision/rebuild remain separate required journeys. Software gates
and synthetic media cannot substitute for them.
