import { createContext, useContext } from "react";
import type { BranchOperationOwner } from "./branchOperationOwner";

export const BranchOperationContext = createContext<BranchOperationOwner | null>(null);
export function useBranchOperationOwner() {
  const owner = useContext(BranchOperationContext);
  if (!owner) throw new Error("Branch suggestions require the workspace operation owner");
  return owner;
}
