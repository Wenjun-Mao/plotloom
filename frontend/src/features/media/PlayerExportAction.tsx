import { useEffect, useRef, useState } from "react";
import { Button } from "../../components";

/** A download acts on fresh server authority; preview flags are only guidance. */
export function PlayerExportAction({ projectId, disabled }: { projectId: string; disabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const owner = useRef(0);
  useEffect(() => { owner.current++; setBusy(false); setMessage(""); return () => { owner.current++; }; }, [projectId]);
  async function download() {
    const captured = owner.current;
    setBusy(true); setMessage("");
    try {
      const presentation = await fetch(`/api/v2/projects/${encodeURIComponent(projectId)}/player-export-presentation`);
      const body = await presentation.json() as unknown;
      if (!presentation.ok) throw new Error("请先安装当前制作交接，再导出独立游戏。");
      if (captured !== owner.current) return;
      const response = await fetch(`/api/v2/projects/${encodeURIComponent(projectId)}/player-exports`, {
        method: "POST", headers: { "Content-Type": "application/json", Accept: "application/zip" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { message?: string } | null;
        throw new Error(body?.message || `导出失败（HTTP ${response.status}）`);
      }
      const content = await response.blob();
      if (captured !== owner.current) return;
      const url = URL.createObjectURL(content);
      const link = document.createElement("a");
      link.href = url; link.download = `plotloom-${projectId}.zip`;
      document.body.append(link); link.click(); link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      setMessage("游戏已导出。完整解压后打开 index.html 即可游玩。");
    } catch (error) {
      if (captured === owner.current) setMessage(error instanceof Error ? error.message : "导出失败。");
    } finally { if (captured === owner.current) setBusy(false); }
  }
  return <div className="player-export-action">
    <Button variant="default" disabled={disabled || busy} onClick={() => void download()}>{busy ? "正在打包…" : "导出独立 H5 游戏"}</Button>
    {message && <p role="status">{message}</p>}
  </div>;
}
