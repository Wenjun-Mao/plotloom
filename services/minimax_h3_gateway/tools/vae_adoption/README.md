# Bounded October 6 D adoption

Operator-only entrypoint for [the approved plan](../../../../docs/roadmap/2026-10-06-h3-vae-adoption.md).
It is not a public gateway route or general updater. All paths, rollback names,
frozen inputs and ceilings intentionally describe this single maintenance.

Run serially on Spark from the staged source release:

1. `python3 deploy.py prepare`: prove gateway/Voice Lab/Comfy idle, capture exact
   baseline and published voice/take hashes, then pause serving services.
2. `python3 deploy.py component`: same Comfy image, no network/server/diffusion,
   read-only node/model mounts; run `verify_lifecycle.py`. That harness imports
   pinned `main` to initialize actual DynamicVRAM, without calling its server.
   Importing only `model_management` leaves a static patcher and is not equivalent.
3. `python3 deploy.py activate`: validate successful lifecycle/idle/original IDs,
   build a **source-only** gateway overlay from a verified local base-image tag
   with pulls disabled, then retain original containers and recreate the pair.
   Preserve environment privately, mounts, entrypoint/Cmd, network, restart and
   shared memory; add only the maintained node, read-only models and fast flag.
4. `python3 canary.py`: **at most two sole POSTs**, ordinary portrait and Ref2VA,
   using hash-bound retained inputs. Durable uncertainty is recorded before each
   submission. Successful polling, full video/audio decode and snapshot checks
   must pass. No retry/replacement switch; inspect an existing receipt instead
   of invoking the script again. `--reconcile-succeeded` is a narrow recovery
   for one acknowledged ID already proven `succeeded`: it GETs/verifies that
   existing output and may then consume the still-unused second claim. It
   refuses unknown/rejected/failed claims, never POSTs the accepted case again,
   and never increases the ceiling. A stopped observer can be reconciled only
   when both claims already have acknowledged IDs, the first passed and the
   second is server-proven succeeded: that path has no POST left to perform.
   Preserve pre-reconciliation receipts and the observer error in final evidence.

Evidence root:
`/home/wjmao/services/spark-comfyui/experiments/h3-vae-d-adoption-20261006`.
Lifecycle/canary proof copies are private; tracked receipts are secret-free.
The lifecycle test uses a 128px image and 0.1s stereo audio, not a full render.

For safe failure recovery, `python3 deploy.py restore` refuses busy/unknown
managed work, unreleased Voice Lab grants or nonempty Comfy queues. It handles
partially absent replacement containers, retains diagnostics, restores the
original pair and verifies identities/readiness. Do not manually bypass those
checks or replay an uncertain generation. Existing proof/container names refuse
collision; completed maintenance is not restartable from `prepare`.

No model downloads, data reset, voice synthesis, Plotloom integration, director
message, merge or push are part of these tools.
