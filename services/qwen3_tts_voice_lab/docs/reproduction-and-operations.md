# Multi-engine Voice Lab: reproduction and operations

This is the private specialist Spark deployment, not a generic pip-only GPU
recipe. Use the checked service lock for the lightweight API; retain the
qualified inference environments and captured inventories.

## Exact installation boundary

| Engines | Python under `/home/wjmao/` | Models under `/home/wjmao/models/` |
|---|---|---|
| Qwen Design/Base | `services/qwen3-tts-trial/.venv/bin/python` | `qwen3-tts/voice-design-1.7b`, `qwen3-tts/base-1.7b` |
| MOSS | `services/moss-voicegenerator-trial/.venv-arm64/bin/python` | `moss-voicegenerator`, `moss-audio-tokenizer` |
| Index | `services/index-tts2-trial/.venv/bin/python` | `index-tts2/2.0` including local `hf_cache` auxiliaries |

All use Python 3.12.3 and the qualified CUDA Torch 2.14.0 build. Qwen uses
qwen-tts 0.1.1, Transformers 4.57.3, BF16/SDPA; MOSS Transformers 5.0.0,
BF16/SDPA with cuDNN SDPA disabled as in its ARM64 trial; Index Transformers
4.52.1, FP32, no DeepSpeed/custom CUDA kernel. Do not flatten these into one
environment or upgrade the proven inference stack to satisfy a generic solver.

Pinned source/checkpoint/codec/classifier revisions and settings are in
[`engines/catalog.py`](../src/plotloom_voice_lab/engines/catalog.py).
MOSS source: `services/moss-voicegenerator-trial/source` at
`934d6826b084c46a0d033402174d5f8ac4ed2519`.
Index source: `services/index-tts2-trial/source` at
`ee40fa7d6c6b8a2c7f06105f9f1e65775b74868c`.
Native Linux WeTextProcessing 1.2.0 / Pynini 2.1.7, FST libraries and Python
3.12 compiler headers live under `services/index-tts2-trial/linux-normalizer`.
Engine-private `PYTHONPATH`, `LD_LIBRARY_PATH`, `C_INCLUDE_PATH` select them.
The trial normalizer monkeypatch is **not** used. Index's local auxiliaries
are `hf_cache/w2v-bert-2.0`, `semantic_codec_model.safetensors`,
`campplus_cn_common.bin`, `bigvgan`; only text mode loads `qwen0.6bemo4-merge`.

### Inventories, not a clean-solver claim

`tools/capture_runtime.py` captures effective package versions, source/model/
tokenizer/normalizer/library/service file hashes and native conda metadata.
Keep the private `runtime.json` and `runtime-inventory/` alongside the wheel.
Captured package inventories are checked in under `deploy/engine-locks/` as
reproduction evidence, not independent pip-only installation recipes.
It never downloads weights. The child verifies files/packages before inference
and uses offline HF mode. Changed runtime makes frozen jobs unavailable.

The pinned MOSS custom processor does not accept `local_files_only`; it leaks
that kwarg to ProcessorMixin and fails before inference. Use the qualified
processor arguments and enforce offline mode in the child environment;
the model loader still accepts its own `local_files_only=True`.

Inherited trial environments have pre-existing `uv pip check` warnings: CUDA
ARM64 wheel platform metadata; unused Qwen package/Transformers constraints in
MOSS/Index; Index ONNXRuntime/Protobuf metadata. Actual adapter paths are pinned
and qualified, not every installed package combination. A fresh rebuild must
reconstruct ARM64/native overrides from the captured inventory and prior
trial receipts, then requalify. Blind `pip install -r` is not a verified rebuild.

## Licenses and intended use

Qwen/MOSS source and checkpoint notices are Apache-2.0; retain notices and
provenance. Index source and checkpoint licensing differ: the installed
checkpoint's `LICENSE_ZH.txt` is the bilibili model agreement, not Apache.
Its Chinese revenue threshold is **RMB 100 million annually**, not the billion
figure in some English summaries. It also sets attribution, redistribution,
downstream-notice, model-training and prohibited-use conditions. Preserve and
review the exact installed notices before changing deployment/use.

Verified notice SHA-256 values (2026-09-30):

| Installed notice | SHA-256 |
|---|---|
| Index checkpoint `LICENSE_ZH.txt` | `366175ecf329274358801b8365922677c52f25e643dcf00f0bc15857b5b2777f` |
| Qwen VoiceDesign `README.md` | `acfaf6c0d433866cb5e2bb73e7915ea3767f5a2e3abca413b485635a2c72b5e6` |
| Qwen Base `README.md` | `621b7e88f1867bc03d817176fc1f7f55f4b5a70654b2a07fdcda1e169efb024b` |
| MOSS source `LICENSE` | `e83b87b4c86fc39a3e3278705e02f3599d63b0a9fd006a6ec7aa721d38d4086d` |

This qualification is private owner-directed creative inference/listening,
not AI training, redistribution or general commercial legal approval.
Recheck applicable agreements before public or third-party use. Notice hashes
are retained with the deployment receipt; a working canary is not permission.

## Build and idle cutover

From this service directory:

```sh
uv run --locked pytest -q
uv build --wheel --out-dir dist
uv export --locked --no-dev --no-emit-project --output-file dist/control-requirements.txt
```

1. Check Lab `/health` idle, gateway active/queued counts zero, ComfyUI queue
   empty. Never preempt somebody else's work.
2. Stage wheel, exported locked requirements, tools and unit in
   `/home/wjmao/services/plotloom-voice-lab/releases/`.
3. Create its lightweight `.venv` with `/usr/bin/python3.12`; `uv pip sync
   --require-hashes` the exported requirements, install wheel `--no-deps`.
   Check app imports without Torch. Preserve the qualified engine packages.
4. For the current shared deployment, stop **both** control owners: the gateway
   container and `plotloom-voice-lab.service`. Prove no accepted work/grant is
   active before replacing a package. The Lab-only command below is the older
   single-service migration helper; for shared cutover use
   `prepare_shared_cutover.py` as specified in the shared deployment section:

   ```sh
   .venv/bin/python releases/preserve_cutover.py \
     --data-root /home/wjmao/services/plotloom-voice-lab/data \
     --backup-root /home/wjmao/services/plotloom-voice-lab/backups/<unique-name>
   ```

   It backs up exact SQLite/media and proves every old column/row and WAV hash
   survive additive migration on a copy. Never overwrite an existing backup.
5. Install the same wheel `--no-deps` into all three engine environments.
   Do not change their Torch/Transformers/native packages.
6. Capture private configuration:

   ```sh
   .venv/bin/python releases/capture_runtime.py \
     --output /home/wjmao/services/plotloom-voice-lab/runtime.json \
     --inventory-dir /home/wjmao/services/plotloom-voice-lab/runtime-inventory
   ```

7. Install the reviewed unit under `~/.config/systemd/user/`, daemon-reload and
   start. Only the existing data root migrates; no reset. Verify old Voice ID
   source/H3 hashes, schema v4, `/api/engines`, chooser and worker health.
8. Retain the old unit/wheel and scoped backup for operator-directed recovery;
   never casually restore over later work. Refresh open browser tabs.

Runtime manifest mode is 0600. Executables and paths are server-owned, never
author fields. Public responses expose engine settings/fingerprints, not
private runtime paths or credentials. Run one worker; the enabled user unit
and linger survive reboot.

A web-only wheel replacement does not require inference changes. At the same
idle boundary, retain the previous release, reinstall the wheel `--no-deps`
into the CPU API and three engine environments, and compare installed Python
files to the existing manifest. If they are identical, keep that manifest and
all model/dependency settings. If Python changes, recapture its fingerprints
and review affected verification. Never disable the check to complete a deploy.
The [2026-10-01 receipt](../../../docs/verification/2026-10-01-published-voice-takes-shared-admission.md)
records the actual deployed artifacts and preservation/restart proof.

## Resources and failure handling

Admission visibly waits below configured MemAvailable of 12 GiB Qwen / 20 GiB
MOSS / 24 GiB Index, or if ComfyUI is busy/unreachable. These are advisory
thresholds, **not certified peak-memory limits** or a global GPU scheduler.
Timeouts: 1800 seconds resource wait, 900 seconds child execution. No replay
or engine fallback. Every child process group is reaped before the next job,
also on stop. Linux page cache need not return to an exact pre-job value.

For qualification, an operator may temporarily stop idle
`qwen-image-sglang.service` under existing owner authorization. Restore it and
verify **both** `http://127.0.0.1:30010/health` and `/v1/models`, plus gateway
readiness. Normal Lab requests never stop another service.

The [controlled CUDA retest](../../../docs/verification/2026-09-30-voice-lab-cuda-neutral-retest.md)
passed after operator-directed image-service pausing. The old incident's
kernel log confirms CUDA context-buffer allocation OOM; its exact allocator
cause remains unresolved. Neither MemAvailable nor CUDA-reported free certifies
an allocation on shared GB10 memory. Do not add silent OOM retries/cache flushes
or use this pass to promise that all resident workloads fit.

The later [closeout](../../../docs/verification/2026-09-30-voice-specialist-reliability-closeout.md)
also passed that exact path with Qwen-Image running: once with Comfy models cold
and once after a real Ref2VA job (30.553 GiB host MemAvailable before Index).
No resource thresholds, inference packages or cache policies were changed.
The old allocation cause remains unresolved, not silently credited to 0.38.

The new [ADR 0212](../../../docs/adr/0212-published-voice-performance-takes-and-shared-admission.md)
contract routes all Lab admissions through the gateway-owned durable lane.
Direct Comfy/SGLang calls and unrelated GPU containers remain outside it; reserve
operator windows for those. Advisory headroom checks are not a memory guarantee.

## Shared admission deployment and recovery

Keep exactly one gateway dispatcher and one Lab execution worker. Do not start
old independent voice workers alongside this deployment. Install the same Lab
wheel in the CPU API and all three qualified engine environments; inference
packages, model assets and resource thresholds stay unchanged. Recapture runtime
fingerprints after installing the new wheel: only the installed Lab source changes;
do not reuse a manifest that pins the previous package's Python files.

Private 0600 file `/home/wjmao/services/plotloom-voice-lab/dispatch.env`:

```text
VOICE_LAB_GATEWAY_URL=http://100.64.35.71:8090
VOICE_LAB_DISPATCH_KEY=<private-control-secret>
```

The systemd unit requires that file. The gateway's existing private `.env` adds
`H3_VOICE_LAB_URL=http://100.64.35.71:8897` and
`H3_VOICE_LAB_KEY=<same-private-control-secret>`. This private channel key is
separate from the ordinary gateway client Bearer Key. No key enters SQLite,
public responses, media or tracked examples. HTTP is deliberate on the Tailnet.

At an idle cutover, stop the two control-plane owners, back up exact Lab and
gateway SQLite/media, prove additive migration on copies, then deploy. Gateway
adds `generation_lane`; Lab schema v4 adds takes, transactional registration
outbox and one-use execution grants. Existing terminal records/JSON and WAVs
are preserved. Restore control services, check all backend health and hashes.
Do not restart or rebuild ComfyUI/SGLang or touch model installations.

Use `tools/prepare_shared_cutover.py` on Spark for the scoped preservation and
copy-migration proofs. Existing Docker-owned gateway WAVs are root/0600: its
no-network Docker helper reads only the identified service roots and assigns
the backup copies to the operator. It never changes live asset permissions or
mounts model directories. Keep failed partial preparations as evidence;
`--services-already-stopped` requires both control owners demonstrably stopped.
SQLite verification needs journal/SHM bookkeeping access even when the queries
are read-only; a read-only filesystem mount is not equivalent to a read-only SQL
connection. Never interpret that verifier failure as damaged media or reset data.

`tools/qualify_published_takes.py` admits the capped experiment exactly once.
If an observer stops after admission, `tools/observe_published_takes.py` can only
GET the three known jobs from its retained receipt, using a new exclusive
observation receipt. Video statuses submitting/submitted/transfer_pending are
nonterminal; the exact reference hash is verified from admission plus its frozen
binding, not ordinary status. No observer can authorize a replacement call.
`tools/verify_shared_restart.py` requires a passed observation and idle owners,
then compares complete SQLite state and retained WAV/media hashes over restart.

CPU registration can reconcile duplicate acknowledgements. The gateway orders
all jobs by its registration sequence, not cross-host timestamps. Until registered,
the UI shows unknown queue position. No local inference fallback exists.

Only private `/internal/executions` may authorize a frozen voice job/hash.
The grant is recorded before enqueueing; duplicate delivery cannot run it twice.
The process group is reaped before `releaseConfirmed=true` is persisted. The
dispatcher queries that exact grant after a lost reply; it never resends it.
Never-started outbox entries survive restart. Dispatched voice jobs become
interrupted with an unreleased grant, retaining uncertainty and blocking the lane.

Investigate `generation_lane` active entry/error, the Lab's exact execution grant,
and retained runner/PID events when blocked. Missing acknowledgement may resolve
through the original grant's status. Hard-crash/reaping uncertainty requires an
explicit operator reconciliation of the owned process and evidence; this slice
has no force-release API. Healthy/idle-looking services are not release proof.
Do not clear registries, delete active rows, reset databases, expire leases or
restart an old dispatcher to bypass the hold. Never replay unknown inference.

The gateway's completed voice-registration audit expires after 30 days. Durable
Lab takes/voices/grants do not. Gateway media/job retention is unchanged; active
uncertain media inputs are protected from expiry cleanup until reconciled.

Gateway `/health` is aggregate backend readiness, not an idle-only endpoint:
it correctly returns 503 while Qwen Image is deliberately stopped. Controlled
operator checks may inspect dispatch counts with read-only gateway SQLite
during that pause; require normal aggregate readiness before and after it.
Do not weaken production readiness or start work through a busy queue.

Inspect `journalctl --user -u plotloom-voice-lab.service` and private
`data/runs/<jobId>/runtime.log`. Diagnose the actual failed layer, not a generic
retry. Prior slot audio/publication survives failed regeneration. Observed
classifier evidence on a failed trial is intentionally retained, not success.

## Bounded qualification

`tools/qualify_workflow.py` makes exactly three creation and six reuse calls
on one new technical project and refuses an existing receipt. It records
host/process memory separately from Torch allocated memory. Keep its receipt
and verify service restoration separately. No new H3 calls, seed sweep or
human naturalness/acting approval is implied.

If a pair has one known failure and no reuse calls, an operator can use
`--existing-pair <projectId>` with a new receipt to spend only the third
creation call regenerating the failed slot. Other history shapes and
unknown/interrupted outcomes are rejected. The original failure receipt stays
intact; completion does not claim nine successful calls.

If exactly four neutral reuse calls have been spent, `--delivery-only
<projectId>` with a new receipt admits only the two remaining Index controls.
It checks the existing attempt shape and retains any known failure; it does
not replay failed neutral synthesis or declare a failed matrix complete.
These continuation modes require checking the cumulative call cap across
all retained receipts, not treating each invocation as a fresh allowance.

Closeout tools are deployed together under `runtime-inventory/closeout-tools/`
so their shared `qualify_workflow` and `verify_resident_reuse` imports resolve:

- `verify_resident_reuse.py`: one exact neutral probe, separate cold/post-H3
  receipt, unchanged failed evidence/Voice IDs and released-child assertions.
- `verify_published_h3.py`: one Ref2VA job consuming a published H3 derivative;
  hash/format/stream checks. `--resume-observation` requires a recorded accepted
  job and only observes it; it never sends another generation POST.
- `verify_idle_restart.py`: only an idle Lab restart, no generation, preserving
  project/trial state, published hashes and every managed WAV.

Keep `qualification_receipts.py` beside the four tools. It atomically claims
each fresh receipt with exclusive creation, mode 0600 and file/directory sync
before preflight. A failed preflight retains the claim. Stop the previous H3
observer before explicitly resuming observation; resume is never submission.
This per-operation claim is not a GPU reservation.

Each tool refuses an existing receipt for a fresh operation. Use new paths only
under an explicitly bounded allowance; that is not permission to repeat a
failed experiment. Never place private raw receipts in Git. The retained
closeout is already complete; these instructions do not ask a future maintainer
to replay it automatically.
