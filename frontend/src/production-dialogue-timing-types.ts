/** Trusted F5 receiving minima; report labels do not select spoken language. */
export interface FrozenF5DialogueTiming {
  version: "plotloom.f5-dialogue-timing.v1";
  scriptContentHash: string;
  language: string;
  profileVersion: string;
  contentHash: string;
  lines: {
    episode: number;
    sceneIndex: number;
    flowIndex: number;
    textHash: string;
    delivery: "measured" | "natural" | "brisk";
    minimumDurationUnits: number;
  }[];
}
