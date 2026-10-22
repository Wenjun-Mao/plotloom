import { useState } from "react";
import { Button } from "../../components";
import { useConfirmation } from "../../confirmation";
import { autopilotApi } from "./api";
import type { AutopilotRun } from "./contracts";
import { CorrectionCount, correctionCount } from "./CorrectionCount";

export function ContinuationAction({ projectId, revision, run, disabled, execute }: {
  projectId: string; revision: number; run: AutopilotRun; disabled: boolean;
  execute: (operation: () => Promise<AutopilotRun>, refresh: boolean) => Promise<void>;
}) {
  const [message, setMessage] = useState("");
  const [reading, setReading] = useState(false);
  const [corrections, setCorrections] = useState(String(run.policy.textCorrectionLimit ?? 1));
  const correctionLimit = correctionCount(corrections);
  const confirmation = useConfirmation(`${projectId}:${run.id}:${run.revision}`, disabled);
  const inspect = async () => {
    setReading(true); setMessage("");
    try {
      const context = await autopilotApi.continuationContext(projectId);
      if (context.runId !== run.id || context.runRevision !== run.revision) {
        setMessage("运行状态已变化，请等待重新读取后再核对。"); return;
      }
      if (!context.eligible) { setMessage(context.blockers.join("；")); return; }
      confirmation.requestConfirmation({ title: "继续剩余素材", message: "保留已完成素材，为尚未准备的工作授权新的自动运行。",
        details: `继承 ${context.inheritedOperations} 项已采用工作。项目累计 ${context.lifetimeJobs} 个任务、${context.lifetimeImages} 项图片。\n旧任务、执行版本、交付和审阅事实保持原始来源；结果不明的原任务不会重复发送。仍需完整人工审阅。`,
        action: () => execute(() => autopilotApi.continueMaterial(projectId, {
          expectedBriefRevision: revision, expectedRunId: context.runId, expectedRunRevision: context.runRevision,
          expectedMaterialClosure: context.materialClosure, styleAuthority: run.policy.styleAuthority || "preset",
          renderStyle: run.policy.renderStyle ?? undefined, artRenderStyle: run.policy.artRenderStyle ?? undefined,
          maxImages: run.policy.maxImages, maxJobs: run.policy.maxJobs, textCorrectionLimit: correctionLimit,
        }), true),
      });
    } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setReading(false); }
  };
  return <><CorrectionCount value={corrections} onChange={setCorrections} disabled={disabled || reading} /><Button disabled={disabled || reading || correctionLimit === undefined} onClick={() => void inspect()}>{reading ? "正在核对继续条件…" : "继续剩余素材"}</Button>
    {message && <p role="status">{message}</p>}{confirmation.confirmation}</>;
}
