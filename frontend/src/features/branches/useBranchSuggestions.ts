import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { plotloomApi } from "../../api";
import type { BranchTaskState, SectionMap } from "../../types";
import { useBranchOperationOwner } from "./BranchOperationContext";
import type { BranchOperationOwner } from "./branchOperationOwner";

const message = (reason: unknown) => reason instanceof Error ? reason.message : "剧情分支建议读取失败，请重试。";
interface ReadIdentity { owner: BranchOperationOwner; projectId: string; basis: string; version: number; retry: number }
interface ReadSnapshot { identity: ReadIdentity; value?: BranchTaskState; error: string }
const matches = (left: ReadIdentity, right: ReadIdentity) => left.owner === right.owner && left.projectId === right.projectId
  && left.basis === right.basis && left.version === right.version && left.retry === right.retry;

export function useBranchSuggestions(projectId: string, basis: string, dirty: boolean, onAdopt: (draft: SectionMap) => void) {
  const owner = useBranchOperationOwner();
  const operation = useSyncExternalStore(
    useCallback(listener => owner.subscribe(projectId, listener), [owner, projectId]),
    useCallback(() => owner.snapshot(projectId), [owner, projectId]),
  );
  const [read, setRead] = useState<ReadSnapshot>();
  const [adopting, setAdopting] = useState(false);
  const [retry, setRetry] = useState(0);
  const epoch = useRef(0);
  const dirtyNow = useRef(dirty); dirtyNow.current = dirty;
  const identity = { owner, projectId, basis, version: operation.version, retry };
  const currentIdentity = useRef(identity); currentIdentity.current = identity;
  // Authority changes during render, before the passive refresh effect runs.
  const acceptedRead = read && matches(read.identity, identity) ? read : undefined;
  const state = acceptedRead?.value;
  const readError = acceptedRead?.error ?? "";
  useEffect(() => {
    const ticket = ++epoch.current;
    const identity = { owner, projectId, basis, version: operation.version, retry };
    setRead(undefined); setAdopting(false);
    const current = () => ticket === epoch.current && matches(identity, currentIdentity.current)
      && owner.snapshot(projectId).version === identity.version;
    void plotloomApi.getBranchSuggestions(projectId).then(value => {
      if (!current()) return;
      setRead({ identity, value, error: "" }); owner.acknowledgeRead(projectId, identity.version);
    }).catch(reason => { if (current()) setRead({ identity, error: message(reason) }); });
    return () => { epoch.current++; };
  }, [owner, projectId, basis, operation.version, retry]);
  const busy = operation.pending || operation.unconfirmed || !state && !readError || adopting;
  const refresh = () => setRetry(value => value + 1);
  const adopt = async () => {
    if (busy || dirty || !state?.candidate || !acceptedRead || !matches(acceptedRead.identity, currentIdentity.current)
      || owner.snapshot(projectId).version !== acceptedRead.identity.version || owner.snapshot(projectId).pending) return;
    const ticket = epoch.current;
    const identity = acceptedRead.identity;
    const current = () => ticket === epoch.current && matches(identity, currentIdentity.current)
      && owner.snapshot(projectId).version === identity.version && !owner.snapshot(projectId).pending;
    setAdopting(true); setRead({ identity, value: state, error: "" });
    try {
      const draft = await plotloomApi.getBranchDraft(projectId, state.candidate.jobId);
      if (!current()) return;
      if (dirtyNow.current) setRead({ identity, value: state, error: "读取建议期间已有本地修改，已保留当前草稿。请保存或放弃后重试。" });
      else onAdopt(draft);
    } catch (reason) { if (current()) setRead({ identity, value: state, error: message(reason) }); }
    finally { if (current()) setAdopting(false); }
  };
  return { state, busy, mutationPending: operation.pending, error: readError || operation.error, refresh, adopt,
    retryDisabled: operation.pending || adopting || !state && !readError,
    mutate: (command: () => Promise<BranchTaskState>) => {
      if (busy || !acceptedRead?.value || !matches(acceptedRead.identity, currentIdentity.current)
        || owner.snapshot(projectId).version !== acceptedRead.identity.version) return Promise.resolve(false);
      return owner.run(projectId, command);
    } };
}
