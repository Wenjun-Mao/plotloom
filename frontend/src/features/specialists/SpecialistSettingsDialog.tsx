import { useEffect, useState } from "react";
import { Button, ErrorNotice } from "../../components";
import { specialistsApi, type SpecialistSettings } from "./api";

export function SpecialistSettingsDialog({ onClose }: { onClose: () => void }) {
  const [settings, setSettings] = useState<SpecialistSettings>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => { let active = true; void specialistsApi.settings().then(value => { if (active) setSettings(value); }).catch(reason => { if (active) setError(String(reason)); }); return () => { active = false; }; }, []);
  const save = async () => {
    if (!settings) return;
    setBusy(true); setError(""); setSaved(false);
    try { setSettings(await specialistsApi.save(settings)); setSaved(true); window.dispatchEvent(new Event("plotloom-specialists-changed")); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "保存失败。"); }
    finally { setBusy(false); }
  };
  const check = async (project: string, stage: import("./api").SpecialistStage, job: string) => {
    setBusy(true); setError("");
    try { await specialistsApi.check(project, stage, job); setSettings(await specialistsApi.settings()); window.dispatchEvent(new Event("plotloom-specialists-changed")); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "检查失败。"); }
    finally { setBusy(false); }
  };
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="specialist-settings-title">
    <button className="modal-backdrop" aria-label="关闭生成助手设置" onClick={onClose} />
    <section className="modal-card compact"><header><h2 id="specialist-settings-title">生成助手设置</h2></header>
      <div className="modal-body"><p>设置保存在当前服务器所在的电脑上，不写入项目。保存设置不会发送任务。</p>
        <p>填写已有 Codex 聊天的 ID，不是聊天标题。两个助手使用不同的聊天，每个助手一次处理一项任务。</p>
        {settings && (["text", "image"] as const).map(role => <fieldset key={role} disabled={busy || settings.busy}><legend>{role === "text" ? "文字创作助手" : "图像生成助手"}</legend>
          <p>{role === "text" ? "处理大纲、角色设定、美术设定、剧本与分镜。" : "处理角色、场景、道具和镜头图片。"}</p>
          <label><span>显示名称</span><input value={settings[role].name} onChange={event => { setSaved(false); setSettings({ ...settings, [role]: { ...settings[role], name: event.target.value } }); }} /></label>
          <label><span>聊天 ID</span><input placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" value={settings[role].taskId || ""} onChange={event => { setSaved(false); setSettings({ ...settings, [role]: { ...settings[role], taskId: event.target.value || null } }); }} /></label>
        </fieldset>)}
        {settings?.busy && <p role="status">助手还有未完成的任务，暂时不能更改设置。请先检查任务结果。</p>}
        {settings?.activeTasks?.map(task => <div key={task.jobId}><small>{task.stage || "图像"} · {task.jobId}</small>{task.projectId && task.stage ? <Button disabled={busy} onClick={() => void check(task.projectId!, task.stage!, task.jobId)}>检查此任务的结果</Button> : <p>请在图像提案中检查交付。</p>}</div>)}
        {saved && <p role="status">设置已保存，即刻生效。聊天是否可接收任务将在发送时确认。</p>}
        {error && <ErrorNotice message={error} />}
      </div><footer><Button onClick={onClose}>关闭</Button><Button variant="primary" disabled={!settings || busy || settings.busy} onClick={() => void save()}>保存助手设置</Button></footer>
    </section>
  </div>;
}
