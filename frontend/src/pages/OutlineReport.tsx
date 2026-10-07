import { useEffect, useRef, useState } from "react";
import { Button, Spinner } from "../components";
import { plotloomApi } from "../api";
import { ProjectReportFrame } from "../components/ProjectReportFrame";
import { OutlineReader } from "./OutlineReader";

export function OutlineReport({ url, outline, acceptedRevision }: { url?: string; outline: Record<string, unknown>; acceptedRevision?: number }) {
  const [expanded, setExpanded] = useState(false);
  const [report, setReport] = useState<"loading" | "html" | "structured">("structured");
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const title = acceptedRevision ? `已确认大纲 r${acceptedRevision}` : "候选大纲";
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
    <button ref={opener} type="button" className="button" onClick={() => setExpanded(true)}>{acceptedRevision ? "阅读已确认大纲" : "展开阅读大纲"}</button>
    {expanded && <dialog ref={dialog} className="review-report-dialog" aria-labelledby="outline-report-title" onClose={close}>
      <header><div><h2 id="outline-report-title">{title} · 只读阅读</h2><p>{acceptedRevision ? "阅读保留的已确认版本；关闭不会开始修订或修改内容。" : "阅读后关闭此窗口，再决定是否接受；关闭不会接受或修改内容。"}</p></div><Button onClick={() => dialog.current?.close()}>关闭阅读</Button></header>
      <p className="outline-report-caveat">报告中的“集数”是组织参数，不代表已确认的成片集数或路线时长。报告可切换视图，但其中的“导出 JSON”下载受隔离阅读限制，不会下载文件。</p>
      {report === "loading" ? <Spinner label="正在读取报告" /> : report === "html" && url ? <ProjectReportFrame title={`${title}完整报告`} sandbox="allow-scripts" referrerPolicy="no-referrer" url={url} /> : <><p className="action-prerequisite">HTML 报告不可用，以下为此版本的结构化只读内容。</p><OutlineReader outline={outline} /></>}
    </dialog>}
  </>;
}
