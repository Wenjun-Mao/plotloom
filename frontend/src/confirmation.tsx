import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Button } from "./components";
import "./confirmation.css";

type Confirmation = {
  title: string;
  message: string;
  details: string;
  action: () => void | Promise<void>;
};

/** Domain owners freeze the payload; this owner handles explicit consent and focus. */
export function useConfirmation(identity: string, disabled = false) {
  const [pending, setPending] = useState<(Confirmation & { identity: string }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const executing = useRef(false);
  const current = useRef({ identity, disabled });
  current.current = { identity, disabled };
  const valid = pending?.identity === identity && !disabled;
  useEffect(() => { setPending(null); setError(""); }, [identity, disabled]);
  const cancel = () => { if (!executing.current) setPending(null); };
  const commitConfirmation = async () => {
    if (!pending || executing.current || current.current.disabled || pending.identity !== current.current.identity) return;
    executing.current = true; setBusy(true); setError("");
    try { await pending.action(); setPending(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作未完成，请重新核对后再确认。"); }
    finally { executing.current = false; setBusy(false); }
  };
  return {
    requestConfirmation: (request: Confirmation) => {
      if (current.current.disabled || executing.current) return;
      setError(""); setPending({ ...request, identity });
    },
    confirmation: valid && pending ? <ConfirmationDialog key={identity} {...pending} busy={busy} error={error} onCancel={cancel} onConfirm={() => void commitConfirmation()} /> : null,
  };
}

function ConfirmationDialog({ title, message, details, busy, error, onCancel, onConfirm }: Confirmation & {
  busy: boolean; error: string; onCancel: () => void; onConfirm: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const id = useId();
  useEffect(() => {
    const element = dialog.current!;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element.showModal();
    cancelButton.current?.focus();
    return () => { element.close(); if (trigger?.isConnected) trigger.focus(); };
  }, []);
  return createPortal(<dialog ref={dialog} className="confirmation-dialog" role="alertdialog" aria-modal="true" aria-labelledby={`${id}-title`} aria-describedby={`${id}-message`}
    onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }}>
    <h2 id={`${id}-title`}>{title}</h2>
    <p id={`${id}-message`}>{message}</p>
    <pre>{details}</pre>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">正在处理，请勿重复确认。</p>}
    <div className="button-row"><button type="button" className="button" ref={cancelButton} disabled={busy} onClick={onCancel}>取消</button><Button variant="danger" disabled={busy} onClick={onConfirm}>确认{title}</Button></div>
  </dialog>, document.body);
}
