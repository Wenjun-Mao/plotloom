import { useCallback, useEffect, useRef, useState } from "react";
import type { MutableRefObject, ReactNode } from "react";
import { ApiError, plotloomApi } from "../../api";
import { acknowledgeDraft, discardDraft, getDraft, findRevisionConflict, type DraftRecord } from "../../draft-registry";
import type { AuthoringDraft, SectionMap, SourceOutlineReviewState, WorkspaceProject } from "../../types";
import { GraphWorkbenchContext } from "./GraphWorkbenchContext";
import { graphDraftKey, readGraphDraft } from "./contracts";
import type { GraphAuthoringDraft, GraphCommand, GraphCommandPreview, GraphMapDraft, GraphWorkbenchState } from "./contracts";
import { completeMap } from "../../pages/sourceStructureModel";
import { readGraphSelection, storeGraphSelection } from "./graphSelection";

interface Input {
  children: ReactNode;
  project: WorkspaceProject;
  enabled: boolean;
  readOnly: boolean;
  restoredPayload?: unknown;
  restoredNonce: number;
  serverDrafts: MutableRefObject<Map<string, AuthoringDraft>>;
  remember: (payload: GraphAuthoringDraft) => void;
  flush: () => Promise<boolean>;
  clearDraftWorkflow: () => void;
  canonicalChanged: () => Promise<void>;
  revisionConflict: (record: DraftRecord) => void;
  readAdmission?: (projectId: string | undefined, allowed: boolean) => void;
}
const sameAuthoredContent = (left: GraphAuthoringDraft, right: GraphAuthoringDraft) => JSON.stringify({ mapping: left.mapping, fieldBuffers: left.fieldBuffers, detachedEndpoints: left.detachedEndpoints })
  === JSON.stringify({ mapping: right.mapping, fieldBuffers: right.fieldBuffers, detachedEndpoints: right.detachedEndpoints });

export function GraphWorkbenchProvider(input: Input) {
  const current = useRef(input); current.current = input;
  const [state, setState] = useState<GraphWorkbenchState | null>(null);
  const [readStatus, setReadStatus] = useState<"loading" | "ready" | "failed">("loading");
  const [readError, setReadError] = useState("");
  const readAuthority = useRef({ projectId: input.project.id, ready: false, epoch: 0 });
  const publishRead = (status: "loading" | "ready" | "failed", editable = false) => {
    readAuthority.current = { projectId: current.current.project.id, ready: status === "ready" && editable, epoch: readAuthority.current.epoch + 1 };
    setReadStatus(status);
    current.current.readAdmission?.(current.current.project.id, readAuthority.current.ready);
  };
  const hasReadAuthority = () => current.current.enabled && readAuthority.current.projectId === current.current.project.id && readAuthority.current.ready;
  const [draft, setDraft] = useState<GraphAuthoringDraft | null>(null);
  const liveDraft = useRef(draft); liveDraft.current = draft;
  const [selectedNodeId, setSelection] = useState<string | null>(null);
  const selectionVersion = useRef(0), liveSelection = useRef<string | null>(null);
  const displaySelection = (identity: string | null) => {
    liveSelection.current = identity;
    setSelection(identity);
    if (current.current.project.id) storeGraphSelection(current.current.project.id, identity);
  };
  const selectNode = (identity: string | null) => { selectionVersion.current++; displaySelection(identity); };
  const [busy, setBusy] = useState(false);
  const busyRef = useRef<symbol | null>(null);
  const [error, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState<unknown>();
  const setError = (message: string, details?: unknown) => { setErrorMessage(message); setErrorDetails(details); };
  const [preview, setPreview] = useState<GraphCommandPreview | null>(null);
  const livePreview = useRef<GraphCommandPreview | null>(null);
  const [previewConflict, setPreviewConflict] = useState(false);
  const conflictRef = useRef(false);
  const displayPreview = (next: GraphCommandPreview | null) => { livePreview.current = next; setPreview(next); };
  const displayConflict = (next: boolean) => { conflictRef.current = next; setPreviewConflict(next); };
  const invalidatePreview = () => { displayPreview(null); previewBasis.current = null; displayConflict(true); };
  const previewBasis = useRef<GraphAuthoringDraft | null>(null);
  const history = useRef<Array<{ before: GraphAuthoringDraft; after: GraphAuthoringDraft }>>([]);
  const [historyCount, setHistoryCount] = useState(0);
  const readGeneration = useRef(0);
  const owner = useRef({ projectId: input.project.id, epoch: 0 });
  const confirmedReadBasis = useRef<{ owner: typeof owner.current; receipt: AuthoringDraft; payload: GraphAuthoringDraft } | null>(null);
  if (owner.current.projectId !== input.project.id) owner.current = { projectId: input.project.id, epoch: owner.current.epoch + 1 };
  const resetHistory = () => { history.current = []; setHistoryCount(0); displayPreview(null); previewBasis.current = null; confirmedReadBasis.current = null; };

  const acceptReceipt = (receipt: AuthoringDraft, authored = false, selectionBasis = selectionVersion.current, keepSelection = false) => {
    const source = current.current;
    const payload = readGraphDraft(receipt.payload);
    source.serverDrafts.current.set(graphDraftKey(receipt.projectId), receipt);
    if (authored) {
      source.remember(payload);
      const local = getDraft(source.project, "story_graph");
      if (local) acknowledgeDraft(source.project, "story_graph", local.localRevision, receipt.draftRevision);
    }
    const laterSelection = (keepSelection || selectionVersion.current !== selectionBasis) && payload.mapping.topology.nodes.some(node => node.id === liveSelection.current);
    setDraft(payload); liveDraft.current = payload;
    displaySelection(laterSelection ? liveSelection.current : payload.selectedNodeId);
    setState(existing => existing ? { ...existing, draft: receipt } : existing);
  };

  const refresh = useCallback(async () => {
    const source = current.current, operation = owner.current;
    if (!source.project.id || !source.enabled) return;
    const generation = ++readGeneration.current;
    publishRead("loading"); setReadError("");
    const knownReceipt = source.serverDrafts.current.get(graphDraftKey(source.project.id));
    try {
      const next = await plotloomApi.getGraphWorkbench(source.project.id);
      if (operation !== owner.current || generation !== readGeneration.current) return;
      const acknowledged = source.serverDrafts.current.get(graphDraftKey(source.project.id));
      if (acknowledged !== knownReceipt && (!next.draft || next.draft.baseCanonicalRevision === acknowledged?.baseCanonicalRevision
        && next.draft.draftRevision < acknowledged.draftRevision)) {
        publishRead("failed"); setReadError("读取结果早于刚保存的图草稿，请重新读取确认当前版本。"); return;
      }
      const previousBase = findRevisionConflict(source.project, "story_graph");
      if (previousBase) source.revisionConflict(previousBase);
      const unsent = getDraft(source.project, "story_graph");
      const unsentConflict = Boolean(unsent && unsent.serverDraftRevision !== (next.draft?.draftRevision ?? 0));
      // A read is not permission to rebase unsent typing. Keep its receipt/CAS
      // basis until the existing explicit conflict workflow resolves it.
      if (unsentConflict) source.revisionConflict(unsent!);
      else if (next.draft) source.serverDrafts.current.set(graphDraftKey(source.project.id), next.draft);
      else source.serverDrafts.current.delete(graphDraftKey(source.project.id));
      const payload = unsent ? readGraphDraft(unsent.payload) : next.draft ? readGraphDraft(next.draft.payload) : next.initialPayload;
      const confirmation = confirmedReadBasis.current;
      const ownConfirmation = confirmation?.owner === operation && !unsent && next.draft
        && next.draft.draftRevision === confirmation.receipt.draftRevision + 1
        && next.draft.baseCanonicalRevision === confirmation.receipt.baseCanonicalRevision
        && payload?.bindingHash === next.bindingHash && sameAuthoredContent(payload, confirmation.payload);
      if (confirmation?.owner === operation) {
        if (ownConfirmation) {
          // Confirmation changes context, not authored content or canonical base.
          // Only a current, receipt-matched read may rebase draft-only Undo.
          history.current = history.current.map(entry => ({
            before: { ...entry.before, bindingHash: next.bindingHash },
            after: { ...entry.after, bindingHash: next.bindingHash },
          }));
          confirmedReadBasis.current = null;
        } else resetHistory();
      }
      setState(next);
      publishRead("ready", !next.readOnlyReason);
      // A background read cannot erase newer typing. The server receipt still
      // updates currentness so explicit recovery/conflict handling remains visible.
      if (!ownConfirmation && !unsent && liveDraft.current?.bindingHash !== payload?.bindingHash) resetHistory();
      if (!unsent || !liveDraft.current) {
        const preferred = liveDraft.current ? liveSelection.current : readGraphSelection(source.project.id);
        const retainedSelection = payload?.mapping.topology.nodes.some(node => node.id === preferred);
        const removedSelection = liveDraft.current && preferred && !retainedSelection;
        setDraft(payload); liveDraft.current = payload;
        displaySelection(retainedSelection ? preferred : payload?.selectedNodeId ?? null);
        setError(removedSelection ? "原选中节点已不在当前服务器图草稿中，已显示其有效选中节点；未发送内容不会被覆盖。" : "");
      } else {
        setError("");
      }
      displayConflict(unsentConflict);
    } catch (reason) { if (operation === owner.current && generation === readGeneration.current) {
      publishRead("failed");
      setReadError(`无法读取共享图草稿。${reason instanceof Error ? reason.message : ""}`);
    } }
  }, []);

  useEffect(() => {
    setState(null); setDraft(null); liveDraft.current = null; liveSelection.current = null; setSelection(null); setError(""); resetHistory();
    publishRead("loading"); setReadError("");
    busyRef.current = null; setBusy(false);
    displayConflict(false);
    void refresh();
    return () => {
      owner.current = { ...owner.current, epoch: owner.current.epoch + 1 };
      busyRef.current = null;
    };
  }, [input.project.id, input.enabled, refresh]);
  useEffect(() => { void refresh(); }, [input.project.revision, input.project.stageRevisions.story_graph, input.project.stageRevisions.story_bible, refresh]);
  useEffect(() => {
    if (input.restoredPayload === undefined) return;
    try {
      const payload = readGraphDraft(input.restoredPayload);
      setDraft(payload); liveDraft.current = payload; selectNode(payload.selectedNodeId); resetHistory();
      // Recovery changes the trusted context without necessarily changing a
      // canonical revision. Re-read its full authority before further edits.
      void refresh();
    }
    catch (reason) { setError(String(reason)); }
  }, [input.restoredNonce]);

  const stale = Boolean(draft && state && draft.bindingHash !== state.bindingHash);
  const writable = () => hasReadAuthority() && !current.current.readOnly && !busyRef.current && !stale;
  const changeMapping = (mapping: GraphMapDraft) => {
    if (!writable() || !liveDraft.current) return;
    const next = { ...liveDraft.current, mapping, selectedNodeId };
    setDraft(next); liveDraft.current = next; current.current.remember(next); displayPreview(null);
  };
  const changeDraft = (next: GraphAuthoringDraft) => {
    if (!writable()) return;
    setDraft(next); liveDraft.current = next; current.current.remember(next); displayPreview(null);
  };
  const adoptMapping = (mapping: SectionMap) => {
    if (!writable() || !state) return;
    const seed = liveDraft.current?.mapping.seedTopology;
    if (seed && JSON.stringify(seed) !== JSON.stringify(mapping.seedTopology)) {
      setError("建议与当前草稿的原始种子不同，请先明确处理当前草稿。"); return;
    }
    const next: GraphAuthoringDraft = { bindingHash: state.bindingHash, mapping: structuredClone(mapping), rowHints: {}, selectedNodeId: mapping.topology.startNodeId, detachedEndpoints: {}, fieldBuffers: {} };
    setDraft(next); liveDraft.current = next; selectNode(next.selectedNodeId); current.current.remember(next); resetHistory();
  };
  const acknowledge = async () => {
    const source = current.current, payload = liveDraft.current, operation = owner.current;
    const readBasis = readAuthority.current;
    if (!hasReadAuthority() || !source.project.id || !payload || source.readOnly || stale) throw new Error("请先读取当前图草稿并处理其版本状态。");
    // The existing autosave owner drains every newer local revision before a
    // command can bind its preview to one acknowledged server buffer.
    if (!source.serverDrafts.current.has(graphDraftKey(source.project.id)) && !getDraft(source.project, "story_graph")) source.remember(payload);
    if (!await source.flush()) throw new Error("图草稿未保存，操作已停止；请处理保存错误后重试。");
    // Every command uses the same acknowledgement boundary. A completed save
    // still belongs to its original project, never to a subsequently opened one.
    if (operation !== owner.current) throw new Error("项目已切换，原图操作已停止。");
    if (readBasis !== readAuthority.current || !hasReadAuthority()) throw new Error("图草稿读取状态已变化，请重新读取后重试操作。");
    const receipt = source.serverDrafts.current.get(graphDraftKey(source.project.id));
    if (!receipt) throw new Error("没有当前图草稿的服务器回执。");
    return receipt;
  };
  const perform = async <T,>(operation: () => Promise<T>): Promise<T | undefined> => {
    if (busyRef.current || !hasReadAuthority() || current.current.readOnly) return;
    const basis = owner.current, lock = Symbol("graph operation"); busyRef.current = lock; setBusy(true); setError("");
    try { return await operation(); }
    catch (reason) { if (basis === owner.current) setError(reason instanceof Error ? reason.message : String(reason), reason instanceof ApiError ? reason.details : undefined); }
    finally { if (busyRef.current === lock) { busyRef.current = null; if (basis === owner.current) setBusy(false); } }
  };
  const saveDraft = async () => (await perform(async () => { await acknowledge(); return true; })) === true;
  const prepareCommand = async (command: GraphCommand) => {
    if (conflictRef.current) return false;
    return (await perform(async () => {
      const basis = owner.current, receipt = await acknowledge();
      const result = await plotloomApi.previewGraphCommand(current.current.project.id!, { expectedDraftRevision: receipt.draftRevision, command });
      if (basis !== owner.current) return false;
      previewBasis.current = { ...readGraphDraft(receipt.payload), selectedNodeId };
      displayPreview(result);
      return true;
    })) === true;
  };
  const applyPreview = async () => {
    const admittedPreview = livePreview.current;
    if (!admittedPreview || !previewBasis.current || conflictRef.current) return;
    await perform(async () => {
      const basis = owner.current, previous = previewBasis.current!, selectionBasis = selectionVersion.current;
      const currentReceipt = await acknowledge();
      if (currentReceipt.draftRevision !== admittedPreview.draftRevision) { invalidatePreview(); throw new Error("预览后图草稿已变化；当前修改仍保留，请重新读取后准备新预览。"); }
      let saved: AuthoringDraft;
      try {
        saved = await plotloomApi.applyGraphCommand(current.current.project.id!, { expectedDraftRevision: admittedPreview.draftRevision, command: admittedPreview.command, previewHash: admittedPreview.previewHash });
      } catch (reason) {
        if (basis === owner.current && reason instanceof ApiError && reason.status === 409
          && reason.details && typeof reason.details === "object" && "code" in reason.details && reason.details.code === "revision_conflict") {
          invalidatePreview();
          throw new Error("服务器图草稿已变化，旧预览已失效；当前文字、未发送字段与所选节点仍保留。请先重新读取图草稿，处理已有冲突后再准备新预览。");
        }
        throw reason;
      }
      if (basis !== owner.current) return;
      const after = readGraphDraft(saved.payload);
      history.current.push({ before: previous, after });
      if (history.current.length > 40) history.current.shift();
      // Creation/reuse explicitly select their node. Other commands must not
      // revive the older selection stored with the last authored draft receipt.
      setHistoryCount(history.current.length); acceptReceipt(saved, true, selectionBasis, !["add", "insert", "reuse"].includes(admittedPreview.command.operation)); displayPreview(null); previewBasis.current = null;
    });
  };
  const undo = async () => {
    const entry = history.current.at(-1);
    if (!entry || !liveDraft.current) return;
    await perform(async () => {
      if (!sameAuthoredContent(entry.after, liveDraft.current!)) throw new Error("结构操作后已有内容修改；请保留并处理这些修改，再撤销该结构操作。");
      const basis = owner.current, selectionBasis = selectionVersion.current, receipt = await acknowledge(), source = current.current;
      const saved = await plotloomApi.saveAuthoringDraft(source.project.id!, {
        editorScope: "story_graph", entityId: "root", baseCanonicalRevision: receipt.baseCanonicalRevision,
        expectedDraftRevision: receipt.draftRevision, payload: entry.before as unknown as Record<string, unknown>,
      });
      if (basis !== owner.current) return;
      history.current.pop(); setHistoryCount(history.current.length); acceptReceipt(saved, true, selectionBasis); displayPreview(null);
    });
  };
  const recover = async () => {
    if (!state?.draft) return;
    await perform(async () => {
      const basis = owner.current, selectionBasis = selectionVersion.current;
      if (getDraft(current.current.project, "story_graph")) throw new Error("还有未发送内容，请先从冲突窗口保留或导出；恢复不能覆盖本地输入。");
      const receipt = await plotloomApi.recoverGraphDraft(current.current.project.id!, { expectedDraftRevision: state.draft!.draftRevision, expectedBindingHash: state.bindingHash, payload: null });
      if (basis !== owner.current) return;
      acceptReceipt(receipt, true, selectionBasis); resetHistory(); await refresh();
    });
  };
  const discard = async () => {
    return (await perform(async () => {
      const basis = owner.current, receipt = await acknowledge(), source = current.current;
      const consumed = await plotloomApi.discardAuthoringDraft(source.project.id!, {
        editorScope: "story_graph", entityId: "root", expectedDraftRevision: receipt.draftRevision,
      });
      if (consumed !== receipt.draftRevision) throw new Error("放弃草稿没有收到精确回执；当前内容仍保留，请重新读取确认。");
      if (basis !== owner.current) return;
      readGeneration.current++;
      source.serverDrafts.current.delete(graphDraftKey(source.project.id!));
      discardDraft(source.project, "story_graph"); source.clearDraftWorkflow();
      setDraft(null); liveDraft.current = null; resetHistory(); await refresh(); return true;
    })) === true;
  };
  const confirmMapping = async (source: SourceOutlineReviewState) => (await perform(async () => {
    if (!source.source || !source.acceptedOutline) throw new Error("请先确认当前来源与大纲。");
    const basis = owner.current, receipt = await acknowledge();
    const payload = readGraphDraft(receipt.payload);
    if (!completeMap(payload.mapping) || Object.keys(payload.fieldBuffers).length) throw new Error("图草稿有待填写、待连接或未提交的字段，请先完成再确认。");
    await plotloomApi.saveSectionMap(current.current.project.id!, {
      expectedGraphDraftRevision: receipt.draftRevision, expectedSectionMapRevision: source.acceptedSectionMap?.revision ?? 0,
      expectedSourceRevision: source.source.revision, expectedOutlineRevision: source.acceptedOutline.revision,
      expectedOutlineContentHash: source.acceptedOutline.contentHash, mapping: payload.mapping as SectionMap,
    });
    if (basis !== owner.current) return false;
    confirmedReadBasis.current = { owner: basis, receipt, payload };
    await refresh();
    // Confirmation has succeeded even if its follow-up read failed or was
    // superseded. Read failure owns recovery and must not relabel that write.
    return true;
  })) === true;
  const installMapping = async (source: SourceOutlineReviewState) => (await perform(async () => {
    const map = source.acceptedSectionMap, material = source.source, outline = source.acceptedOutline;
    if (!map || !material || !outline) throw new Error("请先明确确认当前图内容。");
    const basis = owner.current, receipt = await acknowledge(), projectId = current.current.project.id!;
    await plotloomApi.installSectionMapGraph(projectId, { expectedSourceRevision: material.revision,
      expectedSourceContentHash: material.contentHash, expectedOutlineRevision: outline.revision,
      expectedOutlineContentHash: outline.contentHash, expectedSectionMapRevision: map.revision,
      expectedSectionMapContentHash: map.contentHash, expectedGraphRevision: receipt.baseCanonicalRevision,
      expectedGraphDraftRevision: receipt.draftRevision });
    if (basis !== owner.current) return false;
    readGeneration.current++;
    current.current.serverDrafts.current.delete(graphDraftKey(projectId)); discardDraft(current.current.project, "story_graph");
    current.current.clearDraftWorkflow(); resetHistory(); await current.current.canonicalChanged(); await refresh(); return true;
  })) === true;

  return <GraphWorkbenchContext.Provider value={{ state, readStatus, readError, draft, selectedNodeId, busy, error, errorDetails, stale,
    preview, previewConflict, canUndo: historyCount > 0, refresh, selectNode, changeMapping, changeDraft, adoptMapping, saveDraft,
    confirmMapping, installMapping, prepareCommand, cancelPreview: () => { displayPreview(null); previewBasis.current = null; },
    applyPreview, undo, recover, discard }}>{input.children}</GraphWorkbenchContext.Provider>;
}
