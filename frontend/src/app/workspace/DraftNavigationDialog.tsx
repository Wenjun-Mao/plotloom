import { Button } from "../../components";

export type DraftNavigationIntent = "navigate" | "archive";

const intentCopy: Record<DraftNavigationIntent, {
  title: string; action: string; help: string; save: string; discard: string;
}> = {
  navigate: {
    title: "编辑输入尚未保留", action: "请先保留输入再离开", save: "重试保留并离开", discard: "丢弃本机未同步输入并离开",
    help: "重试只保留编辑输入，不会应用或确认内容。也可取消并复制输入。明确丢弃只移除本机未同步输入；已确认内容和服务器草稿保留。",
  },
  archive: {
    title: "归档前保存当前修改？", action: "即将归档当前项目", save: "保存并归档", discard: "丢弃本页修改并归档",
    help: "保存会按当前阶段的保存方式写入项目，不代表确认内容或批准。丢弃只移除本标签页尚未保存的修改，已保存的草稿仍保留。归档后项目为只读，可在项目目录中恢复。",
  },

};

export function DraftNavigationDialog({ intent, busyMessage, onSave, onDiscard, onCancel }: {
  intent: DraftNavigationIntent; busyMessage?: string; onSave: () => void; onDiscard: () => void; onCancel: () => void;
}) {
  const copy = intentCopy[intent];
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-navigation-title">
    <button className="modal-backdrop" aria-label="继续编辑" disabled={Boolean(busyMessage)} onClick={onCancel} />
    <section className="modal-card compact">
      <header><div><span>未保存的草稿</span><h2 id="draft-navigation-title">{copy.title}</h2></div></header>
      <div className="modal-body"><div className="notice warning"><strong>{copy.action}</strong><span>{copy.help}</span></div>{busyMessage && <p role="status">{busyMessage}</p>}</div>
      <footer>
        <Button variant="quiet" disabled={Boolean(busyMessage)} onClick={onCancel}>取消</Button>
        <Button variant="danger" disabled={Boolean(busyMessage)} onClick={onDiscard}>{copy.discard}</Button>
        <Button variant="primary" disabled={Boolean(busyMessage)} onClick={onSave}>{copy.save}</Button>
      </footer>
    </section>
  </div>;
}
