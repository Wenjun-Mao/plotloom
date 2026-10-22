# Image specialist stopped before generation

Use only after a native assistant's exact assigned image attempt has genuinely
finished **blocked before ImageGen**, with no output and a successful original
executor pin. This procedure supplements that attempt; it does not replay it or
authorize generation from a conflicting/cancelled package.

1. Preserve the request, references, original pin and native final report.
   Verify the assigned assistant and exact completed attempt, then cancel the
   project job through its normal UI. Cancellation alone keeps the native slot.
2. Ask the **same assistant** to read this procedure and the exact retained
   package/pin, then truthfully publish `delivery/terminal.json` once using the
   schema below. Do not rerun preflight, regenerate, alter the package/pin,
   create `completion.json`, clean staging or reinterpret an uncertain failure.
   The marker's executor provenance describes the original pinned attempt,
   not the later acknowledgement's checkout. If any generation tool/background
   operation may still be active, generation began, output exists, evidence is
   missing or the declaration cannot be made truthfully, stop and preserve it.
3. Attend the supplementary acknowledgement through its native final. Record
   its exact task, completed turn ID, status revision and observed idle state.
4. Open **生成助手设置 → 核对生成前阻塞的终止声明**. Choose the correct project
   and request owner, read the validated marker, compare its task/request/hash
   and blocked reason to the native evidence, then enter the exact reviewed
   turn/revision/reviewer and explicitly attest the idle blocked verdict.
5. Settle once and verify the slot is released with a blocked tombstone and no
   candidate. Prepare a **distinct** corrected job at a clean committed revision;
   never resend the preserved failed job.

```json
{
  "schemaVersion": 1,
  "jobId": "<exact ij_ identity>",
  "requestHash": "<exact frozen request SHA-256>",
  "taskId": "<assigned native assistant UUID>",
  "outcome": "blocked",
  "phase": "before_generation",
  "generationStarted": false,
  "activeTools": false,
  "outputsProduced": false,
  "reason": "<truthful bounded cause and evidence>",
  "executorProvenance": {
    "codeRevision": "<original executor-pin value>",
    "skillVersion": "<original executor-pin value>",
    "skillHash": "<original executor-pin value>"
  }
}
```

The exchange uses confined no-follow reads and accepts only this marker, the
original pin and an optional **empty** outputs directory. Missing/invalid proof,
outputs, competing first-time ownership or changed review keeps the reservation.
The explicit operation persists operator attestations; it cannot verify native
queue-message identity automatically. Settings do not become a general lease
clearer. [ADR 0106](../adr/0106-reviewed-pre-generation-image-terminal-outcome.md)
defines this boundary. A retained identical reviewed proof can finish a crash
tombstone without touching a successor's lease; an ordinary idle/cancel cannot.

If a marker is rejected **before settlement** for a proven transcription error,
preserve its exact bytes/hash and the rejection outside the delivery inbox.
The coordinator may authorize the same worker to correct only that unadmitted
declaration. Re-read and review the new marker hash; stale previews cannot be
used. Never rewrite an admitted marker, original pin/package, or an uncertain
worker outcome. This corrects evidence, not reservation validation.
