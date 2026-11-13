// Abundance estimation domain models
// Author: Owen Martin
// ---------------------------------------------------------------------------------------------------------------------------

export type AbundanceStatus =
  | "not prepared"
  | "waiting for proposal"
  | "measuring"
  | "waiting for refit"
  | "target met"
  | "exhausted"
  | "finished";

// detection check: the first tiles, drawn where the detector found animals; the reviewer
//   confirms the detector's boxes
// full review: every tile after that, drawn across the survey; the reviewer looks for both
//   false positives and false negatives
export type AbundancePhase = "detection check" | "full review";

export interface AbundanceEstimate {
  // null while the survey has no measurement (status 'not prepared')
  active_measurement_id: number | null;
  uuid: string | null;
  survey_id: number;
  status: AbundanceStatus;
  n_units: number;
  n_reviewed: number;
  n_pending: number;
  generation: number | null;
  count: number | null;
  std_error: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  relative_ci: number | null;
  target: number | null;
  area_m2: number | null;
  density_per_km2: number | null;
  density_ci_lower_per_km2: number | null;
  density_ci_upper_per_km2: number | null;
  phase: AbundancePhase | null;
  // Tiles of the detection check; null when the measurement has none
  check_units: number | null;
  // Reviewed tiles before the stop rule considers the interval
  min_samples: number | null;
  // Reviewed tiles before the count and interval are shown: that minimum, or 1% of the tiles
  figures_from: number | null;
  // The share of tiles behind figures_from
  show_fraction: number;
}

export interface AbundancePreparationStep {
  key: "detections" | "footprints" | "tiles" | "measurement" | "proposal";
  label: string;
  done: boolean;
  detail: string;
}

export interface AbundancePreparation {
  status: string | null;
  images: number;
  images_with_predictions: number;
  images_with_footprints: number;
  images_with_metadata: number;
  tiles: number;
  images_with_tiles: number;
  tiles_reviewed: number;
  measurement: Record<string, unknown> | null;
  label: string | null;
  detector: { name: string; uuid: string; boxes: number; images: number } | null;
  proposal: {
    generations: number;
    n_units: number;
    expected_total: number;
    first_alpha: number | null;
    alpha: number | null;
    n_labels: number;
  } | null;
  proposal_generations: number;
  steps: AbundancePreparationStep[];
  ready: boolean;
}
