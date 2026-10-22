import { useEffect, useState } from "react";

export type TimingFacts = { observedAt: string; createdAt: string; terminal: boolean; milestone?: string | null; milestoneAt?: string | null; completedAt?: string | null };
export function elapsedLabel(milliseconds: number) {
  const seconds = Math.max(0, Math.floor(milliseconds / 1000));
  return seconds < 60 ? `${seconds} 秒` : seconds < 3600 ? `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒` : `${Math.floor(seconds / 3600)} 小时 ${Math.floor(seconds % 3600 / 60)} 分`;
}

export function WorkflowTiming({ timing, kind, verified = true }: { timing?: TimingFacts | null; kind: "run" | "batch"; verified?: boolean }) {
  const [clock, setClock] = useState({ observedAt: timing?.observedAt, started: performance.now(), delta: 0 });
  useEffect(() => {
    const started = performance.now();
    setClock({ observedAt: timing?.observedAt, started, delta: 0 });
    if (!timing || timing.terminal || !verified) return;
    const timer = setInterval(() => setClock({ observedAt: timing.observedAt, started, delta: Math.max(0, performance.now() - started) }), 1000);
    return () => clearInterval(timer);
  }, [timing?.observedAt, timing?.createdAt, timing?.terminal, verified]);
  if (!timing) return null;
  const created = Date.parse(timing.createdAt); const observed = Date.parse(timing.observedAt);
  if (!Number.isFinite(created) || !Number.isFinite(observed)) return <p>时间事实尚未记录。</p>;
  const delta = clock.observedAt === timing.observedAt ? clock.delta : 0;
  return <div className="workflow-timing">
    <p>{timing.terminal ? timing.completedAt ? `已完成 · ${new Date(timing.completedAt).toLocaleString()}` : `创建于 ${new Date(created).toLocaleString()}`
      : `${kind === "run" ? "距启动已过" : "清单创建后"} ${elapsedLabel(Math.max(0, observed - created) + delta)}${kind === "run" ? "（含排队、暂停和等待）" : "（含准备方向与等待开始）"}`}</p>
    {timing.milestone && timing.milestoneAt && <p>{timing.milestone} · {new Date(timing.milestoneAt).toLocaleString()}</p>}
    {!verified && <p>状态待核实 · 上次成功读取 {new Date(observed).toLocaleString()}</p>}
    {!timing.terminal && <p>时间递增不表示工作进程仍在运行。</p>}
  </div>;
}
