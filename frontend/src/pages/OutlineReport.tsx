import { useEffect, useRef, useState } from "react";
import { Button } from "../components";
import { OutlineReader } from "./OutlineReader";

export function OutlineReport({ url, outline }: { url?: string; outline: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (expanded && dialog.current && !dialog.current.open) dialog.current.showModal();
  }, [expanded]);
  const close = () => {
    setExpanded(false);
    opener.current?.focus();
  };
  return <>
    <button ref={opener} type="button" className="button" onClick={() => setExpanded(true)}>展开阅读大纲</button>
    {expanded && <dialog ref={dialog} className="outline-report-dialog" aria-labelledby="outline-report-title" onClose={close}>
      <header><div><h2 id="outline-report-title">候选大纲 · 只读预览</h2><p>阅读后关闭此窗口，再决定是否接受；关闭不会接受或修改内容。</p></div><Button onClick={() => dialog.current?.close()}>关闭阅读</Button></header>
      <p className="outline-report-caveat">报告沿用上游模板：“集数”是其组织参数，不代表已确认的成片集数或路线时长。报告内可切换视图；文件下载仍受限制。</p>
      {url ? <iframe title="完整候选大纲报告" sandbox="allow-scripts" referrerPolicy="no-referrer" src={url} /> : <OutlineReader outline={outline} />}
    </dialog>}
  </>;
}
