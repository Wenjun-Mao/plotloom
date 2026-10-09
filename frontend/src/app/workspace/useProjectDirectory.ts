import { useCallback, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { ProjectListItem } from "../../types";

/** Owns directory paging only; lifecycle mutations remain project-session actions. */
export function useProjectDirectory(describeError: (error: unknown) => string) {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [open, setOpen] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [error, setError] = useState("");
  const [readError, setReadError] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const epoch = useRef(0);
  const lastRequest = useRef({ includeArchived: false, cursor: undefined as string | undefined, append: false });
  const displayedFilter = useRef<boolean | undefined>(undefined);
  const refresh = useCallback(async (includeArchived = showArchived, cursor?: string, append = false) => {
    const requestEpoch = ++epoch.current;
    lastRequest.current = { includeArchived, cursor, append };
    if (displayedFilter.current !== includeArchived) { setProjects([]); setNextCursor(null); }
    setLoading(true); setReadError("");
    try {
      const response = await plotloomApi.listProjects(includeArchived, 50, cursor);
      if (requestEpoch !== epoch.current) return;
      setProjects((current) => append ? [...current, ...response.projects.filter((candidate) => !current.some((existing) => existing.id === candidate.id))] : response.projects);
      displayedFilter.current = includeArchived;
      setNextCursor(response.nextCursor); setReadError("");
    } catch (requestError) {
      if (requestEpoch !== epoch.current) return;
      setReadError(`无法读取项目目录：${describeError(requestError)}`);
    } finally { if (requestEpoch === epoch.current) setLoading(false); }
  }, [describeError, showArchived]);
  const openDirectory = useCallback(async () => { setOpen(true); await refresh(); }, [refresh]);
  const closeDirectory = useCallback(() => { epoch.current++; setLoading(false); setOpen(false); }, []);
  const retry = useCallback(() => { const request = lastRequest.current; return refresh(request.includeArchived, request.cursor, request.append); }, [refresh]);
  const loadMore = useCallback(() => { if (nextCursor && !loading) void refresh(showArchived, nextCursor, true); }, [loading, nextCursor, refresh, showArchived]);
  return { projects, open, setOpen, showArchived, setShowArchived, error, setError, readError, retry, nextCursor, loading, refresh, openDirectory, closeDirectory, loadMore };
}
