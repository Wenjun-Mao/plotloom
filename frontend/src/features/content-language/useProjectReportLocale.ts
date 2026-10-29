import { useEffect, useState } from "react";
import { plotloomApi } from "../../api";
/** Supported project language only; interface language never selects report metadata. */
export function useProjectReportLocale(projectId: string, enabled: boolean) {
  const [read, setRead] = useState<{ projectId: string; locale: "zh" | "en" | null; error: string }>();
  useEffect(() => {
    setRead(undefined); if (!enabled) return;
    const abort = new AbortController();
    void plotloomApi.getProject(projectId, abort.signal).then(project => {
      if (abort.signal.aborted) return;
      const language = project.brief.language;
      setRead({ projectId, locale: language === "zh-CN" ? "zh" : language === "en-US" ? "en" : null,
        error: ["zh-CN", "en-US"].includes(language) ? "" : "此项目语言暂不支持新的生成候选检查，请核对项目简报。" });
    }).catch(() => { if (!abort.signal.aborted) setRead({ projectId, locale: null, error: "无法核实项目语言，请重新读取项目；不采用默认语言。" }); });
    return () => abort.abort();
  }, [projectId, enabled]);
  return read?.projectId === projectId ? read : { locale: null, error: "" };
}
