import { Button } from "../../components";
import { useGraphWorkbench } from "./GraphWorkbenchContext";

export function GraphPreviewRecovery() {
  const owner = useGraphWorkbench();
  if (!owner.previewConflict) return null;
  return <p className="notice warning" role="alert">旧结构预览已失效；当前内容仍保留。重新读取只检查服务器版本，不覆盖未发送字段。处理已有冲突后，请重新准备预览。
    <Button disabled={owner.busy} onClick={() => void owner.refresh()}>重新读取图草稿</Button>
  </p>;
}
