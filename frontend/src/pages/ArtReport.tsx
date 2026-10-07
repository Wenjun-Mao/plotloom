import { ProjectReportFrame } from "../components/ProjectReportFrame";
import { useEffect, useId, useRef, useState } from "react";
import { plotloomApi } from "../api";
import { Button } from "../components";
import "./ArtReport.css";

const reportCaveat = "静态阅读视图保留助手交付时的内容；提示词完整展开，复制、导出与报告内图片放大停用。若已编辑 art.json，请以当前 JSON 为准；阅读不会接受或修改提案。";

/** Readable review comes first; the immutable report never substitutes for edited JSON. */
export function ArtReport({ projectId, jobId }: { projectId: string; jobId: string }) {
  const [expanded, setExpanded] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const reportUrl = plotloomApi.artCandidateReportUrl(projectId, jobId);
  useEffect(() => {
    if (expanded && dialog.current && !dialog.current.open) dialog.current.showModal();
  }, [expanded]);
  const close = () => {
    setExpanded(false);
    opener.current?.focus();
  };
  return <>
    <details className="art-report-preview" open>
      <summary>查看美术设定报告（静态阅读）</summary>
      <div className="art-report-toolbar">
        <p>{reportCaveat}</p>
        <button ref={opener} type="button" className="button quiet" onClick={() => setExpanded(true)}>放大阅读报告</button>
      </div>
      <ProjectReportFrame sandbox="" title="美术设定报告静态预览" referrerPolicy="no-referrer" url={reportUrl} />
    </details>
    {expanded && <dialog ref={dialog} className="review-report-dialog" aria-labelledby={titleId} onClose={close}>
      <header><div><h2 id={titleId}>美术设定报告（静态阅读）</h2><p>{reportCaveat}</p></div><Button onClick={() => dialog.current?.close()}>关闭报告</Button></header>
      <ProjectReportFrame sandbox="" title="美术设定报告静态内容" referrerPolicy="no-referrer" url={reportUrl} />
    </dialog>}
  </>;
}
