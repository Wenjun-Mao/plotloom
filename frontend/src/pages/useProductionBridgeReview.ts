import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { plotloomApi } from "../api";
import type { AcceptedReviewState } from "../accepted-review-state";
import type { ProductionBridgeIntentEntry, ProductionBridgeProposal, ProductionBridgeState } from "../types";
import { useProductionBridgeOperations } from "./useProductionBridgeOperations";

export interface BridgeReviewBasis {
  revision: number;
  contentHash: string;
  status: AcceptedReviewState["status"];
}
const proposalKey = (proposal: ProductionBridgeProposal | null | undefined) => proposal && `${proposal.revision}:${proposal.contentHash}`;
type Owner = { projectId: string; basis: string; alive: boolean; read: number };
type Read = { owner: Owner; epoch: number; value?: ProductionBridgeState; phase: "loading" | "ready" | "error" };

/** Server acknowledgement owns actions; the editor base owns unsaved text. */
export function useProductionBridgeReview(projectId: string, basis: BridgeReviewBasis, readOnly: boolean, onInstalled: (id: string) => Promise<void>) {
  const basisKey = JSON.stringify([basis.revision, basis.contentHash, basis.status]);
  const active = useRef<Owner>({ projectId, basis: basisKey, alive: true, read: 0 });
  if (active.current.projectId !== projectId || active.current.basis !== basisKey) {
    active.current = { projectId, basis: basisKey, alive: true, read: 0 };
  }
  const owner = active.current;
  const access = useRef(readOnly);
  access.current = readOnly;
  const owns = () => active.current === owner && owner.alive;
  const [read, setRead] = useState<Read>();
  const liveRead = useRef<Read | undefined>(undefined);
  const publishRead = (next: Read) => { liveRead.current = next; setRead(next); };
  const [editor, setEditor] = useState<{ projectId: string; proposal: ProductionBridgeProposal | null }>();
  const [intentEntries, setEntries] = useState<ProductionBridgeIntentEntry[]>([]);
  const entries = useRef(intentEntries);
  const baseline = useRef<ProductionBridgeIntentEntry[]>([]);
  const editorKey = useRef<string | null | undefined>(undefined);
  const editorStatus = useRef<ProductionBridgeState["status"] | undefined>(undefined);
  const editorIdentity = useRef({});
  const [draftConflict, setDraftConflict] = useState(false);
  const [presentationDirty, setDirty] = useState(false);
  const [presentationTouched, setTouched] = useState(false);
  const presentation = useRef({ dirty: false, touched: false });
  const [presentationEditorNonce, setNonce] = useState(0);
  const [error, setError] = useState("");
  const [canonicalReady, setCanonicalReady] = useState(true);
  // A semantic refresh retires response authority, never an admitted operation.
  const mutations = useProductionBridgeOperations();
  const epoch = mutations.epoch(projectId);
  const intentIsDirty = () => JSON.stringify(entries.current) !== JSON.stringify(baseline.current);
  const localEdits = () => intentIsDirty() || presentation.current.touched && presentation.current.dirty;
  const busy = mutations.busy(projectId);
  const acknowledged = read?.owner === owner && read.phase === "ready" && read.epoch === epoch;
  const state = read?.owner.projectId === projectId ? read.value : undefined;
  const proposal = editor?.projectId === projectId ? editor.proposal : undefined;
  const admitted = () => owns() && liveRead.current === read && read?.owner === owner
    && read.phase === "ready" && read.epoch === mutations.epoch(projectId) && !access.current && mutations.available(projectId);

  const adopt = (next: ProductionBridgeState, resetPresentation = false) => {
    if (!owns()) return;
    if (resetPresentation || editorKey.current !== proposalKey(next.proposal)) editorIdentity.current = {};
    editorKey.current = proposalKey(next.proposal);
    editorStatus.current = next.status;
    baseline.current = next.proposal?.intentPackage.entries ?? [];
    entries.current = baseline.current;
    setEntries(entries.current); setEditor({ projectId, proposal: next.proposal }); setDraftConflict(false);
    if (resetPresentation) {
      presentation.current = { dirty: false, touched: false };
      setDirty(false); setTouched(false); setNonce(value => value + 1);
    }
  };
  const receive = (next: ProductionBridgeState, explicit = false, resetPresentation = false) => {
    if (!owns()) return;
    publishRead({ owner, epoch, value: next, phase: "ready" }); setError("");
    if (explicit || !localEdits()) adopt(next, resetPresentation);
    else if (editorKey.current !== proposalKey(next.proposal) || editorStatus.current !== next.status) setDraftConflict(true);
  };
  const load = (signal?: AbortSignal) => {
    if (!owns() || mutations.epoch(projectId) !== epoch) return;
    const sequence = ++owner.read;
    const value = liveRead.current?.owner.projectId === projectId ? liveRead.current.value : undefined;
    publishRead({ owner, epoch, value, phase: "loading" });
    setError("");
    return plotloomApi.getProductionBridge(projectId, signal).then(next => {
      if (owns() && owner.read === sequence && mutations.epoch(projectId) === epoch) receive(next);
    }).catch(reason => {
      if (!owns() || owner.read !== sequence || mutations.epoch(projectId) !== epoch) return;
      publishRead({ owner, epoch, value: liveRead.current?.value, phase: "error" });
      setError(reason instanceof Error ? reason.message : "无法加载投产提案。");
    });
  };
  useLayoutEffect(() => {
    owner.alive = true;
    if (editor?.projectId !== projectId) {
      baseline.current = []; entries.current = []; editorKey.current = undefined;
      editorIdentity.current = {};
      presentation.current = { dirty: false, touched: false };
      setEditor(undefined); setEntries([]); setDirty(false); setTouched(false); setDraftConflict(false); setCanonicalReady(true);
    }
    const controller = new AbortController();
    // Re-read a changed basis even while the project's old mutation settles.
    // Read authority and pending-operation occupancy are independent.
    load(controller.signal);
    return () => { controller.abort(); owner.read += 1; owner.alive = false; };
  }, [projectId, basisKey, epoch]);

  useEffect(() => {
    const refresh = () => { if (owns() && !mutations.busy(projectId)) load(); };
    window.addEventListener("plotloom-specialists-changed", refresh);
    return () => window.removeEventListener("plotloom-specialists-changed", refresh);
  }, [owner, busy]);
  const job = state?.intentJob;
  useEffect(() => {
    if (!job || job.transport === "codex_native" || !["queued", "dispatched"].includes(job.status) || busy) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = () => {
      if (mutations.busy(projectId)) return;
      void load()?.finally(() => { if (!stopped && owns()) timer = setTimeout(poll, 1500); });
    };
    timer = setTimeout(poll, 1500);
    return () => { stopped = true; clearTimeout(timer); };
  }, [owner, job?.id, job?.status, busy]);

  const run = async (operation: () => Promise<ProductionBridgeState>, adoptResult = false, resetPresentation = false, refreshCanonical = false) => {
    if (!admitted()) return;
    const ticket = mutations.begin(projectId);
    if (!ticket) return;
    owner.read += 1; setError("");
    const current = () => owns() && mutations.owns(projectId, ticket);
    let installed = false;
    try {
      const next = await operation();
      if (!current()) return;
      receive(next, adoptResult, resetPresentation);
      if (refreshCanonical) {
        installed = next.installation?.status === "current" && next.status === "accepted";
        setCanonicalReady(false);
        await onInstalled(projectId);
        if (current()) setCanonicalReady(true);
      }
      return next;
    } catch (reason) {
      if (current()) setError(installed ? `投产已确认；请刷新服务器版本读取当前镜头：${reason instanceof Error ? reason.message : "读取失败"}` : reason instanceof Error ? reason.message : "投产提案操作失败。");
    } finally {
      // A read may supersede a response, but must not strand this operation's busy state.
      // An obsolete owner cannot publish its response; retire every read made
      // before that completion, then let the live mount read the actual result.
      mutations.finish(projectId, ticket, !owns());
    }
  };
  const editorOwnerKey = proposalKey(proposal), editorOwner = editorIdentity.current;
  const ownsEditor = () => owns() && editorIdentity.current === editorOwner && editorKey.current === editorOwnerKey;
  return {
    state, proposal, intentEntries, draftConflict, presentationDirty, presentationTouched, presentationEditorNonce,
    acknowledged, busy, canonicalReady, error, loadFailed: read?.owner === owner && read.phase === "error",
    intentDirty: editor?.projectId === projectId && intentIsDirty(), run, canAct: admitted,
    retryLoad: () => { if (owns() && !mutations.busy(projectId)) load(); },
    discard: () => { if (admitted() && state) adopt(state, true); },
    setIntentEntries(update: (current: ProductionBridgeIntentEntry[]) => ProductionBridgeIntentEntry[]) {
      if (!ownsEditor() || !admitted()) return;
      entries.current = update(entries.current); setEntries(entries.current);
    },
    setPresentationDirty(value: boolean) { if (ownsEditor()) { presentation.current.dirty = value; setDirty(value); } },
    presentationEdited() { if (ownsEditor()) { presentation.current.touched = true; setTouched(true); } },
    setError(message: string) { if (owns()) setError(message); },
  };
}
