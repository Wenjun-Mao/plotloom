import { useEffect, useRef, useState } from "react";
import { Button, Spinner } from "../components";
import { plotloomApi } from "../api";
import { ProjectReportFrame } from "../components/ProjectReportFrame";
import { OutlineReader } from "./OutlineReader";
import { useAdoptionLabel, useAutopilot } from "../features/autopilot/AutopilotWorkspace";

export function OutlineReport({ url, outline, accepted }: { url?: string; outline: Record<string, unknown>; accepted?: { revision: number; contentHash: string } }) {
  const label = useAdoptionLabel()("outline", accepted?.revision, accepted?.contentHash);
  const owner = useAutopilot();
  const [expanded, setExpanded] = useState(false);
  const [report, setReport] = useState<"loading" | "html" | "structured">("structured");
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const title = accepted ? `${label}大纲 r${accepted.revision}` : "候选大纲";
  useEffect(() => {
    if (!expanded) return;
    dialog.current?.showModal();
    if (!url) { setReport("structured"); return; }
    const controller = new AbortController();
    setReport("loading");
    void plotloomApi.reportAvailable(url, controller.signal).then(available => {
      if (!controller.signal.aborted) setReport(available ? "html" : "structured");
    }).catch(() => { if (!controller.signal.aborted) setReport("structured"); });
    return () => controller.abort();
  }, [expanded, url]);
  const close = () => { setExpanded(false); opener.current?.focus(); };
  return <>
    <button ref={opener} type="button" className="button" onClick={() => setExpanded(true)}>{accepted ? `阅读${label}大纲` : "展开阅读大纲"}</button>
    {expanded && <dialog ref={dialog} className="review-report-dialog" aria-labelledby="outline-report-title" onClose={close}>
      <header><div><h2 id="outline-report-title">{title} · 只读阅读</h2><p>{accepted ? `阅读保留的${label}版本；阅读与关闭不会确认、接管、开始修订或修改内容。` : "阅读后关闭此窗口，再决定是否接受；关闭不会接受或修改内容。"}</p></div><Button onClick={() => dialog.current?.close()}>关闭阅读</Button></header>
      <p className="outline-report-caveat">报告中的“集数”是组织参数，不代表已确认的成片集数或路线时长。报告可切换视图，但其中的“导出 JSON”下载受隔离阅读限制，不会下载文件。</p>
      {owner?.run && <p role="note">原始上游报告按分集组织，合计可能包含互斥结局；节奏标签不构成人工评价。路线与素材仍以当前故事结构和最终整包审阅为准。</p>}
      {report === "loading" ? <Spinner label="正在读取报告" /> : report === "html" && url ? <ProjectReportFrame title={`${title}完整报告`} sandbox="allow-scripts" referrerPolicy="no-referrer" url={url} /> : <><p className="action-prerequisite">HTML 报告不可用，以下为此版本的结构化只读内容。</p><OutlineReader outline={outline} /></>}
    </dialog>}
  </>;
}
