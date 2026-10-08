/** Chinese interface time, in the reader's local timezone. Exact timestamps remain data. */
export function formatUiTimestamp(value: string): string {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}
