export type ArtRenderStyle = "live-action" | "realistic" | "ghibli";

type ArtPreset = {
  label: string;
  render: string;
  surface: string;
  negative: string;
  tags: string[];
};

type CastPreset = {
  label: string;
  render: string;
  surface: string;
  lighting: string;
  negative: string;
  tags: string[];
};

export interface ArtPresetRenderContract {
  version: 1;
  style: ArtRenderStyle;
  authorDirection: string | null;
  preset: ArtPreset;
  adapterHash: string;
}

export interface CastPresetRenderContract {
  version: 1;
  style: ArtRenderStyle;
  authorDirection: string | null;
  preset: CastPreset;
  implementationHash: string;
}

export interface SavedBriefRenderContract {
  version: 1;
  authority: "saved_brief";
  stageInstructionContract: string;
  direction: string | null;
  emptyDirectionRule: string | null;
  validatorHashes: Record<string, string>;
  contentHash: string;
}

export type ArtRenderContract = ArtPresetRenderContract | SavedBriefRenderContract;
export type CastRenderContract = CastPresetRenderContract | SavedBriefRenderContract;
export type RenderStyleContract = ArtRenderContract | CastRenderContract;

export interface RenderStylePresentation {
  authority: "preset" | "saved_brief";
  label: string;
  details: string | null;
}

/** Project the stage-owned frozen contract without inventing a preset fallback. */
export function renderStylePresentation(contract: RenderStyleContract | null | undefined): RenderStylePresentation | null {
  if (!contract) return null;
  if (!("authority" in contract)) {
    return {
      authority: "preset",
      label: contract.preset.label,
      details: contract.authorDirection ? `项目视觉要求：${contract.authorDirection}` : null,
    };
  }

  if (!Object.prototype.hasOwnProperty.call(contract, "direction")
    || (contract.direction !== null && typeof contract.direction !== "string")) {
    return { authority: "saved_brief", label: "项目简报视觉方向", details: "项目简报视觉方向字段缺失。" };
  }
  if (contract.direction !== null && contract.direction !== "") {
    return { authority: "saved_brief", label: "项目简报视觉方向", details: `项目视觉要求：${contract.direction}` };
  }
  if (contract.emptyDirectionRule) {
    return { authority: "saved_brief", label: "项目简报视觉方向", details: contract.emptyDirectionRule };
  }
  return {
    authority: "saved_brief",
    label: "项目简报视觉方向",
    details: contract.direction === null ? "项目简报未设置视觉方向。" : "项目简报视觉方向为空。",
  };
}
