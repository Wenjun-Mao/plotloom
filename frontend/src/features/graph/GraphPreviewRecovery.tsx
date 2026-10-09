import { Button } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";

export function GraphPreviewRecovery() {
  const owner = useGraphWorkbench();
  if (owner.readStatus !== "ready") return <p className="notice warning" role={owner.readStatus === "failed" ? "alert" : "status"}>
    {owner.readStatus === "loading" ? "正在读取共享图草稿，请稍候。" : owner.readError}
    {owner.draft ? " 当前显示上次读取的内容，未发送输入仍保留；读取成功前暂停编辑与保存。" : " 读取成功后才能显示和编辑图草稿。"}
    <Button disabled={owner.readStatus === "loading" || owner.busy} onClick={() => void owner.refresh()}>重新读取图草稿</Button>
  </p>;
  if (!owner.previewConflict) return null;
  return <p className="notice warning" role="alert">旧结构预览已失效；当前内容仍保留。重新读取只检查服务器版本，不覆盖未发送字段。处理已有冲突后，请重新准备预览。
    <Button disabled={owner.busy} onClick={() => void owner.refresh()}>重新读取图草稿</Button>
  </p>;
}
