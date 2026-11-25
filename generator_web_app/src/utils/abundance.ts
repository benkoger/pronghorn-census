// Abundance estimate display rules and number formatting
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

import type { AbundanceEstimate } from "@/models";

// The count, its interval, the density and the abundance are withheld during the detection
// check and until the estimate's figures_from tiles are reviewed: before that, one animal
// found in a tile the proposal thought empty moves the count by hundreds and the interval by
// thousands of percent, which is the estimator being honest about a tiny sample, not a result
// worth reading.
export function figuresShown(e: AbundanceEstimate | null | undefined): boolean {
  if (!e || e.phase === "detection check") return false;
  return e.figures_from === null || e.n_reviewed >= e.figures_from;
}

// Why the figures are withheld, or "" when they are shown
export function maskedNote(e: AbundanceEstimate | null | undefined): string {
  if (!e || figuresShown(e)) return "";
  const share = `${Math.round(e.show_fraction * 100)}%`;
  const from = e.figures_from === null ? "" : ` (${e.figures_from.toLocaleString()} tiles)`;
  return `Statistics masked until ${share} of tiles reviewed${from}`;
}

export function whole(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : Math.round(value).toLocaleString();
}

export function decimal(value: number | null | undefined, digits: number): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

export function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${(100 * value).toFixed(1)}%`;
}
