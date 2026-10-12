import { useEffect, useId, useRef, useState } from "react";
import { Button } from "../components";
import { ProjectReportFrame } from "./ProjectReportFrame";
import "./StaticReportReader.css";

const reportCopy = {
  script: {
    subject: "剧本",
    explanation: "场次与台词已完整展开；报告内的折叠、复制和导出按钮已停用。",
  },
  storyboard: {
    subject: "分镜",
    explanation: "分段与提示词已完整展开；报告内的复制、导出和图片放大功能已停用。",
  },
} as const;

type Props = { kind: keyof typeof reportCopy; url: string; expandable?: boolean; active?: boolean };

/** A different frozen report must never inherit the previous report's open dialog. */
export function StaticReportReader(props: Props) {
  return <ReportReader key={props.url} {...props} />;
}

/** App-owned reading guidance never changes the original report or its isolation. */
function ReportReader({ kind, url, expandable = false, active = true }: Props) {
  const { subject, explanation } = reportCopy[kind];
  const [expanded, setExpanded] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!active) { setExpanded(false); return; }
    if (expanded && dialog.current && !dialog.current.open) dialog.current.showModal();
  }, [active, expanded]);
  const close = () => { setExpanded(false); if (active) opener.current?.focus(); };
  return <>
    <details className={expandable ? "static-report-reader expandable" : "static-report-reader"}>
    <summary>阅读原始{subject}报告（只读）</summary>
    {expandable && <div className="static-report-toolbar">
      <p>可放大为独立阅读窗口；关闭不会确认或修改{subject}方案。</p>
      <button ref={opener} type="button" className="button quiet" onClick={() => setExpanded(true)}>放大阅读报告</button>
    </div>}
    <p className="action-prerequisite">原始报告的只读展示：{explanation}原始报告独立保留，不会随当前{subject}修改。</p>
    <p className="action-prerequisite">互动故事中，报告按内容段落列出各分支；“集”不一定是一条完整播放路线。所有分支的时长相加，不等于一次从开场到结局的播放时长。</p>
    <ProjectReportFrame sandbox="" referrerPolicy="no-referrer" title={`原始${subject}交付报告（只读）`} className="source-outline-report" url={url} />
    </details>
    {expanded && active && <dialog ref={dialog} className="review-report-dialog" aria-labelledby={titleId} onClose={close}>
      <header><div><h2 id={titleId}>原始{subject}报告（只读）</h2><p>原始报告独立保留。阅读或关闭不会确认、修改方案或生成媒体；所有分支时长之和不等于一次完整播放的时长。</p></div><Button onClick={() => dialog.current?.close()}>关闭报告</Button></header>
      <ProjectReportFrame sandbox="" referrerPolicy="no-referrer" title={`原始${subject}交付报告（放大只读）`} url={url} />
    </dialog>}
  </>;
}
