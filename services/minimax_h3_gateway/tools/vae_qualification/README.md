# Isolated H3 VAE qualification

Operator tooling for the [approved October 6 plan](../../../../docs/roadmap/2026-10-06-h3-vae-qualification.md).
Not a gateway backend, production plugin or precision policy. Never mount these
custom nodes in the production Comfy container.

- `contract.py`: fixed arms, input/hash guards, twelve-cell ceiling, actual
  compute/parameter/kernel validation. Audio stays at baseline BF16 execution.
  Raw parameter dtypes describe dynamic/offloaded checkpoint storage; they need
  not all equal the compute dtype. The guard admits only the known checkpoint
  storage plus the selected execution dtype, while actual compute remains strict.
- `freeze.py`: inspect inputs first; freeze exact bytes, three graphs and model
  hashes. Copy the existing Voice Lab `tools/memory_trace.py` to the private
  experiment root before freezing. Use the gateway's packaged CPU dependencies
  for freezing; Spark system Python lacks Pydantic, Lab control Python lacks PIL.
- `maintenance.py`: idle admission/grant proof before stopping the managed
  control services; recheck afterwards. Preserve the original stopped Comfy
  container as the exact restoration authority. Never cancel racing work.
- `__init__.py`: isolated video-only loader and one small component smoke per
  arm. Retains the audio loader, reload dtype binding and core math unchanged.
- `observer.py`: kernel counters and encoder/decoder pre-hooks prove successful
  dispatch and post-transfer compute precision. CPU entry tensors are staging,
  not GPU execution. Outer VAE synchronized wall time includes model management;
  inner CUDA-event time includes stage transfer/compute, not pure kernel-only
  inference. `load_models_gpu` timing includes any load/offload it performs.
- `run_arm.py`: exclusive file lock, one smoke then three sole submissions,
  cached-compute refusal, uncertainty-first receipt and full media decode.
- `review.py`: offline, hash-checked twelve-clip review page, three fixed-frame
  samples per clip and timing/kernel/memory summary. It submits no GPU requests.
  Copy the frozen `cases.json`/receipt and hash-matching clips named
  `<arm>_<case>.mp4` into the local private root, with retained images in
  `input/`, then run `python review.py --root <local-root>`.

Use a fresh private root, read-only model/input mounts, separate per-arm user and
output directories, the exact approved image ID and loopback port 8193. Preserve
the baseline global BF16 flags in all arms; add only `--fast fp16_accumulation`
for C/D. Point `H3_QUALIFICATION_ARM` and `H3_QUALIFICATION_EVENTS` at the arm and
its private JSONL. Launch the pinned Comfy `main.py` directly to avoid package
installation from an entrypoint that resolves custom-node requirements.

After HTTP/node/precision startup checks, run on Spark:

```sh
python3 <root>/harness/run_arm.py --root <root> --arm A
```

No retry switch. Existing, stopped or ambiguous cells cannot be replayed. Unknown
inference keeps its container until reconciled. Once idle, stop the experiment
container, start the unchanged baseline, verify queue/health and voice/take
hashes, then reopen managed dispatch. A completed screen is not adoption.

For the owner-authorized October 6 resumption, the operator created exactly one
fresh root linked by path/hash to the unchanged stopped precursor. Its original
zero full-call claims were proven, cases copied byte-for-byte, and all original
input/model hashes retained. The fresh receipt has the same twelve-call cap;
do not invoke `freeze.py` again or create another root to replace a failed cell.
The later INT8 continuation inherits all nine completed ABC full claims and ABC
smokes, leaving only the three D cells. It preserves the first D component and
parent stopped receipt, after a D-only FP32-storage guard correction supported
by the official checkpoint header and observed FP16 CUDA compute. The owner's
general testing permission covers the sixth total component workload (fresh D);
the full ceiling is not reset and no extra full clip is allowed.
