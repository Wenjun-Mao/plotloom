import { useState, type Dispatch, type SetStateAction } from "react";
import { clientJournalStorage, type RetainedJournalEntry } from "./clientJournalStorage";
import { RetainedDraftNotice } from "./RetainedDraftNotice";
import type { ProjectDraftQuiescence } from "./projectDraftQuiescence";

/** Enumeration is transport-only; each media owner validates its own basis. */
export function useRetainedMediaJournal<Entry extends { expectedDraftRevision?: number }>({ namespace, key, projectId, entries, setEntries, serverRevision, serverReady, quiescence, validate, basisMatches }: {
  namespace: string; key: string; projectId?: string; entries: Record<string, Entry>; setEntries: Dispatch<SetStateAction<Record<string, Entry>>>;
  serverRevision: number; serverReady: boolean; quiescence?: ProjectDraftQuiescence;
  validate: (entry: unknown) => entry is Entry; basisMatches: (entry: Entry) => boolean;
}) {
  const [, notify] = useState(0);
  const retained = clientJournalStorage.retainedEntries(namespace).filter(entry => entry.key === key);
  const discard = (selected: RetainedJournalEntry) => { clientJournalStorage.discardRetained(selected); notify(value => value + 1); };
  const resume = (selected: RetainedJournalEntry) => {
    if (!projectId || quiescence?.isClosing(projectId) || quiescence && !quiescence.canWrite(projectId)) throw new Error("当前项目不允许恢复编辑输入。");
    if (!serverReady) throw new Error("请先核实服务器版本。");
    const actual = clientJournalStorage.retainedEntries(namespace).find(entry => entry.namespace === selected.namespace && entry.key === selected.key && entry.serialized === selected.serialized);
    if (!actual || !validate(actual.value) || !basisMatches(actual.value) || actual.value.expectedDraftRevision !== serverRevision) throw new Error("来源或服务器草稿已变化；可复制输入，不能直接恢复。");
    if (entries[key]) throw new Error("请先保留或明确丢弃当前会话的输入。");
    const next = { ...entries, [key]: actual.value };
    clientJournalStorage.setItem(namespace, JSON.stringify(next));
    setEntries(next); discard(actual);
  };
  return {
    retained: retained.length > 0,
    notice: <RetainedDraftNotice entries={retained} onDiscard={discard} onResume={projectId && serverReady && (!quiescence || quiescence.canWrite(projectId) && !quiescence.isClosing(projectId)) ? resume : undefined} />,
    acknowledge(revision: number, matches: (entry: Entry) => boolean) {
      for (const selected of retained) if (validate(selected.value) && (selected.value.expectedDraftRevision === revision || selected.value.expectedDraftRevision === revision - 1) && basisMatches(selected.value) && matches(selected.value)) {
        try { clientJournalStorage.discardRetained(selected); } catch { /* A newer exact row remains inspectable. */ }
      }
      notify(value => value + 1);
    },
  };
}
