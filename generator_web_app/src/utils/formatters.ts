// Display formatting utilities
// Author: Michael B. Lance / Antigravity
// ---------------------------------------------------------------------------------------------------------------------------

export function formatDate(
  dateVal: string | Date | undefined | null,
  options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
  },
): string {
  if (!dateVal) return "—";
  const d = typeof dateVal === "string" ? new Date(dateVal) : dateVal;
  return isNaN(d.getTime()) ? "—" : d.toLocaleDateString(undefined, options);
}

export function formatDateTime(
  dateVal: string | Date | undefined | null,
): string {
  return formatDate(dateVal, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatNumber(num: number | undefined | null): string {
  if (num === undefined || num === null || isNaN(num)) return "—";
  return num.toLocaleString();
}
