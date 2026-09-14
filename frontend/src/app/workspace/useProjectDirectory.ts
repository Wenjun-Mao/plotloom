import { useCallback, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import type { ProjectListItem } from "../../types";

/** Owns directory paging only; lifecycle mutations remain project-session actions. */
export function useProjectDirectory(describeError: (error: unknown) => string) {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [open, setOpen] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [error, setError] = useState("");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const epoch = useRef(0);
  const refresh = useCallback(async (includeArchived = showArchived, cursor?: string, append = false) => {
    const requestEpoch = ++epoch.current;
    setLoading(true);
    try {
      const response = await plotloomApi.listProjects(includeArchived, 50, cursor);
      if (requestEpoch !== epoch.current) return;
      setProjects((current) => append ? [...current, ...response.projects.filter((candidate) => !current.some((existing) => existing.id === candidate.id))] : response.projects);
      setNextCursor(response.nextCursor); setError("");
    } catch (requestError) {
      if (requestEpoch !== epoch.current) return;
      if (!append) { setProjects([]); setNextCursor(null); }
      setError(`无法读取项目目录：${describeError(requestError)}`);
    } finally { if (requestEpoch === epoch.current) setLoading(false); }
  }, [describeError, showArchived]);
  const openDirectory = useCallback(() => { setOpen(true); void refresh(); }, [refresh]);
  const loadMore = useCallback(() => { if (nextCursor && !loading) void refresh(showArchived, nextCursor, true); }, [loading, nextCursor, refresh, showArchived]);
  return { projects, open, setOpen, showArchived, setShowArchived, error, setError, nextCursor, loading, refresh, openDirectory, loadMore };
}
