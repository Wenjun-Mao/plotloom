import { useCallback, useEffect, useRef, useState } from "react";

type Activation = { projectId: string; active: boolean; refreshToken: unknown; epoch: number };

/** Retain editor buffers, but revalidate server-owned review authority on entry. */
export function useReviewActivation({ projectId, active, refreshToken, load }: {
  projectId: string;
  active: boolean;
  refreshToken: unknown;
  load: (isCurrent: () => boolean) => Promise<boolean>;
}) {
  const activation = useRef<Activation>({ projectId, active: false, refreshToken, epoch: 0 });
  const previous = activation.current;
  if (previous.projectId !== projectId || previous.active !== active || previous.refreshToken !== refreshToken) {
    activation.current = { projectId, active, refreshToken, epoch: previous.epoch + 1 };
  }
  const epoch = activation.current.epoch;
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [settled, setSettled] = useState({ epoch: -1, success: false });
  const checkSequence = useRef(0);
  const recheck = useCallback(async () => {
    const sequence = ++checkSequence.current;
    const session = activation.current;
    const isCurrent = () => mounted.current && activation.current === session && sequence === checkSequence.current;
    setSettled({ epoch: -1, success: false });
    const success = await load(isCurrent);
    if (isCurrent()) {
      setSettled({ epoch: session.epoch, success });
    }
  }, [load]);
  useEffect(() => {
    if (active) void recheck();
  }, [active, epoch, recheck]);
  const checking = active && settled.epoch !== epoch;
  const failed = active && !checking && !settled.success;
  return { checking, failed, recheck };
}
