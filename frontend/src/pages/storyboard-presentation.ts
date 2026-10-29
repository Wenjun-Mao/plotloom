/** Display projections only: preserve source enum identities and authored prose. */
const sizes: Record<string, string> = {
  extreme_wide: "大远景", wide: "全景", full: "全身", medium: "中景",
  close_up: "近景", extreme_close_up: "特写", insert: "插入镜头",
  EWS: "大远景", WS: "全景", FS: "全身", MS: "中景", MCU: "中近景",
  CU: "近景", ECU: "特写", LS: "远景", MLS: "中远景",
  "extreme-wide": "大远景", close: "特写", "extreme-close": "大特写",
};
const cameras: Record<string, string> = {
  static: "固定", fixed: "固定", pan: "摇镜", tilt: "俯仰",
  tracking: "跟拍", dolly: "移动", handheld: "手持", zoom: "变焦",
  push_in: "推进", pull_out: "拉远",
  "Static Shot": "固定", "Push In": "推", "Pull Out": "拉",
  "Zoom In": "变焦推", "Zoom Out": "变焦拉", "Pan Left": "左摇", "Pan Right": "右摇",
  "Truck Left": "左移", "Truck Right": "右移", "Tilt Up": "仰摇", "Tilt Down": "俯摇",
  "Pedestal Up": "升", "Pedestal Down": "降", "Arc Shot": "环绕", "Tracking Shot": "跟拍",
  "Shake Slightly": "轻微晃动", "Shake Strongly": "强烈晃动", POV: "主观视角",
  "Roll Clockwise": "顺旋", "Roll Counterclockwise": "逆旋",
};
export const shotSizeLabel = (value: unknown): string => sizes[String(value)] || String(value || "未提供");
export const cameraLabel = (value: unknown): string => cameras[String(value)] || String(value || "未提供");
