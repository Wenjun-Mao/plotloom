import { createElement, type ReactNode } from "react";
import { createProjectDraftQuiescence } from "../src/features/authoring/projectDraftQuiescence";
import { createBranchOperationOwner } from "../src/features/branches/branchOperationOwner";
import { BranchOperationContext } from "../src/features/branches/BranchOperationContext";

export const branchOperationFixture = () => createBranchOperationOwner(createProjectDraftQuiescence());
export const branchOperationView = (owner: ReturnType<typeof branchOperationFixture>, children: ReactNode) =>
  createElement(BranchOperationContext.Provider, { value: owner, children });
