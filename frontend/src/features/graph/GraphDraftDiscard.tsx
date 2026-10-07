import { useEffect, useRef, useState } from "react";
import { Button } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";

export function GraphDraftDiscard({ disabled }: { disabled: boolean }) {
  const owner = useGraphWorkbench(), [open, setOpen] = useState(false), dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (open && dialog.current && !dialog.current.open) dialog.current.showModal(); }, [open]);
  return <>
    <Button variant="quiet" disabled={disabled} onClick={() => setOpen(true)}>放弃图草稿…</Button>
    {open && <dialog ref={dialog} className="graph-command-dialog" aria-label="放弃当前图草稿" onCancel={event => { event.preventDefault(); if (!owner.busy) setOpen(false); }}>
      <h2>放弃当前图草稿</h2><p>删除当前未接受的图修改与本次撤销历史，重新读取已确认内容或规划种子。已确认路线、场景、镜头与媒体保留。</p>
      {owner.error && <p role="alert">{owner.error}</p>}
      <Button disabled={owner.busy} onClick={() => setOpen(false)}>保留草稿</Button>
      <Button variant="danger" busy={owner.busy} onClick={() => void owner.discard().then(discarded => { if (discarded) setOpen(false); })}>明确放弃图草稿</Button>
    </dialog>}
  </>;
}
