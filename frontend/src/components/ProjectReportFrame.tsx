import { useEffect, useState } from "react";
import type { IframeHTMLAttributes } from "react";
import { plotloomApi } from "../api";
import type { ProjectReadTicket } from "../project-read-admission";

type Props = Omit<IframeHTMLAttributes<HTMLIFrameElement>, "src" | "srcDoc"> & { url: string };

/** Admit each real navigation before mounting, preserving server CSP and URL. */
export function ProjectReportFrame({ url, onLoad, onError, ...attributes }: Props) {
  const [navigation, setNavigation] = useState<{ url: string; ticket: ProjectReadTicket }>();
  useEffect(() => {
    const controller = new AbortController();
    let ticket: ProjectReadTicket | undefined;
    setNavigation(undefined);
    void plotloomApi.admitReportRead(url, controller.signal).then(admitted => {
      if (controller.signal.aborted) { admitted.cancel(); return; }
      ticket = admitted; setNavigation({ url, ticket });
    }).catch(() => { /* Invalidated or paused owners never mount a late frame. */ });
    return () => { controller.abort(); ticket?.cancel(); };
  }, [url]);
  if (!navigation || navigation.url !== url) return <p role="status">正在读取报告…</p>;
  return <iframe key={url} {...attributes} src={url}
    onLoad={event => { navigation.ticket.complete(); onLoad?.(event); }}
    onError={event => { navigation.ticket.cancel(); onError?.(event); }} />;
}
